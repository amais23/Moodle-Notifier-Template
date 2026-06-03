import sys
import os
import json
import hmac
import hashlib
import base64
import time

# Ensure we can import from workspace root
sys.path.append(r"c:\Users\chiah\Documents\moodle notifier")
from src.config import Config
from server.app import app
import server.routers.line_webhook as line_webhook
import server.handlers.command_handlers as command_handlers
from fastapi.testclient import TestClient

# Mock config
mock_config = Config()
mock_config.username = "test_user"
mock_config.password = "test_pass"
mock_config.line_token = "mock_line_token"
mock_config.line_channel_secret = "mock_secret"
mock_config.line_user_id = "mock_user_id"
mock_config.target_semester = "1142"

Config.load = lambda: mock_config
line_webhook.config = mock_config

# Mock MoodleClient
class MockMoodleClientForTest:
    def __init__(self, *args, **kwargs):
        self.token = "mock_moodle_token"
        self.user_id = 99999
        self.fullname = "Mock Student"
        
    def authenticate(self):
        pass
        
    def get_user_courses(self):
        return [
            {"id": 101, "fullname": "1142 演算法 (Algorithms)"},
            {"id": 102, "fullname": "1142 作業系統 (Operating Systems)"}
        ]
        
    def get_assignments(self, course_ids):
        return {
            "courses": [
                {
                    "fullname": "1142 演算法 (Algorithms)",
                    "assignments": [
                        {"id": 5001, "name": "作業一", "duedate": int(time.time() + 86400 * 3)}
                    ]
                }
            ]
        }
        
    def get_submission_status(self, assign_id):
        return {
            "lastattempt": {
                "submission": {
                    "status": "new"
                }
            },
            "feedback": {
                "gradeforstudent": "90.0",
                "comment": "寫得很好！"
            }
        }
        
    def get_grade_items(self, course_id):
        if course_id == 101:
            return [
                {"itemname": "作業一", "gradeformatted": "95.0"},
                {"itemname": "期中考", "gradeformatted": "88.0"}
            ]
        return []
        
    def get_upcoming_events(self, limit=15):
        return [
            {
                "name": "作業二截止",
                "timesort": int(time.time() + 86400 * 2), # 2 days later
                "course": {"fullname": "1142 演算法 (Algorithms)"}
            }
        ]
        
    def get_conversations(self, limit=5):
        return [
            {
                "unreadcount": 1,
                "members": [{"id": 1, "fullname": "王教授"}, {"id": 99999, "fullname": "Mock Student"}],
                "messages": [{"text": "請記得繳交期末專題"}]
            }
        ]
        
    def get_forums(self, course_ids):
        return [{"id": 1, "type": "news", "name": "公告欄"}]
        
    def get_forum_discussions(self, forum_id, limit=5):
        return [
            {
                "subject": "期末考通知",
                "userfullname": "林助教",
                "created": int(time.time() - 86400),
                "message": "期末考將在下週舉行，請注意時間。"
            }
        ]
        
    def get_course_contents(self, course_id):
        return [
            {
                "id": 1,
                "name": "第一單元",
                "modules": [
                    {
                        "modname": "resource",
                        "name": "投影片第一單元",
                        "contents": [
                            {
                                "type": "file",
                                "fileurl": "https://moodle.ntnu.edu.tw/file.pdf",
                                "filename": "unit1.pdf",
                                "filesize": 102400
                            }
                        ]
                    }
                ]
            }
        ]

# Inject MockMoodleClient
command_handlers.get_moodle_client = lambda config: MockMoodleClientForTest()

sent_messages = []
def mock_send_line_reply(reply_token, content, token):
    sent_messages.append(content)

command_handlers.send_line_reply = mock_send_line_reply

client = TestClient(app)

def calculate_signature(body_bytes, secret):
    hash_val = hmac.new(secret.encode('utf-8'), body_bytes, hashlib.sha256).digest()
    return base64.b64encode(hash_val).decode('utf-8')

def send_webhook_message(text):
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "test_reply_token",
                "source": {"type": "user", "userId": "mock_user_id"},
                "message": {"type": "text", "text": text}
            }
        ]
    }
    body_bytes = json.dumps(payload).encode('utf-8')
    sig = calculate_signature(body_bytes, "mock_secret")
    res = client.post(
        "/webhook/line",
        content=body_bytes,
        headers={"Content-Type": "application/json", "x-line-signature": sig}
    )
    assert res.status_code == 200

def send_webhook_postback(data):
    payload = {
        "events": [
            {
                "type": "postback",
                "replyToken": "test_reply_token",
                "source": {"type": "user", "userId": "mock_user_id"},
                "postback": {"data": data}
            }
        ]
    }
    body_bytes = json.dumps(payload).encode('utf-8')
    sig = calculate_signature(body_bytes, "mock_secret")
    res = client.post(
        "/webhook/line",
        content=body_bytes,
        headers={"Content-Type": "application/json", "x-line-signature": sig}
    )
    assert res.status_code == 200

