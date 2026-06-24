#!/bin/bash
# Script để cài đặt và chạy Ollama ngầm trên Google Colab / Kaggle Notebooks
# Chạy script này trong cell của notebook bằng lệnh: !bash scripts/setup_kaggle_colab.sh

echo "1. Cài đặt Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo "2. Khởi động Ollama server ngầm (background)..."
# Chạy ngầm và chuyển log ra file để không làm rác console
ollama serve > ollama_server.log 2>&1 &

# Đợi vài giây để server khởi động hoàn toàn
sleep 5

echo "3. Tải model llama3.1:8b theo đúng cấu hình Proposal §5.3..."
ollama pull llama3.1:8b

echo "✅ Setup hoàn tất! Bạn có thể gọi API localhost:11434 bằng thư viện Python 'ollama'."
echo "Kiểm tra model đã tải:"
ollama list
