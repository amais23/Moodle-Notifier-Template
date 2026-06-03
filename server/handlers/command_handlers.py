import os
import requests
import time
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from src.moodle_client import MoodleClient
from src.config import Config

# 全域快取 MoodleClient 實例，減少重複登入耗時
_moodle_client_cache: MoodleClient = None

def get_moodle_client(config: Config) -> MoodleClient:
    """獲取已認證的 MoodleClient 快取實例"""
    global _moodle_client_cache
    if _moodle_client_cache is None:
        print("[INFO] Initializing Moodle API client and logging in...")
        _moodle_client_cache = MoodleClient(
            config.moodle_base_url, 
            config.username, 
            config.password, 
            config.http_timeout
        )
        _moodle_client_cache.authenticate()
    return _moodle_client_cache

def clean_course_name(fullname: str, semester: str) -> str:
    """清理學期課程名稱"""
    return fullname.replace(semester, "").split("(")[0].strip()

def html_to_text(html_content: str) -> str:
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text().strip()
    except Exception:
        return html_content[:100]

def chunk_text(text: str, limit: int = 4900) -> List[str]:
    """將文字依照長度切塊，避免超過 LINE 單則 5000 字限制"""
    if len(text) <= limit:
        return [text]
    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1
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

def send_line_reply(reply_token: str, content: Any, token: str):
    """呼叫 LINE Reply API 回覆使用者，支援純文字、Flex Message 字典，或預構建 messages 列表"""
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    if isinstance(content, list):
        messages = content[:5]
    elif isinstance(content, dict):
        messages = [content]
    else:
        # 純文字，依長度切塊，防超出 5000 字
        chunks = chunk_text(str(content), 4900)[:5]
        messages = [{"type": "text", "text": chunk} for chunk in chunks]
    
    payload = {
        "replyToken": reply_token,
        "messages": messages
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code != 200:
            print(f"[ERROR] LINE reply failed: {res.status_code}, details: {res.text}")
    except Exception as e:
        print(f"[ERROR] LINE reply exception: {e}")

def build_error_flex(title: str, error_desc: str) -> dict:
    """構建磨砂玻璃紅色調錯誤提示卡片"""
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"⚠️ {title}",
                    "weight": "bold",
                    "size": "md",
                    "color": "#f38ba8"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "text",
                    "text": error_desc,
                    "wrap": True,
                    "size": "sm",
                    "color": "#cdd6f4"
                }
            ]
        }
    }
    return {
        "type": "flex",
        "altText": f"⚠️ {title}",
        "contents": bubble
    }

def build_help_flex(dashboard_url: str) -> dict:
    """構建暗色磨砂底色、藍色漸層 Header 的說明卡片"""
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"},
            "footer": {"backgroundColor": "#1e1e2e"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🎓 NTNU Moodle 說明書",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#89b4fa"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "您可以點選圖文選單或發送以下指令：",
                    "size": "sm",
                    "color": "#a6adc8"
                },
                {"type": "separator", "color": "#313244"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {"type": "text", "text": "📚 /courses — 查看本學期監控課程", "size": "sm", "color": "#cdd6f4"},
                        {"type": "text", "text": "📋 /assignments — 查看未繳作業 (可縮寫 /todo)", "size": "sm", "color": "#cdd6f4"},
                        {"type": "text", "text": "📊 /grades — 查詢所有科目成績明細", "size": "sm", "color": "#cdd6f4"},
                        {"type": "text", "text": "📅 /upcoming — 查詢一週內行事曆待辦", "size": "sm", "color": "#cdd6f4"},
                        {"type": "text", "text": "💬 /messages — 查詢最近的未讀私訊", "size": "sm", "color": "#cdd6f4"},
                        {"type": "text", "text": "❓ /help — 顯示此說明書", "size": "sm", "color": "#cdd6f4"}
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#89b4fa",
                    "action": {
                        "type": "uri",
                        "label": "開啟 Web 控制台",
                        "uri": dashboard_url
                    }
                }
            ]
        }
    }
    return {
        "type": "flex",
        "altText": "🎓 NTNU Moodle 說明書",
        "contents": bubble
    }

