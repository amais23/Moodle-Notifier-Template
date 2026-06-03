from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from src.moodle_client import MoodleClient
from src.storage import Storage
from src.diff_engine import DiffEngine
from src.models import Course

class AnnouncementMonitor:
    """公告監控器，負責追蹤各課程公告討論區的新帖子"""
    
    def __init__(self, client: MoodleClient, storage: Storage):
        self.client = client
        self.storage = storage

    @staticmethod
    def clean_course_name(fullname: str, semester: str) -> str:
        return fullname.replace(semester, "").split("(")[0].strip()

    @staticmethod
    def html_to_text(html_content: str) -> str:
        if not html_content:
            return "無內容"
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            for element in soup(["script", "style"]):
                element.extract()
            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines[:6]) + ("\n..." if len(lines) > 6 else "")
        except Exception:
            return html_content[:300]

    def check(self, courses: List[Course]) -> List[Dict[str, Any]]:
        """檢查所有課程的新公告"""
        notifications = []
        course_ids = [c.id for c in courses]
        if not course_ids:
            return notifications

        # 1. 取得所有討論區列表
        try:
            forums = self.client.get_forums(course_ids)
        except Exception as e:
            self.storage.add_error(f"取得討論區列表失敗: {e}")
            return notifications

        # 2. 篩選出「最新公告」或新聞類討論區
        announcement_forums = []
        for f in forums:
            ftype = f.get("type", "")
            fname = f.get("name", "")
            if ftype == "news" or "公告" in fname or "news" in fname.lower():
                announcement_forums.append(f)

        if not announcement_forums:
            return notifications

        # 3. 取得每個公告討論區的最新貼文
        new_discussions_state = []
        for forum in announcement_forums:
            forum_id = forum.get("id")
            course_id = forum.get("course")
            course_obj = next((c for c in courses if c.id == course_id), None)
            course_fullname = course_obj.fullname if course_obj else ""
            course_name = self.clean_course_name(course_fullname, self.storage.semester)
            
            try:
                discussions = self.client.get_forum_discussions(forum_id, limit=5)
                for d in discussions:
                    modified_dt = datetime.fromtimestamp(d.get("timemodified", 0))
                    new_discussions_state.append({
                        "id": str(d["id"]),
                        "forum_id": str(forum_id),
                        "course_id": str(course_id),
                        "course_name": course_name,
                        "subject": d.get("name", "無標題"),
                        "author": d.get("userfullname", "系統"),
                        "message": d.get("message", ""),
                        "timemodified": d.get("timemodified", 0),
                        "timemodified_str": modified_dt.strftime("%Y-%m-%d %H:%M")
                    })
            except Exception as e:
                self.storage.add_error(f"取得討論區 [ID={forum_id}] 貼文失敗: {e}")

        # 4. 比對舊公告
        old_discussions_dict = self.storage.data.get("announcements", {})
        old_discussions_list = list(old_discussions_dict.values())
        
        is_first_run = len(old_discussions_dict) == 0
        
        if not is_first_run:
            new_items = DiffEngine.detect_new(old_discussions_list, new_discussions_state, "id")
            for item in new_items:
                clean_msg = self.html_to_text(item["message"])
                body = (
                    f"課程：{item['course_name']}\n"
                    f"標題：{item['subject']}\n"
                    f"發布者：{item['author']}\n"
                    f"時間：{item['timemodified_str']}\n"
                    f"內容摘要：\n{clean_msg}"
                )
                url = f"{self.client.base_url}/mod/forum/discuss.php?d={item['id']}"
                notifications.append({
                    "title": f"📢 [最新公告] {item['course_name']}",
                    "body": body,
                    "url": url
                })

        # 5. 更新快取
        updated_discussions_dict = {item["id"]: item for item in new_discussions_state}
        self.storage.data["announcements"] = updated_discussions_dict

        return notifications
