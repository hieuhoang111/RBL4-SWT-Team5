
# DÁN TOÀN BỘ CODE FULL MATH CỦA BẠN VÀO ĐÂY
# ============================================================
# FULL MATH EXPERIMENT — KAGGLE + OLLAMA + CHECKPOINT + RESUME
# ============================================================

PROJECT = "Math"
MODE = "full"
MODEL = "qwen3.6:latest"

# None = cố gắng chạy toàn bộ Math trong full_ground_truth.csv
LIMIT = None

# Cứ mỗi 100 mutant tạo lại checkpoint ZIP
CHECKPOINT_EVERY = 100

RESULTS_DIR = "/kaggle/working/results"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"

OUTPUT_FILENAME = "math_full_llm_output.csv"
LOG_FILENAME = "math_full_api_log.txt"
CHECKPOINT_ZIP_NAME = "math_full_checkpoint.zip"
FINAL_ZIP_NAME = "math_full_results.zip"

import csv
import json
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import requests


# ============================================================
# 1. PATHS
# ============================================================

results_dir = Path(RESULTS_DIR)
results_dir.mkdir(parents=True, exist_ok=True)

output_file = results_dir / OUTPUT_FILENAME
log_file = results_dir / LOG_FILENAME

checkpoint_zip = (
    Path("/kaggle/working") / CHECKPOINT_ZIP_NAME
)

final_zip = (
    Path("/kaggle/working") / FINAL_ZIP_NAME
)

progress_file = (
    results_dir / "math_full_progress.json"
)

print("Output CSV    :", output_file)
print("API log       :", log_file)
print("Progress JSON :", progress_file)
print("Checkpoint ZIP:", checkpoint_zip)


# ============================================================
# 2. TÌM FULL_GROUND_TRUTH.CSV
# ============================================================

print("\nFinding full_ground_truth.csv...")

input_candidates = list(
    Path("/kaggle/input").glob(
        "**/full_ground_truth.csv"
    )
)

if not input_candidates:
    raise FileNotFoundError(
        "Không tìm thấy full_ground_truth.csv "
        "trong /kaggle/input"
    )

# Ưu tiên file nằm cùng pilot_ground_truth.csv
input_file = None

for candidate in input_candidates:
    if (candidate.parent / "pilot_ground_truth.csv").exists():
        input_file = candidate
        break

if input_file is None:
    input_file = input_candidates[0]

data_dir = input_file.parent

print("DATA_DIR =", data_dir)
print("INPUT    =", input_file)


# ============================================================
# 3. KIỂM TRA OLLAMA VÀ MODEL
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
        "Không kết nối được Ollama tại "
        "127.0.0.1:11434. "
        "Hãy start Ollama trước."
    ) from exc

models = tags_response.json().get("models", [])

available_model_names = {
    item.get("name", "")
    for item in models
}

print("Available models:", sorted(available_model_names))

model_exists = any(
    name == MODEL
    or name.startswith("qwen3.6:")
    for name in available_model_names
)

if not model_exists:
    raise RuntimeError(
        f"Không tìm thấy model {MODEL}. "
        f"Hãy chạy: ollama pull {MODEL}"
    )

print("Selected model:", MODEL)

print("\nChecking Ollama processor...")

subprocess.run(
    ["ollama", "ps"],
    check=False,
)


# ============================================================
# 4. PROMPT
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
# 5. OUTPUT SCHEMA
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


# ============================================================
# 6. HELPER FUNCTIONS
# ============================================================

def parse_score(raw):
    """
    Parse response thành float trong khoảng [0, 1].
    """
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
        r"(?<![\d.])"
        r"(?:0(?:\.\d+)?|1(?:\.0+)?)"
        r"(?![\d.])",
        text,
    )

    if not match:
        return None

    value = float(match.group(0))

    if 0 <= value <= 1:
        return value

    return None


def make_mutant_id(
    project,
    bug_id,
    mutant_no,
):
    """
    Ví dụ: Math-1-0001
    """
    return (
        f"{project}-"
        f"{bug_id}-"
        f"{int(mutant_no):04d}"
    )


def call_qwen(
    prompt,
    max_retries=3,
):
    """
    Gọi qwen3.6 thông qua Ollama.
    """
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

    for attempt in range(
        1,
        max_retries + 1,
    ):
        start = time.time()

        try:
            response = requests.post(
                OLLAMA_GENERATE_URL,
                json=payload,
                timeout=600,
            )

            last_latency_ms = int(
                (time.time() - start)
                * 1000
            )

            if response.status_code != 200:
                last_error = (
                    f"[HTTP_ERROR_"
                    f"{response.status_code}] "
                    f"{response.text[:500]}"
                )

            else:
                response_data = response.json()
                raw = response_data.get(
                    "response",
                    "",
                )

                score = parse_score(raw)

                return (
                    score,
                    raw,
                    last_latency_ms,
                )

        except Exception as exc:
            last_latency_ms = int(
                (time.time() - start)
                * 1000
            )

            last_error = (
                f"[REQUEST_ERROR "
                f"attempt={attempt}/"
                f"{max_retries}: {exc}]"
            )

        if attempt < max_retries:
            wait_seconds = attempt * 5

            print(
                f"Request failed. "
                f"Retrying in "
                f"{wait_seconds}s..."
            )

            time.sleep(wait_seconds)

    return (
        None,
        last_error,
        last_latency_ms,
    )


