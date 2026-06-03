# 🎓 NTNU Moodle 專用控制中心 (LINE & Discord 雙平台機器人 + 網頁控制台)

這是一個為國立臺灣師範大學 (NTNU) 學生量身打造的 **Moodle 替代平台控制中心**。
**💡 注意：本專案採用無伺服器 (Serverless) 與雲端託管架構，完全不需要在本機電腦執行！** 系統定時排程跑在 **GitHub Actions** 上（進行資料監控與推播），而互動機器人與控制台網頁則託管在 **Render.com** 上。

---

## ✨ 核心功能 (Features)

* **🔔 即時定時推播通知 (GitHub Actions)**
  - **新上傳講義/公告**：教授一上傳新檔案、新消息或新作業，LINE/Discord 機器人會第一時間推播給您。若有修改檔案或作業說明亦會偵測通知。
  - **死線催繳與提醒**：作業截止前 24 小時與 3 天自動發送提醒，防範漏繳作業。
  - **每日傍晚日報**：每日 18:00 定時發送本日運行狀態與待繳作業清單。

* **🤖 LINE Bot 一鍵式快捷助理 (v2 升級版)**
  - **免輸入指令**：對話框內附有精美的磨砂玻璃風格 **圖文選單 (Rich Menu)**，一鍵點選即可快速查詢。
  - **Flex Message 氣泡卡片**：
    - `/courses` — 查看本學期修習的監控課程（卡片附 Web 連結按鈕）。
    - `/assignments` (或 `/todo`) — 以 Carousel 跑馬燈卡片顯示**未繳交的作業、截止時間與緊急倒數（依緊急程度變色）**，卡片下方附有 **「🔍 查詢繳交狀態」** Postback 互動按鈕。
    - `/grades` — 查詢本學期所有學科的詳細成績明細。
    - `/upcoming` — 查詢一週內行事曆上的待辦活動。
    - `/messages` — 查看最近的 Moodle 站內對話與未讀私訊。
    - `/help` — 顯示指令使用說明。
  - **個人隱私安全防禦**：機器人會嚴格校驗發送者的 LINE ID，只有您本人的 LINE 帳號才能查詢您的資料，其他人無法非法窺探。

* **👾 Discord Bot 互動助理 (v2 新功能)**
  - 整合 Discord 機器人，支援 **Slash Commands (斜線指令)**：
    - `/courses` — 查詢本學期監控課程。
    - `/todo` — 查詢未繳作業。
    - `/grades` — 查詢各科成績明細。
    - `/upcoming` — 查詢一週內行事曆待辦。
    - `/messages` — 查詢未讀私訊與對話。
    - `/help` — 顯示說明指南。
  - **Rich Embed 卡片**：所有指令回應均包裝成精美的 Discord 嵌入式卡片，排版清晰美觀，並附加 Web Dashboard 連結按鈕。
  - **高度解耦執行**：Discord Bot 與 LINE Bot 互相獨立，若不想使用其中一個，只需留空其 Token，另一平台的服務仍能正常運作。

* **💻 Premium 網頁儀表板 (Render.com)**
  - **極致磨砂玻璃質感 (Glassmorphism)**：現代化毛玻璃美學，支持 Shimmer 加載動畫，體驗流暢。
  - **課程與教材中心**：免找連結！直接在網頁中點選課程，即可展開各單元與下載上課講義 PDF（內建安全下載代理代理）。
  - **成績明細**：下拉選單快速切換各科目，一覽所有評分項目與教授的回饋評語。
  - **站內私訊聊天**：完美整合對話氣泡視圖，直接在控制台閱讀 Moodle 站內私訊。

---

## 🚀 雲端部署與使用步驟

本專案完全部署於雲端平台，請按以下步驟完成配置：

