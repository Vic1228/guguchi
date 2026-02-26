FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 建立資料目錄（部署時應掛 Volume 到 /app/data）
RUN mkdir -p /app/data

# 設定環境變數
ENV DB_PATH=/app/data/stocks.db
ENV PYTHONUNBUFFERED=1

# 使用 gunicorn 啟動 (Zeabur 建議監聽 5000 並輸出存取與錯誤日誌)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
