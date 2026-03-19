---
name: Bug Report (程式錯誤回報)
about: 回報 Moodle 抓取失敗、GitHub Actions 執行錯誤或 LINE 通知異常
title: "[Bug] 請簡述問題 (例如：無法抓取作業說明)"
labels: bug
assignees: amais23

---

**Describe the bug (問題描述)**
請簡短描述你遇到的錯誤是什麼。（例如：GitHub Actions 執行出現紅叉叉、LINE 一直沒收到通知、或是 Moodle 某堂課的作業一直重複通知）

**Error Logs (錯誤日誌)**
請貼上 GitHub Actions 執行失敗時，終端機畫面顯示的 Python 錯誤訊息（例如 `AttributeError`, `KeyError` 等等）。這對修復問題非常有幫助！
```text
(請將錯誤訊息貼在這一區塊內)
```

**To Reproduce (問題發生的情境)**
1. 你有自己修改過 main_monitor.py 裡的其他程式碼嗎？ (有 / 沒有)
2. 這個錯誤是發生在特定的課程嗎？ (例如：只有某堂課的公告抓不到)
3. 這是第一次執行就失敗，還是原本正常，突然壞掉的？

**Expected behavior (預期結果)**
原本預期程式應該怎麼運作？（例如：預期 18:00 會收到日報，但卻什麼都沒收到）

**Screenshots (截圖)**
如果可以，請直接將 GitHub Actions 報錯畫面的截圖，或是 LINE 通知異常的畫面截圖拖曳上傳到這裡。

**Checklist (發問前請先檢查)**
請在括號內打 x 表示已確認： `[x]`
- [ ] 我已經確認 GitHub Secrets 的 4 個變數 (學號、密碼、LINE ID、Token) 都設定正確且沒有多餘的空白。
- [ ] 我已經確認這份專案倉庫的權限是 Private (私有)。
- [ ] 我的師大 Moodle 密碼最近沒有更改過，且可以正常登入網頁版。

**Additional context (補充說明)**
有其他想補充的資訊都可以在這裡填寫。
