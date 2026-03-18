import os
import json
import requests
import hashlib
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ==========================================
# 1. 基礎設定區
# ==========================================

try:
    MOODLE_USERNAME = "請填寫學號"  # <--- 填寫你的學號
    MOODLE_PASSWORD = os.environ.get("MOODLE_PASSWORD") # <--- 在 Setting > secrets and variables > Repository secrets 中設定 MOODLE_PASSWORD
    LINE_USER_ID = "請填寫你的LINE_USER_ID" # <--- 填寫你的 ID (U開頭)
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_TOKEN")# <--- 在 Setting > secrets and variables > Repository secrets 中設定 LINE_TOKEN
    TARGET_SEMESTER = "1142" # <--- 填寫當前的學期

    if not MOODLE_PASSWORD or not LINE_CHANNEL_ACCESS_TOKEN:
        raise ValueError("環境變數未設定！請確認已在 GitHub Secrets 中設定 MOODLE_PASSWORD 與 LINE_TOKEN。")
except Exception as e:
    print(f"❌ 讀取憑證失敗：{e}")
    exit()

DATA_FILE = f"moodle_data_{TARGET_SEMESTER}.json"

# ==========================================
# 2. 功能函式區
# ==========================================


def send_line_push_message(text_message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": text_message}]}
    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(payload), timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"LINE 發送異常: {e}")
        return False


def moodle_login(session):
    login_url = "https://moodle3.ntnu.edu.tw/login/index.php"
    res = session.get(login_url)
    soup = BeautifulSoup(res.text, "html.parser")
    logintoken_tag = soup.find("input", {"name": "logintoken"})
    if not logintoken_tag:
        raise Exception("找不到 logintoken，登入頁面可能改版。")

    payload = {
        "username": MOODLE_USERNAME,
        "password": MOODLE_PASSWORD,
        "logintoken": logintoken_tag["value"],
    }
    login_res = session.post(login_url, data=payload)
    if "login/index.php" in login_res.url:
        raise Exception("登入失敗，請檢查帳號密碼。")
    return True


def fetch_target_courses(session):
    frontpage_url = "https://moodle3.ntnu.edu.tw/"
    res = session.get(frontpage_url)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    courses_dict = {}
    for card in soup.find_all("div", class_="card"):
        course_id = card.get("data-courseid")
        title_tag = card.find("h4", class_="card-title")
        if (
            course_id
            and title_tag
            and TARGET_SEMESTER in title_tag.get_text(strip=True)
        ):
            courses_dict[course_id] = title_tag.get_text(strip=True)
    return courses_dict