def build_courses_flex(semester_courses: list, semester: str, dashboard_url: str) -> dict:
    """構建監控課程的 Flex Message Bubble，包含公告與講義按鈕"""
    contents = []
    for c in semester_courses:
        clean_name = clean_course_name(c["fullname"], semester)
        contents.append({
            "type": "box",
            "layout": "vertical",
            "margin": "md",
            "spacing": "xs",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📖",
                            "flex": 0,
                            "size": "sm"
                        },
                        {
                            "type": "text",
                            "text": clean_name,
                            "wrap": True,
                            "size": "sm",
                            "weight": "bold",
                            "color": "#ffffff"
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "md",
                    "margin": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "color": "#b4befe",
                            "action": {
                                "type": "postback",
                                "label": "📢 公告",
                                "data": f"action=course_announcements_choice&course_id={c['id']}&course_name={urllib.parse.quote(clean_name)}"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "color": "#b4befe",
                            "action": {
                                "type": "postback",
                                "label": "📁 講義",
                                "data": f"action=course_files&course_id={c['id']}&course_name={urllib.parse.quote(clean_name)}"
                            }
                        }
                    ]
                },
                {"type": "separator", "color": "#313244", "margin": "md"}
            ]
        })
        
    if contents:
        contents.pop()  # 移除最後一個分隔線
        
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"},
            "footer": {"backgroundColor": "#1e1e2e"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"📚 本學期 ({semester}) 監控課程",
                    "weight": "bold",
                    "size": "md",
                    "color": "#89b4fa"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": contents
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#89b4fa",
                    "action": {
                        "type": "uri",
                        "label": "開啟 Web 控制台",
                        "uri": dashboard_url
                    }
                }
            ]
        }
    }
    
    return {
        "type": "flex",
        "altText": "📚 本學期監控課程",
        "contents": bubble
    }

def build_assignments_flex(pending_assigns: list, semester: str, dashboard_url: str) -> dict:
    """構建未繳作業的 Flex Message Carousel"""
    bubbles = []
    now = datetime.now()
    
    for cname, assign in pending_assigns[:9]:
        due_ts = assign.get("duedate", 0)
        due_str = "無截止日期"
        time_left = ""
        time_color = "#a6e3a1"  # green
        
        if due_ts > 0:
            due_dt = datetime.fromtimestamp(due_ts)
            due_str = due_dt.strftime("%Y-%m-%d %H:%M")
            if due_dt > now:
                rem = due_dt - now
                days = rem.days
                hrs = rem.seconds // 3600
                if days > 0:
                    time_left = f" (剩 {days} 天 {hrs} 小時)"
                    if days < 3:
                        time_color = "#fab387"  # orange
                else:
                    mins = (rem.seconds % 3600) // 60
                    time_left = f" (🚨 僅剩 {hrs} 小時 {mins} 分)"
                    time_color = "#f38ba8"  # red
            else:
                time_left = " (⚠️ 已逾期)"
                time_color = "#f38ba8"  # red

        bubble = {
            "type": "bubble",
            "styles": {
                "header": {"backgroundColor": "#1e1e2e"},
                "body": {"backgroundColor": "#242538"},
                "footer": {"backgroundColor": "#1e1e2e"}
            },
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": cname,
                        "weight": "bold",
                        "size": "sm",
                        "color": "#89b4fa",
                        "wrap": True
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": assign["name"],
                        "weight": "bold",
                        "size": "md",
                        "color": "#ffffff",
                        "wrap": True
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "xs",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"⏰ 截止：{due_str}",
                                "size": "xs",
                                "color": "#a6adc8"
                            },
                            {
                                "type": "text",
                                "text": time_left,
                                "size": "xs",
                                "color": time_color,
                                "weight": "bold"
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#89b4fa",
                        "action": {
                            "type": "postback",
                            "label": "🔍 查詢繳交狀態",
                            "data": f"action=check_submission&assign_id={assign['id']}"
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)
        
    tail_bubble = {
        "type": "bubble",
        "styles": {
            "body": {"backgroundColor": "#1e1e2e"}
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "justifyContent": "center",
            "contents": [
                {
                    "type": "text",
                    "text": "📊 還有更多作業資訊？",
                    "weight": "bold",
                    "size": "md",
                    "color": "#ffffff",
                    "align": "center"
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#89b4fa",
                    "action": {
                        "type": "uri",
                        "label": "前往 Web 控制台",
                        "uri": dashboard_url
                    }
                }
            ]
        }
    }
    bubbles.append(tail_bubble)
    
    return {
        "type": "flex",
        "altText": "📋 待繳作業清單",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }

def build_grades_flex(courses_grades: List[Dict[str, Any]], semester: str) -> dict:
    """構建成績明細 Flex Carousel"""
    bubbles = []
    for cg in courses_grades:
        cname = cg["course_name"]
        grades = cg["grades"]
        
        body_contents = []
        if not grades:
            body_contents.append({
                "type": "text",
                "text": "📭 尚未有成績登錄資料",
                "color": "#a6adc8",
                "size": "sm",
                "style": "italic"
            })
        else:
            for item in grades[:10]:  # 限制最多 10 個項目防 Payload 過大
                body_contents.append({
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": item["name"],
                            "color": "#cdd6f4",
                            "size": "xs",
                            "flex": 3,
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": item["value"],
                            "color": "#f9e2af" if item["value"] != "—" else "#a6adc8",
                            "size": "xs",
                            "weight": "bold",
                            "flex": 1,
                            "align": "end"
                        }
                    ]
                })
                body_contents.append({"type": "separator", "color": "#313244", "margin": "xs"})
            if body_contents:
                body_contents.pop()  # 移除最後一個分隔線
                
        bubble = {
            "type": "bubble",
            "styles": {
                "header": {"backgroundColor": "#1e1e2e"},
                "body": {"backgroundColor": "#242538"}
            },
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": cname,
                        "weight": "bold",
                        "size": "sm",
                        "color": "#89b4fa",
                        "wrap": True
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": body_contents
            }
        }
        bubbles.append(bubble)
        
    if not bubbles:
        return build_error_flex("成績查詢", "沒有找到任何課程的成績資訊。")
        
    return {
        "type": "flex",
        "altText": "📊 成績查詢結果",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }

