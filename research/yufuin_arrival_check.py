#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2/1 福岡空港 → 由布院 的實際班次（含高速巴士），以及 2/3 節分日回博多的接續確認。"""
import gzip
import io
import re
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept-Encoding": "gzip"}


def routes(frm, to, y, m, d, hh, m1=0, m2=0, bus=True):
    params = {"from": frm, "to": to, "y": y, "m": m, "d": d, "hh": hh,
              "m1": m1, "m2": m2, "type": "1", "ticket": "ic", "expkind": "1",
              "al": "1", "shin": "1", "ex": "1", "sr": "1", "s": "0",
              "hb": "1" if bus else "0", "lb": "1" if bus else "0"}
    url = "https://transit.yahoo.co.jp/search/result?" + urllib.parse.urlencode(params)
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    html = raw.decode("utf-8", "replace")
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    out = []
    for k in range(1, 4):
        j = txt.find(f"ルート {k} ")
        if j < 0:
            continue
        seg = txt[j:j + 900]
        h = re.search(r"(\d\d:\d\d) → (\d\d:\d\d) ([^ ]+) ([\d,]+) 円 乗換： (\d) 回", seg)
        if not h:
            continue
        p = -1
        for mark in ["早", "楽", "安"]:
            p = txt.find(f"ルート {k} {mark}")
            if p >= 0:
                break
        slab = txt[p:p + 1600] if p >= 0 else seg
        veh = re.findall(r"(ゆふいんの森\d*号|ゆふ\d+号|ソニック\d+号|[^ ]*高速バス[^ ]*|"
                         r"[^ ]*ゆふいん号|[^ ]*とよのくに[^ ]*|新幹線[ぁ-んァ-ヶ]+\d*号|"
                         r"地下鉄[^ ]*|[^ ]*空港線)", slab)
        u = []
        for v in veh:
            if v not in u:
                u.append(v)
        out.append((h.group(1), h.group(2), h.group(3), h.group(4), h.group(5), u[:4]))
    return out


print("=== 2/1(月) 福岡空港国際線 → 由布院 ===")
seen = set()
for hh in ["10", "11", "12", "13"]:
    for r in routes("福岡空港", "由布院", 2027, "02", "01", hh):
        if r[:2] in seen:
            continue
        seen.add(r[:2])
        print(f"  {r[0]} → {r[1]}  {r[2]}  ¥{r[3]}  換{r[4]}回  {' / '.join(r[5])}")
    time.sleep(1.2)

print("\n=== 2/3(水) 由布院 → 博多 12:01 那班的續行（櫛田神社 節分） ===")
for r in routes("博多", "櫛田神社", 2027, "02", "03", "14", m1=3, m2=0):
    print(f"  {r[0]} → {r[1]}  {r[2]}  ¥{r[3]}  {' / '.join(r[5])}")
