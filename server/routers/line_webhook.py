import hmac
import hashlib
import base64
import json
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from src.config import Config
from server.handlers.command_handlers import handle_command, build_error_flex, send_line_reply

router = APIRouter()

# 載入系統設定
try:
    config = Config.load()
except Exception as e:
    # 避免 Windows CP950 編碼崩潰，先過濾非 ASCII 字元
    clean_error = str(e).encode('ascii', errors='ignore').decode('ascii')
    print(f"[WARNING] Config load warning during server startup: {clean_error}")
    config = None

def verify_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    """驗證 LINE Webhook 簽章是否正確"""
    if not channel_secret:
        return False
    hash_val = hmac.new(channel_secret.encode('utf-8'), body, hashlib.sha256).digest()
    expected = base64.b64encode(hash_val).decode('utf-8')
    return hmac.compare_digest(expected, signature)

@router.post("/webhook/line")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(None)
):
    """處理 LINE Webhook 訊息"""
    global config
    if not config:
        try:
            config = Config.load()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"系統設定載入失敗: {e}")

    # 取得原始 Body 以進行簽章驗證
    body = await request.body()
    
    # 1. 驗證憑證與簽章
    if not config or not config.line_token or not config.line_channel_secret:
        print("[WARNING] LINE webhook received but LINE Bot credentials are not fully configured.")
        raise HTTPException(status_code=400, detail="LINE Bot is not fully configured")

    if not x_line_signature or not verify_signature(body, x_line_signature, config.line_channel_secret):
        print("[ERROR] Webhook signature verification failed!")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 2. 解析 JSON Body
    try:
        payload = json.loads(body.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    events = payload.get("events", [])
    for event in events:
        user_id = event.get("source", {}).get("userId")
        reply_token = event.get("replyToken")

        # 3. 嚴格限定僅允許特定的 LINE_USER_ID 查詢
        if user_id != config.line_user_id:
            print(f"[WARNING] Unauthorized user query intercepted [UserId: {user_id}]")
            # 回傳 200 避免 LINE Platform 判定 Webhook 故障
            continue

        event_type = event.get("type")

        # 處理文字訊息事件
        if event_type == "message" and event.get("message", {}).get("type") == "text":
            text = event.get("message", {}).get("text", "").strip()
            if reply_token and text.startswith("/"):
                # 4. 調用指令處理器
                try:
                    await handle_command(text, reply_token, config)
                except Exception as e:
                    print(f"[ERROR] Exception processing command '{text}': {e}")
                    try:
                        err_flex = build_error_flex("系統執行錯誤", f"執行指令 '{text}' 時發生錯誤：\n{e}")
                        send_line_reply(reply_token, err_flex, config.line_token)
                    except Exception as reply_err:
                        print(f"[ERROR] Failed to send error reply: {reply_err}")

        # 處理 Postback 事件
        elif event_type == "postback":
            data = event.get("postback", {}).get("data", "")
            if reply_token and data:
                try:
                    await handle_command(f"/postback {data}", reply_token, config)
                except Exception as e:
                    print(f"[ERROR] Exception processing postback '{data}': {e}")
                    try:
                        err_flex = build_error_flex("系統執行錯誤", f"處理回傳動作時發生錯誤：\n{e}")
                        send_line_reply(reply_token, err_flex, config.line_token)
                    except Exception as reply_err:
                        print(f"[ERROR] Failed to send error reply: {reply_err}")

    return JSONResponse(status_code=200, content={"status": "ok"})
