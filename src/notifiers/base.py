from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class NotifierBase(ABC):
    """通知發送的抽象基類，所有通知平台都必須實作此介面"""
    
    @abstractmethod
    def send_text(self, message: str) -> bool:
        """發送純文字訊息"""
        pass
    
    @abstractmethod
    def send_alert(self, title: str, body: str, url: Optional[str] = None) -> bool:
        """發送結構化警示通知（含標題、主體內容與可選連結）"""
        pass
    
    @abstractmethod
    def send_daily_report(self, report: Dict[str, Any]) -> bool:
        """發送每日統計日報"""
        pass
        
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名稱（用於日誌紀錄）"""
        pass
