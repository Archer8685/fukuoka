#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由布院→博多 2/3 早上各班次逐一拆解，分清楚哪一班是列車、哪一班是巴士。"""
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


def fetch(frm, to, y, m, d, hh, m1=0, m2=0, extra=None):
    params = {
        "from": frm, "to": to, "y": y, "m": m, "d": d,
        "hh": hh, "m1": m1, "m2": m2, "type": "1", "ticket": "ic",
        "expkind": "1", "al": "1", "shin": "1", "ex": "1",
        "hb": "1", "lb": "1", "sr": "1", "s": "0",
    }
    if extra:
        params.update(extra)
    url = "https://transit.yahoo.co.jp/search/result?" + urllib.parse.urlencode(params)
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    html = raw.decode("utf-8", "replace")
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def detail(label, frm, to, y, m, d, hh, m1=0, m2=0, extra=None, n=3):
    body = fetch(frm, to, y, m, d, hh, m1, m2, extra)
    print("=" * 74)
    print(label, f"[{frm} → {to} {y}/{m}/{d} {hh}:{m1}{m2}~]")
    for k in range(1, n + 1):
        i = body.find(f"ルート {k} ")
        if i < 0:
            continue
        seg = body[i:i + 1400]
        head = re.search(r"(\d\d:\d\d) → (\d\d:\d\d) ([^ ]+) ([\d,]+) 円 乗換： (\d) 回", seg)
        j = body.find(f"ルート {k} 早")
        if j < 0:
            j = body.find(f"ルート {k} 楽")
        if j < 0:
            j = body.find(f"ルート {k} 安")
        slab = body[j:j + 1400] if j >= 0 else seg
        names = re.findall(r"(ゆふいんの森\d*号|ゆふ\d+号|ソニック\d*号|きらめき\d*号|"
                           r"高速バス[・\w−]*|[ぁ-んァ-ヶ一-龯]{0,6}号\(高速・連絡バス\))", slab)
        uniq = []
        for x in names:
            if x not in uniq:
                uniq.append(x)
        bus = "(高速・連絡バス)" in slab or "高速バス" in slab
        fare = re.search(r"乗車券([\d,]+)円 特別料金([\d,]+)円", slab)
        print(f"  ルート{k}: " + (head.group(0) if head else "?"))
        print(f"    交通: {'🚌 巴士' if bus else '🚃 鐵路'} | {' / '.join(uniq[:5]) or '-'}")
        if fare:
            print(f"    明細: 乗車券 ¥{fare.group(1)} ＋ 特別料金 ¥{fare.group(2)}")
    sys.stdout.flush()


if __name__ == "__main__":
    # 只走鐵路（關掉高速巴士 hb=0、lb=0）看真正的 ゆふいんの森 價格
    detail("由布院→博多 2/3 09:00~ 全modes", "由布院", "博多", 2027, "02", "03", "09")
    time.sleep(1.5)
    detail("由布院→博多 2/3 09:00~ 僅鐵路", "由布院", "博多", 2027, "02", "03", "09",
           extra={"hb": "0", "lb": "0"})
    time.sleep(1.5)
    detail("福岡空港国際線→由布院 2/1 10:30~", "福岡空港国際線", "由布院",
           2027, "02", "01", "10", m1=3, m2=0)
    time.sleep(1.5)
    detail("博多→小倉 2/5 08:00~ 不含新幹線", "博多", "小倉", 2027, "02", "05", "08",
           extra={"shin": "0"})
    time.sleep(1.5)
    detail("博多→由布院 (參考・反向) 2/3", "博多", "由布院", 2027, "02", "03", "09")
