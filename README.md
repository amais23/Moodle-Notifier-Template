# 🎓 NTNU Moodle 專用 LINE 通知器(模板)

這是一個為國立臺灣師範大學 (NTNU) 學生量身打造的 **Moodle 替代平台控制中心**。
您完全不需要開啟繁雜擁擠的師大 Moodle 網頁，透過 **LINE Bot 互動查詢與即時推播**，即可輕鬆掌握日常所有學習動態！

---

## ✨ 核心功能 (Features)

* **🔔 即時定時推播通知**
  - **新上傳講義/公告**：教授一上傳新檔案、新消息或新作業，LINE 機器人會第一時間推播給您。若有修改檔案或作業說明亦會偵測通知。
  - **死線催繳與提醒**：作業截止前 24 小時與 3 天自動發送提醒，防範漏繳作業。
  - **每日傍晚日報**：每日 18:00 定時發送本日運行狀態與待繳作業清單。

* **🤖 LINE Bot 隨身助理**
  - 在 LINE 對話框發送簡單指令，即可即時查詢 Moodle 上的資訊：
    - `/courses` — 查看本學期修習的監控課程。
    - `/assignments` (或 `/todo`) — 查詢所有科目**未繳交的作業與截止倒數**。
    - `/grades` — 查詢本學期所有學科的詳細成績與小考項目。
    - `/upcoming` — 查詢一週內行事曆上的待辦活動或截止日。
    - `/messages` — 查看最近的 Moodle 站內對話與未讀私訊。
    - `/help` — 顯示指令使用說明。
  - **個人隱私安全防禦**：機器人會嚴格校驗發送者的 LINE ID，只有您本人的 LINE 帳號才能查詢您的資料，其他人無法非法窺探。

* **💻 Premium 網頁儀表板**
  - **課程與教材中心**：免找連結！直接在網頁中點選課程，即可展開各單元與下載上課講義 PDF。
  - **成績明細**：下拉選單快速切換各科目，一覽所有評分項目與教授的回饋評語。
  - **站內私訊聊天**：完美整合對話氣泡視圖，直接在控制台閱讀 Moodle 站內私訊。
  - **安全檔案下載**：透過後端代理串流下載教材，雙重保障您的帳密安全。

---

## 🚀 快速部署與使用方法

### 步驟 1：建立您專屬的 LINE 官方帳號機器人
1. 登入 [LINE Developers 控制台](https://developers.line.biz/console/)，建立一個 Provider 並創建一個 **Messaging API** 頻道。
2. 進入 [LINE 官方帳號管理後台](https://manager.line.biz/)，點選右上角設定 -> **Messaging API** -> 啟用，並綁定剛創立的 Provider。
3. 在 LINE Developers 的 Messaging API 頻道中複製並留存以下 3 個金鑰：
   - **`LINE_USER_ID`**：在 `Basic settings` 頁籤最下方的 `Your user ID`（以 `U` 開頭的一串字串）。
   - **`LINE_TOKEN`**：在 `Messaging API` 頁籤最下方的 `Channel access token` (點 Issue 產生)。
   - **`LINE_CHANNEL_SECRET`**：在 `Basic settings` 頁籤中的 `Channel secret`。
   - **💡 記得**：掃描 Messaging API 頁籤中的 QR Code，將您的機器人加為 LINE 好友。

---

### 步驟 2：建立您的私有 GitHub 倉庫
1. 點擊此專案右上角的 **「Use this template」** -> **「Create a new repository」**。
2. 命名您的專案，並 **⚠️ 務必設定為 Private (私有倉庫)**，以保障您的密碼與隱私安全！
3. 建立後，前往 GitHub 倉庫的 `Settings` -> `Secrets and variables` -> `Actions`，新增以下四個 **Repository secrets**：
   - `MOODLE_USERNAME`：您的 Portal 帳號（學號）。
   - `MOODLE_PASSWORD`：您的 Portal 密碼。
   - `LINE_USER_ID`：您的 LINE 用戶 ID (步驟 1 取得的 U 開頭字串)。
   - `LINE_TOKEN`：您的 LINE Channel Access Token。
4. 前往上方 **Actions** 頁籤，點選 **Moodle Monitor Bot** -> **Run workflow** 進行第一次測試。若 LINE 成功收到啟動通知，即表示 Actions 定時排程已部署成功！

> [!IMPORTANT]
> ⚠️ **務必將設定為私有倉庫**，否則您的課程資訊會被公開！

---

### 步驟 3：部署 LINE Bot 互動與網頁控制台 (Render)
本專案已配置好 Render Blueprint 一鍵部署，系統會自動在雲端完成網頁編譯與上線。

1. 登入 [Render Dashboard](https://dashboard.render.com)。
2. 點選 **New** -> **Blueprint**。
3. 連接您建立的私有 `Moodle-Notifier` GitHub 倉庫，選擇 **`main`** 分支並點擊下一步。
4. 在環境變數欄位中填入以下 5 個對應的金鑰值：
   - `MOODLE_USERNAME` (校務行政系統帳號)
   - `MOODLE_PASSWORD` (校務行政系統密碼)
   - `LINE_USER_ID` (步驟 1 取得的 LINE 用戶 ID)
   - `LINE_TOKEN` (步驟 1 取得的 LINE Access Token)
   - `LINE_CHANNEL_SECRET` (步驟 1 取得的 LINE Channel Secret)
5. 點擊 **Deploy** 開始建置。
6. 建置成功後，您會獲得一個專屬的公網網址 (例如 `https://your-app-name.onrender.com`)：
   - **綁定 LINE 指令**：將此網址加上 `/webhook/line` (例如 `https://your-app-name.onrender.com/webhook/line`)，填入 LINE Developers 中 `Messaging API` 頁籤的 **Webhook URL** 中，點擊驗證並開啟 **Use webhook**。現在您就可以在 LINE 中向機器人發送指令進行互動了！
   - **進入網頁控制台**：直接在瀏覽器輸入您的公網網址 (例如 `https://your-app-name.onrender.com/`)，即可使用您的 Portal 帳密登入體驗高質感的儀表板！

---

## ⚙️ 進階調整
- **更換學期**：每學期初，請在您的 GitHub 倉庫的 [src/config.py](file:///c:/Users/chiah/Documents/moodle%20notifier/src/config.py) 中，將 `TARGET_SEMESTER` 修改為新的學期代碼（例如本學期為 `"1142"`），或直接在 GitHub Secrets / Render 環境變數中設定 `TARGET_SEMESTER` 即可。

## 🚨 免責聲明
* **安全性與隱私**：本專案需要使用您的個人校務行政系統帳密以連接 Moodle API。請務必確保 GitHub 倉庫權限為 **Private (私有)**。開發者不會收集任何個人憑證資料，若因公開倉庫或其他不當使用導致的帳號資安風險，需請自行承擔。
* **合理使用**：預設的 Actions 監控頻率為每日數次。請勿惡意修改排程為高頻率查詢（如每分鐘執行一次），以免對學校 Moodle 伺服器造成負載或引起封鎖。
* **僅供學術交流**：本專案僅為自動化程式學習與交流之用途，非校方官方工具。
* **使用風險**：若因 Moodle 系統改版導致腳本失效，或因執行此腳本引發任何衍生問題，請使用者自行承擔風險。