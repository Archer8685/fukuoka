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

**唯一合法來源是 `verify_places.py`（Google Places API）。**

- ❌ **禁止**用 WebSearch／WebFetch／記憶查到營業時間後直接寫進 `data/*.json`。
  食べログ、ぐるなび、HotPepper、店家官網、觀光協會頁面都**不能**單獨當來源——
  這些頁面互相矛盾且常過期，本專案三次填錯都是這樣來的
  （プリンセスピピ、ステーキハウス ミディアムレア、三麗鷗）。
- ✅ 流程：改完行程 → `python verify_places.py`（可只查改動的天，例 `verify_places.py 5 7`）
  → 用它回傳的 hours 寫進 `data/*.json` → `check_all.py` 驗。
- 官網／電話只能用來補 **API 拿不到的欄位**（訂位方式、服務費、清真對應細節），
  並在 note 標明來源等級。
- API 查不到營業時間就寫「查不到，出發前自行確認」，**不要填看起來合理的數字**。

`check_all.py` 會擋：行程站點若不在 `audit/verify_places_*.json` 快取中 → **錯誤**（非警告）。

### 地點快取（不會重複查同一家店）

`verify_places.py` 有兩層快取，所以「硬性規則」不等於每次都燒 80 次 API：

| 檔案 | 內容 | 作用 |
|---|---|---|
| `audit/places_cache.json` | 以**查詢字串 q** 為 key 的店家原始資料＋`fetched` 日期 | 同一家店只打一次 API，跨執行有效，預設 **30 天**內重用 |
| `audit/verify_places_<date>.json` | 每個**行程站點**一筆（check_all 讀這份） | 部分執行會自動接續最近一份報告 |

- 同一家店出現在兩天 → 只打一次 API。
- 只改了 2/5 就 `verify_places.py 5`：沒動過的店全部命中快取，**API 呼叫 0 次**。
- 執行完會印 `API 呼叫 N 次、快取命中 M 次`，可以直接看有沒有白花。
- **出發前務必跑一次 `verify_places.py --refresh`** 全部重驗——快取會讓你看到 30 天前的營業時間。
- 部分執行（`verify_places.py 5 7`）會接續**最近一份**報告，不只今天那份；
  否則換一天再跑會產出只含那兩天的報告，check_all 就把其餘站點全判成未實查。

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
- 文字檔由 `.gitattributes` 統一為 **LF**；不要手動轉成 CRLF
- `trip.js` 用 `const` 宣告，Node 解析要用
  `new Function(src + '; return {TRIP};')()`，**直接 `eval` 會 exit 1**
- 站點 `kind`：`spot` / `meal` / `shop` / `move`（轉乘，不算停留）/ `hotel`

## 🔴 第二類常犯錯：改了主站，沒清乾淨連帶物

從 58 個 commit 的歷史看，「改一處、漏三處」是本專案第二高頻的錯誤來源。
實際發生過：`修 prep.html 殘留的長崎駅Ⅲ`、`清除舊館殘留`、`v84 還原 v83 的樣式`、
`旅館資訊全庫同步`。**換掉一個站點時，同一輪必須全部檢查：**

1. **`alt` 備選清單** — 被判定「會撲空」的店**不可以留在備選裡**。
   曾經把 馬桜 下通り店（週六無午餐）、松月乘船場（中午休息）換掉，
   卻仍留在 `alt` 讓使用者當備案挑 → 等於沒修。
   若要保留當反面提醒，寫進 note 的「不要改去 X」，不要放 `alt`。
2. **其他天的 note 交叉引用** — 例如 2/5 note 提到「小倉昨天逛完」，
   2/4 內容改了就要回頭看 2/5。
3. **`prep.html` / `itinerary.html` / `HANDOFF.md`** — 是否還寫著舊店名。
4. **`data/*.json`** — 新主站有沒有座標與營業時間；舊站是否還被別處引用
   （`check_all.py` 會抓 alt 參照缺資料，但不會抓 note 裡的文字）。

## 🔴 第三類常犯錯：note 寫成修改歷程

**站點 note 只寫「現在的結果」，不寫「我改了什麼」。**
使用者已經為此開過兩個 commit 清理（`v65 清除全檔歷程語言`、
`站點註記改成只講結果，不留修改歷程`），但之後又再犯。

- ❌ `2026-08-22 用 Google Places 實查後換掉了原本的「馬桜 下通り店」`
- ❌ `已從 18:00 夜景版改為 17:10 夕陽版`
- ❌ `開門時間訂正（Google Places 實查 2026-08-22）`
- ✅ `全週 11:30–14:30 都做午餐，週六沒有例外`
- ✅ `⚠️ 不要改去「馬桜 下通り店」：那家週六 16:00 才開`（反面提醒可以留，但講的是現況）

理由：使用者看的是**出發當天要用的行程**，不是開發日誌。
修改歷程屬於 commit message 與 changelog，不屬於 note。
**不要在 note 裡寫日期戳記或「訂正」「換掉了」「原本是」這類字眼。**

## 🟡 第四類：HANDOFF.md 會落後

`HANDOFF.md` 自稱「唯一權威」，但實際曾停在 v78 而行程已到 v103。
**「行程現在長什麼樣」永遠以 `trip.js` 為準**，HANDOFF 只存決策理由與外部待確認事項。
改完行程若動到決策，順手更新 HANDOFF 的「最後更新」與相關段落。

## 🟡 第五類：UI 改動來回反覆

`v82→v83→v84→v85` 四個 commit 在 30 分鐘內反覆改同一個版面
（`修正單行顯示` → `還原間距` → `微調樣式`）。
**改 CSS／版面前先用瀏覽器實際看一次再動手**，不要憑想像連續微調。

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
- 在 Windows 驗證 JavaScript 語法用 `node.exe --check ./trip.js`，不要用
  `node --check trip.js`，避免 Git Bash 包裝層偶發 `stdin is not a tty`
- `terminal` 裡 **heredoc 會報 `stdin is not a tty`**；node 單行內用
  **arrow function 也會觸發同錯**，改寫成 `function(x){...}`
- Google Places API key 在 `config.js`，需帶 `Referer: https://archer8685.github.io/fukuoka/`
- `searchText` 必須加 `regionCode: "JP"` ＋ `locationBias`（radius 上限 50000），
  否則會回台灣的店家