def build_upcoming_flex(events: List[Dict[str, Any]], semester: str) -> dict:
    """構建行事曆待辦 Flex Card (時間軸風格)"""
    now_ts = time.time()
    contents = []
    
    valid_events = []
    for ev in events:
        ts = ev.get("timesort", 0)
        if ts - now_ts > 7 * 86400:
            continue
        valid_events.append(ev)
        
    if not valid_events:
        bubble = {
            "type": "bubble",
            "styles": {
                "body": {"backgroundColor": "#242538"}
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "justifyContent": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": "📅 一週內無待辦行事曆事項",
                        "color": "#a6adc8",
                        "align": "center",
                        "weight": "bold"
                    }
                ]
            }
        }
        return {
            "type": "flex",
            "altText": "📅 一週內行事曆",
            "contents": bubble
        }
        
    for ev in valid_events:
        ts = ev.get("timesort", 0)
        dt = datetime.fromtimestamp(ts)
        ev_name = ev.get("name", "未命名事件")
        cname = ev.get("course", {}).get("fullname", "系統")
        if semester in cname:
            cname = clean_course_name(cname, semester)
            
        time_str = dt.strftime("%m/%d %H:%M")
        
        time_left = ts - now_ts
        if time_left < 86400:
            dot_color = "#f38ba8"  # 紅色
            text_color = "#f38ba8"
        elif time_left < 3 * 86400:
            dot_color = "#fab387"  # 橘色
            text_color = "#fab387"
        else:
            dot_color = "#a6e3a1"  # 綠色
            text_color = "#cdd6f4"
            
        contents.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "margin": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 0,
                    "width": "15px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "•",
                            "size": "xl",
                            "color": dot_color,
                            "weight": "bold",
                            "align": "center"
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 1,
                    "contents": [
                        {
                            "type": "text",
                            "text": f"[{cname}] {ev_name}",
                            "weight": "bold",
                            "size": "xs",
                            "color": text_color,
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": f"⏰ {time_str}",
                            "size": "xxs",
                            "color": "#a6adc8"
                        }
                    ]
                }
            ]
        })
        contents.append({"type": "separator", "color": "#313244", "margin": "xs"})
        
    if contents:
        contents.pop()
        
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"📅 即將到來事項 ({semester})",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#89b4fa"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": contents
        }
    }
    
    return {
        "type": "flex",
        "altText": f"📅 即將到來事項 ({semester})",
        "contents": bubble
    }

