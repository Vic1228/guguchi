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

# 預設 PORT 為 5000，如果 Zeabur 給了 PORT 就用它給的
ENV PORT=5000
EXPOSE ${PORT}

# 使用 gunicorn 啟動
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