def count_math_rows():
    """
    Đếm tổng số dòng Math trong full dataset.
    """
    total = 0

    with open(
        input_file,
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            if (
                row.get("project", "")
                .strip()
                == PROJECT
            ):
                total += 1

    return total


def load_completed_ids():
    """
    Load mutant_id đã ghi trong output CSV.
    Đây là cơ sở resume.
    """
    completed = set()

    if (
        not output_file.exists()
        or output_file.stat().st_size == 0
    ):
        return completed

    with open(
        output_file,
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            mutant_id = row.get(
                "mutant_id"
            )

            if mutant_id:
                completed.add(mutant_id)

    return completed


def save_progress_json(
    total_dataset,
    completed_total,
    processed_this_run,
    success_this_run,
    empty_this_run,
):
    """
    Lưu trạng thái dễ đọc.
    """
    progress = {
        "project": PROJECT,
        "mode": MODE,
        "model": MODEL,
        "input_file": str(input_file),
        "output_file": str(output_file),
        "total_math_mutants": total_dataset,
        "completed_total": completed_total,
        "remaining": max(
            total_dataset - completed_total,
            0,
        ),
        "processed_this_run": (
            processed_this_run
        ),
        "successful_this_run": (
            success_this_run
        ),
        "invalid_this_run": empty_this_run,
        "updated_at": time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    }

    temp_file = progress_file.with_suffix(
        ".json.tmp"
    )

    temp_file.write_text(
        json.dumps(
            progress,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temp_file.replace(progress_file)


def save_checkpoint_zip():
    """
    Tạo checkpoint ZIP theo kiểu atomic:
    tạo file tạm trước, sau đó thay thế file cũ.
    """
    temp_base = (
        "/kaggle/working/"
        "math_full_checkpoint_temp"
    )

    temp_zip = Path(
        temp_base + ".zip"
    )

    if temp_zip.exists():
        temp_zip.unlink()

    created_path = shutil.make_archive(
        temp_base,
        "zip",
        RESULTS_DIR,
    )

    created_path = Path(created_path)

    created_path.replace(
        checkpoint_zip
    )

    print(
        "\n[CHECKPOINT SAVED]",
        checkpoint_zip,
        "|",
        time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    )


def create_final_zip():
    """
    Tạo ZIP cuối cùng của toàn bộ thư mục results.
    """
    temp_base = (
        "/kaggle/working/"
        "math_full_results_temp"
    )

    temp_zip = Path(
        temp_base + ".zip"
    )

    if temp_zip.exists():
        temp_zip.unlink()

    created_path = shutil.make_archive(
        temp_base,
        "zip",
        RESULTS_DIR,
    )

    created_path = Path(created_path)

    created_path.replace(final_zip)

    print(
        "[FINAL ZIP CREATED]",
        final_zip,
    )


# ============================================================
# 7. KIỂM TRA DATASET VÀ CHECKPOINT CŨ
# ============================================================

print("\nCounting Math mutants...")

total_math_mutants = count_math_rows()

print(
    "Total Math mutants:",
    total_math_mutants,
)

done = load_completed_ids()

initial_completed = len(done)

print(
    "Already completed:",
    initial_completed,
)

print(
    "Remaining:",
    max(
        total_math_mutants
        - initial_completed,
        0,
    ),
)

if initial_completed >= total_math_mutants:
    print(
        "\nFull Math experiment "
        "đã hoàn thành trước đó."
    )

    save_progress_json(
        total_dataset=total_math_mutants,
        completed_total=initial_completed,
        processed_this_run=0,
        success_this_run=0,
        empty_this_run=0,
    )

    create_final_zip()

    raise SystemExit(
        "Không còn mutant nào cần chạy."
    )


# ============================================================
# 8. CHUẨN BỊ FILE OUTPUT
# ============================================================

file_is_new = (
    not output_file.exists()
    or output_file.stat().st_size == 0
)

processed = 0
success = 0
empty = 0

start_experiment_time = time.time()


# ============================================================
# 9. CHẠY FULL EXPERIMENT
# ============================================================

print(
    f"\nRunning FULL {PROJECT} experiment..."
)

print(
    "Nhấn Stop/Interrupt trên cell "
    "để dừng an toàn."
)

try:
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

        current_columns = set(
            reader.fieldnames or []
        )

        missing_columns = (
            required_columns
            - current_columns
        )

        if missing_columns:
            raise ValueError(
                "Dataset thiếu các cột: "
                f"{sorted(missing_columns)}"
            )

        for row in reader:
            if (
                row["project"].strip()
                != PROJECT
            ):
                continue

            if (
                LIMIT is not None
                and processed >= LIMIT
            ):
                print(
                    "\nReached LIMIT:",
                    LIMIT,
                )
                break

            mutant_id = make_mutant_id(
                row["project"],
                row["bug_id"],
                row["mutant_no"],
            )

            # Resume:
            # bỏ qua mutant đã có trong CSV
            if mutant_id in done:
                continue

            prompt = PROMPT_TEMPLATE.format(
                class_name=row["class"],
                line=row["line"],
                operator=row["operator"],
                from_val=row["from"],
                to_val=row["to"],
                code_context=row[
                    "code_context"
                ],
            )

            current_number = (
                initial_completed
                + processed
                + 1
            )

            print(
                f"[{current_number}/"
                f"{total_math_mutants}] "
                f"Processing "
                f"{mutant_id}..."
            )

            score, raw, latency = call_qwen(
                prompt
            )

            writer.writerow({
                "mutant_id": mutant_id,
                "project": row["project"],
                "bug_id": row["bug_id"],
                "mutant_no": row[
                    "mutant_no"
                ],
                "operator": row["operator"],
                "category": (
                    OPERATOR_CATEGORY.get(
                        row["operator"],
                        "other",
                    )
                ),
                "class": row["class"],
                "line": row["line"],
                "killed": row["killed"],
                "llm_score": (
                    score
                    if score is not None
                    else ""
                ),
                "llm_raw_response": raw,
                "llm_latency_ms": latency,
                "model_used": MODEL,
            })

            # Ghi checkpoint CSV ngay
            # sau từng mutant.
            fout.flush()

            flog.write(
                f"{mutant_id}\t"
                f"score={score}\t"
                f"latency_ms={latency}\t"
                f"raw={raw!r}\n"
            )

            flog.flush()

            done.add(mutant_id)
            processed += 1

            if score is None:
                empty += 1
            else:
                success += 1

            completed_total = len(done)

            elapsed_seconds = (
                time.time()
                - start_experiment_time
            )

            average_seconds = (
                elapsed_seconds / processed
                if processed > 0
                else 0
            )

            remaining_count = max(
                total_math_mutants
                - completed_total,
                0,
            )

            estimated_remaining = (
                remaining_count
                * average_seconds
            )

            print(
                f"score={score} | "
                f"latency={latency}ms | "
                f"completed="
                f"{completed_total}/"
                f"{total_math_mutants} | "
                f"empty={empty} | "
                f"ETA="
                f"{estimated_remaining / 3600:.2f}h"
            )

            save_progress_json(
                total_dataset=(
                    total_math_mutants
                ),
                completed_total=(
                    completed_total
                ),
                processed_this_run=(
                    processed
                ),
                success_this_run=success,
                empty_this_run=empty,
            )

            if (
                processed
                % CHECKPOINT_EVERY
                == 0
            ):
                save_checkpoint_zip()

except KeyboardInterrupt:
    print(
        "\n\nExperiment đã được "
        "dừng thủ công."
    )

    print(
        "Mutant đang xử lý dở "
        "sẽ được chạy lại lần sau."
    )

except Exception as exc:
    print(
        "\n\nExperiment dừng do lỗi:"
    )

    print(
        type(exc).__name__,
        str(exc),
    )

    raise

finally:
    completed_total = len(done)

    save_progress_json(
        total_dataset=total_math_mutants,
        completed_total=completed_total,
        processed_this_run=processed,
        success_this_run=success,
        empty_this_run=empty,
    )

    save_checkpoint_zip()
    create_final_zip()

    elapsed_seconds = (
        time.time()
        - start_experiment_time
    )

    print(
        "\n================ RESULT "
        "================"
    )

    print(
        "Processed this run :",
        processed,
    )

    print(
        "Successful this run:",
        success,
    )

    print(
        "Invalid this run   :",
        empty,
    )

    print(
        "Completed total    :",
        completed_total,
    )

    print(
        "Total Math mutants :",
        total_math_mutants,
    )

    print(
        "Remaining          :",
        max(
            total_math_mutants
            - completed_total,
            0,
        ),
    )

    print(
        "Elapsed hours      :",
        round(
            elapsed_seconds / 3600,
            3,
        ),
    )

    print(
        "Output CSV         :",
        output_file,
    )

    print(
        "Log                :",
        log_file,
    )

    print(
        "Checkpoint ZIP     :",
        checkpoint_zip,
    )

    print(
        "Final ZIP          :",
        final_zip,
    )
