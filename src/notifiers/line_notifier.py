import requests
import json
from typing import Optional, Dict, Any, List
from src.notifiers.base import NotifierBase

class LineNotifier(NotifierBase):
    """LINE Messaging API Push 通知實作"""
    
    def __init__(self, channel_token: str, user_id: str):
        self.channel_token = channel_token
        self.user_id = user_id
        self.api_url = "https://api.line.me/v2/bot/message/push"

    @property
    def platform_name(self) -> str:
        return "LINE"

    def send_text(self, message: str) -> bool:
        """發送純文字訊息，若長度超過 5000 字會自動分割為多則訊息發送"""
        if not message.strip():
            return False
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_token}",
        }
        
        # LINE 訊息單則上限為 5000 字，在此進行防禦性切段
        message_chunks = self._chunk_message(message, 4900)
        success = True
        
        for chunk in message_chunks:
            payload = {
                "to": self.user_id,
                "messages": [{"type": "text", "text": chunk}]
            }
            try:
                res = requests.post(self.api_url, headers=headers, json=payload, timeout=15)
                if res.status_code != 200:
                    print(f"❌ LINE 發送失敗，狀態碼: {res.status_code}，回應: {res.text}")
                    success = False
            except Exception as e:
                print(f"❌ LINE 發送異常: {e}")
                success = False
                
        return success

    def send_alert(self, title: str, body: str, url: Optional[str] = None) -> bool:
        """發送結構化警示通知（格式化為純文字）"""
        message_parts = [
            f"🔔 {title}",
            "=" * 15,
            body
        ]
        if url:
            message_parts.append(f"🔗 連結：{url}")
            
        return self.send_text("\n".join(message_parts))

    def send_daily_report(self, report: Dict[str, Any]) -> bool:
        """發送每日巡邏報告"""
        date_str = report.get("date", "")
        run_count = report.get("run_count", 0)
        errors = report.get("errors", [])
        pending_list = report.get("pending_list", [])
        
        msg_parts = [
            f"📊 Moodle 每日巡邏報告 ({date_str})",
            "=" * 15,
            f"✅ 今日已為您執行 {run_count} 次檢查。"
        ]
        
        if errors:
            msg_parts.append(f"⚠️ 今日執行期間發生 {len(errors)} 次異常：")
            # 顯示最近 3 筆錯誤
            for err in errors[-3:]:
                msg_parts.append(f"- {err}")
        else:
            msg_parts.append("🎉 今日系統運行穩定，無任何錯誤！")
            
        msg_parts.append("")
        
        if pending_list:
            msg_parts.append("📋 【目前待辦作業】")
            msg_parts.append("-" * 15)
            for item in pending_list:
                msg_parts.append(item)
        else:
            msg_parts.append("🎉 太棒了！目前沒有任何待辦作業！")
            
        return self.send_text("\n".join(msg_parts))

    def _chunk_message(self, message: str, limit: int) -> List[str]:
        """將訊息按照字數限制進行安全切割，避免截斷字詞"""
        if len(message) <= limit:
            return [message]
            
        chunks = []
        lines = message.split("\n")
        current_chunk = []
        current_len = 0
        
        for line in lines:
            line_len = len(line) + 1  # 加上換行符
            if current_len + line_len > limit:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len
                
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        return chunks
