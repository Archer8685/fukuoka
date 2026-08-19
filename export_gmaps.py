#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 data.js 的 PLACES 匯出成可餵給 Google 我的地圖（My Maps）的檔案。

    python export_gmaps.py

產出 export/：
  mymaps_all.csv        全部地點（單一圖層）
  mymaps_NN_xxx.csv     依類別分檔（一個檔 = 我的地圖一個圖層，可分色）
  fukuoka.kml           KML 版本，含類別資料夾
  save_links.html       逐點「開 Google Maps → 儲存」清單，含勾選進度

註：Google 沒有寫入「想去的地點」的公開 API，這裡只能做到匯入「我的地圖」，
或用 save_links.html 半手動存。詳見 README。
"""
import json
import os
import re
import html
import csv
from urllib.parse import quote

CATEGORY_ORDER = ["景點", "祭典", "溫泉", "購物", "餐飲", "住宿", "交通"]
CAT_SLUG = {"景點": "sights", "祭典": "festivals", "溫泉": "onsen", "購物": "shopping",
            "餐飲": "food", "住宿": "hotels", "交通": "transport"}
CAT_COLOR = {"景點": "#1a73e8", "祭典": "#d93025", "溫泉": "#e8710a", "購物": "#9334e6",
             "餐飲": "#188038", "住宿": "#795548", "交通": "#5f6368"}
OUT = "export"
NL = "\n"


def load_places(path="data.js"):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"const PLACES = (\[.*?\]);\n", src, re.S)
    if not m:
        raise SystemExit("data.js 解析失敗——先跑 python build_data.py")
    return json.loads(m.group(1))


def gmaps_url(p):
    """用店名搜尋（開得到店家資訊卡，才有「儲存」按鈕），區域字串當定位輔助。"""
    q = p.get("name_ja") or p["name"]
    area = p.get("area") or p.get("city") or ""
    return ("https://www.google.com/maps/search/?api=1&query="
            + quote(("%s %s" % (q, area)).strip()))


def desc(p):
    bits = []
    if p.get("name_ja") and p["name_ja"] != p["name"]:
        bits.append(p["name_ja"])
    if p.get("activities"):
        bits.append("／".join(p["activities"]))
    for k in ("reason", "notes", "address"):
        if p.get(k):
            bits.append(re.sub(r"<[^>]+>", "", p[k]))
    for label, k in (("價位", "price"), ("門票", "ticket"), ("營業", "hours"), ("建議停留", "duration")):
        if p.get(k):
            bits.append("%s：%s" % (label, p[k]))
    if p.get("tabelog"):
        bits.append("食べログ %s" % p["tabelog"])
    if p.get("halal"):
        bits.append("清真：%s" % p["halal"])
    return NL.join(bits)


HEADER = ["名稱", "緯度", "經度", "類別", "城市", "區域", "說明", "座標精度", "Google Maps"]


def row(p):
    return [p["name"], p.get("lat", ""), p.get("lng", ""), p["category"],
            p.get("city", ""), p.get("area", ""), desc(p),
            p.get("coord_status", ""), gmaps_url(p)]


def write_csv(path, places):
    # BOM：Google 我的地圖／Excel 才不會把中文吃成亂碼
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for p in places:
            w.writerow(row(p))


def write_kml(path, places):
    def esc(s):
        return html.escape(str(s), quote=False)

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
           '<name>福岡九州行程地點</name>']
    for cat in CATEGORY_ORDER:
        color = CAT_COLOR.get(cat, "#1a73e8")
        abgr = "ff" + color[5:7] + color[3:5] + color[1:3]   # KML 顏色是 aabbggrr
        out.append('<Style id="s_%s"><IconStyle><color>%s</color>'
                   '<Icon><href>http://maps.google.com/mapfiles/kml/paddle/wht-blank.png</href></Icon>'
                   '</IconStyle></Style>' % (CAT_SLUG.get(cat, cat), abgr))
    for cat in CATEGORY_ORDER:
        group = [p for p in places if p["category"] == cat]
        if not group:
            continue
        out.append("<Folder><name>%s</name>" % esc(cat))
        for p in group:
            body = html.escape(desc(p)).replace(NL, "<br>")
            out.append("<Placemark><name>%s</name>"
                       "<description><![CDATA[%s<br><a href=\"%s\">在 Google Maps 開啟</a>]]></description>"
                       "<styleUrl>#s_%s</styleUrl>"
                       "<Point><coordinates>%s,%s,0</coordinates></Point></Placemark>"
                       % (esc(p["name"]), body, gmaps_url(p),
                          CAT_SLUG.get(cat, cat), p["lng"], p["lat"]))
        out.append("</Folder>")
    out.append("</Document></kml>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(NL.join(out))


PAGE = """<!DOCTYPE html>
<html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>存進 Google 想去的地點</title>
<style>
:root{color-scheme:light dark}
body{margin:0 auto;padding:16px 14px 64px;max-width:720px;font:16px/1.5 -apple-system,"Noto Sans TC",sans-serif}
h1{font-size:20px;margin:0 0 8px}
.tip{background:#fff8e1;border-left:4px solid #f9ab00;padding:10px 12px;border-radius:4px;font-size:14px;color:#3c4043}
@media(prefers-color-scheme:dark){.tip{background:#3a3323;color:#e8eaed}}
h2{font-size:16px;margin:26px 0 8px;padding-bottom:4px;border-bottom:2px solid #1a73e8}
h2 .n{float:right;font-weight:400;color:#5f6368;font-size:13px}
.p{display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid rgba(128,128,128,.25)}
.p input{width:20px;height:20px;flex:none}
.p a{flex:1;min-width:0;text-decoration:none;color:inherit}
.p b{display:block;font-weight:600}
.p small{color:#5f6368;font-size:12px}
.p.done{opacity:.4}.p.done b{text-decoration:line-through}
#bar{position:fixed;left:0;right:0;bottom:0;display:flex;justify-content:space-between;align-items:center;
     background:#1a73e8;color:#fff;padding:10px 14px;font-size:14px}
#bar button{background:rgba(255,255,255,.22);color:#fff;border:0;padding:6px 12px;border-radius:4px;font-size:13px}
</style></head><body>
<h1>存進 Google「想去的地點」</h1>
<p class="tip">Google 沒有開放寫入儲存清單的 API，這頁是半手動作法：<br>
點名稱 → Google Maps 開啟該地點 → 按「儲存」→ 選<b>想去的地點</b> → 回這頁打勾。<br>
勾選進度只存在這台裝置的瀏覽器（localStorage）。</p>
__BODY__
<div id="bar"><span id="stat"></span><button id="reset">清除進度</button></div>
<script>
var KEY = 'gmaps-saved-v1';
var done = JSON.parse(localStorage.getItem(KEY) || '{}');
var boxes = [].slice.call(document.querySelectorAll('.p input'));
function stat() {
  var n = boxes.filter(function (b) { return b.checked; }).length;
  document.getElementById('stat').textContent = '已存 ' + n + ' / ' + boxes.length;
}
boxes.forEach(function (b) {
  var k = b.getAttribute('data-k');
  b.checked = !!done[k];
  b.parentNode.classList.toggle('done', b.checked);
  b.addEventListener('change', function () {
    if (b.checked) { done[k] = 1; } else { delete done[k]; }
    localStorage.setItem(KEY, JSON.stringify(done));
    b.parentNode.classList.toggle('done', b.checked);
    stat();
  });
});
document.getElementById('reset').addEventListener('click', function () {
  if (!confirm('清除所有勾選進度？')) return;
  localStorage.removeItem(KEY);
  location.reload();
});
stat();
</script></body></html>"""


def write_links(path, places):
    rows = []
    for cat in CATEGORY_ORDER:
        group = [p for p in places if p["category"] == cat]
        if not group:
            continue
        rows.append('<h2>%s<span class="n">%d</span></h2>'
                    % (html.escape(cat), len(group)))
        for p in group:
            key = html.escape(p["name"], quote=True)
            sub = " · ".join(x for x in (p.get("name_ja"), p.get("city"), p.get("area")) if x)
            rows.append('<div class="p"><input type="checkbox" data-k="%s">'
                        '<a href="%s" target="_blank" rel="noopener">'
                        '<b>%s</b><small>%s</small></a></div>'
                        % (key, html.escape(gmaps_url(p), quote=True),
                           html.escape(p["name"]), html.escape(sub)))
    with open(path, "w", encoding="utf-8") as f:
        f.write(PAGE.replace("__BODY__", NL.join(rows)))


def main():
    places = [p for p in load_places() if p.get("lat") and p.get("lng")]
    os.makedirs(OUT, exist_ok=True)

    write_csv(os.path.join(OUT, "mymaps_all.csv"), places)
    made = ["mymaps_all.csv（全部 %d）" % len(places)]
    for i, cat in enumerate(CATEGORY_ORDER, 1):
        group = [p for p in places if p["category"] == cat]
        if not group:
            continue
        fn = "mymaps_%02d_%s.csv" % (i, CAT_SLUG.get(cat, cat))
        write_csv(os.path.join(OUT, fn), group)
        made.append("%s（%s %d）" % (fn, cat, len(group)))
    write_kml(os.path.join(OUT, "fukuoka.kml"), places)
    write_links(os.path.join(OUT, "save_links.html"), places)
    made += ["fukuoka.kml", "save_links.html"]

    print("匯出 %d 個地點到 %s/：" % (len(places), OUT))
    for m in made:
        print("  -", m)


if __name__ == "__main__":
    main()
