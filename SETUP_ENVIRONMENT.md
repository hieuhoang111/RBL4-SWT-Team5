# Hướng dẫn Cài đặt Môi trường (RBL-4)

Dựa theo Proposal §5.3 và §8.1, môi trường làm việc của nhóm được chia làm 2 phần rõ rệt. Không phải ai cũng cần cài tất cả.

---

## 1. Môi trường phân tích dữ liệu & Tính toán (Dành cho Cả nhóm)
Tất cả các thành viên (đặc biệt là **Thiện LR** và **Bình MS**) cần có chung môi trường Python trên máy cá nhân để chạy các file script và tính toán metric.

**Cài đặt thư viện Python chuẩn:**
Mở Terminal tại thư mục project và chạy:
```bash
pip install -r requirements.txt
```


---

## 2. Môi trường chạy LLM (Dành riêng cho Thiện - LR)
Proposal chỉ định dùng **Llama-3.1-8B qua Ollama API**. Vì máy cá nhân có thể không đủ GPU để chạy Llama 3.1 8B, Thiện sẽ chạy trên nền tảng **Google Colab (T4 GPU)** hoặc **Kaggle**.

**Cách khởi động Ollama ngầm trên Colab/Kaggle:**
Thiện chỉ cần tạo một ô code (cell) trong Notebook và chạy lệnh sau để tự động tải và khởi động server Llama 3.1:
```bash
!bash scripts/setup_kaggle_colab.sh
```
*Script này sẽ tự động cài Ollama, kéo model `llama3.1:8b` về và mở API tại `localhost:11434` đúng hệt như máy tính cá nhân.*

---

## 3. Môi trường thu thập Defects4J (Dành riêng cho Phát - DG)
Theo Bước 1 và 2 trong Pipeline, Phát là người phải cài Defects4J và chạy PIT Maven plugin để tạo ra bộ Ground Truth. 

**Yêu cầu hệ thống trên máy Phát (Cần dùng WSL2 / Linux):**
*   **Java (JDK 1.8):** Defects4J v2.0 yêu cầu Java 8 để biên dịch các dự án Lang và Math.
*   **Perl & SVN:** Để clone các version lỗi của Defects4J.
*   **Maven:** Để chạy lệnh `org.pitest:pitest-maven`.

**Các bước Phát cần làm (chạy trên Terminal của Linux/WSL):**
```bash
# 1. Cài đặt các công cụ nền
sudo apt-get update
sudo apt-get install -y openjdk-8-jdk perl subversion git maven

# 2. Clone Defects4J
git clone https://github.com/rjust/defects4j.git
cd defects4j

# 3. Khởi tạo Defects4J
cpanm --installdeps .
./init.sh
```
*Sau khi cài xong, Phát dùng lệnh `defects4j checkout -p Lang -v 1b -w /tmp/lang_1_buggy` để lấy code lỗi ra chạy PIT Maven nhé.*
