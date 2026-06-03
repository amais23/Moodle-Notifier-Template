from fastapi import FastAPI
from fastapi.responses import JSONResponse
from server.routers import line_webhook

app = FastAPI(
    title="Moodle Notifier Webhook Server",
    description="FastAPI server to handle LINE Webhooks and provide query endpoints.",
    version="1.0.0"
)

# 註冊 LINE Webhook 路由
app.include_router(line_webhook.router)

@app.get("/")
def read_root():
    return {
        "message": "🎓 NTNU Moodle Notifier API is running!",
        "status": "healthy"
    }

@app.get("/health")
def health_check():
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "message": "alive"}
    )
