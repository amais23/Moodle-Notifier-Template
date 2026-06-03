import os
import sys
from datetime import datetime
from src.config import Config
from src.storage import Storage
from src.moodle_client import MoodleClient
from src.models import Course
from src.notifiers.line_notifier import LineNotifier
from src.notifiers.discord_notifier import DiscordNotifier
from src.monitors.assignment_monitor import AssignmentMonitor
from src.monitors.announcement_monitor import AnnouncementMonitor
from src.monitors.grade_monitor import GradeMonitor
from src.monitors.message_monitor import MessageMonitor

# 確保在 Windows 上正確輸出 UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Moodle Monitor 啟動...")

    # 1. 載入設定與初始化持久化儲存
    try:
        config = Config.load()
    except Exception as e:
        print(f"❌ 載入設定檔失敗: {e}")
        sys.exit(1)

    storage = Storage(config.data_dir, config.target_semester)
    stats = storage.get_stats()
    
    # 確保當日計數正確
    if stats.get("date") != today_str:
        # 跨日補發昨天的日報
        if not stats.get("summary_sent", False) and stats.get("run_count", 0) > 0:
            print("ℹ️ 偵測到跨日且昨日未送出日報，準備補發...")
            # 建立臨時的昨日 notifier 來補發 (使用目前的憑證)
            yesterday_notifiers = []
            if config.line_token:
                yesterday_notifiers.append(LineNotifier(config.line_token, config.line_user_id))
            if config.discord_webhook_url:
                yesterday_notifiers.append(DiscordNotifier(config.discord_webhook_url))
                
            # 取得昨日的待辦作業清單
            pending_list = []
            for item in storage.data.get("assignments", {}).values():
                if not item.get("is_submitted", True):
                    pending_list.append(f"- [{item.get('course_name')}] {item.get('name')} (截止: {item.get('due_date_str')})")
                    
            report = {
                "date": stats.get("date"),
                "run_count": stats.get("run_count"),
                "errors": stats.get("errors", []),
                "pending_list": pending_list
            }
            
            for notifier in yesterday_notifiers:
                notifier.send_daily_report(report)
                
        # 載入並重置當日統計
        storage.save() # 這會自動更新 date 與重置當日計數
        stats = storage.get_stats()

    storage.increment_run_count()

    # 2. 初始化通知管道
    notifiers = []
    if config.line_token and config.line_user_id:
        notifiers.append(LineNotifier(config.line_token, config.line_user_id))
        print("✅ LINE 通知器載入成功。")
    if config.discord_webhook_url:
        notifiers.append(DiscordNotifier(config.discord_webhook_url))
        print("✅ Discord 通知器載入成功。")

    if not notifiers:
        print("⚠️ 警告：沒有啟用任何通知平台，程式將僅更新資料庫。")

    # 3. 連線至 Moodle
    client = MoodleClient(config.moodle_base_url, config.username, config.password, config.http_timeout)
    try:
        client.authenticate()
        print(f"✅ 成功連線 Moodle，使用者: {client.fullname} (ID: {client.user_id})")
    except Exception as e:
        error_msg = f"登入或驗證失敗: {e}"
        print(f"❌ {error_msg}")
        storage.add_error(error_msg)
        storage.save()
        sys.exit(1)

    # 4. 取得學期課程列表
    try:
        courses_data = client.get_user_courses()
    except Exception as e:
        error_msg = f"無法取得課程清單: {e}"
        print(f"❌ {error_msg}")
        storage.add_error(error_msg)
        storage.save()
        sys.exit(1)

    semester_courses = []
    for c in courses_data:
        fullname = c.get("fullname", "")
        if config.target_semester in fullname:
            semester_courses.append(Course(
                id=c["id"],
                fullname=fullname,
                shortname=c.get("shortname", "")
            ))

    print(f"📚 本學期 ({config.target_semester}) 共有 {len(semester_courses)} 門課需要監控。")

    # 5. 執行各個監控器
    monitors = [
        AssignmentMonitor(client, storage),
        AnnouncementMonitor(client, storage),
        GradeMonitor(client, storage),
        MessageMonitor(client, storage)
    ]

    all_notifications = []
    
    # 執行監控並搜集通知
    # 為了方便將來擴展，在此以循序或多執行緒執行
    # 由於 API client 內部已經用了並行，這裡直接循序呼叫
    for monitor in monitors:
        try:
            if isinstance(monitor, MessageMonitor):
                # MessageMonitor 不需要傳入 course 列表
                notifs = monitor.check()
            else:
                notifs = monitor.check(semester_courses)
            all_notifications.extend(notifs)
        except Exception as e:
            err_msg = f"監控器 {monitor.__class__.__name__} 執行異常: {e}"
            print(f"❌ {err_msg}")
            storage.add_error(err_msg)

    # 6. 發送即時通知
    for notif in all_notifications:
        for notifier in notifiers:
            try:
                notifier.send_alert(notif["title"], notif["body"], notif.get("url"))
            except Exception as e:
                print(f"❌ {notifier.platform_name} 發送警示失敗: {e}")

    # 7. 處理首次啟動的歡迎通知與現狀摘要
    current_courses_db = {str(c.id): c.fullname for c in semester_courses}
    is_first_run = len(storage.data.get("courses", {})) == 0

    if is_first_run and semester_courses:
        print("🆕 偵測到首次啟動，建立基準快取...")
        storage.data["courses"] = current_courses_db
        
        # 整理出初始的待辦清單
        pending_list = []
        for item in storage.data.get("assignments", {}).values():
            if not item.get("is_submitted", True):
                pending_list.append(f"- [{item.get('course_name')}] {item.get('name')} (截止: {item.get('due_date_str')})")
        
        course_list_str = "\n".join([f"📖 {AssignmentMonitor.clean_course_name(c.fullname, config.target_semester)}" for c in semester_courses])
        
        welcome_body = (
            f"✅ 已成功連線，正在監控 {len(semester_courses)} 門課程：\n"
            f"{course_list_str}\n"
            f"================\n"
        )
        
        if pending_list:
            welcome_body += "📋 【目前的待辦作業】\n" + "\n".join(pending_list)
        else:
            welcome_body += "🎉 太棒了！目前無待辦作業，請繼續保持！"
            
        for notifier in notifiers:
            try:
                notifier.send_alert("🎉 Moodle 通知系統啟動成功！", welcome_body)
            except Exception as e:
                print(f"❌ 發送啟動歡迎詞失敗: {e}")

    # 8. 每日統計日報發送判斷 (每天 18:00 後，且本日未送出)
    if now.hour >= config.daily_report_hour and not stats.get("summary_sent", False):
        print(f"📊 達到每日日報時間 ({config.daily_report_hour}:00)，準備發送報告...")
        
        # 取得目前的待辦作業清單
        pending_list = []
        for item in storage.data.get("assignments", {}).values():
            if not item.get("is_submitted", True):
                pending_list.append(f"- [{item.get('course_name')}] {item.get('name')} (截止: {item.get('due_date_str')})")
                
        report = {
            "date": stats.get("date"),
            "run_count": stats.get("run_count"),
            "errors": stats.get("errors", []),
            "pending_list": pending_list
        }
        
        all_sent = True
        for notifier in notifiers:
            try:
                if not notifier.send_daily_report(report):
                    all_sent = False
            except Exception as e:
                print(f"❌ 發送每日報告失敗: {e}")
                all_sent = False
                
        if all_sent:
            storage.mark_summary_sent(True)

    # 9. 保存所有變更至 JSON 資料庫
    # 確保同步最新的 course 列表
    storage.data["courses"] = current_courses_db
    storage.save()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 💾 狀態已安全寫入資料庫，檢查程序結束。")

if __name__ == "__main__":
    main()
