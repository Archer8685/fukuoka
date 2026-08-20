#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""掃出 2027/2/3 由布院→博多 一整天的鐵路班次，找出 ゆふいんの森 真正的發車時刻。

背景：HANDOFF_v4 §五 寫「ゆふいんの森 09:55→12:13 ¥3,250」，
但 transit_detail.py 顯示 09:55／¥3,250 那班是高速巴士（亀の井バス ゆふいん号）。
本腳本關掉巴士（hb=0、lb=0）只看鐵路，逐時段掃描。
"""
import gzip
import io
import re
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept-Encoding": "gzip"}


def fetch(frm, to, y, m, d, hh, m1=0, m2=0, rail_only=True):
    params = {
        "from": frm, "to": to, "y": y, "m": m, "d": d,
        "hh": hh, "m1": m1, "m2": m2, "type": "1", "ticket": "ic",
        "expkind": "1", "al": "1", "shin": "1", "ex": "1", "sr": "1", "s": "0",
        "hb": "0" if rail_only else "1", "lb": "0" if rail_only else "1",
    }
    url = "https://transit.yahoo.co.jp/search/result?" + urllib.parse.urlencode(params)
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    html = raw.decode("utf-8", "replace")
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


found = {}

for hh in ["07", "09", "11", "13", "15", "17"]:
    try:
        body = fetch("由布院", "博多", 2027, "02", "03", hh)
    except Exception as e:
        print(hh, "ERROR", e)
        continue
    for k in range(1, 4):
        j = body.find(f"ルート {k} ")
        if j < 0:
            continue
        seg = body[j:j + 1500]
        head = re.search(r"(\d\d:\d\d) → (\d\d:\d\d) ([^ ]+) ([\d,]+) 円 乗換： (\d) 回", seg)
        if not head:
            continue
        # 找該路線詳情區塊
        d2 = body.find(f"ルート {k} 早")
        for mark in ["早", "楽", "安"]:
            p = body.find(f"ルート {k} {mark}")
            if p >= 0:
                d2 = p
                break
        slab = body[d2:d2 + 1500] if d2 >= 0 else seg
        trains = re.findall(r"(ゆふいんの森\d*号|ゆふ\d+号|ソニック\d+号|きらめき\d+号|"
                            r"新幹線[ぁ-んァ-ヶ]+\d*号)", slab)
        uniq = []
        for t in trains:
            if t not in uniq:
                uniq.append(t)
        key = (head.group(1), head.group(2))
        if key not in found:
            found[key] = (head.group(3), head.group(4), head.group(5), uniq)
    sys.stdout.flush()
    time.sleep(1.5)

print("=== 2027/2/3 由布院 → 博多（僅鐵路）===")
for (dep, arr), (dur, fare, tr, trains) in sorted(found.items()):
    flag = "⭐ ゆふいんの森" if any("の森" in t for t in trains) else ""
    print(f"{dep} → {arr}  {dur}  ¥{fare}  換{tr}回  {' / '.join(trains[:4])} {flag}")
