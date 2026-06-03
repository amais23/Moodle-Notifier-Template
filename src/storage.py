import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

class Storage:
    """資料持久化儲存與歷史追蹤"""
    
    def __init__(self, data_dir: str, semester: str):
        self.data_dir = Path(data_dir)
        self.semester = semester
        self.db_file = self.data_dir / f"moodle_data_{semester}.json"
        
        # 記憶體內快取的狀態
        self.data = {
            "courses": {},
            "assignments": {},
            "announcements": {},
            "grades": {},
            "messages": {},
            "notifications_history": {},
            "stats": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "run_count": 0,
                "errors": [],
                "summary_sent": False
            }
        }
        self.load()

    def load(self) -> dict:
        """載入 JSON 資料庫，具備錯誤容忍與舊版本相容"""
        if not self.db_file.exists():
            return self.data
            
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                
            # 相容性檢查與基礎鍵補全
            if isinstance(loaded, dict):
                # 如果是舊結構（只有 courses 與 stats），我們就只更新 stats 且清空舊 courses（因為結構不同了）
                if "courses" in loaded and "assignments" not in loaded:
                    # 舊版結構轉換：重置 courses 為 API 架構，保留 stats
                    self.data["stats"].update(loaded.get("stats", {}))
                else:
                    for k in self.data:
                        if k in loaded:
                            if isinstance(self.data[k], dict):
                                self.data[k].update(loaded[k])
                            else:
                                self.data[k] = loaded[k]
        except Exception as e:
            print(f"⚠️ 載入資料庫時發生異常 (可能檔案毀損)，將初始化新資料庫: {e}")
            
        return self.data

    def save(self) -> None:
        """使用原子性寫入儲存資料"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 確保 stats 內的日期與目前一致
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self.data["stats"].get("date") != today_str:
            # 跨日，重置今日計數與錯誤紀錄
            self.data["stats"]["date"] = today_str
            self.data["stats"]["run_count"] = 0
            self.data["stats"]["errors"] = []
            self.data["stats"]["summary_sent"] = False
            
        temp_file = None
        try:
            # 在同一目錄下建立臨時檔以利原子替換
            with tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8", suffix=".json") as f:
                temp_file = f.name
                json.dump(self.data, f, indent=4, ensure_ascii=False)
                
            os.replace(temp_file, self.db_file)
        except Exception as e:
            print(f"❌ 寫入資料庫失敗: {e}")
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    # --- 統計數據方法 ---
    def get_stats(self) -> dict:
        return self.data["stats"]
        
    def increment_run_count(self) -> None:
        self.data["stats"]["run_count"] = self.data["stats"].get("run_count", 0) + 1
        
    def add_error(self, err_msg: str) -> None:
        time_str = datetime.now().strftime("%H:%M")
        self.data["stats"]["errors"].append(f"[{time_str}] {err_msg}")
        
    def mark_summary_sent(self, sent: bool = True) -> None:
        self.data["stats"]["summary_sent"] = sent

    # --- 通知去重冷卻方法 ---
    def is_notification_cooldown(self, key: str, cooldown_hours: int) -> bool:
        """檢查特定通知是否還在冷卻時間內"""
        history = self.data.get("notifications_history", {})
        last_sent_str = history.get(key)
        if not last_sent_str:
            return False
            
        try:
            last_sent = datetime.fromisoformat(last_sent_str)
            elapsed = datetime.now() - last_sent
            return elapsed.total_seconds() < cooldown_hours * 3600
        except Exception:
            return False

    def record_notification(self, key: str) -> None:
        """記錄通知發送時間"""
        if "notifications_history" not in self.data:
            self.data["notifications_history"] = {}
        self.data["notifications_history"][key] = datetime.now().isoformat()
