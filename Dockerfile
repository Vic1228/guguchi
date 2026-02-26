FROM python:3.11-slim  
WORKDIR /app  
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt  
COPY . .  
RUN mkdir -p /app/data  
ENV DB_PATH=/app/data/stocks.db  
ENV PYTHONUNBUFFERED=1  
ENV PORT=5000  
EXPOSE 5000  
# 簡化的健康檢查 - 直接檢查 Port 是否開放  
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \  
    CMD python -c "import socket; socket.create_connection(('localhost', 5000), timeout=5)" || exit 1  
CMD sh -c "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 --access-logfile - --error-logfile - app:app"
