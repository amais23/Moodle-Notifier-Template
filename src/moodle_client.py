import requests
import time
from typing import List, Dict, Any, Optional
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

class MoodleClient:
    """Moodle Web Services API 客戶端"""
    
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 15):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.fullname: str = ""
        
        # 建立 Session 並配置自動重試
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def authenticate(self) -> None:
        """透過 login/token.php 取得 Mobile App Web Service Token 並取得使用者資訊"""
        url = f"{self.base_url}/login/token.php"
        payload = {
            "username": self.username,
            "password": self.password,
            "service": "moodle_mobile_app",
        }
        
        try:
            res = self.session.post(url, data=payload, timeout=self.timeout)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            raise RuntimeError(f"連線至 Moodle 伺服器失敗: {e}")
            
        if "token" in data:
            self.token = data["token"]
        else:
            error_msg = data.get("error", "未知錯誤")
            raise ValueError(f"Moodle 登入授權失敗: {error_msg}")
            
        # 取得登入者基本資訊以取得 user_id
        site_info = self._call_raw_api("core_webservice_get_site_info")
        self.user_id = site_info.get("userid")
        self.fullname = site_info.get("fullname", "")
        
        if not self.user_id:
            raise ValueError("無法從 Moodle 取得使用者識別碼 (User ID)")

    def _call_raw_api(self, function: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """調用底層 Moodle Web Service REST API"""
        if not self.token and function != "core_webservice_get_site_info":
            # 延遲驗證
            self.authenticate()
            
        url = f"{self.base_url}/webservice/rest/server.php"
        payload = {
            "wstoken": self.token,
            "wsfunction": function,
            "moodlewsrestformat": "json",
        }
        if params:
            payload.update(params)
            
        try:
            res = self.session.post(url, data=payload, timeout=self.timeout)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            raise RuntimeError(f"呼叫 API {function} 失敗: {e}")
            
        # Moodle API 錯誤通常會回傳一個包含 exception 的 JSON 物件
        if isinstance(data, dict) and "exception" in data:
            raise RuntimeError(f"Moodle API 回傳異常 ({function}): {data.get('message')}")
            
        return data

    # --- 課程 API ---
    def get_user_courses(self) -> List[Dict[str, Any]]:
        """取得使用者的所有課程"""
        return self._call_raw_api("core_enrol_get_users_courses", {"userid": self.user_id})

    def get_course_contents(self, course_id: int) -> List[Dict[str, Any]]:
        """取得單門課程內容結構"""
        return self._call_raw_api("core_course_get_contents", {"courseid": course_id})

    # --- 作業 API ---
    def get_assignments(self, course_ids: List[int]) -> Dict[str, Any]:
        """批量取得課程作業"""
        params = {}
        for i, cid in enumerate(course_ids):
            params[f"courseids[{i}]"] = cid
        return self._call_raw_api("mod_assign_get_assignments", params)

    def get_submission_status(self, assign_id: int) -> Dict[str, Any]:
        """取得單一作業繳交狀態"""
        return self._call_raw_api("mod_assign_get_submission_status", {"assignid": assign_id})

    # --- 討論區與公告 API ---
    def get_forums(self, course_ids: List[int]) -> List[Dict[str, Any]]:
        """取得課程討論區列表"""
        params = {}
        for i, cid in enumerate(course_ids):
            params[f"courseids[{i}]"] = cid
        return self._call_raw_api("mod_forum_get_forums_by_courses", params)

    def get_forum_discussions(self, forum_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """取得特定討論區的最新討論串列表"""
        res = self._call_raw_api("mod_forum_get_forum_discussions", {
            "forumid": forum_id,
            "sortorder": 3,  # 按時間修改排序
            "perpage": limit
        })
        return res.get("discussions", [])

    # --- 成績 API ---
    def get_grade_items(self, course_id: int) -> List[Dict[str, Any]]:
        """取得單一課程的成績明細"""
        res = self._call_raw_api("gradereport_user_get_grade_items", {
            "courseid": course_id,
            "userid": self.user_id
        })
        # 取得 usergrades 底下的第一個 usergrade 底下的 gradeitems
        usergrades = res.get("usergrades", [])
        if usergrades:
            return usergrades[0].get("gradeitems", [])
        return []

    # --- 私訊 API ---
    def get_unread_conversations_count(self) -> int:
        """取得未讀私訊對話總數"""
        res = self._call_raw_api("core_message_get_unread_conversation_counts")
        # 回傳結構範例: {"favourites": 0, "types": {"1": 0, "2": 0, "3": 0}}
        # types 通常是不同類型的對話類型，加總即為未讀數
        types = res.get("types", {})
        return sum(types.values()) if isinstance(types, dict) else 0

    def get_conversations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """取得最近的對話列表"""
        res = self._call_raw_api("core_message_get_conversations", {
            "userid": self.user_id,
            "limitnum": limit
        })
        return res.get("conversations", [])

    # --- 行事曆 API ---
    def get_upcoming_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """取得即將到來的事項"""
        now_ts = int(time.time())
        res = self._call_raw_api("core_calendar_get_action_events_by_timesort", {
            "timesortfrom": now_ts,
            "limitnum": limit
        })
        return res.get("events", [])
