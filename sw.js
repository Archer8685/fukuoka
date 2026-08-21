// sw.js — 離線快取
// 策略：App 殼層（HTML/JS/CSS/Leaflet/資料）可離線；國土地理院底圖圖磚 cache-first，看過或預載過即離線可用。
const APP_CACHE = 'fukuoka-app-v85';
const TILE_CACHE = 'fukuoka-tiles-v1';
// 首次安裝就把「離線看行程」需要的全部檔案預快取。
// data.js／trip.js 帶 ?v= 版號，版號直接從 APP_CACHE 推導，不用另外維護一份常數
// （原本這兩支靠執行時快取，但首次造訪時頁面還沒被 SW 接管，fetch 不會被攔 →
//   離線時殼層有、PLACES/TRIP 是 undefined，行程頁會空白。2026/08/18 實測踩到。）
const V = APP_CACHE.replace(/^.*-v/, '');
const SHELL = ['./', 'itinerary.html', 'map.html', 'prep.html', 'verify.html', 'libs/leaflet.js', 'libs/leaflet.css',
               'data.js?v=' + V, 'trip.js?v=' + V, 'config.js'];

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(APP_CACHE);
    // 逐一加入、容忍個別失敗（避免單一檔缺失導致整包安裝失敗）
    await Promise.allSettled(SHELL.map(u => c.add(new Request(u, { cache: 'reload' }))));
    self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keep = [APP_CACHE, TILE_CACHE];
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => !keep.includes(k)).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch (_) { return; }

  // Google Maps 的資源一律直接走網路、絕不快取——Google 服務條款禁止儲存圖磚。
  if (url.hostname.endsWith('googleapis.com') || url.hostname.endsWith('google.com') || url.hostname.endsWith('gstatic.com')) return;

  // 底圖圖磚（國土地理院／OSM）：cache-first（離線可用；圖磚不變動）
  if (url.hostname.includes('cyberjapandata.gsi.go.jp') || url.hostname.includes('tile.openstreetmap.org')) {
    e.respondWith((async () => {
      const c = await caches.open(TILE_CACHE);
      const hit = await c.match(req);
      if (hit) return hit;
      try { const res = await fetch(req); c.put(req, res.clone()); return res; }
      catch (_) { return hit || Response.error(); }
    })());
    return;
  }

  // 同源 App 檔案
  if (url.origin === location.origin) {
    // HTML 導覽：network-first（線上取最新、離線回退快取）
    if (req.mode === 'navigate') {
      e.respondWith((async () => {
        try {
          const res = await fetch(req);
          const c = await caches.open(APP_CACHE); c.put(req, res.clone());
          return res;
        } catch (_) {
          return (await caches.match(req, { ignoreSearch: true })) || (await caches.match('itinerary.html')) || Response.error();
        }
      })());
      return;
    }
    // config.js：network-first。它沒有版本號（使用者貼上 Google 金鑰後要立刻生效），
    // 若也走 cache-first 會一直吃到舊的空金鑰。
    if (url.pathname.endsWith('/config.js')) {
      e.respondWith((async () => {
        try {
          const res = await fetch(req);
          const c = await caches.open(APP_CACHE); c.put(req, res.clone());
          return res;
        } catch (_) { return (await caches.match(req)) || Response.error(); }
      })());
      return;
    }
    // 其他資產（js/css/圖）：cache-first；帶 ?v= 的檔案版本改變即為新網址、會自動抓新版
    e.respondWith((async () => {
      const hit = await caches.match(req);
      if (hit) return hit;
      try { const res = await fetch(req); const c = await caches.open(APP_CACHE); c.put(req, res.clone()); return res; }
      catch (_) { return Response.error(); }
    })());
    return;
  }
  // 其他跨網域（例如 Google Maps 連結）：直接走網路
});
