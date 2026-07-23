
# DÁN TOÀN BỘ CODE CELL FULL MATH PILOT VÀO ĐÂY
# ============================================================
# RUN FULL MATH PILOT EXPERIMENT ON KAGGLE
# Ollama và qwen3.6:latest đã được cài, chạy và test trước đó
# ============================================================

PROJECT = "Math"
MODE = "pilot"
MODEL = "qwen3.6:latest"

# Chạy toàn bộ mutant Math trong pilot_ground_truth.csv
LIMIT = None

RESULTS_DIR = "/kaggle/working/results"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"

import csv
import re
import time
import shutil
from pathlib import Path

import requests


# ============================================================
# 1. TÌM DATASET
# ============================================================

print("Finding data...")

data_dir = None

for pilot_file in Path("/kaggle/input").glob("**/pilot_ground_truth.csv"):
    candidate = pilot_file.parent

    if (candidate / "full_ground_truth.csv").exists():
        data_dir = candidate
        break

if data_dir is None:
    raise FileNotFoundError(
        "Không tìm thấy pilot_ground_truth.csv và "
        "full_ground_truth.csv trong /kaggle/input"
    )

input_file = data_dir / "pilot_ground_truth.csv"

print("DATA_DIR =", data_dir)
print("INPUT    =", input_file)


# ============================================================
# 2. KIỂM TRA OLLAMA SERVER
# ============================================================

print("\nChecking Ollama server...")

try:
    tags_response = requests.get(
        f"{OLLAMA_BASE_URL}/api/tags",
        timeout=10,
    )
    tags_response.raise_for_status()
except Exception as exc:
    raise RuntimeError(
        "Không kết nối được Ollama tại 127.0.0.1:11434. "
        "Ollama server có thể đã dừng."
    ) from exc

models = tags_response.json().get("models", [])

available_model_names = {
    model.get("name", "")
    for model in models
}

print("Ollama is ready")
print("Available models:", sorted(available_model_names))

model_exists = any(
    name == MODEL or name.startswith("qwen3.6:")
    for name in available_model_names
)

if not model_exists:
    raise RuntimeError(
        f"Không tìm thấy model {MODEL}. "
        f"Hãy chạy ollama pull {MODEL} trước."
    )

print("Selected model:", MODEL)


# ============================================================
# 3. PROMPT
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


# ============================================================
# 4. HÀM HỖ TRỢ
# ============================================================

def parse_score(raw):
    if raw is None:
        return None

    text = raw.strip()

    if not text:
        return None

    try:
        value = float(text)

        if 0 <= value <= 1:
            return value

        return None

    except ValueError:
        pass

    match = re.search(
        r"(?<![\d.])(?:0(?:\.\d+)?|1(?:\.0+)?)(?![\d.])",
        text,
    )

    if not match:
        return None

    value = float(match.group(0))

    if 0 <= value <= 1:
        return value

    return None


def make_mutant_id(project, bug_id, mutant_no):
    return f"{project}-{bug_id}-{int(mutant_no):04d}"


