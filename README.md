# 福岡・九州旅遊網站（2027/2/1–2/12）

純靜態網站，任何靜態空間（GitHub Pages / Netlify / Vercel / S3 / nginx）皆可部署，無後端、無資料庫。
架構沿用 [sichuan](../sichuan) 專案。

- **行程**：12 天 11 夜，JR 為主，換宿 3 次（博多 6 晚＋長崎 3 晚＋湯布院 2 晚）
- **航班**：CI110 TPE 06:50 → FUK 10:00（2/1 一）／ CI117 FUK 20:35 → TPE 22:20（2/12 五）
- **溫泉據點**：湯布院（別府已排除）

## 檔案結構

```
index.html        入口（轉址到行程頁）
config.js         底圖設定（Google Maps 金鑰，預設空白＝用國土地理院）
prep.html         行前準備（倒數時間軸、訂票清單、入境、免稅、打包、清真）
itinerary.html    逐日行程（載入 data.js 自動附加地點詳情）
map.html          互動地圖（Leaflet + 國土地理院圖磚，可選 Google 底圖）
verify.html       座標稽核：用 Google Places 逐筆驗證 data.js 的座標（見下節）
lookup.html       座標補齊：對「還沒有座標」的新地點向 Google Places 要座標／地址／營業時間（見下節，僅本機可用）
data.js           ★ 唯一資料檔（PLACES / J2T），由 build_data.py 產生
trip.js           ★ 最終行程資料（TRIP / BACKUPS），手動維護
sw.js             Service Worker（離線快取）
libs/             Leaflet 1.9.4 ＋ Leaflet.GoogleMutant 0.13.4 本地副本（已去 CDN 依賴）
data/*.json       原始研究資料（部署可不上傳，僅重建 data.js 用）
build_data.py     資料合併：python build_data.py → 重新產生 data.js
geocode.py        座標稽核：Overpass → Nominatim → 國土地理院，逐城市 bbox 驗證（有執行鎖，不可並行）
fix_coords.py     手動座標覆寫表：自動查不到或配錯的地點在這裡指定 lat/lng
bump_version.py   版號 +1／--check：一次改完散在 4 處的版號
check_all.py      一鍵健檢：資料／座標／同步／版號／行程邏輯
export_gmaps.py   匯出 Google 我的地圖用的 CSV／KML ＋ 逐點儲存清單（見下節）
apply_google_coords.py  把 verify.html 稽核出的座標套回 data/*.json（偏掉的才改）
apply_google_lookup.py  把 lookup.html 查到的座標／地址／營業時間套進 data/*.json
fix_coords.py     手動座標表：補自動查不到、或明顯配錯的地點（詳見下節）
audit/            座標查詢紀錄（geocode_latest.json）與稽核報告（REVIEW-*.md）
export/           export_gmaps.py 的產出（CSV／KML／save_links.html）
```

## 部署清單（最小集合）

`index.html`、`prep.html`、`itinerary.html`、`map.html`、`verify.html`、`data.js`、`trip.js`、`config.js`、`sw.js`、`libs/`（整個資料夾）

## 對外相依（部署後仍需網路的部分）

1. **國土地理院圖磚** `cyberjapandata.gsi.go.jp`：官方、免金鑰、日本境內細節最好，**預設底圖**。
   地圖右上可切換「淡色／標準／OpenStreetMap」。
   - 日本座標為 **WGS-84**，與 Leaflet／OSM／國土地理院／Google 一致——**不需要**像中國那樣做
     GCJ-02 偏移轉換。瀏覽器定位回傳的座標也可以直接用。
2. 各地點的「🧭 在 Google Maps 開啟」為外部連結。
3. **Google Map 底圖（選用，預設關閉）**：見下節。

## 用 Google Map 當底圖（選用）

在 [`config.js`](config.js) 填入 Google Maps JavaScript API 金鑰即可，右上角圖層選單會多出
「Google 道路／Google 衛星／Google 地形」。沒填金鑰就完全不載入 Google 的東西，網站照常運作。

```js
const GMAPS_KEY = "你的金鑰";
```