def build_messages_flex(conversations: List[Dict[str, Any]], client_user_id: int) -> dict:
    """構建最近私訊對話 Flex Card (紅點未讀提示)"""
    contents = []
    if not conversations:
        bubble = {
            "type": "bubble",
            "styles": {
                "body": {"backgroundColor": "#242538"}
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "justifyContent": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": "💬 目前無任何私訊紀錄",
                        "color": "#a6adc8",
                        "align": "center",
                        "weight": "bold"
                    }
                ]
            }
        }
        return {
            "type": "flex",
            "altText": "💬 最近對話",
            "contents": bubble
        }
        
    for convo in conversations:
        unread = convo.get("unreadcount") or 0
        members = convo.get("members", [])
        sender = next((m for m in members if m.get("id") != client_user_id), None)
        sender_name = sender.get("fullname") if sender else "未知使用者"
        
        messages = convo.get("messages", [])
        msg_text = "無訊息"
        if messages:
            msg_text = html_to_text(messages[0].get("text", ""))
            if len(msg_text) > 40:
                msg_text = msg_text[:40] + "..."
                
        dot_box = []
        if unread > 0:
            dot_box.append({
                "type": "text",
                "text": "🔴",
                "size": "xxs",
                "flex": 0,
                "margin": "xs"
            })
            
        contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "margin": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"👤 {sender_name}",
                            "weight": "bold",
                            "size": "sm",
                            "color": "#89b4fa",
                            "flex": 1
                        }
                    ] + dot_box
                },
                {
                    "type": "text",
                    "text": msg_text,
                    "size": "xs",
                    "color": "#cdd6f4",
                    "wrap": True
                }
            ]
        })
        contents.append({"type": "separator", "color": "#313244", "margin": "xs"})
        
    if contents:
        contents.pop()
        
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "💬 最近 Moodle 私訊",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#89b4fa"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": contents
        }
    }
    
    return {
        "type": "flex",
        "altText": "💬 最近 Moodle 私訊",
        "contents": bubble
    }

def build_postback_result_flex(assign_id: str, status_str: str, grade_str: str, feedback_str: str) -> dict:
    """構建獨立的作業繳交詳情 Flex Bubble"""
    status_fg = "#cdd6f4"
    if "已繳交" in status_str:
        status_fg = "#a6e3a1"
    elif "草稿" in status_str:
        status_fg = "#fab387"
    elif "未繳交" in status_str:
        status_fg = "#f38ba8"
        
    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": "🆔 作業 ID",
                    "color": "#a6adc8",
                    "size": "xs",
                    "flex": 1
                },
                {
                    "type": "text",
                    "text": str(assign_id),
                    "color": "#cdd6f4",
                    "size": "xs",
                    "flex": 2
                }
            ]
        },
        {"type": "separator", "color": "#313244", "margin": "xs"},
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": "📝 繳交狀態",
                    "color": "#a6adc8",
                    "size": "xs",
                    "flex": 1
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 2,
                    "contents": [
                        {
                            "type": "text",
                            "text": status_str,
                            "color": status_fg,
                            "size": "xs",
                            "weight": "bold"
                        }
                    ]
                }
            ]
        }
    ]
    
    if grade_str:
        body_contents.append({"type": "separator", "color": "#313244", "margin": "xs"})
        body_contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": "📊 獲得成績",
                    "color": "#a6adc8",
                    "size": "xs",
                    "flex": 1
                },
                {
                    "type": "text",
                    "text": grade_str,
                    "color": "#f9e2af",
                    "size": "xs",
                    "weight": "bold",
                    "flex": 2
                }
            ]
        })
        
    if feedback_str:
        body_contents.append({"type": "separator", "color": "#313244", "margin": "xs"})
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "💬 評語與回饋",
                    "color": "#a6adc8",
                    "size": "xs",
                    "margin": "xs"
                },
                {
                    "type": "text",
                    "text": feedback_str,
                    "color": "#cdd6f4",
                    "size": "xs",
                    "wrap": True,
                    "margin": "xs"
                }
            ]
        })
        
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🔍 作業繳交狀態查詢",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#89b4fa"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": body_contents
        }
    }
    
    return {
        "type": "flex",
        "altText": "🔍 作業狀態查詢結果",
        "contents": bubble
    }

