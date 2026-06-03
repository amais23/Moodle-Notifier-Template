import os
import sys
import re
import json
import subprocess
from pathlib import Path

class Config:
    """系統設定管理器"""
    
    def __init__(self):
        # 預設參數值
        self.moodle_base_url = "https://moodle3.ntnu.edu.tw"
        self.target_semester = "1142"
        self.data_dir = str(Path(__file__).parent.parent)  # 專案根目錄
        self.max_workers = 5
        self.http_timeout = 15
        self.daily_report_hour = 18
        self.cooldown_hours = 6
        
        # 憑證資料
        self.username = ""
        self.password = ""
        self.line_user_id = ""
        self.line_token = ""
        self.line_channel_secret = ""
        self.discord_webhook_url = ""
        self.discord_bot_token = ""
        self.dashboard_url = ""

    @classmethod
    def load(cls) -> 'Config':
        config = cls()
        
        # 1. 載入非憑證參數（優先從環境變數，其次保留預設）
        config.target_semester = os.environ.get("TARGET_SEMESTER", config.target_semester)
        config.moodle_base_url = os.environ.get("MOODLE_BASE_URL", config.moodle_base_url)
        config.data_dir = os.environ.get("DATA_DIR", config.data_dir)
        config.dashboard_url = os.environ.get("DASHBOARD_URL", "").rstrip("/")
        
        try:
            config.max_workers = int(os.environ.get("MAX_WORKERS", config.max_workers))
        except ValueError:
            pass
            
        try:
            config.http_timeout = int(os.environ.get("HTTP_TIMEOUT", config.http_timeout))
        except ValueError:
            pass
            
        try:
            config.daily_report_hour = int(os.environ.get("DAILY_REPORT_HOUR", config.daily_report_hour))
        except ValueError:
            pass
            
        try:
            config.cooldown_hours = int(os.environ.get("COOLDOWN_HOURS", config.cooldown_hours))
        except ValueError:
            pass

        # 2. 載入憑證（環境變數 -> 本機文字檔/加密檔 -> JSON檔）
        config.username = os.environ.get("MOODLE_USERNAME", "")
        config.password = os.environ.get("MOODLE_PASSWORD", "")
        config.line_user_id = os.environ.get("LINE_USER_ID", "")
        config.line_token = os.environ.get("LINE_TOKEN", "")
        config.line_channel_secret = os.environ.get("LINE_CHANNEL_SECRET", "")
        config.discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
        config.discord_bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")

        # 檢查是否需要載入本機憑證檔
        if not (config.username and config.password and config.line_user_id and config.line_token and config.line_channel_secret and config.discord_bot_token):
            config._load_local_files()
            
        # 檢查是否需要載入 JSON 憑證檔 (相容測試工具)
        if not (config.username and config.password):
            config._load_credentials_json()

        # 驗證必要憑證
        if not config.username or not config.password:
            raise ValueError("❌ 錯誤：未設定 Moodle 帳號或密碼！")
            
        if not config.line_token and not config.discord_webhook_url and not config.discord_bot_token:
            raise ValueError("❌ 錯誤：必須至少設定 LINE_TOKEN、DISCORD_WEBHOOK_URL 或 DISCORD_BOT_TOKEN 其中一種通知管道！")

        return config

    def _decrypt_secure_string(self, file_path: str) -> str:
        """解密 Windows SecureString 檔案"""
        if not os.path.exists(file_path):
            return ""
        if not re.match(r"^[\w\-./\\]+$", file_path):
            raise ValueError(f"偵測到不安全的檔案路徑字元，拒絕解密：{file_path}")
        
        command = f"$sec = Get-Content '{file_path}' | ConvertTo-SecureString; (New-Object System.Management.Automation.PSCredential('Dummy', $sec)).GetNetworkCredential().Password"
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception as e:
            # 如果非 Windows 系統或 PowerShell 出錯，則回傳空字串
            return ""

    def _read_txt_file(self, file_path: str) -> str:
        """讀取純文字檔案內容"""
        p = Path(self.data_dir) / file_path
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return ""

    def _load_local_files(self):
        """讀取本機個別文字檔與加密檔"""
        # Moodle 帳號
        if not self.username:
            self.username = self._read_txt_file("moodle_user.txt")
            
        # Moodle 密碼 (加密)
        if not self.password:
            pass_path = Path(self.data_dir) / "moodle_pass.txt"
            if pass_path.exists():
                self.password = self._decrypt_secure_string(str(pass_path))
                
        # LINE 使用者 ID
        if not self.line_user_id:
            self.line_user_id = self._read_txt_file("line_user.txt")
            
        # LINE Token (加密)
        if not self.line_token:
            token_path = Path(self.data_dir) / "line_token.txt"
            if token_path.exists():
                self.line_token = self._decrypt_secure_string(str(token_path))

        # LINE Channel Secret (加密或文字)
        if not self.line_channel_secret:
            secret_path = Path(self.data_dir) / "line_secret.txt"
            if secret_path.exists():
                self.line_channel_secret = self._decrypt_secure_string(str(secret_path))
                if not self.line_channel_secret:
                    self.line_channel_secret = self._read_txt_file("line_secret.txt")

        # Discord Webhook URL
        if not self.discord_webhook_url:
            self.discord_webhook_url = self._read_txt_file("discord_webhook.txt")

        # Discord Bot Token (加密或文字)
        if not self.discord_bot_token:
            bot_token_path = Path(self.data_dir) / "discord_bot_token.txt"
            if bot_token_path.exists():
                self.discord_bot_token = self._decrypt_secure_string(str(bot_token_path))
                if not self.discord_bot_token:
                    self.discord_bot_token = self._read_txt_file("discord_bot_token.txt")

        # 載入控制台網址
        if not self.dashboard_url:
            self.dashboard_url = self._read_txt_file("dashboard_url.txt").rstrip("/")

    def _load_credentials_json(self):
        """從 moodle_credentials.json 載入憑證"""
        json_path = Path(self.data_dir) / "moodle_credentials.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    creds = json.load(f)
                if not self.username:
                    self.username = creds.get("username", "")
                if not self.password:
                    self.password = creds.get("password", "")
                if not self.line_user_id:
                    self.line_user_id = creds.get("line_user_id", "")
                if not self.line_token:
                    self.line_token = creds.get("line_token", "")
                if not self.line_channel_secret:
                    self.line_channel_secret = creds.get("line_channel_secret", "")
                if not self.discord_webhook_url:
                    self.discord_webhook_url = creds.get("discord_webhook_url", "")
                if not self.discord_bot_token:
                    self.discord_bot_token = creds.get("discord_bot_token", "")
                if not self.dashboard_url:
                    self.dashboard_url = creds.get("dashboard_url", "").rstrip("/")
            except Exception:
                pass