實作走**官方路線**：載入 Google Maps JavaScript API，再用
[`libs/Leaflet.GoogleMutant.js`](libs/Leaflet.GoogleMutant.js) 把它包成 Leaflet 圖層——
既有的圖釘、popup、行程路線程式碼一行都不用改。

⚠️ **不使用 `mt0.google.com/vt/...` 之類的裸圖磚網址。** 那種寫法一行就能換底圖、網路上也到處都是，
但它違反 Google 服務條款（繞過計費與歸屬），而且是非公開端點、Google 隨時可以擋掉。本專案不採用。

### 取得金鑰的注意事項

1. Google Cloud Console 建專案 → 啟用 **Maps JavaScript API** → 建立 API 金鑰。
2. ⚠️ **一定要加「HTTP 參照網址」限制**，只允許自己的網域
   （`https://archer8685.github.io/fukuoka/*`、`http://localhost:5173/*`）。
   靜態網站無法隱藏金鑰，它一定會出現在原始碼裡——安全性來自參照網址限制，不是來自藏起來。
   再加「API 限制」只允許 Maps JavaScript API。
3. ⚠️ **需要綁信用卡**才會發金鑰。個人行程網站的用量遠低於免費額度，實務上不會產生費用，
   但帳號本身要有計費設定。
4. ⚠️ **Google 圖磚不可離線快取**（服務條款）。所以：
   - 切到 Google 底圖時「離線預載此區地圖」按鈕會自動停用
   - `sw.js` 對 `googleapis.com` / `google.com` / `gstatic.com` 一律直接走網路、不進快取
   - 要離線用，請切回國土地理院或 OpenStreetMap

`config.js` 刻意**不帶 `?v=` 版本號**，且在 `sw.js` 走 network-first——否則貼上金鑰後會一直吃到
快取裡的舊空金鑰（實測踩過）。

其餘（Leaflet、字型、資料）皆已本地化，離線也能開啟版面；地圖頁有「⬇️ 離線預載此區地圖」可把目前範圍的圖磚存進快取。

## ⚠️ 座標精度（重要）

座標是用 `geocode.py` 自動查的，三段來源的精度差很多，每個地點都記在 `coord_status`：

| coord_status | 來源 | 精度 | 地圖上的提示 |
|---|---|---|---|
| `overpass` | OSM POI 名稱完全比對 | 門口級 | 無 |
| `nominatim` | OSM 全文檢索（bbox 內） | 門口至街區級 | 無 |
| `gsi` | 國土地理院地名／地址檢索 | **地名／地址級，可能差數十至數百公尺** | popup 顯示黃色警告 |
| `approx` | `fix_coords.py` 依地址／街區推估 | **可能差數十至數百公尺** | popup 顯示黃色警告 |
| `manual` | `fix_coords.py` 人工確認的地標位置 | 通常 50m 內 | popup 註明手動填入 |
| `missing` | 查不到 | 無座標，**地圖上不會出現** | 行程頁的站點會標註 |

**所以每個地點的 popup 都放了「🧭 在 Google Maps 開啟」——用日文店名去 Google Maps 搜，
就算我們的圖釘偏了幾百公尺，現場導航一定找得到正確的門口。** 這是設計上的安全網，請以它為準。

要提升精度就跑：

```bash
python geocode.py           # 只補沒有座標的（增量）
python geocode.py --all     # 全部重查
python geocode.py --only 櫛田  # 只查名稱含關鍵字的
```

查不到的（`missing`）與**自動查錯的**，統一寫在 `fix_coords.py` 的 `FIX` 表裡，跑 `python fix_coords.py` 套用；
`manual`／`approx` 之後重跑 `geocode.py` 都不會被覆蓋。查詢紀錄在 `audit/geocode_latest.json`。

⚠️ **bbox 驗證擋不住「同名但同縣」的錯配**，實際踩到的例子（都已在 `fix_coords.py` 修正）：
日田站與想夫恋被配到大分市（日田在經度 130.94，原本大分 bbox 從 131.10 才開始，已放寬到 130.85）、
空想之森アルテジオ被配到別府的 artegio dining、長崎縣美術館被配到佐世保、
岩田屋本店被配到西區石丸的另一家岩田屋、やま中被配到南區的同名店。
**新增地點後請肉眼掃一遍 `audit/geocode_latest.json` 的 display_name，不要盲信自動結果。**