def build_announcement_choice_flex(course_id: int, course_name: str) -> dict:
    """選擇 7 天內或歷史公告的引導卡片"""
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"📢 {course_name} 公告查詢",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#89b4fa",
                    "wrap": True
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "請選擇您要查詢的公告範圍：",
                    "size": "xs",
                    "color": "#a6adc8"
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#89b4fa",
                    "action": {
                        "type": "postback",
                        "label": "📅 7 天內最新公告",
                        "data": f"action=course_announcements&course_id={course_id}&course_name={urllib.parse.quote(course_name)}&filter=7days"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "color": "#313244",
                    "action": {
                        "type": "postback",
                        "label": "📜 歷史公告 (前 5 則)",
                        "data": f"action=course_announcements&course_id={course_id}&course_name={urllib.parse.quote(course_name)}&filter=all"
                    }
                }
            ]
        }
    }
    return {
        "type": "flex",
        "altText": f"📢 {course_name} 公告查詢",
        "contents": bubble
    }

def build_announcements_list_flex(discussions: List[Dict[str, Any]], course_name: str, filter_type: str) -> dict:
    """展示公告列表卡片"""
    title_suffix = "最新公告 (7天內)" if filter_type == "7days" else "歷史公告"
    contents = []
    
    if not discussions:
        contents.append({
            "type": "text",
            "text": "📭 目前無公告內容",
            "color": "#a6adc8",
            "size": "sm",
            "align": "center",
            "style": "italic"
        })
    else:
        for disc in discussions[:5]:
            subject = disc.get("subject", "無主旨")
            author = disc.get("userfullname", "未知講師")
            created_ts = disc.get("created", 0)
            created_str = datetime.fromtimestamp(created_ts).strftime("%m/%d %H:%M") if created_ts else ""
            
            raw_msg = disc.get("message", "")
            preview = html_to_text(raw_msg)
            if len(preview) > 80:
                preview = preview[:80] + "..."
                
            contents.append({
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"📌 {subject}",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#ffffff",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": f"👤 {author} | ⏰ {created_str}",
                        "size": "xxs",
                        "color": "#a6adc8"
                    },
                    {
                        "type": "text",
                        "text": preview,
                        "size": "xs",
                        "color": "#cdd6f4",
                        "wrap": True,
                        "margin": "xs"
                    }
                ]
            })
            contents.append({"type": "separator", "color": "#313244", "margin": "md"})
            
        if contents:
            contents.pop()
            
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"📢 {course_name} - {title_suffix}",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#89b4fa",
                    "wrap": True
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": contents
        }
    }
    return {
        "type": "flex",
        "altText": f"📢 {course_name} 公告清單",
        "contents": bubble
    }