def call_qwen(prompt, max_retries=3):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "keep_alive": -1,
        "options": {
            "temperature": 0,
            "top_p": 1.0,
            "seed": 42,
            "num_ctx": 4096,
            "num_predict": 8,
        },
    }

    last_error = None
    last_latency_ms = 0

    for attempt in range(1, max_retries + 1):
        start = time.time()

        try:
            response = requests.post(
                OLLAMA_GENERATE_URL,
                json=payload,
                timeout=600,
            )

            last_latency_ms = int(
                (time.time() - start) * 1000
            )

            if response.status_code != 200:
                last_error = (
                    f"[HTTP_ERROR_{response.status_code}] "
                    f"{response.text[:500]}"
                )
            else:
                response_data = response.json()
                raw = response_data.get("response", "")
                score = parse_score(raw)

                return score, raw, last_latency_ms

        except Exception as exc:
            last_latency_ms = int(
                (time.time() - start) * 1000
            )

            last_error = (
                f"[REQUEST_ERROR "
                f"attempt={attempt}/{max_retries}: {exc}]"
            )

        if attempt < max_retries:
            wait_seconds = attempt * 5

            print(
                f"Request failed. Retrying in "
                f"{wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)

    return None, last_error, last_latency_ms


# ============================================================
# 5. TẠO THƯ MỤC OUTPUT
# ============================================================

results_dir = Path(RESULTS_DIR)
results_dir.mkdir(parents=True, exist_ok=True)

output_file = (
    results_dir / "math_pilot_llm_output.csv"
)

log_file = (
    results_dir / "math_pilot_api_log.txt"
)

print("\nOUTPUT =", output_file)
print("LOG    =", log_file)


# ============================================================
# 6. ĐỌC CÁC MUTANT ĐÃ CHẠY
# ============================================================

done = set()

if output_file.exists() and output_file.stat().st_size > 0:
    with open(
        output_file,
        newline="",
        encoding="utf-8",
    ) as file:
        for existing_row in csv.DictReader(file):
            mutant_id = existing_row.get("mutant_id")

            if mutant_id:
                done.add(mutant_id)

print("Already completed:", len(done))


# ============================================================
# 7. CẤU TRÚC FILE OUTPUT
# ============================================================

fieldnames = [
    "mutant_id",
    "project",
    "bug_id",
    "mutant_no",
    "operator",
    "category",
    "class",
    "line",
    "killed",
    "llm_score",
    "llm_raw_response",
    "llm_latency_ms",
    "model_used",
]

file_is_new = (
    not output_file.exists()
    or output_file.stat().st_size == 0
)

processed = 0
success = 0
empty = 0


# ============================================================
# 8. CHẠY THỰC NGHIỆM
# ============================================================

print(f"\nRunning {PROJECT} pilot...")

with (
    open(
        input_file,
        newline="",
        encoding="utf-8",
    ) as fin,
    open(
        output_file,
        "a",
        newline="",
        encoding="utf-8",
    ) as fout,
    open(
        log_file,
        "a",
        encoding="utf-8",
    ) as flog
):
    reader = csv.DictReader(fin)

    writer = csv.DictWriter(
        fout,
        fieldnames=fieldnames,
    )

    if file_is_new:
        writer.writeheader()
        fout.flush()

    required_columns = {
        "project",
        "bug_id",
        "mutant_no",
        "operator",
        "class",
        "line",
        "from",
        "to",
        "code_context",
        "killed",
    }

    current_columns = set(reader.fieldnames or [])

    missing_columns = (
        required_columns - current_columns
    )

    if missing_columns:
        raise ValueError(
            "Dataset thiếu các cột bắt buộc: "
            f"{sorted(missing_columns)}"
        )

    for row in reader:
        if row["project"].strip() != PROJECT:
            continue

        if LIMIT is not None and processed >= LIMIT:
            break

        mutant_id = make_mutant_id(
            row["project"],
            row["bug_id"],
            row["mutant_no"],
        )

        if mutant_id in done:
            continue

        prompt = PROMPT_TEMPLATE.format(
            class_name=row["class"],
            line=row["line"],
            operator=row["operator"],
            from_val=row["from"],
            to_val=row["to"],
            code_context=row["code_context"],
        )

        print(
            f"[{processed + 1}/{LIMIT or 'ALL'}] "
            f"Processing {mutant_id}..."
        )

        score, raw, latency = call_qwen(prompt)

        writer.writerow({
            "mutant_id": mutant_id,
            "project": row["project"],
            "bug_id": row["bug_id"],
            "mutant_no": row["mutant_no"],
            "operator": row["operator"],
            "category": OPERATOR_CATEGORY.get(
                row["operator"],
                "other",
            ),
            "class": row["class"],
            "line": row["line"],
            "killed": row["killed"],
            "llm_score": (
                score if score is not None else ""
            ),
            "llm_raw_response": raw,
            "llm_latency_ms": latency,
            "model_used": MODEL,
        })

        fout.flush()

        flog.write(
            f"{mutant_id}\t"
            f"score={score}\t"
            f"latency_ms={latency}\t"
            f"raw={raw!r}\n"
        )
        flog.flush()

        processed += 1

        if score is None:
            empty += 1
        else:
            success += 1

        print(
            f"score={score} | "
            f"latency={latency} ms | "
            f"success={success} | "
            f"empty={empty}"
        )


# ============================================================
# 9. TỔNG KẾT
# ============================================================

print("\n================ RESULT ================")
print("DONE")
print("Processed           :", processed)
print("Successful scores   :", success)
print("Invalid/empty scores:", empty)
print("Output              :", output_file)
print("Log                 :", log_file)


# ============================================================
# 10. NÉN KẾT QUẢ
# ============================================================

archive_path = shutil.make_archive(
    "/kaggle/working/math_pilot_results",
    "zip",
    RESULTS_DIR,
)

print("ZIP                 :", archive_path)