### 步驟 1：取得平台金鑰
- **LINE 機器人金鑰 (可選)**：
  1. 登入 [LINE Developers 控制台](https://developers.line.biz/console/)，建立一個 Provider 並創建一個 **Messaging API** 頻道。
  2. 進入 [LINE 官方帳號管理後台](https://manager.line.biz/)，點選右上角設定 -> **Messaging API** -> 啟用，並綁定剛創立的 Provider。
  3. 在 LINE Developers 的 Messaging API 頻道中複製並留存以下 3 個金鑰：
     - **`LINE_USER_ID`**：在 `Basic settings` 頁籤最下方的 `Your user ID`（以 `U` 開頭的一串字串）。
     - **`LINE_TOKEN`**：在 `Messaging API` 頁籤最下方的 `Channel access token` (點 Issue 產生)。
     - **`LINE_CHANNEL_SECRET`**：在 `Basic settings` 頁籤中的 `Channel secret`。
   - **💡 記得**：掃描 Messaging API 頁籤中的 QR Code，將您的機器人加為 LINE 好友。
- **Discord 機器人金鑰 (可選)**：
  1. 登入 [Discord Developer Portal](https://discord.com/developers/applications)。
  2. 建立新 Application，並在 `Bot` 頁籤中創建 Bot，點擊 Reset Token 取得 **`DISCORD_BOT_TOKEN`**。
  3. 在 `OAuth2` -> `URL Generator` 頁籤中，Scopes 勾選 `bot` 與 `applications.commands`，Bot Permissions 勾選 `Send Messages`, `Embed Links`, `Use Slash Commands`。
  4. 複製生成的 URL 在瀏覽器打開，將機器人邀請至您的 Discord 伺服器中。

---

### 步驟 2：建立私有 GitHub 倉庫 (執行定時通知)
1. 點擊此專案右上角的 **「Use this template」** -> **「Create a new repository」**。
2. 命名您的專案，並 **⚠️ 務必設定為 Private (私有倉庫)**，以保障您的密碼與隱私安全！
3. 建立後，前往 GitHub 倉庫的 `Settings` -> `Secrets and variables` -> `Actions`，新增以下 **Repository secrets**：
   - `MOODLE_USERNAME`：您的 Portal 帳號（學號）。
   - `MOODLE_PASSWORD`：您的 Portal 密碼。
   - `LINE_USER_ID`：您的 LINE 用戶 ID (步驟 1 取得的 U 開頭字串，若使用 LINE 推播)。
   - `LINE_TOKEN`：您的 LINE Channel Access Token (若使用 LINE 推播)。
   - `DISCORD_WEBHOOK_URL`：您 Discord 頻道的 Webhook 連結 (若使用 Discord 推播，可在 Discord 頻道設定 -> 整合 -> 建立 Webhook 取得)。
4. 前往上方 **Actions** 頁籤，點選 **Moodle Monitor Bot** -> **Run workflow** 進行第一次測試。若 LINE/Discord 成功收到啟動通知，即表示 Actions 定時排程已部署成功！

> [!IMPORTANT]
> ⚠️ **務必設定為私有倉庫**，否則您的密碼與課程資訊會被公開！

---

### 步驟 3：部署控制台與機器人服務 (Render.com)
本專案已配置好 Render Blueprint 一鍵部署，系統會自動在雲端完成網頁編譯與多階段容器上線。

1. 登入 [Render Dashboard](https://dashboard.render.com)。
2. 點選 **New** -> **Blueprint**。
3. 連接您建立的私有 `Moodle-Notifier` GitHub 倉庫，選擇 **`main`** 分支並點擊下一步。
4. 在環境變數 (Environment Variables) 欄位中，填入對應的金鑰值（可依需求選填平台，缺漏平台 Token 會自動跳過該平台啟動）：
   - `MOODLE_USERNAME` (必填：校務行政系統帳號)
   - `MOODLE_PASSWORD` (必填：校務行政系統密碼)
   - `LINE_USER_ID` (選填：您的 LINE 用戶 ID)
   - `LINE_TOKEN` (選填：您的 LINE Access Token)
   - `LINE_CHANNEL_SECRET` (選填：您的 LINE Channel Secret)
   - `DISCORD_BOT_TOKEN` (選填：您的 Discord Bot Token)
5. 點擊 **Deploy** 開始建置。
6. 建置成功後，您會獲得一個專屬的公網網址 (例如 `https://your-app-name.onrender.com`)：
   - **進入網頁控制台**：直接在瀏覽器輸入您的公網網址 (例如 `https://your-app-name.onrender.com/`)，即可使用您的 Portal 帳密登入體驗儀表板！
   - **綁定 LINE 互動指令**：將您的公網網址加上 `/webhook/line` (例如 `https://your-app-name.onrender.com/webhook/line`)，填入 LINE Developers 中 `Messaging API` 頁籤的 **Webhook URL** 中，點擊驗證並開啟 **Use webhook**。

---

### 步驟 4：設定 LINE 圖文選單 (Rich Menu)
部署完成後，您需要執行一次設定腳本，以便在您的 LINE 官方帳號上綁定 3x2 的磨砂選單底圖。
**💡 注意**：此步驟僅需在您本地電腦的虛擬環境中執行 **一次** 即可完成 LINE 雲端的綁定，完成後即可關閉本機。

1. 確保本地已安裝依賴並載入配置（可在本地專案目錄建立一個 `moodle_credentials.json`，內容為 `{"username": "學號", "password": "密碼", "line_token": "您的Token"}` 作為執行腳本時的臨時憑證）。
2. 在本地專案目錄中，執行設定腳本並傳入您的 Render 公網網址：
   ```powershell
   .venv\Scripts\python server/tools/setup_rich_menu.py --url=您的Render公網網址
   ```
3. 看到 `Setup complete.` 訊息後，打開手機 LINE 對話框，即可看到精美的圖文選單已成功配置啟用！

---

## ⚙️ 進階調整
- **更換學期**：每學期初，請在您的 GitHub 倉庫的 [src/config.py](file:///c:/Users/chiah/Documents/moodle%20notifier/src/config.py) 中，將 `TARGET_SEMESTER` 修改為新的學期代碼（例如本學期為 `"1142"`），或直接在 GitHub Secrets / Render 環境變數中設定 `TARGET_SEMESTER` 即可。

## 🚨 免責聲明
* **安全性與隱私**：本專案需要使用您的個人校務行政系統帳密以連接 Moodle API。請務必確保 GitHub 倉庫權限為 **Private (私有)**。開發者不會收集 any 個人憑證資料，若因公開倉庫或其他不當使用導致的帳號資安風險，需請自行承擔。
* **合理使用**：預設的 Actions 監控頻率為每日數次。請勿惡意修改排程為高頻率查詢（如每分鐘執行一次），以免對學校 Moodle 伺服器造成負載或引起封鎖。
* **僅供學術交流**：本專案僅為自動化程式學習與交流之用途，非校方官方工具。
* **使用風險**：若因 Moodle 系統改版導致腳本失效，或因執行此腳本引發任何衍生問題，請使用者自行承擔風險。