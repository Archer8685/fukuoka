# AGENTS.md — fukuoka 專案工作規則

2027/2/1–2/12 九州行程網站。GitHub Pages: https://archer8685.github.io/fukuoka/

## 🔴 絕對禁止

**不可憑記憶或推測寫入營業時間、定休日、座標、地址、票價。**

這是本專案最常出錯的地方。實際犯過的錯：
- プリンセスピピ 寫 18:00 開（實際 11:00）
- ステーキハウス ミディアムレア 寫午餐到 14:00（實際 15:00），還抓到 10km 外的同名店
- 三麗鷗／teamLab 寫 10:00 開（實際平日 11:00，撞週三）
- 松月乘船場 寫 09:00–16:00（實際中午休息，10:50 上不了船）
- 馬桜 下通り店 排 13:30 午餐（實際週六只做晚餐）

**唯一合法來源**：`verify_places.py`（Google Places API）或官方網站。
查不到就寫「查不到」，不要填看起來合理的數字。

## 標準流程

改資料 → 一定要跑完這串，缺一步就會出事：

```bash
python build_data.py      # data/*.json → data.js（改 data.js 會被洗掉）
python verify_places.py   # Google Places 實查營業時間／座標
python check_all.py       # 全域健檢
python bump_version.py    # 同步 16 處版號
git add -A && git commit && git push
```

### 各腳本用途

| 腳本 | 作用 | 注意 |
|---|---|---|
| `build_data.py` | `data/*.json` → `data.js` | **會剝掉 `q` 欄位** |
| `verify_places.py` | 打 Places API 實查 | 全量約 3–5 分鐘；`verify_places.py 5 7` 只查指定天（會與既有快取合併，不會洗掉） |
| `check_all.py` | 離線健檢（不打 API） | 定休日檢查依賴 `audit/verify_places_*.json` 快取 |
| `bump_version.py` | 版號 | `--check` 只驗不改 |

### check_all.py 檢查什麼

1. `data/*.json` 合法、名稱不重複、都有座標且落在九州＋下關
2. `data.js` 與 `data/*.json` 同步（忘了 build 會被抓到）
3. 版號 16 處一致
4. 12 天、日期↔星期符合 2027 年曆、每天時間遞增、站點名稱都存在、住宿連續性
5. **每站停留時間 ≥ 該地點建議 duration**（扣掉移動時間）
6. **定休日 vs 造訪星期**

第 5、6 項是後來補的，因為它們各自漏掉過一次真 bug。

### 停留時間基準線

有些站是刻意壓縮的（門司港復古區 建議 120 分但只給 50）。這些現況存在
`audit/stay_baseline.json`，所以乾淨狀態是 0 警告。
**刻意調整某站時間後**：`python check_all.py --save-baseline` 重設基準線。
未經 `--save-baseline` 而冒出的新警告 = 你剛剛不小心擠爆了某一站。

## 資料慣例

- **新增／修改地點一律改 `data/*.json`**，不要直接改 `data.js`（build 會覆蓋）
- 同名店家消歧義：在 `data/*.json` 該筆加 `q` 欄位當搜尋字串
  （例 `"q": "ステーキハウス ミディアムレア ザ・ルイガンズ 西戸崎"`）
- `trip.js` 是 **CRLF** 換行，Python 讀寫要 `open(p, newline="")` 保留
- `trip.js` 用 `const` 宣告，Node 解析要用
  `new Function(src + '; return {TRIP};')()`，**直接 `eval` 會 exit 1**
- 站點 `kind`：`spot` / `meal` / `shop` / `move`（轉乘，不算停留）/ `hotel`

## 回報規則

- **所有問題都要列出來，包含你判斷為「無害」的**。曾經全掃出 6 個問題只回報 3 個。
  由使用者決定哪些無害，不要自行過濾。
- 改動後要說明「這次改動可能影響到的其他站」，不是只講改的那一站。
- 明確區分：①API 實查的 ②官網查到的 ③推測的 ④查不到的。
- 行程調整**先給差異表（改前→改後＋理由）等確認**，不要直接改檔案。
  使用者曾明講「先不要調整 先問我」。

## 外部待確認（API 查不到，需人工）

- ν鋼彈點燈時刻表
- 人形町今半 訂位
- くまモンスクエア「部長」出勤場次
- ゆふいんの森 指定席開賣（乘車日前一個月 10:00）
- 田舎庵 小倉本店 訂位

## 環境

- Windows / git-bash。POSIX 語法，不要用 PowerShell 指令
- `terminal` 裡 **heredoc 會報 `stdin is not a tty`**；node 單行內用
  **arrow function 也會觸發同錯**，改寫成 `function(x){...}`
- Google Places API key 在 `config.js`，需帶 `Referer: https://archer8685.github.io/fukuoka/`
- `searchText` 必須加 `regionCode: "JP"` ＋ `locationBias`（radius 上限 50000），
  否則會回台灣的店家
