import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from src.notifiers.base import NotifierBase

class DiscordNotifier(NotifierBase):
    """Discord Webhook 通知實作"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    @property
    def platform_name(self) -> str:
        return "Discord"

    def send_text(self, message: str) -> bool:
        """發送普通純文字訊息到 Discord"""
        if not message.strip():
            return False
            
        payload = {"content": message}
        try:
            res = requests.post(self.webhook_url, json=payload, timeout=15)
            if res.status_code not in [200, 204]:
                print(f"❌ Discord 發送失敗，狀態碼: {res.status_code}，回應: {res.text}")
                return False
            return True
        except Exception as e:
            print(f"❌ Discord 發送異常: {e}")
            return False

    def send_alert(self, title: str, body: str, url: Optional[str] = None) -> bool:
        """發送富文字 (Embed) 警示通知"""
        # 根據標題或內容關鍵字，自動決定 Embed 卡片的側邊顏色
        color = 3447003  # 預設為藍色 (Blue)
        
        lower_title = title.lower()
        if any(k in lower_title for k in ["新增", "🟢", "success", "成功"]):
            color = 3066993  # 綠色 (Green)
        elif any(k in lower_title for k in ["更新", "修改", "黃色", "🟡", "warning", "⚠️"]):
            color = 15105570  # 黃色 (Yellow)
        elif any(k in lower_title for k in ["緊急", "催繳", "🔥", "🚨", "critical", "error", "失敗"]):
            color = 15158332  # 紅色 (Red)

        embed = {
            "title": title,
            "description": body,
            "color": color,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if url:
            embed["url"] = url

        payload = {"embeds": [embed]}
        
        try:
            res = requests.post(self.webhook_url, json=payload, timeout=15)
            if res.status_code not in [200, 204]:
                print(f"❌ Discord Embed 發送失敗，狀態碼: {res.status_code}，回應: {res.text}")
                return False
            return True
        except Exception as e:
            print(f"❌ Discord Embed 發送異常: {e}")
            return False

    def send_daily_report(self, report: Dict[str, Any]) -> bool:
        """發送結構化 Embed 每日巡邏報告"""
        date_str = report.get("date", "")
        run_count = report.get("run_count", 0)
        errors = report.get("errors", [])
        pending_list = report.get("pending_list", [])

        # 狀態描述與顏色
        status_text = "🎉 系統運行穩定，無任何錯誤！"
        color = 3066993  # 綠色
        
        if errors:
            status_text = f"⚠️ 發生了 {len(errors)} 次異常。\n"
            # 顯示最近 3 個錯誤
            for err in errors[-3:]:
                status_text += f"- {err}\n"
            color = 15105570  # 黃色

        # 待辦清單描述
        if pending_list:
            pending_desc = "\n".join(pending_list)
        else:
            pending_desc = "🎉 太棒了！目前沒有任何待辦作業！"

        embed = {
            "title": f"📊 Moodle 每日巡邏報告 ({date_str})",
            "color": color,
            "fields": [
                {
                    "name": "⚙️ 巡邏狀態",
                    "value": f"今日已執行 **{run_count}** 次檢查。\n{status_text}",
                    "inline": False
                },
                {
                    "name": "📋 目前待辦作業",
                    "value": pending_desc,
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        payload = {"embeds": [embed]}
        
        try:
            res = requests.post(self.webhook_url, json=payload, timeout=15)
            if res.status_code not in [200, 204]:
                print(f"❌ Discord 報告發送失敗，狀態碼: {res.status_code}，回應: {res.text}")
                return False
            return True
        except Exception as e:
            print(f"❌ Discord 報告發送異常: {e}")
            return False