`geocode.py` 用 **curl** 發 HTTP，不用 Python urllib——本機的 CA bundle 已過期，
urllib 連 overpass-api.de 會 `CERTIFICATE_VERIFY_FAILED`。

另外每次查詢都會用「該城市的 bbox」過濾：日本同名地點極多
（福岡市也有「別府駅」、茨城縣也有「竹瓦」、岩手縣也有「福岡」），
不做 bbox 驗證會配到完全另一個縣的地方。

## 用 Google 驗證座標（verify.html）

`geocode.py`／`area_fallback.py` 的來源（OSM、國土地理院、區域中心點）精度落差很大，
所以另外做了一支 **`verify.html`**：把每個地點的日文名丟給 **Google Places**，
比對回傳座標與現有座標的距離，一次看完全部。

```
在 http://localhost:5173/verify.html 開啟（金鑰的參照網址限制必須涵蓋這個網域）
→ 先按「試跑前 20 筆」確認 API 可用
→ 再按「全部驗證」
→ 按「產生 fix_coords.py 修正表」，把 >100m 的項目貼回 fix_coords.py 的 FIX
```

判讀標準：**<100m** 視為一致；**100–500m** 值得看（同名分店、建物大、或我們用的是區域中心點）；
**>500m** 幾乎確定配錯。**「查無」不代表錯**——像「豪斯登堡 園內美食」這種概念性地點
Google 上本來就沒有。

⚠️ **這是計費 API**。全跑一次約 286 次 Places Text Search 請求，個人用量通常在免費額度內，
但請自行確認 Google Cloud 的帳單設定。
⚠️ 金鑰的「API 限制」必須包含 **Places API**，專案也要啟用它，否則會 `REQUEST_DENIED`。
⚠️ **不要盲目套用 Google 的座標**：Google 回傳的是它自己的 POI 位置，偶爾也會指到分店或
行政區中心。修正表產生後請逐筆看 Google 回傳的名稱與地址對不對，再決定要不要採用。

## 新地點補座標（lookup.html）

`verify.html` 的前提是「已經有座標，拿 Google 比距離」。
新增一批**還沒有座標**的地點時用另一支 **`lookup.html`**：它直接 `fetch` `data/*.json`，
挑出 `lat` 為空或 `coord_status=missing` 的地點，用各筆的 **`q` 欄位**當查詢字串問 Google Places，
一次取回**官方座標、地址、每週營業時間、歇業狀態**。

```
python -m http.server 5173
在 http://localhost:5173/lookup.html 開啟 → 按「開始查詢」
→ 逐筆看「Google 回傳名稱／地址」對不對（地址欄會標「區域相符 / 對不上 / 不在福岡縣」）
→ 結果存成 audit/google_lookup_<日期>.json
→ 寫一支 apply_google_lookup.py 把它套進 data/*.json，再跑 build_data.py
```

⚠️ 它讀的是 `data/` 原始目錄（靠 `http.server` 的目錄索引列檔），**只有本機跑得起來**，
所以 `lookup.html` 不在部署清單裡。
⚠️ 同樣是計費 API，且金鑰的參照網址限制必須涵蓋 `localhost:5173`。
⚠️ **Google 的第一筆不一定是你要的那家。** 實際踩到的：
`Comme des Garçons` 配到岩田屋本店的專櫃（獨立店已歇業）、
`1834` 沒有獨立點位而回傳母店 LIGHT YEARS、
`ヤシの木ブランコ`（沙灘上的鞦韆）配到旁邊的餐廳ざうお。
這些都在 `apply_google_lookup.py` 的 `SPECIAL` 表裡人工覆寫，並寫明理由。

`apply_google_lookup.py` 除了座標還會做兩件事：
1. **用 Google 地址反推 `area` 標籤**——手寫的區域常常是錯的
   （例：Dice&Dice、Factory-market、artwork 其實都在**今泉**不是大名；Loopwheeler 在**藥院**）
