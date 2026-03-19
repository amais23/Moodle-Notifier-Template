# NTNU Moodle 專用 LINE 通知器(模板)

這是一個部署在 GitHub Actions 上的自動化 Python 腳本，用來 24 小時監控師大 Moodle 的課程更新與作業，並利用自己專屬的的 LINE 官方帳號發送 LINE 通知給使用者。

## 核心功能 (Core Features)

- **監控檔案**：監控 [NTNU Moodle](https://moodle3.ntnu.edu.tw/) 作業說明與檔案，檔案或作業上傳 Moodle 時立刻通知，若教授修改檔案或修改作業說明也會通知。
- **作業催繳**：作業期限前 24 小時，每次執行都會發送 LINE 通知。
- **每日日報**：每天傍晚 18:00 準時發送本日運行狀況與待辦作業清單。
- **資料持久化**：自動將最新的 `moodle_data_1142.json` 更新回私人倉庫，保留歷史紀錄與比對基準。

---

## 使用方法 (Setup Guide)

請依照以下步驟完成雲端自動化部署：

### 步驟 0：事前準備 (取得你專屬的LINE官方帳號)

本專案使用 LINE Messaging API 來發送通知，請先至 [LINE Developers 控制台](https://developers.line.biz/) 完成以下準備：

1. 先至 [LINE Developers 控制台](https://developers.line.biz/en/console/) 登入並建立一個 Provider，並且填入任意 Provider name，接著創建一個 **Messaging API** 頻道 (Create a **Messaging API** Channel)。接著建立一個 LINE 官方帳號(Create a LINE Official Account)，並且填入基本資料，不須申請認證帳號。
2. 接著進入 [LINE 官方帳號管理](https://manager.line.biz/) 進入你創建的官方帳號主頁，點選右側設定，在設定頁面左側選擇列表中找到 Messaging API，點擊啟用Messaging API，並且選擇你的 Provider。
3. 回到 [LINE Developers 控制台](https://developers.line.biz/en/console/) ，選擇你的 Messaging API 頻道。
4. **取得 LINE_USER_ID**：切換到 `Basic settings` 頁籤，滑到最下方的 `Your user ID`，複製這串以 `U` 開頭的字串。
5. **取得 LINE_TOKEN**：切換到 `Messaging API` 頁籤，滑到最下方的 `Channel access token (long-lived)`，點擊 **Issue** 產生 Token 並複製。
> **💡 重要提醒**：請務必先在 `Messaging API` 頁籤掃描 QR Code，將你剛創建的機器人加為好友，它才有權限傳訊息給你！

### 步驟 1：建立你自己的私有倉庫

1. 註冊並登入 github
2. 點擊本專案右上角的綠色按鈕 **「Use this template」** -> **「Create a new repository」**。
3. 命名你的專案，並且 **⚠️ 務必將權限設定為 Private (私有)**，以保護你的密碼安全！
4. 建立完成後，你的個人倉庫就會擁有這份程式碼。

### 步驟 2：設定基本變數

若有更動需求，請直接在你的倉庫中修改 `main_monitor.py` 程式碼最上方的「1. 基礎設定區」：

- `TARGET_SEMESTER`：欲監控的學期代碼（例如 `"1142"`）。

> **⚠️ 換學期提醒**：每學期初請務必更新 `TARGET_SEMESTER`，系統會自動建立全新的 JSON 基準檔，確保新舊學期資料不衝突。

### 步驟 3：設定 GitHub Secrets (雲端金庫)

進入你 GitHub 倉庫的 `Settings` -> 左側欄 `Secrets and variables` -> `Actions`，點擊綠色按鈕 **New repository secret**，新增以下四個變數：

1. `MOODLE_USERNAME`：你的 Moodle 登入帳號（學號，例如 `41200000S`）。
2. `MOODLE_PASSWORD`：你的 Moodle 登入密碼。
3. `LINE_USER_ID`：接收推播的 LINE 目標 ID（步驟 0 取得的 `U` 開頭字串）。
4. `LINE_TOKEN`：步驟 0 取得的 LINE Channel Access Token。

### 步驟 4：啟動 GitHub Actions 排程

1. 確認倉庫中已有 `.github/workflows/monitor.yml` 檔案。
2. 前往 GitHub 上方的 **Actions** 頁籤。
3. 點擊左側的 **Moodle Monitor Bot**，然後點擊右側的 **Run workflow** 進行第一次手動測試。若 LINE 成功收到啟動通知，即大功告成！

---

## 排程時間 (Cron Job)

自動執行設定檔位於 `.github/workflows/monitor.yml`。
*(註：GitHub 伺服器使用的是 UTC 時間，台灣時間需 +8 小時)*

若要修改執行頻率，請調整 `yml` 檔中 `on.schedule` 的 `cron` 參數：

- **每 2 小時執行一次**: `cron: '0 */2 * * *'`
- **每 6 小時執行一次**: `cron: '0 */6 * * *'`
- **每天 07:58, 12:08, 16:18, 18:00, 20:58, 22:58 各執行一次 (預設)**:

  ```yaml
    schedule:
      - cron: '58 12,14,23 * * *'  # 台灣 07:58, 20:58, 22:58
      - cron: '8 4 * * *'          # 台灣 12:08
      - cron: '18 8 * * *'         # 台灣 16:18
      - cron: '0 10 * * *'         # 台灣 18:00```

---

## 免責聲明 (Disclaimer)

1. 僅供學術交流：本專案僅為自動化程式學習與交流之用途，非校方官方工具。
2. 資安風險自負：本腳本需使用個人學號密碼，請務必確保於個人的 Private Repository 內執行，並妥善保管 GitHub Secrets。若因操作不當導致帳號安全問題，開發者概不負責。
3. 合理使用：請遵守伺服器合理使用原則，預設排程為每日 6 次，請勿惡意修改為高頻率執行（如每分鐘執行一次），以免對學校 Moodle 伺服器造成負擔。
4. 使用風險：若因 Moodle 系統改版導致腳本失效，或因執行此腳本引發任何衍生問題，請使用者自行承擔風險。
