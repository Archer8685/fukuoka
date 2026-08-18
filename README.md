# 福岡・九州旅遊網站（2027/2/1–2/12）

純靜態網站，任何靜態空間（GitHub Pages / Netlify / Vercel / S3 / nginx）皆可部署，無後端、無資料庫。
架構沿用 [sichuan](../sichuan) 專案。

- **行程**：12 天 11 夜，JR 為主，換宿 3 次（博多 6 晚＋長崎 3 晚＋湯布院 2 晚）
- **航班**：CI110 TPE 06:50 → FUK 10:00（2/1 一）／ CI117 FUK 20:35 → TPE 22:20（2/12 五）
- **溫泉據點**：湯布院（別府已排除）

## 檔案結構

```
index.html        入口（轉址到行程頁）
itinerary.html    逐日行程（載入 data.js 自動附加地點詳情）
map.html          互動地圖（Leaflet + 國土地理院圖磚）
data.js           ★ 唯一資料檔（PLACES / J2T），由 build_data.py 產生
trip.js           ★ 最終行程資料（TRIP / BACKUPS），手動維護
sw.js             Service Worker（離線快取）
libs/             Leaflet 1.9.4 本地副本（已去 CDN 依賴）
data/*.json       原始研究資料（部署可不上傳，僅重建 data.js 用）
build_data.py     資料合併：python build_data.py → 重新產生 data.js
geocode.py        座標稽核：Overpass → Nominatim → 國土地理院，逐城市 bbox 驗證
fix_coords.py     手動座標表：補自動查不到、或明顯配錯的地點（詳見下節）
audit/            座標查詢結果紀錄（geocode_latest.json）
```

## 部署清單（最小集合）

`index.html`、`itinerary.html`、`map.html`、`data.js`、`trip.js`、`sw.js`、`libs/`（整個資料夾）

## 對外相依（部署後仍需網路的部分）

1. **國土地理院圖磚** `cyberjapandata.gsi.go.jp`：官方、免金鑰、日本境內細節最好。
   地圖右上可切換「淡色／標準／OpenStreetMap」。
   - 日本座標為 **WGS-84**，與 Leaflet／OSM／國土地理院一致——**不需要**像中國那樣做 GCJ-02 偏移轉換。
     瀏覽器定位回傳的座標也可以直接用。
2. 各地點的「🧭 在 Google Maps 開啟」為外部連結。

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

## 快取提醒

`map.html`／`itinerary.html` 以 `data.js?v=N`／`trip.js?v=N` 帶版本號載入，避免瀏覽器快取舊檔。
每次修改 `data.js` 或 `trip.js` 後，記得把兩個 HTML 檔裡的 `?v=N` +1。

⚠️ **改版號時，Service Worker 快取名也必須同步更新**，否則 PWA 會一直吃舊殼層。
版號散落在 4 個位置，**必須全部一起改成同一個 vN**：

1. `sw.js` 的 `const APP_CACHE = 'fukuoka-app-vN'`
2. `itinerary.html` 與 `map.html` 的 `?v=N`（各 2 處：preload 與 script）
3. `itinerary.html` 與 `map.html` 底部 warm-up 腳本裡的 `caches.open('fukuoka-app-vN')`
4. `trip.js` 的 `SITE_VERSION`（顯示在導覽列）

## 待確認事項（2027 年官方公告後要回頭查）

- **節分日期**：推算 2027/2/3（立春 2/4），2026 年為 2/3 — 待櫛田神社公告
- **長崎燈會**：會期 2027/2/5–2/21 已由長崎旅網公告；**皇帝遊行／媽祖行列的詳細時刻表**約 2026 年 12 月公告
- **柳川雛祭さげもんめぐり**：開幕日慣例 2/11 — 待柳川市公告
- **太宰府梅花花況**：出發前看天滿宮官方開花情報
- **JR 九州 Pass 價格**：全九州 3/5/7 日 ¥22,000/¥24,000/¥26,000（2026/08 官網），出發前再確認
- **旅館房價與房型**：`data/hotels.json` 內的價位帶是概算，務必逐家上官網／樂天／一休確認，
  並注意「客室露天風呂付き」是房型條件而非全館條件

## 已定住宿

| 城市 | 飯店 | 晚數 |
|---|---|---|
| 福岡 | 東急STAY博多（客室內洗衣烘乾機） | 6（2/1–2/4、2/10–2/11） |
| 長崎 | Coruscant Hotel 長崎駅Ⅲ（公寓式，三館中位置最好） | 3（2/5–2/7） |
| 湯布院 | 由布院 玉の湯（御三家） | 2（2/8–2/9） |

其餘旅館候選都留在 `data/hotels.json`，在地圖的 🏨 住宿類別可以看到各自的取捨。