2. **把營業時間壓成一行**，並比對行程日：本行程在福岡只有
   **2/1(一)、2/2(二)、2/3(三)、2/4(四)、2/10(三)、2/11(四)、2/12(五)——完全沒有週末**，
   所以「週三定休」「只有六日營業」這種店會直接在 `notes` 標出來。

## 更新資料

改或新增 `data/*.json` 後執行：

```bash
python geocode.py && python fix_coords.py && python build_data.py
```

⚠️ **不要同時跑兩個 `geocode.py`**：兩個 process 各持一份 `data/*.json` 快照互相覆寫，
後結束的那個會把先前的編輯還原（2026/08/18 實際踩過，`data/hotels.json` 整批新增被蓋掉）。
`geocode.py` 現在有鎖檔 `audit/.geocode.lock` 防這件事；若異常中斷需手動刪除該檔。

`build_data.py` 會去重、依分類排序、產生繁體／日文新字體搜尋對照表（J2T），
並列出還沒有座標的地點。

## 匯進 Google 地圖（export_gmaps.py）

**Google 沒有開放寫入「想去的地點」的 API。** 儲存清單（Saved lists）是帳號私有資料，
Maps Platform 那組 API 全部是唯讀的，也沒有對應的 OAuth scope；Takeout 只能把清單匯出，
不能反向匯入。所以「一鍵把 305 個點灌進想去的地點」在官方管道下做不到。

能做的是這兩條，跑 `python export_gmaps.py` 產生 `export/`：

**A. 匯進「我的地圖」（My Maps）——全自動，但存的是自訂地圖不是想去的地點**

```
https://www.google.com/mymaps → 建立新地圖 → 匯入 → 選 export/mymaps_01_sights.csv
→ 標記位置的欄位選「緯度」「經度」→ 標題欄位選「名稱」
→ 其餘 mymaps_02..07 各自「新增圖層」再匯入一次（一個類別一層，可分色）
```

手機版 Google Maps 在「已儲存 → 地圖」看得到，可離線、可導航，但不會併進「想去的地點」。
`export/fukuoka.kml` 是同一份資料的 KML 版（含類別資料夾），偏好匯 KML 的話用這個。
My Maps 限制：一層 2000 列、最多 10 層、單檔 5MB——目前 305 點都遠低於上限。

**B. `export/save_links.html`——逐點手動存進「想去的地點」**

每個地點一個 Google Maps 連結（用日文店名＋區域搜尋，開得到店家資訊卡才有「儲存」鈕），
點開存完回來打勾，進度存在瀏覽器 localStorage。305 點全部存完大概要半小時，
但這是唯一能真的進到「想去的地點」的路。

**C. 瀏覽器自動化（2026/08/19 實測可行，但有前提）**

用 Claude in Chrome 驅動已登入的 Chrome，逐點「儲存 → 想去的地點」，88 個行程站點全部成功。
關鍵限制：**Chrome 分頁必須是 `document.visibilityState === 'visible'`**——分頁被其他視窗完全遮住時，
Google Maps 收得到 hover 但不處理點擊，儲存選單根本不開（背景分頁還會被計時器節流，
in-page 輪詢曾讓 renderer 卡死 45 秒）。把 Chrome 放到第二螢幕或左右並排才穩。

實作重點：`computer` 的真實點擊在這頁不可靠，改用 JS 合成 pointerdown/mousedown/pointerup/click；
搜尋結果是列表時先點第一筆 `a.hfpxzc`，並排除 `.Nv2PK` 內含「贊助商」的廣告卡
（踩過一次：找飯店時存到廣告的 Hotel Indigo）。

⚠️ 這仍然違反 Google 服務條款、帳號有被鎖的風險，UI 一改就壞。要跑請自負風險，
一般情況用 A 或 B 就好。

## 快取提醒

`map.html`／`itinerary.html` 以 `data.js?v=N`／`trip.js?v=N` 帶版本號載入，避免瀏覽器快取舊檔。
每次修改 `data.js` 或 `trip.js` 後，記得把兩個 HTML 檔裡的 `?v=N` +1。

