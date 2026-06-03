from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from src.moodle_client import MoodleClient
from src.storage import Storage
from src.diff_engine import DiffEngine

class MessageMonitor:
    """私訊監控器，負責將 Moodle 站內未讀私訊轉發至通知平台"""
    
    def __init__(self, client: MoodleClient, storage: Storage):
        self.client = client
        self.storage = storage

    @staticmethod
    def html_to_text(html_content: str) -> str:
        if not html_content:
            return "無內容"
        try:
            # 私訊內容有時可能包含 HTML
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text().strip()
        except Exception:
            return html_content.strip()

    def check(self) -> List[Dict[str, Any]]:
        """檢查未讀私訊"""
        notifications = []
        
        # 1. 取得最近的對話列表
        try:
            conversations = self.client.get_conversations(limit=10)
        except Exception as e:
            self.storage.add_error(f"取得私訊對話列表失敗: {e}")
            return notifications

        # 2. 篩選有未讀訊息且最新訊息非自己發送的對話
        new_messages_state = []
        for convo in conversations:
            convo_id = convo.get("id")
            unread_count = convo.get("unreadcount") or 0
            messages = convo.get("messages", [])
            
            if unread_count > 0 and messages:
                # messages[0] 是最新的一則訊息
                last_msg = messages[0]
                
                # 排除自己發送的訊息（防禦性檢查）
                if last_msg.get("useridfrom") == self.client.user_id:
                    continue
                    
                # 尋找對話發送者（即成員中不是自己的那個人）
                members = convo.get("members", [])
                sender = next((m for m in members if m.get("id") != self.client.user_id), None)
                sender_name = sender.get("fullname") if sender else "未知使用者"
                
                msg_time = last_msg.get("timecreated", 0)
                msg_text = self.html_to_text(last_msg.get("text", ""))
                
                new_messages_state.append({
                    "conversation_id": str(convo_id),
                    "sender_name": sender_name,
                    "text": msg_text,
                    "timecreated": msg_time,
                    "unread_count": unread_count
                })

        # 3. 比對舊私訊狀態快取
        old_messages_dict = self.storage.data.get("messages", {})
        
        is_first_run = len(old_messages_dict) == 0
        
        # 只要不是第一次運行，就偵測是否有新的未讀訊息
        if not is_first_run:
            for new_msg in new_messages_state:
                cid = new_msg["conversation_id"]
                new_time = new_msg["timecreated"]
                
                # 如果是新對話，或是同對話中有更新的訊息時間戳
                old_time = old_messages_dict.get(cid, {}).get("timecreated", 0)
                if cid not in old_messages_dict or new_time > old_time:
                    sender = new_msg["sender_name"]
                    preview = new_msg["text"]
                    if len(preview) > 100:
                        preview = preview[:100] + "..."
                        
                    body = (
                        f"發送者：{sender}\n"
                        f"內容摘要：\n{preview}"
                    )
                    url = f"{self.client.base_url}/message/index.php"
                    
                    notifications.append({
                        "title": f"💬 [Moodle 私訊] 來自 {sender}",
                        "body": body,
                        "url": url
                    })

        # 4. 更新資料庫快取
        updated_messages_dict = {}
        # 為了避免快取無限膨脹，我們保留目前有未讀的，以及原本就快取著的已讀對話時間戳
        # 先載入舊的
        for cid, old_val in old_messages_dict.items():
            updated_messages_dict[cid] = old_val
        # 用新的（未讀）覆蓋或新增
        for item in new_messages_state:
            updated_messages_dict[item["conversation_id"]] = {
                "conversation_id": item["conversation_id"],
                "sender_name": item["sender_name"],
                "timecreated": item["timecreated"]
            }
            
        self.storage.data["messages"] = updated_messages_dict

        return notifications
