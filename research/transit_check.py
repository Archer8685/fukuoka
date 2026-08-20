#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yahoo 乘換案內實查（含特急／新幹線）。用法見 skill japan-itinerary-verification。"""
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


def fetch(frm, to, y, m, d, hh, m1, m2):
    qs = urllib.parse.urlencode({
        "from": frm, "to": to, "y": y, "m": m, "d": d,
        "hh": hh, "m1": m1, "m2": m2, "type": "1", "ticket": "ic",
        "expkind": "1", "al": "1", "shin": "1", "ex": "1",
        "hb": "1", "lb": "1", "sr": "1", "s": "0",
    })
    url = "https://transit.yahoo.co.jp/search/result?" + qs
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=40).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    html = raw.decode("utf-8", "replace")
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)


def report(label, frm, to, y, m, d, hh, m1=0, m2=0):
    body = fetch(frm, to, y, m, d, hh, m1, m2)
    i = body.find("ルート 1")
    print("=" * 70)
    print(label, f"({frm} → {to}, {y}/{m}/{d} {hh}:{m1}{m2}~)")
    if i < 0:
        print("  !! 找不到 ルート 1")
        return
    print("  摘要:", body[i:i + 260].strip())
    j = body.find("ルート 1 早")
    slab = body[j:j + 1200] if j >= 0 else body[i:i + 1200]
    trains = re.findall(r"(ゆふいんの森|ゆふ\d*号|ソニック|きらめき|みずほ|さくら|つばめ|"
                        r"ハウステンボス|みどり|かもめ|リレーかもめ|特急[^ ]{0,8}|"
                        r"新幹線[^ ]{0,8}|高速[^ ]{0,10}バス[^ ]{0,8})", slab)
    seen = []
    for t in trains:
        if t not in seen:
            seen.append(t)
    print("  列車:", " / ".join(seen[:8]) or "(無)")
    fare = re.search(r"乗車券([\d,]+)円\s*特別料金([\d,]+)円", slab)
    if fare:
        print(f"  票價明細: 乗車券 ¥{fare.group(1)} ＋ 特別料金 ¥{fare.group(2)}")


if __name__ == "__main__":
    jobs = [
        ("由布院→博多 (2/3 朝)", "由布院", "博多", 2027, "02", "03", "09"),
        ("博多→ハウステンボス (2/9 朝)", "博多", "ハウステンボス", 2027, "02", "09", "08"),
        ("ハウステンボス→博多 (2/9 夜)", "ハウステンボス", "博多", 2027, "02", "09", "20"),
        ("博多→熊本 (2/6 朝)", "博多", "熊本", 2027, "02", "06", "08"),
        ("博多→小倉 (2/5 朝)", "博多", "小倉", 2027, "02", "05", "08"),
        ("博多→下関 (2/4 朝)", "博多", "下関", 2027, "02", "04", "08"),
        ("博多→西戸崎 (2/8 朝)", "博多", "西戸崎", 2027, "02", "08", "09"),
        ("博多→太宰府 (2/7 朝)", "博多", "太宰府", 2027, "02", "07", "09"),
    ]
    for job in jobs:
        try:
            report(*job)
        except Exception as e:
            print("=" * 70)
            print(job[0], "ERROR", e)
        sys.stdout.flush()
        time.sleep(1.5)
