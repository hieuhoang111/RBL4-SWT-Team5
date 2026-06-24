# Phân công nhiệm vụ RBL-4 theo Cấu trúc Thư mục

Tài liệu này quy định rõ trách nhiệm (Ownership) của từng thành viên đối với các file và thư mục trong repository `RBL4-SWT-Team5`. Bất kỳ ai phụ trách thư mục/file nào sẽ chịu trách nhiệm code, tính toán, push code và fix lỗi cho thư mục/file đó.

## 👑 Quản lý chung (Project Lead - PL)
**Phụ trách: Hoàng Trung Hiếu**
*   `.gitignore`: Đảm bảo không ai push nhầm API key hay file rác.
*   `notes.md`: Ghi chép mọi quyết định thay đổi kỹ thuật, sửa lỗi, và lịch sử xin Amendment với Giảng viên.
*   `SETUP_ENVIRONMENT.md`: Cập nhật tài liệu hướng dẫn cài đặt môi trường.
*   `TASK_ASSIGNMENT.md`: File phân công công việc này.
*   **Trách nhiệm cốt lõi:** Quản lý Repo, review code của các thành viên trước khi gộp (merge), đốc thúc tiến độ, xử lý lỗi API/Data và ngăn chặn hành vi gian lận (HARKing).

---

## 🗂️ Thư mục `data/` (Data & Ground Truth - DG)
**Phụ trách 100%: Huỳnh Tấn Phát**
Khu vực chứa dữ liệu đầu vào và đáp án chuẩn. Mọi sai sót về data ở khâu này sẽ làm hỏng toàn bộ dự án.
*   `data/raw/` : Thư mục chứa dataset gốc Defects4J. Tuyệt đối KHÔNG sửa đổi file gốc.
*   `data/raw/README.md` : Ghi rõ nguồn, license, cấu trúc cột, ngày tải dataset.
*   `data/pilot_sample.csv` *(Tuần 7)*: File chứa 10-20% N (dữ liệu ngẫu nhiên) để chạy thử. (Nhớ báo Hiếu ghi Random Seed vào notes.md).
*   `data/pilot_ground_truth.csv` *(Tuần 7)*: File đáp án chuẩn của nhóm trên tập chạy thử + điểm IAA.
*   `data/full_ground_truth.csv` *(Tuần 8)*: File đáp án chuẩn của toàn bộ dữ liệu + điểm IAA.

---

## 💻 Thư mục `scripts/` (Code thực thi)
**Phụ trách: Nguyễn Trần Ngọc Thiện (LR) & Huỳnh Quốc Bình (MS)**
Khu vực chứa các kịch bản chạy tự động. Thiện lo phần gọi AI, Bình lo phần chấm điểm.
*   `scripts/test_api.py` ** 👉 **Ngọc Thiện (LR)**: Code test 1 câu hỏi gọi API (Pass Gate E3).
*   `scripts/run_experiment.py` 👉 **Ngọc Thiện (LR)**: Code chạy LLM hàng loạt. **Yêu cầu bắt buộc:** Phải có cơ chế Retry (chống Rate Limit) và lưu Checkpoint mỗi 50 dòng.
*   `scripts/setup_kaggle_colab.sh`  👉 **Ngọc Thiện (LR)**: Script cài đặt Ollama trên Colab/Kaggle.
*   `scripts/compute_metric.py` 👉 **Quốc Bình (MS)**: Code tính Metric và chạy kiểm định thống kê (Pass Gate E4).

---

## 📊 Thư mục `results/` (Kết quả đầu ra)
**Phụ trách: Nguyễn Trần Ngọc Thiện (LR) & Huỳnh Quốc Bình (MS)**
Khu vực lưu trữ kết quả chạy script.
*   **Sản phẩm của Ngọc Thiện (LR):**
    *   `results/pilot_llm_output.csv` : Output LLM trên tập pilot.
    *   `results/pilot_api_log.txt` : Nhật ký gọi API (timestamp, response model, cost/call).
    *   `results/full_llm_output.csv` *: Output LLM toàn bộ dataset.
    *   `results/full_api_log.txt` : Nhật ký chạy bản Full (cost, errors).
*   **Sản phẩm của Quốc Bình (MS):**
    *   `results/pilot_analysis.ipynb` : Phân tích mẻ pilot (Histogram + descriptive stats). Báo cáo Hiếu xác nhận lại Test choice.
    *   `results/full_analysis.ipynb` : Chấm điểm bản full. Tính p-value, effect size, kết luận per RQ. **Yêu cầu:** File phải chạy mượt từ đầu đến cuối (Restart & Run All).
    *   `results/summary.csv` : Bảng chốt hạ (1 dòng/RQ: metric, p, effect size, N).

---

## 🎨 Thư mục `figures/` (Trực quan hóa dữ liệu)
**Phụ trách 100%: Võ Minh Trí (RW)**
Lấy số liệu từ các file `results/*.csv` do Bình tạo ra để vẽ biểu đồ chèn vào báo cáo.
*   `figures/fig1_distribution.png` : Biểu đồ phân phối (Boxplot/violin) cho metric chính. Đảm bảo chất lượng sắc nét ≥ 300 DPI.
*   `figures/fig2_comparison.png` : Biểu đồ so sánh (Comparative plot - dùng cho RQ2).

---
**💡 Checklist khi push code (Dành cho TẤT CẢ thành viên):**
- [ ] KHÔNG commit file chứa API key (`api_key.txt`), file môi trường `.env`, hoặc thư mục rác `__pycache__`, `.DS_Store`. (File `.gitignore` đã lo việc này, nhưng cẩn thận vẫn hơn).
- [ ] Chạy xong mẻ nào (batch) là commit ngay, không ngâm đến cuối Tuần 8.
- [ ] Đặt tên commit có ý nghĩa (VD: `feat: add pilot results (N=262, 98.1% valid)`).
- [ ] Tuyệt đối tuân thủ hợp đồng Proposal. Cấm HARKing (gian lận kết quả). Mọi khó khăn phải báo ngay cho Leader Trung Hiếu.
