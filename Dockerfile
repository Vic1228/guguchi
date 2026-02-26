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

# 預設 PORT 為 5000
ENV PORT=5000
EXPOSE $PORT

# 添加健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:' + __import__('os').environ.get('PORT', '5000') + '/api/health').read()" || exit 1

# 使用 sh -c 執行 gunicorn，確保能正確讀取 $PORT 環境變數
CMD sh -c "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 --access-logfile - --error-logfile - app:app"
