#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版號 +1：一次改完散在 4 個地方的版號，避免 PWA 吃到舊快取。

為什麼需要這支：
改了 data.js／trip.js 但沒 bump 版號時，Service Worker 會繼續發舊的
`data.js?v=N`／`trip.js?v=N`（cache-first），瀏覽器上看到的還是舊行程——
2026/08/18 就實際發生過：行程改了但頁面完全沒變，查了半天才發現是快取。

版號散在 4 處，手動改很容易漏掉其中一處：
  1. sw.js          const APP_CACHE = 'fukuoka-app-vN'
  2. itinerary.html / map.html / prep.html 的 ?v=N（preload 與 script）
  3. 三個 HTML 底部 warm-up 腳本的 caches.open('fukuoka-app-vN')
  4. trip.js        SITE_VERSION（顯示在導覽列）

用法：
    python bump_version.py          # 全部 +1
    python bump_version.py --set 7  # 指定版號
    python bump_version.py --check  # 只檢查是否一致，不改（CI 用，不一致回傳 1）
"""
import io
import re
import sys

FILES = ("sw.js", "trip.js", "itinerary.html", "map.html", "prep.html", "verify.html")
PATTERNS = (
    r"fukuoka-app-v(\d+)",
    r"data\.js\?v=(\d+)",
    r"trip\.js\?v=(\d+)",
    r'SITE_VERSION = "v(\d+)"',
)


def scan():
    """回傳 {檔名: {版號: 出現次數}}"""
    found = {}
    for f in FILES:
        s = io.open(f, encoding="utf-8").read()
        vs = {}
        for pat in PATTERNS:
            for m in re.finditer(pat, s):
                vs[int(m.group(1))] = vs.get(int(m.group(1)), 0) + 1
        found[f] = vs
    return found


def main():
    found = scan()
    versions = sorted({v for vs in found.values() for v in vs})
    for f, vs in found.items():
        print(f"  {f:16s} {dict(sorted(vs.items()))}")

    if len(versions) != 1:
        print(f"\n⚠️ 版號不一致：{versions}")
        if "--check" in sys.argv:
            sys.exit(1)
    elif "--check" in sys.argv:
        print(f"\n✅ 版號一致：v{versions[0]}")
        return

    cur = max(versions) if versions else 1
    if "--set" in sys.argv:
        new = int(sys.argv[sys.argv.index("--set") + 1])
    else:
        new = cur + 1

    total = 0
    for f in FILES:
        s = io.open(f, encoding="utf-8").read()
        orig = s
        for pat in PATTERNS:
            s = re.sub(pat, lambda m: m.group(0).replace(m.group(1), str(new)), s)
        if s != orig:
            io.open(f, "w", encoding="utf-8", newline="").write(s)
            n = sum(len(re.findall(pat, s)) for pat in PATTERNS)
            total += n
            print(f"  {f:16s} -> v{new}（{n} 處）")
    print(f"\n✅ v{cur} → v{new}，共改 {total} 處")
    print("   記得同時確認 data.js 是最新的：python build_data.py")


if __name__ == "__main__":
    main()
