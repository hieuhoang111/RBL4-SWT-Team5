# Dataset & Ground Truth — Defects4J Mutation Study

# 23/06/20026

## Tong quan
- Benchmark: Defects4J v3
- Projects: Commons-Lang + Commons-Math
- Active bugs: 167 (Lang 61 + Math 106)
  - 4 bug Lang (2,18,25,48)  deprecated do đó không tái lập trên Java mới
- Ground truth sinh thanh cong: 150 bug (Lang 59 + Math 91)
  - 17 bug loại do mutant non-termination (xem excluded_bugs.txt)
- Tổng mutant: 88,187
  - Killed: 65,432 (74.2%)
  - Survived/Uncovered: 22,755 (25.8%)
- Ground truth sinh tự động bằng Major mutation engine (defects4j mutation)

## Dinh dang full_ground_truth.csv
| Cột | Ý nghĩa |
|-----|---------|
| project | Lang hoặc Math |
| bug_id | số thứ tự bug |
| mutant_no | số thứ tự mutant trong bug đó |
| status | FAIL/TIME/EXC (killed) hoặc LIVE/UNCOV (survived) |
| killed | 1 = bi giết, 0 = sống sót/không cover |

## Tai lap
1. Cài Defects4J v3 (Java 11)
2. Chạy checkout_all.sh -> tạo thư mục raw/
3. Chạy run_mutation_full.sh (timeout 600) -> tạo mutation/
4. Tao full_ground_truth.csv
