FROM python:3.11-slim  
WORKDIR /app  
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt  
COPY . .  
RUN mkdir -p /app/data  
ENV DB_PATH=/app/data/stocks.db  
ENV PYTHONUNBUFFERED=1  
EXPOSE 8080  
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \  
    CMD python -c "import socket; socket.create_connection(('localhost', 8080), timeout=5)" || exit 1  
# 使用 Zeabur 注入的 PORT 環境變數（預設 8080）  
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120 --access-logfile - --error-logfile - app:app"]
