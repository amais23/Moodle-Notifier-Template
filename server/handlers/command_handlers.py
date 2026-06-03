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

def build_courses_flex(semester_courses: list, semester: str, dashboard_url: str) -> dict:
    """構建監控課程的 Flex Message Bubble"""
    contents = []
    for c in semester_courses:
        clean_name = clean_course_name(c["fullname"], semester)
        contents.append({
            "type": "box",
            "layout": "horizontal",
            "margin": "md",
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
                    "color": "#e0e0e0"
                }
            ]
        })
        
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
            "spacing": "sm",
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
    
    # 最多顯示 9 個作業，最後留 1 格給外連 Dashboard
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
        
    # 加入外連 Web Dashboard 卡片
    tail_bubble = {
        "type": "bubble",
        "styles": {
            "body": {"backgroundColor": "#1e1e2e"}
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "gravity": "center",
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

async def handle_command(text: str, reply_token: str, config: Config):
    """解析並執行 LINE 指令與 Postback 事件"""
    cmd_parts = text.split(maxsplit=1)
    cmd = cmd_parts[0].lower()
    arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

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
                    grade_str = f"\n📊 成績：{grade}" if grade else ""
                    
                    reply_text = (
                        f"🔍 作業狀態查詢結果：\n"
                        f"--------------------\n"
                        f"🆔 作業 ID: {assign_id}\n"
                        f"📝 狀態: {status_str}{grade_str}\n"
                    )
                    send_line_reply(reply_token, reply_text, config.line_token)
                except Exception as e:
                    send_line_reply(reply_token, f"❌ 查詢作業繳交狀態失敗: {e}", config.line_token)
            else:
                send_line_reply(reply_token, "❌ 缺少 assign_id 參數", config.line_token)
        return

    # 1. 幫助指令
    if cmd in ["/help", "/start", "/說明"]:
        reply_msg = (
            "🎓 NTNU Moodle 互動助理\n"
            "====================\n"
            "您可以點選下方圖文選單，或直接發送以下指令：\n\n"
            "📚 /courses — 查看本學期監控課程\n"
            "📋 /assignments — 查看未繳作業 (可縮寫 /todo)\n"
            "📊 /grades — 查詢所有科目成績明細\n"
            "📅 /upcoming — 查詢一週內行事曆待辦\n"
            "💬 /messages — 查詢最近的未讀私訊\n"
            "❓ /help — 顯示此說明"
        )
        send_line_reply(reply_token, reply_msg, config.line_token)
        return

    # 需要 Moodle API 的指令，取得 Client 快取
    try:
        client = get_moodle_client(config)
    except Exception as e:
        send_line_reply(reply_token, f"❌ Moodle 登入授權失敗，請確認伺服器憑證設定。({e})", config.line_token)
        return

    # 取得課程列表（過濾目前學期）
    try:
        courses_data = client.get_user_courses()
        semester_courses = [c for c in courses_data if config.target_semester in c.get("fullname", "")]
        course_ids = [c["id"] for c in semester_courses]
    except Exception as e:
        send_line_reply(reply_token, f"❌ 取得課程清單失敗: {e}", config.line_token)
        return

    dashboard_url = os.environ.get("DASHBOARD_URL", "https://moodle-notifier-c.onrender.com")

    # 2. 課程列表 (Flex 卡片)
    if cmd == "/courses":
        if not semester_courses:
            send_line_reply(reply_token, f"📚 本學期 ({config.target_semester}) 沒有正在監控的課程。", config.line_token)
            return
            
        flex_msg = build_courses_flex(semester_courses, config.target_semester, dashboard_url)
        send_line_reply(reply_token, flex_msg, config.line_token)

    # 3. 待辦作業 (Flex Carousel)
    elif cmd in ["/assignments", "/todo"]:
        if not course_ids:
            send_line_reply(reply_token, "📋 目前無監控課程，故無作業清單。", config.line_token)
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
                send_line_reply(reply_token, "🎉 太棒了！本學期目前沒有任何作業項目！", config.line_token)
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
                # 排序 (按截止日期從小到大)
                pending_assigns.sort(key=lambda x: x[1].get("duedate", 9999999999))
                flex_msg = build_assignments_flex(pending_assigns, config.target_semester, dashboard_url)
                send_line_reply(reply_token, flex_msg, config.line_token)
            else:
                send_line_reply(reply_token, "🎉 檢查完畢！目前沒有任何待繳交作業！", config.line_token)
        except Exception as e:
            send_line_reply(reply_token, f"❌ 查詢作業狀態失敗: {e}", config.line_token)

    # 4. 成績查詢
    elif cmd == "/grades":
        if not semester_courses:
            send_line_reply(reply_token, "📊 目前無監控課程，無法查詢成績。", config.line_token)
            return

        lines = ["📊 本學期科目成績明細：", "===================="]
        for course in semester_courses:
            cname = clean_course_name(course["fullname"], config.target_semester)
            try:
                grade_items = client.get_grade_items(course["id"])
                course_grades = []
                for item in grade_items:
                    item_name = item.get("itemname") or item.get("itemtype")
                    if not item_name or item_name == "course":
                        continue
                    grade_val = item.get("gradeformatted", "—").strip()
                    course_grades.append(f"  - {item_name}: {grade_val}")
                
                if course_grades:
                    lines.append(f"\n📚 {cname}：")
                    lines.extend(course_grades)
            except Exception as e:
                lines.append(f"\n📚 {cname}：讀取失敗 ({e})")
                
        send_line_reply(reply_token, "\n".join(lines), config.line_token)

    # 5. 行事曆/即時待辦
    elif cmd == "/upcoming":
        try:
            events = client.get_upcoming_events(limit=15)
            if not events:
                send_line_reply(reply_token, "📅 行事曆中目前沒有即將到來的事項。", config.line_token)
                return
                
            lines = ["📅 即將到來事項 (一週內)：", "--------------------"]
            now_ts = time.time()
            for ev in events:
                ts = ev.get("timesort", 0)
                if ts - now_ts > 7 * 86400:
                    continue
                dt = datetime.fromtimestamp(ts)
                ev_name = ev.get("name", "未命名事件")
                cname = ev.get("course", {}).get("fullname", "系統")
                if config.target_semester in cname:
                    cname = clean_course_name(cname, config.target_semester)
                lines.append(
                    f"📌 [{cname}] {ev_name}\n"
                    f"⏰ 時間：{dt.strftime('%m/%d (%a) %H:%M')}\n"
                )
                
            if len(lines) == 2:
                send_line_reply(reply_token, "📅 行事曆中一週內沒有即將到來的事項。", config.line_token)
            else:
                send_line_reply(reply_token, "\n".join(lines), config.line_token)
        except Exception as e:
            send_line_reply(reply_token, f"❌ 取得行事曆失敗: {e}", config.line_token)

    # 6. 私訊查詢
    elif cmd == "/messages":
        try:
            conversations = client.get_conversations(limit=5)
            if not conversations:
                send_line_reply(reply_token, "💬 目前無任何聯絡人私訊紀錄。", config.line_token)
                return
                
            lines = ["💬 最近的 Moodle 對話：", "--------------------"]
            for convo in conversations:
                unread = convo.get("unreadcount") or 0
                members = convo.get("members", [])
                sender = next((m for m in members if m.get("id") != client.user_id), None)
                sender_name = sender.get("fullname") if sender else "未知使用者"
                
                messages = convo.get("messages", [])
                msg_text = "無訊息"
                if messages:
                    msg_text = html_to_text(messages[0].get("text", ""))
                    if len(msg_text) > 40:
                        msg_text = msg_text[:40] + "..."
                        
                unread_tag = " 🔴" if unread > 0 else ""
                lines.append(f"👤 {sender_name}{unread_tag}\n✉️ {msg_text}\n")
                
            send_line_reply(reply_token, "\n".join(lines), config.line_token)
        except Exception as e:
            send_line_reply(reply_token, f"❌ 取得對話列表失敗: {e}", config.line_token)

    # 7. 未知指令
    else:
        send_line_reply(
            reply_token, 
            f"❓ 未知指令: '{cmd}'\n請輸入 /help 查看可用指令清單。", 
            config.line_token
        )