def test_flex_reply_flow():
    # 1. Test /help command
    send_webhook_message("/help")
    assert len(sent_messages) == 1
    assert sent_messages[-1]["type"] == "flex"
    assert "說明書" in sent_messages[-1]["altText"]
    print("Help card test passed!")

    # 2. Test /courses command
    send_webhook_message("/courses")
    assert len(sent_messages) == 2
    assert sent_messages[-1]["type"] == "flex"
    assert "監控課程" in sent_messages[-1]["altText"]
    
    # Safe debug print (ASCII safe)
    print("Courses card content (safe):")
    print(json.dumps(sent_messages[-1], indent=2, ensure_ascii=True))

    # Check buttons
    body_boxes = sent_messages[-1]["contents"]["body"]["contents"]
    
    found_ann_btn = False
    found_file_btn = False
    for course_box in body_boxes:
        for inner in course_box.get("contents", []):
            if inner.get("type") == "box":  # Buttons box
                for btn in inner.get("contents", []):
                    if btn.get("type") == "button":
                        label = btn["action"]["label"]
                        if "公告" in label:
                            found_ann_btn = True
                        if "講義" in label:
                            found_file_btn = True
                            
    assert found_ann_btn, "Could not find announcement button!"
    assert found_file_btn, "Could not find files button!"
    print("Courses card test passed!")

    # 3. Test /grades command
    send_webhook_message("/grades")
    assert len(sent_messages) == 3
    assert sent_messages[-1]["type"] == "flex"
    assert "成績查詢結果" in sent_messages[-1]["altText"]
    print("Grades card test passed!")

    # 4. Test /upcoming command
    send_webhook_message("/upcoming")
    assert len(sent_messages) == 4
    assert sent_messages[-1]["type"] == "flex"
    assert "即將到來事項" in sent_messages[-1]["altText"]
    print("Upcoming card test passed!")

    # 5. Test /messages command
    send_webhook_message("/messages")
    assert len(sent_messages) == 5
    assert sent_messages[-1]["type"] == "flex"
    assert "私訊" in sent_messages[-1]["altText"]
    print("Messages card test passed!")

    # 6. Test /assignments command
    send_webhook_message("/assignments")
    assert len(sent_messages) == 6
    assert sent_messages[-1]["type"] == "flex"
    assert "作業清單" in sent_messages[-1]["altText"]
    print("Assignments card test passed!")

    # 7. Test postback check_submission
    send_webhook_postback("action=check_submission&assign_id=5001")
    assert len(sent_messages) == 7
    assert sent_messages[-1]["type"] == "flex"
    assert "狀態" in sent_messages[-1]["altText"]
    print("Postback check submission test passed!")

    # 8. Test postback course_announcements_choice
    send_webhook_postback("action=course_announcements_choice&course_id=101&course_name=%E6%BC%94%E7%AE%97%E6%B3%95")
    assert len(sent_messages) == 8
    assert sent_messages[-1]["type"] == "flex"
    assert "公告查詢" in sent_messages[-1]["altText"]
    print("Postback announcements choice test passed!")

    # 9. Test postback course_announcements
    send_webhook_postback("action=course_announcements&course_id=101&course_name=%E6%BC%94%E7%AE%97%E6%B3%95&filter=7days")
    assert len(sent_messages) == 9
    assert sent_messages[-1]["type"] == "flex"
    assert "公告清單" in sent_messages[-1]["altText"]
    print("Postback announcements list test passed!")

    # 10. Test postback course_files (now returns section menu)
    send_webhook_postback("action=course_files&course_id=101&course_name=%E6%BC%94%E7%AE%97%E6%B3%95")
    assert len(sent_messages) == 10
    assert sent_messages[-1]["type"] == "flex"
    assert "\u4e3b\u984c\u9078\u55ae" in sent_messages[-1]["altText"]
    print("Postback course files section menu test passed!")

    # 11. Test postback course_section_files (returns file list under section)
    send_webhook_postback("action=course_section_files&course_id=101&course_name=%E6%BC%94%E7%AE%97%E6%B3%95&section_id=1")
    assert len(sent_messages) == 11
    assert sent_messages[-1]["type"] == "flex"
    assert "\u8ab2\u7a0b\u8b1b\u7fa9" in sent_messages[-1]["altText"]
    print("Postback course section files list test passed!")

    # 12. Test postback recent_news
    send_webhook_postback("action=recent_news")
    assert len(sent_messages) == 12
    assert sent_messages[-1]["type"] == "flex"
    assert "\u6700\u8fd1\u6d88\u606f" in sent_messages[-1]["altText"]
    print("Postback recent news test passed!")

    print("All LINE Bot Flex Message flows validated successfully!")

if __name__ == "__main__":
    test_flex_reply_flow()