⚠️ **改版號時，Service Worker 快取名也必須同步更新**，否則 PWA 會一直吃舊殼層。
版號散落在 4 個位置，**必須全部一起改成同一個 vN**：

1. `sw.js` 的 `const APP_CACHE = 'fukuoka-app-vN'`
2. `itinerary.html`／`map.html`／`prep.html` 的 `?v=N`
3. 三個 HTML 底部 warm-up 腳本裡的 `caches.open('fukuoka-app-vN')`
4. `trip.js` 的 `SITE_VERSION`（顯示在導覽列）

**不要手動改這 4 處**——用 `bump_version.py`，它會一次改完並檢查一致性：

```bash
python bump_version.py          # 全部 +1
python bump_version.py --check  # 只檢查是否一致（不一致回傳 1，可放 CI）
python bump_version.py --set 7  # 指定版號
```

漏 bump 的症狀是「檔案改了但畫面沒變」——SW 會繼續回舊的 `data.js?v=N`。
遇到時先跑 `python bump_version.py --check`。

## 一鍵健檢

改完任何東西後跑這一支就好，它會把下面全部檢查一遍（有問題回傳 1，可掛 CI 或 pre-commit）：

```bash
python check_all.py
```

1. `data/*.json` 合法、名稱不重複
2. 每個地點都有座標且落在九州＋下關 bbox 內（擋掉配到外縣市的座標）
3. `data.js` 與 `data/*.json` 同步（忘記 `build_data.py` 會被抓到）
4. 版號 4 處一致（忘記 `bump_version.py` 會被抓到）
5. `trip.js` 語法（需要 node，沒有就跳過這兩項）
6. 行程邏輯：12 天、日期↔星期符合 2027 年曆、每天時間遞增、方案標記完整、
   住宿連續性與換宿次數、每個站點與備選都能在 `data.js` 找到

## 待確認事項（2027 年官方公告後要回頭查）

- **節分日期**：推算 2027/2/3（立春 2/4），2026 年為 2/3 — 待櫛田神社公告
- **長崎燈會**：會期 2027/2/5–2/21 已由長崎旅網公告；**皇帝遊行／媽祖行列的詳細時刻表**約 2026 年 12 月公告
- **柳川雛祭さげもんめぐり**：開幕日慣例 2/11 — 待柳川市公告
- **太宰府梅花花況**：出發前看天滿宮官方開花情報
- **JR 九州 Pass 價格**：全九州 3/5/7 日 ¥22,000/¥24,000/¥26,000（2026/08 官網），出發前再確認
- **日本免稅新制**：2026/11/1 起改為「リファンド方式」（先付含稅價、出境時退稅），
  廢止一般品／消耗品區分與 50 萬日圓上限。2027/2 出行會適用新制，實際流程以現場為準
- **動漫類景點的營業日／票價**：ハーモニーランド（三麗鷗和諧樂園）**冬季平日多休園**，2/9 是週二極可能沒開，看 harmonyland.jp 營業日曆；
  進撃の巨人 in HITA ミュージアム（本館／ANNEX）票價與休館日看 shingeki-hita.com；
  北九州市漫畫博物館**週二休**（2/4 是週四沒問題）；サンリオキャラクターズ ドリーミングパーク 看 e-zofukuoka.com
- **旅館房價與房型**：`data/hotels.json` 內的價位帶是概算，務必逐家上官網／樂天／一休確認，
  並注意「客室露天風呂付き」是房型條件而非全館條件

## 已定住宿

| 城市 | 飯店 | 晚數 |
|---|---|---|
| 福岡 | 東急STAY博多（客室內洗衣烘乾機） | 6（2/1–2/4、2/10–2/11） |
| 長崎 | Coruscant Hotel 長崎駅Ⅲ（公寓式，三館中位置最好） | 3（2/5–2/7） |
| 湯布院 | 由布院 玉の湯（御三家） | 2（2/8–2/9） |

其餘旅館候選都留在 `data/hotels.json`，在地圖的 🏨 住宿類別可以看到各自的取捨。
