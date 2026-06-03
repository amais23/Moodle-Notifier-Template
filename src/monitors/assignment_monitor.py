import hashlib
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from src.moodle_client import MoodleClient
from src.storage import Storage
from src.diff_engine import DiffEngine
from src.models import Course

class AssignmentMonitor:
    """作業監控器，負責偵測新作業、說明修改及到期提醒"""
    
    def __init__(self, client: MoodleClient, storage: Storage):
        self.client = client
        self.storage = storage
        
    @staticmethod
    def clean_course_name(fullname: str, semester: str) -> str:
        """清理課程名稱，例如 '1142計算物理(二)' -> '計算物理'"""
        return fullname.replace(semester, "").split("(")[0].strip()

    @staticmethod
    def html_to_text(html_content: str) -> str:
        """將 HTML 格式內容轉換為純文字，便於通訊軟體閱讀"""
        if not html_content:
            return "無說明"
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # 移除 script 與 style
            for element in soup(["script", "style"]):
                element.extract()
            text = soup.get_text(separator="\n")
            # 清理過多換行
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines[:5]) + ("\n..." if len(lines) > 5 else "")
        except Exception:
            return html_content[:200]

    def check(self, courses: List[Course]) -> List[Dict[str, Any]]:
        """執行作業狀態檢查，回傳需要發送的通知清單"""
        notifications = []
        course_ids = [c.id for c in courses]
        if not course_ids:
            return notifications

        # 1. 批次取得課程的作業清單
        try:
            assigns_data = self.client.get_assignments(course_ids)
        except Exception as e:
            self.storage.add_error(f"取得作業清單失敗: {e}")
            return notifications

        api_courses = assigns_data.get("courses", [])
        
        # 整理出所有作業的基本資料
        raw_assignments = []
        for api_course in api_courses:
            course_id = api_course.get("id")
            course_obj = next((c for c in courses if c.id == course_id), None)
            course_fullname = course_obj.fullname if course_obj else api_course.get("fullname", "")
            course_name = self.clean_course_name(course_fullname, self.storage.semester)
            
            for a in api_course.get("assignments", []):
                raw_assignments.append({
                    "id": a["id"],
                    "course_id": course_id,
                    "course_name": course_name,
                    "name": a["name"],
                    "due_date_ts": a.get("duedate", 0),
                    "intro": a.get("intro", ""),
                })

        if not raw_assignments:
            return notifications

        # 2. 並行查詢每項作業的繳交與成績狀態
        assignment_states = {}
        
        def fetch_status(assign):
            try:
                status_data = self.client.get_submission_status(assign["id"])
                
                # 解析繳交狀態
                last_attempt = status_data.get("lastattempt", {})
                submission = last_attempt.get("submission", {})
                status = submission.get("status", "new")
                
                # 判斷是否已繳交
                # Moodle 狀態可能包含 'submitted' (已繳交) 或 'draft' 等
                is_submitted = status in ["submitted", "draft"]
                
                # 解析評分回饋
                feedback = status_data.get("feedback", {})
                grade = feedback.get("grade", {}).get("grade") if feedback.get("grade") else None
                
                return assign["id"], status, is_submitted, grade
            except Exception as e:
                # 查詢單一作業失敗，容錯處理
                return assign["id"], "unknown", False, None

        max_workers = min(len(raw_assignments), 10)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_status, a) for a in raw_assignments]
            for future in as_completed(futures):
                aid, status, is_submitted, grade = future.result()
                assignment_states[aid] = {
                    "status": status,
                    "is_submitted": is_submitted,
                    "grade": grade
                }

        # 3. 組裝最新的作業狀態清單
        new_assignments_state = []
        for a in raw_assignments:
            aid = a["id"]
            state = assignment_states.get(aid, {"status": "unknown", "is_submitted": False, "grade": None})
            
            due_date_ts = a["due_date_ts"]
            due_date_str = "無截止日期"
            if due_date_ts:
                due_date_str = datetime.fromtimestamp(due_date_ts).strftime("%Y-%m-%d %H:%M")
                
            intro_text = a["intro"]
            intro_hash = hashlib.sha256(intro_text.encode("utf-8")).hexdigest()

            new_assignments_state.append({
                "id": str(aid),
                "course_id": str(a["course_id"]),
                "course_name": a["course_name"],
                "name": a["name"],
                "due_date_ts": due_date_ts,
                "due_date_str": due_date_str,
                "intro_hash": intro_hash,
                "status": state["status"],
                "is_submitted": state["is_submitted"],
                "grade": state["grade"]
            })

        # 4. 比對舊狀態 (從 storage 中讀取)
        old_assignments_dict = self.storage.data.get("assignments", {})
        old_assignments_list = list(old_assignments_dict.values())

        # 首次執行：不推播新增通知，只記錄基準，但進行死線掃描
        is_first_run = len(old_assignments_dict) == 0

        if not is_first_run:
            # 偵測新增作業
            new_items = DiffEngine.detect_new(old_assignments_list, new_assignments_state, "id")
            for item in new_items:
                clean_intro = self.html_to_text(next(a["intro"] for a in raw_assignments if a["id"] == int(item["id"])))
                body = (
                    f"課程：{item['course_name']}\n"
                    f"作業：{item['name']}\n"
                    f"截止時間：{item['due_date_str']}\n"
                    f"說明預覽：\n{clean_intro}"
                )
                url = f"{self.client.base_url}/mod/assign/view.php?id={item['id']}"
                notifications.append({
                    "title": f"🟢 [新增作業] {item['course_name']}",
                    "body": body,
                    "url": url
                })

            # 偵測說明修改
            modified_pairs = DiffEngine.detect_modified(
                old_assignments_list, new_assignments_state, "id", ["intro_hash"]
            )
            for old_item, new_item in modified_pairs:
                url = f"{self.client.base_url}/mod/assign/view.php?id={new_item['id']}"
                body = f"課程：{new_item['course_name']}\n作業：{new_item['name']}\n"
                
                # 如果已繳交，給予警告
                if old_item.get("is_submitted", False):
                    title = f"🚨 [作業說明修改] {new_item['course_name']} (注意：您已繳交)"
                    body += "⚠️ 警告：您已經繳交此作業，但教授剛修改了作業說明，請點擊連結確認修改內容！"
                else:
                    title = f"🟡 [作業說明修改] {new_item['course_name']}"
                    body += "提示：作業說明已被更新，請點擊連結確認新要求。"
                    
                notifications.append({
                    "title": title,
                    "body": body,
                    "url": url
                })

        # 5. 到期提醒 (催繳掃描) — 無論是否為第一次執行，都要掃描未繳交的項目
        now = datetime.now()
        for item in new_assignments_state:
            # 僅針對未繳交且有截止日的作業
            if not item["is_submitted"] and item["due_date_ts"] > 0:
                due_dt = datetime.fromtimestamp(item["due_date_ts"])
                remaining_seconds = (due_dt - now).total_seconds()
                remaining_hours = remaining_seconds / 3600

                url = f"{self.client.base_url}/mod/assign/view.php?id={item['id']}"
                
                # 分級一：24 小時內緊急催繳 (6 小時冷卻)
                if 0 < remaining_hours <= 24:
                    cooldown_key = f"assign_{item['id']}_urgent"
                    # 使用 config 的 cooldown_hours
                    cooldown_time = self.storage.data.get("stats", {}).get("cooldown_hours", 6)
                    if not self.storage.is_notification_cooldown(cooldown_key, cooldown_time):
                        hrs = int(remaining_hours)
                        mins = int((remaining_seconds % 3600) // 60)
                        body = (
                            f"課程：{item['course_name']}\n"
                            f"作業：{item['name']}\n"
                            f"截止時間：{item['due_date_str']}\n"
                            f"剩餘時間：🚨 僅剩 {hrs} 小時 {mins} 分！"
                        )
                        notifications.append({
                            "title": f"🔥 [緊急催繳] {item['course_name']}",
                            "body": body,
                            "url": url
                        })
                        self.storage.record_notification(cooldown_key)
                        
                # 分級二：3 天 (72 小時) 內到期警告 (24 小時冷卻，每天一次)
                elif 24 < remaining_hours <= 72:
                    cooldown_key = f"assign_{item['id']}_warning"
                    if not self.storage.is_notification_cooldown(cooldown_key, 24):
                        days = int(remaining_hours / 24)
                        body = (
                            f"課程：{item['course_name']}\n"
                            f"作業：{item['name']}\n"
                            f"截止時間：{item['due_date_str']}\n"
                            f"剩餘時間：約 {days} 天"
                        )
                        notifications.append({
                            "title": f"⚠️ [作業到期提醒] {item['course_name']}",
                            "body": body,
                            "url": url
                        })
                        self.storage.record_notification(cooldown_key)

        # 6. 更新資料庫中的作業快取
        updated_assignments_dict = {item["id"]: item for item in new_assignments_state}
        self.storage.data["assignments"] = updated_assignments_dict

        return notifications
