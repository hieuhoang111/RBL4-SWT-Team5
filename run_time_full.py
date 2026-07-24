"""
Role 1 — LLM Ranking Agent (Generic Branch)
Chấm điểm ranking [0,1] cho từng mutant Java bằng Qwen 3.6 qua Ollama.
Script được thiết lập để chạy cho nhiều project liên tiếp nhau cho cả chế độ pilot và full.
"""

import csv
import json
import time
import random
import requests
from pathlib import Path

# ============================================================
# 0. CONFIGURATION
# ============================================================
MODEL = "qwen3.6:latest"
OLLAMA_URL = "http://localhost:11434/api/generate"
TEMPERATURE = 0
TOP_P = 1.0
NUM_CTX = 4096
NUM_PREDICT = 64
RANDOM_SEED = 42

# ------------------------------------------------------------
# THIẾT LẬP CHẠY:
# ------------------------------------------------------------
# Khai báo danh sách các project muốn chạy. Script sẽ chạy lần lượt từng project.
PROJECTS = ["Time"]   
RUN_MODE = "full"         # "pilot" hoặc "full"

# File ground truth đầy đủ để lấy nhãn killed
GROUND_TRUTH_FILE = "full_ground_truth.csv"

REQUEST_TIMEOUT = 60          # giây, timeout mỗi lần gọi Ollama
MAX_RETRY = 1                  # retry tối đa 1 lần nếu lỗi/empty

# ============================================================
# 1. PROMPT TEMPLATE
# ============================================================
PROMPT_TEMPLATE = """You are a Java mutation testing expert. For each mutant, assess how likely it is to be killed by the test suite. A HIGH score means the mutant is easy to kill (low testing value). Return ONLY a decimal number in [0,1]. No explanation.

Few-shot examples:
[HIGH - score: 0.9] Operator: ROR, from: LT, to: LE, on a boundary check condition with multiple existing tests covering edge cases -> easy to detect -> 0.9
[HIGH - score: 0.85] Operator: AOR, from: PLUS, to: MINUS, in a core arithmetic method called by many tests -> 0.85
[HIGH - score: 0.8] Operator: LVR, from: 1, to: 0, replacing return value in a simple getter method with high coverage -> 0.8
[LOW - score: 0.1] Operator: STD, deleting a logging statement with no observable effect on test outputs -> 0.1
[LOW - score: 0.15] Operator: LVR, from: POS, to: NEG, in a rarely-executed branch with no direct test coverage -> 0.15
[LOW - score: 0.2] Operator: ROR, from: GE, to: GT, in dead code path -> 0.2

Mutant:
Class: {class_name}
Line: {line}
Operator: {operator} (from: {from_val} -> to: {to_val})
Code context:
{code_context}

Score:"""

# ============================================================
# 2. OPERATOR -> CATEGORY MAPPING
# ============================================================
OPERATOR_CATEGORY = {
    "ROR": "relational",
    "LOR": "logical",
    "COR": "logical",
    "AOR": "arithmetic",
    "LVR": "arithmetic",
    "SOR": "arithmetic",
    "STD": "statement_deletion",
    "ORU": "return_value",
}


def make_mutant_id(project: str, bug_id: str, mutant_no: str) -> str:
    """Tạo ID duy nhất"""
    return f"{project}-{bug_id}-{int(mutant_no):04d}"


def parse_score(raw: str) -> float | None:
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    try:
        val = float(text)
        if 0.0 <= val <= 1.0:
            return val
        return None
    except ValueError:
        pass

    import re
    match = re.search(r"(\d*\.\d+|\d+\.?\d*)", text)
    if match:
        try:
            val = float(match.group(1))
            if 0.0 <= val <= 1.0:
                return val
        except ValueError:
            pass

    return None


def call_qwen(prompt: str) -> tuple[float | None, str, int]:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "num_ctx": NUM_CTX,
            "num_predict": NUM_PREDICT,
        },
    }

    last_raw = ""
    total_latency_ms = 0

    for attempt in range(MAX_RETRY + 1):
        start = time.time()
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
            latency_ms = int((time.time() - start) * 1000)
            total_latency_ms += latency_ms

            if resp.status_code != 200:
                last_raw = f"[HTTP_ERROR_{resp.status_code}]"
                continue

            data = resp.json()
            raw_text = data.get("response", "")
            last_raw = raw_text

            score = parse_score(raw_text)
            if score is not None:
                return score, raw_text, total_latency_ms

        except requests.exceptions.RequestException as e:
            latency_ms = int((time.time() - start) * 1000)
            total_latency_ms += latency_ms
            last_raw = f"[REQUEST_ERROR: {e}]"
            continue

    return None, last_raw, total_latency_ms


def load_ground_truth(filepath: str) -> dict:
    gt = {}
    path = Path(filepath)
    if not path.exists():
        print(f"[WARNING] Ground truth file not found: {filepath}")
        return gt

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["bug_id"], row["mutant_no"])
            try:
                gt[key] = int(row["killed"])
            except (ValueError, KeyError):
                gt[key] = None
    return gt


