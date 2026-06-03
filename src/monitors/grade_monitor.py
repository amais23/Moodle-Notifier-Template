from typing import List, Dict, Any
from src.moodle_client import MoodleClient
from src.storage import Storage
from src.diff_engine import DiffEngine
from src.models import Course

class GradeMonitor:
    """成績監控器，負責偵測成績發布與分數更新"""
    
    def __init__(self, client: MoodleClient, storage: Storage):
        self.client = client
        self.storage = storage

    @staticmethod
    def clean_course_name(fullname: str, semester: str) -> str:
        return fullname.replace(semester, "").split("(")[0].strip()

    def check(self, courses: List[Course]) -> List[Dict[str, Any]]:
        """檢查所有課程的成績更新"""
        notifications = []
        course_ids = [c.id for c in courses]
        if not course_ids:
            return notifications

        # 1. 取得所有課程的成績明細
        new_grades_state = []
        for course in courses:
            course_name = self.clean_course_name(course.fullname, self.storage.semester)
            try:
                grade_items = self.client.get_grade_items(course.id)
                for item in grade_items:
                    # 略過沒有名稱且非特殊類型的項目
                    item_name = item.get("itemname") or item.get("itemtype")
                    if not item_name or item_name == "course":
                        continue
                        
                    grade_val = item.get("gradeformatted", "—").strip()
                    item_id = item.get("id")
                    
                    # 建立唯一的鍵值（課程ID + 成績項目ID/名稱）
                    unique_key = f"{course.id}_{item_id if item_id is not None else item_name}"
                    
                    new_grades_state.append({
                        "key": unique_key,
                        "course_id": str(course.id),
                        "course_name": course_name,
                        "item_name": item_name,
                        "grade": grade_val
                    })
            except Exception as e:
                self.storage.add_error(f"取得課程 {course_name} 成績失敗: {e}")

        # 2. 比對舊成績快取
        old_grades_dict = self.storage.data.get("grades", {})
        
        is_first_run = len(old_grades_dict) == 0
        
        if not is_first_run:
            # 遍歷新狀態並與舊狀態比對
            for new_item in new_grades_state:
                key = new_item["key"]
                new_grade = new_item["grade"]
                
                # 成績被標示為無成績字元 (例如 '—' or '-')
                has_score = new_grade not in ["—", "-", "", "N/A"]
                
                if key in old_grades_dict:
                    old_grade = old_grades_dict[key].get("grade", "—")
                    if old_grade != new_grade:
                        # 分數發生變化
                        # 情況 A：原本無分數 -> 現在有分數 (成績發布)
                        if old_grade in ["—", "-", "", "N/A"] and has_score:
                            body = (
                                f"課程：{new_item['course_name']}\n"
                                f"項目：{new_item['item_name']}\n"
                                f"成績：🎉 **{new_grade}**"
                            )
                            url = f"{self.client.base_url}/grade/report/user/index.php?id={new_item['course_id']}"
                            notifications.append({
                                "title": f"📊 [成績發布] {new_item['course_name']}",
                                "body": body,
                                "url": url
                            })
                        # 情況 B：原本有分數 -> 分數被更改 (成績更新)
                        elif old_grade not in ["—", "-", "", "N/A"] and has_score:
                            body = (
                                f"課程：{new_item['course_name']}\n"
                                f"項目：{new_item['item_name']}\n"
                                f"原成績：{old_grade}\n"
                                f"新成績：🔄 **{new_grade}**"
                            )
                            url = f"{self.client.base_url}/grade/report/user/index.php?id={new_item['course_id']}"
                            notifications.append({
                                "title": f"📊 [成績更新] {new_item['course_name']}",
                                "body": body,
                                "url": url
                            })
                else:
                    # 全新發布的欄位 (且有分數才推播)
                    if has_score:
                        body = (
                            f"課程：{new_item['course_name']}\n"
                            f"項目：{new_item['item_name']}\n"
                            f"成績：🎉 **{new_grade}**"
                        )
                        url = f"{self.client.base_url}/grade/report/user/index.php?id={new_item['course_id']}"
                        notifications.append({
                            "title": f"📊 [成績發布] {new_item['course_name']}",
                            "body": body,
                            "url": url
                        })

        # 3. 儲存至資料庫
        updated_grades_dict = {item["key"]: item for item in new_grades_state}
        self.storage.data["grades"] = updated_grades_dict

        return notifications