def build_files_list_flex(files: List[Dict[str, Any]], course_name: str, token: str, dashboard_url: str) -> dict:
    """展示講義資源列表卡片"""
    contents = []
    if not files:
        contents.append({
            "type": "text",
            "text": "📭 目前無講義或教材檔案",
            "color": "#a6adc8",
            "size": "sm",
            "align": "center",
            "style": "italic"
        })
    else:
        for f in files[:8]:  # 限制最多 8 個檔案以防長度超出
            fname = f["name"]
            furl = f["url"]
            fsize = f["size"]
            
            if fsize >= 1024 * 1024:
                size_str = f" ({fsize / (1024 * 1024):.1f} MB)"
            elif fsize >= 1024:
                size_str = f" ({fsize / 1024:.1f} KB)"
            elif fsize > 0:
                size_str = f" ({fsize} B)"
            else:
                size_str = ""
                
            encoded_url = urllib.parse.quote_plus(furl)
            dl_url = f"{dashboard_url.rstrip('/')}/api/download?url={encoded_url}&token={token}"
            
            contents.append({
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"📄 {fname}{size_str}",
                        "weight": "bold",
                        "size": "xs",
                        "color": "#ffffff",
                        "wrap": True
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "color": "#313244",
                        "action": {
                            "type": "uri",
                            "label": "⬇️ 下載檔案",
                            "uri": dl_url
                        }
                    }
                ]
            })
            contents.append({"type": "separator", "color": "#313244", "margin": "md"})
            
        if contents:
            contents.pop()
            
    bubble = {
        "type": "bubble",
        "styles": {
            "header": {"backgroundColor": "#1e1e2e"},
            "body": {"backgroundColor": "#242538"}
        },
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"📁 {course_name} 課程講義",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#89b4fa",
                    "wrap": True
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": contents
        }
    }
    return {
        "type": "flex",
        "altText": f"📁 {course_name} 課程講義",
        "contents": bubble
    }

