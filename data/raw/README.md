# Dataset & Ground Truth — Defects4J Mutation Study

# 23/06/20026

## Tong quan
- Benchmark: Defects4J v3
- Projects: Commons-Lang + Commons-Math
- Active bugs: 167 (Lang 61 + Math 106)
  - 4 bug Lang (2,18,25,48) da deprecated do khong tai lap tren Java moi
- Ground truth sinh thanh cong: 150 bug (Lang 59 + Math 91)
  - 17 bug loai do mutant non-termination (xem excluded_bugs.txt)
- Tong mutant: 88,187
  - Killed: 65,432 (74.2%)
  - Survived/Uncovered: 22,755 (25.8%)
- Ground truth sinh tu dong bang Major mutation engine (defects4j mutation)

## Dinh dang full_ground_truth.csv
| Cot | Y nghia |
|-----|---------|
| project | Lang hoac Math |
| bug_id | so thu tu bug |
| mutant_no | so thu tu mutant trong bug do |
| status | FAIL/TIME/EXC (killed) hoac LIVE/UNCOV (survived) |
| killed | 1 = bi giet, 0 = song sot/khong cover |

## Tai lap
1. Cai Defects4J v3 (Java 11)
2. Chay checkout_all.sh -> tao thu muc raw/
3. Chay run_mutation_full.sh (timeout 600) -> tao mutation/
4. Tao full_ground_truth.csv