def get_content_hash(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def parse_moodle_date(date_str):
    """將 Moodle 的中文時間轉為 Python datetime 物件，以便計算倒數時間"""
    if not date_str:
        return None
    match = re.search(
        r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日.*?\s+(\d{1,2}):(\d{2})", date_str
    )
    if match:
        try:
            y, m, d, h, minute = map(int, match.groups())
            return datetime(y, m, d, h, minute)
        except:
            pass
    return None


def fetch_inner_details(session, url, item_type):
    details = {"hash": "", "status": "", "due_date": "", "is_submitted": True}
    if not url:
        return details

    try:
        res = session.get(url, timeout=10, stream=True)
        if "text/html" not in res.headers.get("Content-Type", ""):
            file_size = res.headers.get("Content-Length", "")
            details["hash"] = f"file_size_{file_size}" if file_size else "unknown_file"
            return details

        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        if item_type == "作業":
            status_label = soup.find(
                lambda tag: tag.name in ["th", "td"] and "繳交狀態" in tag.text
            )
            if status_label:
                next_td = status_label.find_next_sibling("td")
                if next_td:
                    status_text = next_td.text.strip()
                    details["status"] = status_text
                    if any(
                        k in status_text
                        for k in ["未繳交", "沒有繳交", "尚未繳交", "No attempt"]
                    ):
                        details["is_submitted"] = False

            due_label = soup.find(
                lambda tag: (
                    tag.name in ["th", "td"]
                    and any(
                        k in tag.text
                        for k in ["截止", "Due", "規定繳交時間", "繳交期限"]
                    )
                )
            )
            if due_label:
                next_td = due_label.find_next_sibling("td")
                if next_td:
                    details["due_date"] = next_td.text.strip()

        main_content = soup.find("div", role="main")
        if main_content:
            for table in main_content.find_all("table", class_="generaltable"):
                table.extract()
            details["hash"] = get_content_hash(main_content.get_text(strip=True))

    except Exception as e:
        print(f"抓取內部網址失敗 {url}: {e}")

    return details


def fetch_and_parse_course(session, course_id):
    url = f"https://moodle3.ntnu.edu.tw/course/view.php?id={course_id}"
    res = session.get(url)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    course_data = []
    for sec in soup.select("li.section.main"):
        h3 = sec.select_one("h3.sectionname")
        if not h3:
            continue
        topic_name = h3.get_text(strip=True)

        items = []
        for act in sec.select("li.activity"):
            a_tag = act.find("a")
            if a_tag:
                name_span = act.select_one("span.instancename")
                item_name = name_span.get_text(strip=True) if name_span else "未知"
                accesshide = act.select_one("span.accesshide")
                if accesshide:
                    item_name = item_name.replace(
                        accesshide.get_text(strip=True), ""
                    ).strip()

                item_type = (
                    "檔案"
                    if "modtype_resource" in act.get("class", [])
                    else "作業"
                    if "modtype_assign" in act.get("class", [])
                    else "討論區"
                    if "modtype_forum" in act.get("class", [])
                    else "其他"
                )

                link = a_tag.get("href", "")
                details = fetch_inner_details(session, link, item_type)

                items.append(
                    {
                        "name": item_name,
                        "link": link,
                        "type": item_type,
                        "hash": details["hash"],
                        "status": details["status"],
                        "due_date": details["due_date"],
                        "is_submitted": details["is_submitted"],
                    }
                )
        course_data.append({"topic": topic_name, "items": items})
    return course_data


# ==========================================
# 3. 主程式與排程邏輯
# ==========================================


def main():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 啟動監控腳本")

    old_db = {
        "courses": {},
        "stats": {
            "date": today_str,
            "run_count": 0,
            "errors": [],
            "summary_sent": False,
        },
    }
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                loaded = json.load(f)
                if "stats" in loaded:
                    old_db = loaded
            except:
                pass

    stats = old_db["stats"]

    if stats["date"] != today_str:
        if not stats["summary_sent"] and stats["run_count"] > 0:
            msg = f"⚠️ [補發] 昨天的 Moodle 日報 ({stats['date']})\n運行次數: {stats['run_count']}\n"
            if stats["errors"]:
                msg += f"❌ 錯誤紀錄: {len(stats['errors'])} 筆\n"
            send_line_push_message(msg)
        stats = {"date": today_str, "run_count": 0, "errors": [], "summary_sent": False}

    stats["run_count"] += 1
    current_courses_db = {}

    all_new_notifications = []
    pending_list = []
    urgent_list = []

    try:
        with requests.Session() as session:
            moodle_login(session)
            courses_dict = fetch_target_courses(session)

            for course_id, course_name in courses_dict.items():
                print(f"檢查中: {course_name} ...")
                current_course_data = fetch_and_parse_course(session, course_id)
                current_courses_db[course_id] = current_course_data

                short_course = (
                    course_name.replace(TARGET_SEMESTER, "").split("(")[0].strip()
                )

                for current_topic in current_course_data:
                    topic_name = current_topic["topic"]
                    current_items = current_topic["items"]

                    for item in current_items:
                        if item["type"] == "作業" and not item.get(
                            "is_submitted", True
                        ):
                            due_str = item.get("due_date", "")
                            due_dt = parse_moodle_date(due_str)

                            pending_msg = f"- [{short_course}] {item['name']}"
                            if due_str:
                                pending_msg += f"\n  (截止: {due_str})"
                            pending_list.append(pending_msg)

                            if due_dt:
                                remaining = due_dt - now
                                if timedelta(0) < remaining <= timedelta(hours=24):
                                    hrs = int(remaining.total_seconds() // 3600)
                                    mins = int((remaining.total_seconds() % 3600) // 60)
                                    urgent_list.append(
                                        f"🔥 [{short_course}] {item['name']} (剩 {hrs}小時{mins}分)"
                                    )

                    if not old_db["courses"]:
                        continue
                    old_course_data = old_db["courses"].get(course_id, [])
                    old_topic = next(
                        (t for t in old_course_data if t["topic"] == topic_name), None
                    )
                    new_items_found = []

                    if old_topic is None:
                        for item in current_items:
                            msg = f"🟢 [新增] {topic_name} - {item['type']}：{item['name']}"
                            if item["type"] == "作業" and not item["is_submitted"]:
                                msg += f"\n⚠️ 尚未繳交！截止：{item['due_date']}"
                            msg += f"\n連結：{item['link']}"
                            new_items_found.append(msg)
                    else:
                        old_items_dict = {
                            (i["link"] if i["link"] else i["name"]): i
                            for i in old_topic["items"]
                        }
                        for item in current_items:
                            item_key = item["link"] if item["link"] else item["name"]
                            if item_key not in old_items_dict:
                                msg = f"🟢 [新增] {topic_name} - {item['type']}：{item['name']}"
                                if item["type"] == "作業" and not item["is_submitted"]:
                                    msg += f"\n⚠️ 尚未繳交！截止：{item['due_date']}"
                                msg += f"\n連結：{item['link']}"
                                new_items_found.append(msg)
                            else:
                                old_item = old_items_dict[item_key]
                                if item["name"] != old_item["name"]:
                                    new_items_found.append(
                                        f"🟡 [標題更新] {topic_name} - {item['type']}：\n「{old_item['name']}」 ➝ 「{item['name']}」\n連結：{item['link']}"
                                    )
                                elif item["hash"] and item["hash"] != old_item.get(
                                    "hash", item["hash"]
                                ):
                                    msg = f"📝 [內容更新] {topic_name} - {item['type']}說明已被修改：{item['name']}"
                                    if item["type"] == "作業":
                                        if item.get("is_submitted", True):
                                            msg += f"\n🚨 警告：您已繳交此作業，但教授剛才修改了作業要求！"
                                        else:
                                            msg += f"\n⚠️ 尚未繳交！截止：{item['due_date']}"
                                    msg += f"\n連結：{item['link']}"
                                    new_items_found.append(msg)

                    if new_items_found:
                        all_new_notifications.append(
                            f"📚 【{short_course}】\n" + "\n\n".join(new_items_found)
                        )

    except Exception as e:
        error_msg = f"{str(e)}"
        print(f"❌ 執行發生錯誤: {error_msg}")
        stats["errors"].append(f"[{now.strftime('%H:%M')}] {error_msg}")

    if not old_db["courses"] and current_courses_db:
        print("第一次執行，寫入基準資料庫。")
        
        tracked_courses = []
        for course_name in courses_dict.values():
            short_name = course_name.replace(TARGET_SEMESTER, "").split("(")[0].strip()
            tracked_courses.append(short_name)
        
        welcome_msg = "【NTNU Moodle 專用LINE通知器】啟動成功！\n"
        welcome_msg += "=" * 15 + "\n"
        welcome_msg += f"✅ 已成功連線，正在監控 {len(tracked_courses)} 門課程：\n"
        
        for c_name in tracked_courses:
            welcome_msg += f"📖 {c_name}\n"
            
        welcome_msg += "=" * 15 + "\n"
        
        if urgent_list:
            welcome_msg += "\n🚨 【注意！有即將到期的作業】\n" + "\n".join(urgent_list) + "\n"
            
        if pending_list:
            welcome_msg += "\n📋 【目前的待辦清單】\n" + "\n".join(pending_list)
        else:
            welcome_msg += "\n🎉 太棒了！目前無待辦作業，請繼續保持！"
            
        print("準備發送 LINE 首次啟動通知！")
        if send_line_push_message(welcome_msg):
            print("LINE 首次啟動通知發送成功！")
        else:
            stats["errors"].append(f"[{now.strftime('%H:%M')}] LINE 首次啟動通知發送失敗")
        # ----------------------------------------    else:
        send_alert = False
        alert_parts = []

        if all_new_notifications:
            alert_parts.append(
                "🔔 Moodle 更新通知\n"
                + "=" * 15
                + "\n\n"
                + "\n\n".join(all_new_notifications)
            )
            send_alert = True

        if urgent_list:
            alert_parts.append(
                "🚨 【緊急催繳】24小時內死線！\n"
                + "=" * 15
                + "\n"
                + "\n".join(urgent_list)
            )
            send_alert = True

        if send_alert:
            if pending_list:
                alert_parts.append(
                    "📋 【目前待辦清單】\n" + "-" * 15 + "\n" + "\n".join(pending_list)
                )
            else:
                alert_parts.append("\n🎉 太棒了！目前沒有任何待辦作業！")

            final_message = "\n\n".join(alert_parts)
            print("準備發送 LINE 更新/催繳通知！")
            if send_line_push_message(final_message):
                print("LINE 通知發送成功！")
            else:
                stats["errors"].append(
                    f"[{now.strftime('%H:%M')}] LINE 更新通知發送失敗"
                )

    if now.hour >= 18 and not stats["summary_sent"]:
        report_msg = f"📊 Moodle 每日巡邏報告 ({stats['date']})\n"
        report_msg += f"✅ 今日已為您執行 {stats['run_count']} 次檢查。\n"

        if stats["errors"]:
            report_msg += f"⚠️ 期間發生 {len(stats['errors'])} 次異常：\n"
            for err in stats["errors"][-3:]:
                report_msg += f"- {err}\n"
        else:
            report_msg += "🎉 今日系統運行穩定，無任何錯誤！\n"

        if pending_list:
            report_msg += (
                "\n📋 【目前待辦清單】\n" + "=" * 15 + "\n" + "\n".join(pending_list)
            )
        else:
            report_msg += "\n🎉 太棒了！目前沒有任何待辦作業！"

        if send_line_push_message(report_msg):
            print("LINE 每日日報發送成功！")
            stats["summary_sent"] = True

    if current_courses_db:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"courses": current_courses_db, "stats": stats},
                f,
                indent=4,
                ensure_ascii=False,
            )


if __name__ == "__main__":
    main()
