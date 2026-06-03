import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from server.routers import line_webhook, api_dashboard
from src.config import Config
from server.services.discord_bot import start_discord_bot, stop_discord_bot

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load config and launch Discord bot if configured
    print("[INFO] Server starting up. Initializing modules...")
    try:
        config = Config.load()
        await start_discord_bot(config)
    except Exception as e:
        clean_error = str(e).encode('ascii', errors='ignore').decode('ascii')
        print(f"[WARNING] Lifespan initialization warning: {clean_error}")
        
    yield
    
    # Shutdown: Clean up Discord bot connections
    print("[INFO] Server shutting down. Cleaning up...")
    await stop_discord_bot()

app = FastAPI(
    title="Moodle Notifier Webhook Server",
    description="FastAPI server to handle LINE Webhooks and provide query endpoints.",
    version="1.0.0",
    lifespan=lifespan
)

# 註冊 API 路由 (API 路由器必須優先註冊)
app.include_router(line_webhook.router)
app.include_router(api_dashboard.router)

@app.get("/health")
def health_check():
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "message": "alive"}
    )

# 託管前端靜態檔案 (必須放在所有路由器的最後，避免接管 API 路由)
dist_path = os.path.join(os.path.dirname(__file__), "dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")
else:
    @app.get("/")
    def read_root():
        return {
            "message": "🎓 NTNU Moodle Notifier API is running!",
            "status": "healthy",
            "info": "前端靜態目錄 server/dist 未找到。請先編譯前端專案以提供控制台網頁。"
        }
