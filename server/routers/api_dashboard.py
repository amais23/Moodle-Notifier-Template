import sys
import os
import requests
from typing import List, Optional
from fastapi import APIRouter, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from urllib.parse import urlparse

# 確保能導入 src 目錄
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.moodle_client import MoodleClient
from src.config import Config

router = APIRouter()

# 載入系統設定
try:
    sys_config = Config.load()
except Exception as e:
    clean_error = str(e).encode('ascii', errors='ignore').decode('ascii')
    print(f"[WARNING] Config load warning during API router startup: {clean_error}")
    sys_config = None

class LoginSchema(BaseModel):
    username: str
    password: str
    moodle_url: Optional[str] = None

# --- Dependency: Get Authenticated MoodleClient ---
def get_moodle_client(
    authorization: str = Header(None),
    x_moodle_url: str = Header(None)
) -> MoodleClient:
    """從 Header 憑證初始化無狀態的 MoodleClient"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少或無效的授權憑證 (Authorization Header)")
    
    token = authorization.split(" ")[1]
    
    # 決定 Moodle 伺服器網址
    moodle_url = x_moodle_url
    if not moodle_url:
        moodle_url = sys_config.moodle_base_url if sys_config else "https://moodle3.ntnu.edu.tw"
        
    # 初始化 MoodleClient
    client = MoodleClient(base_url=moodle_url, username="", password="")
    client.token = token
    
    try:
        # 調用基本資訊初始化 user_id 與 fullname
        site_info = client._call_raw_api("core_webservice_get_site_info")
        client.user_id = site_info.get("userid")
        client.fullname = site_info.get("fullname", "")
        if not client.user_id:
            raise ValueError("無法取得 User ID，Token 可能無效")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Moodle 憑證無效或連線逾期: {e}")
        
    return client

# --- Endpoints ---

@router.post("/api/login")
def api_login(payload: LoginSchema):
    """驗證 Moodle 帳號密碼並回傳 Token"""
    moodle_url = payload.moodle_url
    if not moodle_url:
        moodle_url = sys_config.moodle_base_url if sys_config else "https://moodle3.ntnu.edu.tw"
        
    client = MoodleClient(base_url=moodle_url, username=payload.username, password=payload.password)
    try:
        client.authenticate()
        return {
            "token": client.token,
            "user_id": client.user_id,
            "fullname": client.fullname,
            "moodle_url": client.base_url
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"登入失敗: {e}")

@router.get("/api/dashboard/summary")
def get_dashboard_summary(client: MoodleClient = Depends(get_moodle_client)):
    """快速取得主頁面統計摘要"""
    try:
        # 1. 取得未讀對話數
        unread_messages = client.get_unread_conversations_count()
        
        # 2. 取得即將到來事項
        upcoming = client.get_upcoming_events()
        upcoming_count = len(upcoming)
        
        # 3. 待繳作業：篩選即將到來事項中，類型為 assign 的數量
        pending_assignments = len([e for e in upcoming if e.get("modulename") == "assign"])
        
        return {
            "unread_messages": unread_messages,
            "upcoming_events": upcoming_count,
            "pending_assignments": pending_assignments
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得摘要: {e}")

@router.get("/api/courses")
def get_courses(client: MoodleClient = Depends(get_moodle_client)):
    """取得所有課程清單"""
    try:
        return client.get_user_courses()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得課程: {e}")

@router.get("/api/courses/{course_id}/contents")
def get_course_contents(course_id: int, client: MoodleClient = Depends(get_moodle_client)):
    """取得特定課程單元與資源教材"""
    try:
        return client.get_course_contents(course_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得課程內容: {e}")

@router.get("/api/assignments")
def get_assignments(client: MoodleClient = Depends(get_moodle_client)):
    """批量取得所有課程作業清單"""
    try:
        courses = client.get_user_courses()
        course_ids = [c["id"] for c in courses]
        if not course_ids:
            return []
            
        res = client.get_assignments(course_ids)
        assignments_list = []
        for c_assign in res.get("courses", []):
            course_name = c_assign.get("fullname", "")
            for assign in c_assign.get("assignments", []):
                assign["course_name"] = course_name
                assignments_list.append(assign)
                
        # 依截止時間排序
        assignments_list.sort(key=lambda x: x.get("duedate", 0))
        return assignments_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得作業: {e}")

@router.get("/api/assignments/{assign_id}/status")
def get_assignment_status(assign_id: int, client: MoodleClient = Depends(get_moodle_client)):
    """取得單一作業的詳細繳交狀態與評分回饋"""
    try:
        return client.get_submission_status(assign_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得作業狀態: {e}")

@router.get("/api/grades/{course_id}")
def get_grades(course_id: int, client: MoodleClient = Depends(get_moodle_client)):
    """取得單一課程的成績明細"""
    try:
        return client.get_grade_items(course_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得成績: {e}")

@router.get("/api/upcoming")
def get_upcoming(client: MoodleClient = Depends(get_moodle_client)):
    """取得即將到來的行事曆事項"""
    try:
        return client.get_upcoming_events()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得行事曆: {e}")

@router.get("/api/messages")
def get_messages(client: MoodleClient = Depends(get_moodle_client)):
    """取得最近私訊對話"""
    try:
        return client.get_conversations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法取得私訊: {e}")

@router.get("/api/download")
def proxy_download(
    url: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """安全代理下載：防盜連、防 Token 暴露"""
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
    if not token:
        # 下載連結可能會直接帶在 query 裡（因為 a 標籤點擊）
        # 我們將 token 帶在 URL 參數中也可以，只要保存在 query param 即可
        # 我們在 frontend 拼接時，如果使用 a 標籤，可以直接把 token 當成 query param 帶上
        # 這邊會透過 query param 的 token 解析
        pass

    if not token:
        raise HTTPException(status_code=401, detail="存取權限不足，需要 Token")

    # 安全校驗：限制必須為 ntnu 網域下的連結，防止被惡意當作通用 HTTP Proxy
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    if not domain.endswith("ntnu.edu.tw"):
        raise HTTPException(status_code=400, detail="不允許的下載網域，僅限師大 Moodle")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # 呼叫 Moodle 檔案下載，並將 Token 當作參數傳入
        res = requests.get(url, params={"token": token}, headers=headers, stream=True, timeout=30)
        res.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"連線師大 Moodle 下載失敗: {e}")

    content_type = res.headers.get("content-type", "application/octet-stream")
    content_disposition = res.headers.get("content-disposition", "")

    # 串流傳輸，避免記憶體溢出
    def file_streamer():
        for chunk in res.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    response_headers = {}
    if content_disposition:
        response_headers["Content-Disposition"] = content_disposition

    return StreamingResponse(
        file_streamer(),
        media_type=content_type,
        headers=response_headers
    )
