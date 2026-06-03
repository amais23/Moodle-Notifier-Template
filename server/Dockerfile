FROM python:3.12-slim

WORKDIR /app

# 複製依賴檔案並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式邏輯與來源程式碼到工作目錄
COPY src/ /app/src/
COPY server/ /app/server/

EXPOSE 10000

# 從根目錄啟動 FastAPI，確保伺服器程式碼可直接以 src.moodle_client 形式導入套件
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "10000"]