def extract_course_files(contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """從課程內容中提取檔案列表"""
    files = []
    for section in contents:
        for module in section.get("modules", []):
            if module.get("modname") == "resource":
                for content in module.get("contents", []):
                    if content.get("type") == "file":
                        files.append({
                            "name": module.get("name", content.get("filename")),
                            "url": content.get("fileurl"),
                            "size": content.get("filesize", 0)
                        })
    return files

def get_course_announcements(client: MoodleClient, course_id: int, filter_type: str = "7days") -> List[Dict[str, Any]]:
    """獲取課程最新公告"""
    forums = client.get_forums([course_id])
    news_forum = None
    for f in forums:
        if f.get("type") == "news" or "公告" in f.get("name", "") or "News" in f.get("name", ""):
            news_forum = f
            break
    if not news_forum:
        if forums:
            news_forum = forums[0]
        else:
            return []
    discussions = client.get_forum_discussions(news_forum["id"], limit=10)
    if filter_type == "7days":
        now_ts = time.time()
        filtered = []
        for d in discussions:
            created_ts = d.get("created", 0)
            if now_ts - created_ts <= 7 * 86400:
                filtered.append(d)
        return filtered
    else:
        return discussions[:5]

async def handle_command(text: str, reply_token: str, config: Config, base_url: str = None):
    """解析並執行 LINE 指令與 Postback 事件"""
    cmd_parts = text.split(maxsplit=1)
    cmd = cmd_parts[0].lower()
    arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""
    
    dashboard_url = config.dashboard_url
    if not dashboard_url:
        if base_url:
            dashboard_url = base_url.rstrip("/")
        else:
            dashboard_url = "http://localhost:8000"

    # 0. 處理特殊的 /postback 事件
    if cmd == "/postback":
        params = urllib.parse.parse_qs(arg)
        action = params.get("action", [None])[0]
        if action == "check_submission":
            assign_id = params.get("assign_id", [None])[0]
            if assign_id:
                try:
                    client = get_moodle_client(config)
                    status_data = client.get_submission_status(assign_id)
                    last_attempt = status_data.get("lastattempt", {})
                    submission = last_attempt.get("submission", {})
                    status = submission.get("status", "new")
                    
                    status_map = {
                        "submitted": "🟢 已繳交 (Submitted)",
                        "draft": "🟡 草稿 (Draft - 未正式送出)",
                        "new": "🔴 未繳交 (Not submitted)",
                        "reopened": "🔄 已重新開放",
                        "noattempt": "🔴 未繳交 (No attempt)"
                    }
                    status_str = status_map.get(status, f"未知狀態 ({status})")
                    
                    feedback = status_data.get("feedback", {})
                    grade = feedback.get("gradeforstudent", "")
                    grade_str = grade if grade else ""
                    feedback_str = html_to_text(feedback.get("comment", ""))
                    
                    flex_msg = build_postback_result_flex(assign_id, status_str, grade_str, feedback_str)
                    send_line_reply(reply_token, flex_msg, config.line_token)
                except Exception as e:
                    send_line_reply(reply_token, build_error_flex("查詢作業繳交狀態失敗", str(e)), config.line_token)
            else:
                send_line_reply(reply_token, build_error_flex("錯誤", "缺少 assign_id 參數"), config.line_token)
        
        elif action == "course_announcements_choice":
            course_id = params.get("course_id", [None])[0]
            course_name = params.get("course_name", [None])[0]
            if course_id and course_name:
                course_name = urllib.parse.unquote(course_name)
                flex_msg = build_announcement_choice_flex(int(course_id), course_name)
                send_line_reply(reply_token, flex_msg, config.line_token)
            else:
                send_line_reply(reply_token, build_error_flex("錯誤", "缺少課程 ID 或課程名稱"), config.line_token)
                
        elif action == "course_announcements":
            course_id = params.get("course_id", [None])[0]
            course_name = params.get("course_name", [None])[0]
            filter_val = params.get("filter", ["7days"])[0]
            if course_id and course_name:
                course_name = urllib.parse.unquote(course_name)
                try:
                    client = get_moodle_client(config)
                    discussions = get_course_announcements(client, int(course_id), filter_val)
                    flex_msg = build_announcements_list_flex(discussions, course_name, filter_val)
                    send_line_reply(reply_token, flex_msg, config.line_token)
                except Exception as e:
                    send_line_reply(reply_token, build_error_flex("公告查詢失敗", str(e)), config.line_token)
            else:
                send_line_reply(reply_token, build_error_flex("錯誤", "缺少課程 ID 或課程名稱"), config.line_token)
                
        elif action == "course_files":
            course_id = params.get("course_id", [None])[0]
            course_name = params.get("course_name", [None])[0]
            if course_id and course_name:
                course_name = urllib.parse.unquote(course_name)
                try:
                    client = get_moodle_client(config)
                    contents = client.get_course_contents(int(course_id))
                    files = extract_course_files(contents)
                    flex_msg = build_files_list_flex(files, course_name, client.token, dashboard_url)
                    send_line_reply(reply_token, flex_msg, config.line_token)
                except Exception as e:
                    send_line_reply(reply_token, build_error_flex("講義讀取失敗", str(e)), config.line_token)
            else:
                send_line_reply(reply_token, build_error_flex("錯誤", "缺少課程 ID 或課程名稱"), config.line_token)
        return

    # 1. 幫助指令
    if cmd in ["/help", "/start", "/說明"]:
        flex_msg = build_help_flex(dashboard_url)
        send_line_reply(reply_token, flex_msg, config.line_token)
        return

    # 需要 Moodle API 的指令，取得 Client 快取
    try:
        client = get_moodle_client(config)
    except Exception as e:
        send_line_reply(reply_token, build_error_flex("授權失敗", f"Moodle 登入授權失敗，請確認伺服器憑證設定。\n({e})"), config.line_token)
        return

    # 取得課程列表（過濾目前學期）
    try:
        courses_data = client.get_user_courses()
        semester_courses = [c for c in courses_data if config.target_semester in c.get("fullname", "")]
        course_ids = [c["id"] for c in semester_courses]
    except Exception as e:
        send_line_reply(reply_token, build_error_flex("取得課程清單失敗", str(e)), config.line_token)
        return

    # 2. 課程列表 (Flex 卡片)
    if cmd == "/courses":
        if not semester_courses:
            send_line_reply(reply_token, build_error_flex("監控課程", f"📚 本學期 ({config.target_semester}) 沒有正在監控的課程。"), config.line_token)
            return
            
        flex_msg = build_courses_flex(semester_courses, config.target_semester, dashboard_url)
        send_line_reply(reply_token, flex_msg, config.line_token)

    # 3. 待辦作業 (Flex Carousel)
    elif cmd in ["/assignments", "/todo"]:
        if not course_ids:
            send_line_reply(reply_token, build_error_flex("作業清單", "📋 目前無監控課程，故無作業清單。"), config.line_token)
            return

        try:
            assigns_data = client.get_assignments(course_ids)
            api_courses = assigns_data.get("courses", [])
            
            raw_assigns = []
            for ac in api_courses:
                cname = clean_course_name(ac.get("fullname", ""), config.target_semester)
                for a in ac.get("assignments", []):
                    raw_assigns.append((cname, a))
                    
            if not raw_assigns:
                send_line_reply(reply_token, build_help_flex(dashboard_url), config.line_token)
                return

            pending_assigns = []
            def check_assign_status(cname, assign):
                try:
                    status_data = client.get_submission_status(assign["id"])
                    last_attempt = status_data.get("lastattempt", {})
                    submission = last_attempt.get("submission", {})
                    status = submission.get("status", "new")
                    is_submitted = status in ["submitted", "draft"]
                    if not is_submitted:
                        return (cname, assign)
                except Exception:
                    pass
                return None

            with ThreadPoolExecutor(max_workers=min(len(raw_assigns), 10)) as executor:
                futures = [executor.submit(check_assign_status, cn, a) for cn, a in raw_assigns]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        pending_assigns.append(result)

            if pending_assigns:
                pending_assigns.sort(key=lambda x: x[1].get("duedate", 9999999999))
                flex_msg = build_assignments_flex(pending_assigns, config.target_semester, dashboard_url)
                send_line_reply(reply_token, flex_msg, config.line_token)
            else:
                send_line_reply(reply_token, build_error_flex("待繳作業", "🎉 檢查完畢！目前沒有任何待繳交作業！"), config.line_token)
        except Exception as e:
            send_line_reply(reply_token, build_error_flex("查詢作業狀態失敗", str(e)), config.line_token)

    # 4. 成績查詢
    elif cmd == "/grades":
        if not semester_courses:
            send_line_reply(reply_token, build_error_flex("成績查詢", "📊 目前無監控課程，無法查詢成績。"), config.line_token)
            return

        courses_grades = []
        
        def fetch_course_grades(course):
            cname = clean_course_name(course["fullname"], config.target_semester)
            try:
                grade_items = client.get_grade_items(course["id"])
                grades = []
                for item in grade_items:
                    item_name = item.get("itemname") or item.get("itemtype")
                    if not item_name or item_name == "course":
                        continue
                    grade_val = item.get("gradeformatted", "—").strip()
                    grades.append({"name": item_name, "value": grade_val})
                return {"course_name": cname, "grades": grades}
            except Exception as e:
                return {"course_name": cname, "grades": [{"name": "讀取失敗", "value": str(e)}]}

        with ThreadPoolExecutor(max_workers=min(len(semester_courses), 10)) as executor:
            futures = [executor.submit(fetch_course_grades, c) for c in semester_courses]
            for future in as_completed(futures):
                courses_grades.append(future.result())

        courses_grades.sort(key=lambda x: x["course_name"])
        flex_msg = build_grades_flex(courses_grades, config.target_semester)
        send_line_reply(reply_token, flex_msg, config.line_token)

    # 5. 行事曆/即時待辦
    elif cmd == "/upcoming":
        try:
            events = client.get_upcoming_events(limit=15)
            flex_msg = build_upcoming_flex(events, config.target_semester)
            send_line_reply(reply_token, flex_msg, config.line_token)
        except Exception as e:
            send_line_reply(reply_token, build_error_flex("取得行事曆失敗", str(e)), config.line_token)

    # 6. 私訊查詢
    elif cmd == "/messages":
        try:
            conversations = client.get_conversations(limit=5)
            flex_msg = build_messages_flex(conversations, client.user_id)
            send_line_reply(reply_token, flex_msg, config.line_token)
        except Exception as e:
            send_line_reply(reply_token, build_error_flex("取得對話列表失敗", str(e)), config.line_token)

    # 7. 未知指令
    else:
        send_line_reply(
            reply_token, 
            build_error_flex("未知指令", f"指令 '{cmd}' 未被辨識。\n請輸入 /help 查看可用指令清單。"), 
            config.line_token
        )
