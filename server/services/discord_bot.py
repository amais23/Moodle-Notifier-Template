import asyncio
import os
import urllib.parse
from datetime import datetime
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import discord
from discord import app_commands
from discord.ext import commands

from src.config import Config
from server.handlers.command_handlers import get_moodle_client, clean_course_name, html_to_text

# Global bot instance
bot: commands.Bot = None
_bot_task: asyncio.Task = None

class MoodleDiscordBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.config = config

    async def setup_hook(self):
        # Sync slash commands globally
        print("[INFO] Syncing Discord slash commands...")
        try:
            synced = await self.tree.sync()
            print(f"[INFO] Successfully synced {len(synced)} slash commands globally.")
        except Exception as e:
            clean_error = str(e).encode('ascii', errors='ignore').decode('ascii')
            print(f"[ERROR] Failed to sync slash commands: {clean_error}")

def init_bot(config: Config):
    global bot
    bot = MoodleDiscordBot(config)

    # Helper function to get clean course name
    def get_clean_name(fullname: str) -> str:
        return clean_course_name(fullname, config.target_semester)

    @bot.event
    async def on_ready():
        print(f"[INFO] Discord Bot logged in as {bot.user}")

    @bot.tree.command(name="help", description="顯示 NTNU Moodle 互動助理指令說明")
    async def help_command(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎓 NTNU Moodle 互動助理說明",
            description="本機器人已與 Moodle 系統連線，您可以使用以下 Slash Commands 進行即時查詢：",
            color=9024762 # #89b4fa
        )
        embed.add_field(name="📚 /courses", value="查看本學期監控課程", inline=False)
        embed.add_field(name="📋 /todo", value="查看未繳作業", inline=False)
        embed.add_field(name="📊 /grades", value="查詢所有科目成績明細", inline=False)
        embed.add_field(name="📅 /upcoming", value="查詢一週內行事曆待辦", inline=False)
        embed.add_field(name="💬 /messages", value="查詢最近的未讀與對話私訊", inline=False)
        embed.add_field(name="❓ /help", value="顯示此說明", inline=False)
        
        # Add dashboard URL button if configured
        dashboard_url = config.dashboard_url or "http://localhost:8000"
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="開啟 Web 控制台", url=dashboard_url, style=discord.ButtonStyle.link))
        
        await interaction.response.send_message(embed=embed, view=view)

    @bot.tree.command(name="courses", description="查看本學期監控課程")
    async def courses_command(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            client = get_moodle_client(config)
            courses_data = client.get_user_courses()
            semester_courses = [c for c in courses_data if config.target_semester in c.get("fullname", "")]
        except Exception as e:
            embed = discord.Embed(title="❌ Moodle 連線失敗", description=str(e), color=15961000)
            await interaction.followup.send(embed=embed)
            return

        if not semester_courses:
            embed = discord.Embed(
                title="📚 監控課程",
                description=f"本學期 ({config.target_semester}) 沒有正在監控的課程。",
                color=9024762
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"📚 本學期 ({config.target_semester}) 監控課程",
            color=9024762
        )
        for c in semester_courses:
            clean_name = get_clean_name(c["fullname"])
            embed.add_field(name=clean_name, value=f"ID: `{c['id']}`", inline=False)

        dashboard_url = config.dashboard_url or "http://localhost:8000"
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="開啟 Web 控制台", url=dashboard_url, style=discord.ButtonStyle.link))
        await interaction.followup.send(embed=embed, view=view)

    @bot.tree.command(name="todo", description="查看未繳作業")
    async def todo_command(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            client = get_moodle_client(config)
            courses_data = client.get_user_courses()
            semester_courses = [c for c in courses_data if config.target_semester in c.get("fullname", "")]
            course_ids = [c["id"] for c in semester_courses]
        except Exception as e:
            embed = discord.Embed(title="❌ Moodle 連線失敗", description=str(e), color=15961000)
            await interaction.followup.send(embed=embed)
            return

        if not course_ids:
            embed = discord.Embed(title="📋 未繳作業", description="目前無監控課程，故無作業清單。", color=9024762)
            await interaction.followup.send(embed=embed)
            return

        try:
            # 取得作業
            assigns_data = client.get_assignments(course_ids)
            api_courses = assigns_data.get("courses", [])
            
            raw_assigns = []
            for ac in api_courses:
                cname = get_clean_name(ac.get("fullname", ""))
                for a in ac.get("assignments", []):
                    raw_assigns.append((cname, a))
                    
            if not raw_assigns:
                embed = discord.Embed(title="🎉 未繳作業", description="太棒了！本學期目前沒有任何作業項目！", color=10937249)
                await interaction.followup.send(embed=embed)
                return

            pending_assigns = []
            now = datetime.now()

            # 使用執行緒池查詢繳交狀態
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

            if not pending_assigns:
                embed = discord.Embed(title="🎉 未繳作業", description="檢查完畢！目前沒有任何待繳交作業！", color=10937249)
                await interaction.followup.send(embed=embed)
                return

            # 排序 (按截止日期從小到大)
            pending_assigns.sort(key=lambda x: x[1].get("duedate", 9999999999))

            embed = discord.Embed(
                title="📋 目前未繳交的作業清單",
                description="以下是您尚未繳交的作業：",
                color=9024762
            )

            for cname, assign in pending_assigns[:25]:  # Discord embed max fields is 25
                due_ts = assign.get("duedate", 0)
                due_str = "無截止日期"
                time_left = ""
                
                if due_ts > 0:
                    due_dt = datetime.fromtimestamp(due_ts)
                    due_str = due_dt.strftime("%Y-%m-%d %H:%M")
                    if due_dt > now:
                        rem = due_dt - now
                        days = rem.days
                        hrs = rem.seconds // 3600
                        if days > 0:
                            time_left = f" (剩 {days} 天 {hrs} 小時)"
                        else:
                            mins = (rem.seconds % 3600) // 60
                            time_left = f" (🚨 僅剩 {hrs} 小時 {mins} 分)"
                    else:
                        time_left = " (⚠️ 已逾期)"

                embed.add_field(
                    name=f"📖 {cname}",
                    value=f"📝 **{assign['name']}**\n⏰ 截止：`{due_str}`{time_left}",
                    inline=False
                )

            dashboard_url = config.dashboard_url or "http://localhost:8000"
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="開啟 Web 控制台", url=dashboard_url, style=discord.ButtonStyle.link))
            await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            embed = discord.Embed(title="❌ 查詢作業狀態失敗", description=str(e), color=15961000)
            await interaction.followup.send(embed=embed)

    @bot.tree.command(name="grades", description="查詢所有科目成績明細")
    async def grades_command(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            client = get_moodle_client(config)
            courses_data = client.get_user_courses()
            semester_courses = [c for c in courses_data if config.target_semester in c.get("fullname", "")]
        except Exception as e:
            embed = discord.Embed(title="❌ Moodle 連線失敗", description=str(e), color=15961000)
            await interaction.followup.send(embed=embed)
            return

        if not semester_courses:
            embed = discord.Embed(title="📊 成績查詢", description="目前無監控課程，無法查詢成績。", color=9024762)
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="📊 本學期科目成績明細",
            color=9024762
        )

        for course in semester_courses:
            cname = get_clean_name(course["fullname"])
            try:
                grade_items = client.get_grade_items(course["id"])
                course_grades = []
                for item in grade_items:
                    item_name = item.get("itemname") or item.get("itemtype")
                    if not item_name or item_name == "course":
                        continue
                    grade_val = item.get("gradeformatted", "—").strip()
                    course_grades.append(f"• {item_name}: `{grade_val}`")
                
                if course_grades:
                    embed.add_field(name=f"📚 {cname}", value="\n".join(course_grades), inline=False)
            except Exception as e:
                embed.add_field(name=f"📚 {cname}", value=f"❌ 讀取失敗 ({e})", inline=False)

        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="upcoming", description="查詢一週內行事曆待辦")
    async def upcoming_command(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            client = get_moodle_client(config)
            events = client.get_upcoming_events(limit=15)
        except Exception as e:
            embed = discord.Embed(title="❌ Moodle 連線失敗", description=str(e), color=15961000)
            await interaction.followup.send(embed=embed)
            return

        if not events:
            embed = discord.Embed(title="📅 近期活動", description="行事曆中目前沒有即將到來的事項。", color=9024762)
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="📅 即將到來事項 (一週內)",
            color=9024762
        )
        now_ts = time.time()
        count = 0
        for ev in events:
            ts = ev.get("timesort", 0)
            if ts - now_ts > 7 * 86400:
                continue
            dt = datetime.fromtimestamp(ts)
            ev_name = ev.get("name", "未命名事件")
            cname = ev.get("course", {}).get("fullname", "系統")
            if config.target_semester in cname:
                cname = get_clean_name(cname)
            embed.add_field(
                name=f"📌 {ev_name}",
                value=f"課程：`{cname}`\n時間：`{dt.strftime('%m/%d (%a) %H:%M')}`",
                inline=False
            )
            count += 1

        if count == 0:
            embed.description = "行事曆中一週內沒有即將到來的事項。"
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="messages", description="查詢最近的未讀私訊")
    async def messages_command(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            client = get_moodle_client(config)
            conversations = client.get_conversations(limit=5)
        except Exception as e:
            embed = discord.Embed(title="❌ Moodle 連線失敗", description=str(e), color=15961000)
            await interaction.followup.send(embed=embed)
            return

        if not conversations:
            embed = discord.Embed(title="💬 最新私訊", description="目前無任何聯絡人私訊紀錄。", color=9024762)
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="💬 最近的 Moodle 對話",
            color=9024762
        )
        for convo in conversations:
            unread = convo.get("unreadcount") or 0
            members = convo.get("members", [])
            sender = next((m for m in members if m.get("id") != client.user_id), None)
            sender_name = sender.get("fullname") if sender else "未知使用者"
            
            messages = convo.get("messages", [])
            msg_text = "無訊息"
            if messages:
                msg_text = html_to_text(messages[0].get("text", ""))
                if len(msg_text) > 60:
                    msg_text = msg_text[:60] + "..."
                    
            unread_tag = " 🔴 [未讀]" if unread > 0 else ""
            embed.add_field(
                name=f"👤 {sender_name}{unread_tag}",
                value=f"✉️ {msg_text}",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    async def course_name_autocomplete(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        try:
            client = get_moodle_client(config)
            loop = asyncio.get_event_loop()
            courses_data = await loop.run_in_executor(None, client.get_user_courses)
            semester_courses = [c for c in courses_data if config.target_semester in c.get("fullname", "")]
            
            choices = []
            for c in semester_courses:
                clean_name = get_clean_name(c["fullname"])
                if current.lower() in clean_name.lower():
                    choices.append(app_commands.Choice(name=clean_name, value=clean_name))
            return choices[:25]
        except Exception as e:
            print(f"[ERROR] Autocomplete error: {e}")
            return []

    @bot.tree.command(name="announcements", description="取得指定課程最新公告")
    @app_commands.describe(course_name="請選擇課程名稱", filter_type="選擇要讀取的公告範圍")
    @app_commands.choices(filter_type=[
        app_commands.Choice(name="📅 7天內最新", value="7days"),
        app_commands.Choice(name="📜 歷史前5則", value="all")
    ])
    async def announcements_command(
        interaction: discord.Interaction,
        course_name: str,
        filter_type: str = "7days"
    ):
        await interaction.response.defer()
        try:
            client = get_moodle_client(config)
            courses_data = client.get_user_courses()
            semester_courses = [c for c in courses_data if config.target_semester in c.get("fullname", "")]
            
            target_course = None
            for c in semester_courses:
                if get_clean_name(c["fullname"]) == course_name:
                    target_course = c
                    break
            
            if not target_course:
                for c in semester_courses:
                    if course_name.lower() in get_clean_name(c["fullname"]).lower():
                        target_course = c
                        break
                        
            if not target_course:
                embed = discord.Embed(title="❌ 找不到課程", description=f"找不到名為 '{course_name}' 的監控課程，請重新選擇。", color=15961000)
                await interaction.followup.send(embed=embed)
                return
                
            from server.handlers.command_handlers import get_course_announcements
            loop = asyncio.get_event_loop()
            discussions = await loop.run_in_executor(
                None, get_course_announcements, client, target_course["id"], filter_type
            )
            
            title_suffix = "最新公告 (7天內)" if filter_type == "7days" else "歷史公告"
            embed = discord.Embed(
                title=f"📢 {course_name} - {title_suffix}",
                color=9024762
            )
            
            if not discussions:
                embed.description = "📭 目前無公告內容"
            else:
                for disc in discussions[:5]:
                    subject = disc.get("subject", "無主旨")
                    author = disc.get("userfullname", "未知講師")
                    created_ts = disc.get("created", 0)
                    created_str = datetime.fromtimestamp(created_ts).strftime("%m/%d %H:%M") if created_ts else ""
                    
                    preview = html_to_text(disc.get("message", ""))
                    if len(preview) > 150:
                        preview = preview[:150] + "..."
                        
                    embed.add_field(
                        name=f"📌 {subject}",
                        value=f"👤 {author} | ⏰ {created_str}\n{preview}",
                        inline=False
                    )
                    
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="❌ 取得公告失敗", description=str(e), color=15961000)
            await interaction.followup.send(embed=embed)

    @announcements_command.autocomplete("course_name")
    async def announcements_autocomplete(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        return await course_name_autocomplete(interaction, current)

    @bot.tree.command(name="files", description="取得課程教材與講義檔案清單")
    @app_commands.describe(course_name="請選擇課程名稱")
    async def files_command(
        interaction: discord.Interaction,
        course_name: str
    ):
        await interaction.response.defer()
        try:
            client = get_moodle_client(config)
            courses_data = client.get_user_courses()
            semester_courses = [c for c in courses_data if config.target_semester in c.get("fullname", "")]
            
            target_course = None
            for c in semester_courses:
                if get_clean_name(c["fullname"]) == course_name:
                    target_course = c
                    break
            
            if not target_course:
                for c in semester_courses:
                    if course_name.lower() in get_clean_name(c["fullname"]).lower():
                        target_course = c
                        break
                        
            if not target_course:
                embed = discord.Embed(title="❌ 找不到課程", description=f"找不到名為 '{course_name}' 的監控課程，請重新選擇。", color=15961000)
                await interaction.followup.send(embed=embed)
                return
                
            from server.handlers.command_handlers import extract_course_files
            loop = asyncio.get_event_loop()
            contents = await loop.run_in_executor(None, client.get_course_contents, target_course["id"])
            files = extract_course_files(contents)
            
            embed = discord.Embed(
                title=f"📁 {course_name} 課程講義",
                color=9024762
            )
            
            if not files:
                embed.description = "📭 目前無講義或教材檔案"
                await interaction.followup.send(embed=embed)
            else:
                dashboard_url = config.dashboard_url or "http://localhost:8000"
                token = client.token
                
                lines = []
                import urllib.parse
                for i, f in enumerate(files[:15]):
                    fsize = f["size"]
                    if fsize >= 1024 * 1024:
                        size_str = f" ({fsize / (1024 * 1024):.1f} MB)"
                    elif fsize >= 1024:
                        size_str = f" ({fsize / 1024:.1f} KB)"
                    elif fsize > 0:
                        size_str = f" ({fsize} B)"
                    else:
                        size_str = ""
                        
                    encoded_url = urllib.parse.quote_plus(f["url"])
                    dl_url = f"{dashboard_url.rstrip('/')}/api/download?url={encoded_url}&token={token}"
                    lines.append(f"{i+1}. 📄 **{f['name']}**{size_str} — [⬇️ 點此下載]({dl_url})")
                    
                embed.description = "\n".join(lines)
                
                view = discord.ui.View()
                for f in files[:5]:
                    encoded_url = urllib.parse.quote_plus(f["url"])
                    dl_url = f"{dashboard_url.rstrip('/')}/api/download?url={encoded_url}&token={token}"
                    label = f"⬇️ {f['name']}"
                    if len(label) > 80:
                        label = label[:77] + "..."
                    view.add_item(discord.ui.Button(label=label, url=dl_url, style=discord.ButtonStyle.link))
                    
                await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            embed = discord.Embed(title="❌ 取得檔案失敗", description=str(e), color=15961000)
            await interaction.followup.send(embed=embed)

    @files_command.autocomplete("course_name")
    async def files_autocomplete(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        return await course_name_autocomplete(interaction, current)


async def start_discord_bot(config: Config):
    """啟動 Discord 機器人"""
    if not config.discord_bot_token:
        print("[WARNING] DISCORD_BOT_TOKEN is not set. Discord Bot startup will be skipped.")
        return

    init_bot(config)
    
    global _bot_task
    print("[INFO] Starting Discord Bot in event loop background task...")
    try:
        _bot_task = asyncio.create_task(bot.start(config.discord_bot_token))
    except Exception as e:
        clean_error = str(e).encode('ascii', errors='ignore').decode('ascii')
        print(f"[ERROR] Failed to start Discord Bot task: {clean_error}")

async def stop_discord_bot():
    """安全關閉 Discord 機器人連線"""
    global bot, _bot_task
    if bot:
        print("[INFO] Closing Discord Bot connection...")
        try:
            await bot.close()
            print("[INFO] Discord Bot closed successfully.")
        except Exception as e:
            clean_error = str(e).encode('ascii', errors='ignore').decode('ascii')
            print(f"[ERROR] Error closing Discord Bot: {clean_error}")
        bot = None
    if _bot_task:
        _bot_task.cancel()
        _bot_task = None
