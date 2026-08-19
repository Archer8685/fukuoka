#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""餐廳座標：先用 Nominatim 查，查不到的用「區域中心點」墊底。

為什麼要墊底：
Tabelog 上的小店有一大半在 OSM／國土地理院都沒有節點，自動查一定查不到，
但 check_all.py 要求每個地點都有座標（沒座標的話地圖上直接消失，等於白加）。

所以查不到的就放該區域的中心點，並把 coord_status 設成 "area"，
地圖 popup 會顯示「這是區域概略位置」的警告。
真正的導航一律走 popup 裡的「🧭 在 Google Maps 開啟」（用日文店名搜尋）。

只處理 data/*.json 裡有 area_center 欄位的項目（＝這次新增的餐廳與清真店）。

用法： python area_fallback.py [--no-geocode]
"""
import glob
import json
import subprocess
import sys
import time
import urllib.parse

UA = "fukuoka-trip-site/1.0 (personal itinerary project)"

# 各區域的中心點（用來墊底，不是店家實際位置）
AREA_CENTER = {
    "博多":   (33.5897, 130.4207),
    "中洲":   (33.5931, 130.4055),
    "天神":   (33.5896, 130.3986),
    "太宰府": (33.5199, 130.5340),
    "糸島":   (33.5580, 130.1969),
    "門司港": (33.9451, 130.9628),
    "下關":   (33.9518, 130.9427),
    "長崎":   (32.7440, 129.8780),
    "湯布院": (33.2640, 131.3560),
    "日田":   (33.3211, 130.9410),
    "柳川":   (33.1630, 130.4060),
    "熊本":   (32.8030, 130.7080),
    "別府":   (33.2793, 131.5010),
    "佐世保": (33.1595, 129.7230),
}

# 每個區域允許的座標範圍，擋掉查到別的縣市的結果
AREA_BBOX = {
    "博多": (33.53, 130.36, 33.65, 130.48), "中洲": (33.53, 130.36, 33.65, 130.48),
    "天神": (33.53, 130.34, 33.63, 130.45), "太宰府": (33.46, 130.48, 33.58, 130.60),
    "糸島": (33.45, 130.05, 33.68, 130.30), "門司港": (33.88, 130.90, 34.00, 131.05),
    "下關": (33.90, 130.85, 34.05, 131.05), "長崎": (32.68, 129.80, 32.83, 129.95),
    "湯布院": (33.20, 131.28, 33.35, 131.45), "日田": (33.25, 130.85, 33.42, 131.05),
    "柳川": (33.08, 130.32, 33.25, 130.50), "熊本": (32.74, 130.62, 32.87, 130.78),
    "別府": (33.22, 131.42, 33.38, 131.58),
    "佐世保": (33.03, 129.62, 33.30, 129.85),
}


def nominatim(q, bbox):
    s, w, n, e = bbox
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": q, "format": "json", "limit": "3",
        "viewbox": f"{w},{n},{e},{s}", "bounded": "1", "accept-language": "ja"})
    r = subprocess.run(["curl", "-sS", "-m", "25", "-A", UA, url], capture_output=True)
    if r.returncode:
        return None
    try:
        res = json.loads(r.stdout.decode("utf-8", "replace"))
    except ValueError:
        return None
    for x in res:
        lat, lng = float(x["lat"]), float(x["lon"])
        if s <= lat <= n and w <= lng <= e:
            return round(lat, 6), round(lng, 6)
    return None


def main():
    do_geo = "--no-geocode" not in sys.argv
    stats = {"nominatim": 0, "area": 0, "skip": 0, "no_center": 0}
    for path in sorted(glob.glob("data/*.json")):
        with open(path, encoding="utf-8") as f:
            places = json.load(f)
        changed = False
        for p in places:
            ac = p.get("area_center")
            if not ac:
                continue
            if p.get("lat") and p.get("coord_status") in ("nominatim", "manual", "approx", "overpass"):
                stats["skip"] += 1
                continue
            if ac not in AREA_CENTER:
                print(f"  ! 未知的 area_center：{ac}（{p['name']}）")
                stats["no_center"] += 1
                continue
            hit = None
            if do_geo:
                for q in [x for x in (p.get("q"), p.get("name_ja")) if x]:
                    hit = nominatim(q, AREA_BBOX[ac])
                    if hit:
                        break
                    time.sleep(1.1)
                time.sleep(1.1)
            if hit:
                p["lat"], p["lng"], p["coord_status"] = hit[0], hit[1], "nominatim"
                stats["nominatim"] += 1
                print(f"  OK   {p['name'][:24]:24s} {hit[0]},{hit[1]}")
            else:
                lat, lng = AREA_CENTER[ac]
                p["lat"], p["lng"], p["coord_status"] = lat, lng, "area"
                stats["area"] += 1
                print(f"  AREA {p['name'][:24]:24s} -> {ac} 中心點")
            changed = True
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(places, f, ensure_ascii=False, indent=1)
                f.write("\n")
    print("\n統計：", stats)
    print("coord_status='area' 的項目在地圖 popup 會標示為區域概略位置。")


if __name__ == "__main__":
    main()