def load_checkpoint(output_file: str) -> set:
    done = set()
    path = Path(output_file)
    if not path.exists():
        return done

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mid = row.get("mutant_id")
                if mid:
                    done.add(mid)
    except Exception as e:
        print(f"[WARNING] Lỗi đọc checkpoint, coi như chưa có gì: {e}")
        return set()

    return done


def log_line(log_path: str, message: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


# ============================================================
# 3. CHẠY CHO TỪNG PROJECT
# ============================================================
def process_project(project_name: str, run_mode: str, gt_data: dict):
    # Cấu hình tự động theo project
    input_file = "pilot_ground_truth.csv" if run_mode == "pilot" else "full_ground_truth.csv"
    output_file = f"results/{project_name.lower()}_{run_mode}_llm_output.csv"
    log_file = f"results/{project_name.lower()}_{run_mode}_api_log.txt"

    done_ids = load_checkpoint(output_file)
    output_path = Path(output_file)
    file_is_new = not output_path.exists() or output_path.stat().st_size == 0

    fieldnames = [
        "mutant_id", "project", "bug_id", "mutant_no",
        "operator", "category", "class", "line", "killed",
        "llm_score", "llm_raw_response", "llm_latency_ms", "model_used",
    ]

    log_line(log_file, f"=== START RUN === model={MODEL} project={project_name} "
                        f"mode={run_mode} resume_count={len(done_ids)}")

    total_processed = 0
    total_skipped_resume = 0
    total_empty = 0
    start_time = time.time()

    print(f"\n>> Đang xử lý: PROJECT = {project_name} | MODE = {run_mode}")
    print(f">> Ghi log vào: {output_file}")
    
    # Đếm trước tổng số dòng để hiển thị (tùy chọn)
    # Tuy nhiên vì file có thể lớn, ta sẽ cứ chạy tuần tự
    
    with open(input_file, newline="", encoding="utf-8") as fin, \
         open(output_file, "a", newline="", encoding="utf-8") as fout:

        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=fieldnames)

        if file_is_new:
            writer.writeheader()

        for row in reader:
            if row["project"] != project_name:
                continue

            mutant_id = make_mutant_id(row["project"], row["bug_id"], row["mutant_no"])

            if mutant_id in done_ids:
                total_skipped_resume += 1
                continue

            prompt = PROMPT_TEMPLATE.format(
                class_name=row["class"],
                line=row["line"],
                operator=row["operator"],
                from_val=row["from"],
                to_val=row["to"],
                code_context=row["code_context"],
            )

            score, raw, latency = call_qwen(prompt)

            key = (row["bug_id"], row["mutant_no"])
            killed = gt_data.get(key, "")

            writer.writerow({
                "mutant_id": mutant_id,
                "project": row["project"],
                "bug_id": row["bug_id"],
                "mutant_no": row["mutant_no"],
                "operator": row["operator"],
                "category": OPERATOR_CATEGORY.get(row["operator"], "other"),
                "class": row["class"],
                "line": row["line"],
                "killed": killed,
                "llm_score": score if score is not None else "",
                "llm_raw_response": raw,
                "llm_latency_ms": latency,
                "model_used": MODEL,
            })
            fout.flush()

            total_processed += 1
            if score is None:
                total_empty += 1
                log_line(log_file, f"[EMPTY/INVALID] {mutant_id} raw={raw!r}")

            if total_processed % 50 == 0:
                elapsed = time.time() - start_time
                avg_per_mutant = elapsed / total_processed
                print(f"  [{project_name}] Processed: {total_processed} | "
                      f"Empty: {total_empty} | "
                      f"Avg: {avg_per_mutant:.2f}s/mutant")

    elapsed_total = time.time() - start_time
    empty_rate = (total_empty / total_processed * 100) if total_processed else 0

    summary = (
        f"=== END RUN [{project_name}] === total_processed={total_processed} "
        f"skipped_resume={total_skipped_resume} "
        f"empty_invalid={total_empty} ({empty_rate:.1f}%) "
        f"elapsed_sec={elapsed_total:.1f} "
        f"avg_sec_per_mutant={(elapsed_total/total_processed if total_processed else 0):.2f}"
    )
    log_line(log_file, summary)
    print("\n" + summary)

    if empty_rate > 5.0:
        print(f"⚠️  CẢNH BÁO ({project_name}): tỷ lệ empty/invalid = {empty_rate:.1f}% (>5%)")


def main():
    random.seed(RANDOM_SEED)
    Path("results").mkdir(exist_ok=True)
    
    # Load ground truth 1 lần duy nhất để dùng chung cho tất cả project
    print("Đang nạp file Ground Truth...")
    gt_data = load_ground_truth(GROUND_TRUTH_FILE)

    for project in PROJECTS:
        print(f"\n=======================================================")
        print(f"🚀 BẮT ĐẦU CHẠY CHO PROJECT: {project}")
        print(f"=======================================================")
        process_project(project, RUN_MODE, gt_data)

    print("\n✅ ĐÃ CHẠY XONG TẤT CẢ CÁC PROJECT TRONG DANH SÁCH!")

if __name__ == "__main__":
    main()
