# Stage 1: Build Frontend SPA
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Python Runtime
FROM python:3.12-slim
WORKDIR /app

# 安裝 Python 相依套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式邏輯與來源程式碼到工作目錄
COPY src/ /app/src/
COPY server/ /app/server/

# 從前端建置器複製編譯好的靜態檔案至 FastAPI 靜態託管目錄
COPY --from=frontend-builder /app/frontend/dist /app/server/dist

EXPOSE 10000

# 從根目錄啟動 FastAPI，確保伺服器程式碼可直接以 src.moodle_client 形式導入套件
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "10000"]
