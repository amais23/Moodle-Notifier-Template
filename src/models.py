from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Course:
    id: int
    fullname: str
    shortname: str

@dataclass
class Assignment:
    id: int
    course_id: int
    course_name: str
    name: str
    due_date: Optional[datetime]  # 由 Unix timestamp 轉換
    intro: str                    # HTML 說明文檔
    status: str                   # "submitted" | "new" | "draft" 等
    grade: Optional[str] = None   # 成績回饋
    intro_hash: str = ""          # 說明內容 Hash

@dataclass
class Announcement:
    id: int
    course_id: int
    course_name: str
    title: str
    author: str
    message: str                  # HTML 內容
    time_modified: datetime

@dataclass
class GradeItem:
    course_id: int
    course_name: str
    item_name: str
    grade: Optional[str]          # 分數 (例如 "100.00" 或 "—")

@dataclass
class MoodleMessage:
    conversation_id: int
    sender_name: str
    text: str
    time: datetime
    is_read: bool

@dataclass
class CalendarEvent:
    id: int
    name: str
    course_name: str
    due_date: datetime
    event_type: str
    url: str
