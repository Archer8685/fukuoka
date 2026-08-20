#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只替指定名稱的地點補座標（geocode_new.py 的通用版）。

用法：python geocode_one.py <data/檔名.json> <地點名稱>
理由：geocode.py 會掃全部 data/*.json，中途逾時會把既有座標清成 missing。
"""
import json
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "fukuoka-trip-geocoder/1.0 (personal itinerary project)"}
JP = (30.9, 33.9, 128.5, 132.1)  # 九州＋下關 lat_min, lat_max, lon_min, lon_max


def overpass(q):
    ql = ('[out:json][timeout:25];('
          f'node["name"~"{q}"]({JP[0]},{JP[2]},{JP[1]},{JP[3]});'
          f'way["name"~"{q}"]({JP[0]},{JP[2]},{JP[1]},{JP[3]});'
          ');out center 1;')
    req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                data=urllib.parse.urlencode({"data": ql}).encode(),
                                headers=UA)
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=40).read())
    except Exception as e:
        print("  overpass err", e)
        return None
    for el in d.get("elements", []):
        c = el.get("center") or el
        if c.get("lat"):
            return float(c["lat"]), float(c["lon"]), "overpass"
    return None


def nominatim(q):
    url = ("https://nominatim.openstreetmap.org/search?" +
           urllib.parse.urlencode({"q": q, "format": "json", "limit": 3,
                                   "viewbox": f"{JP[2]},{JP[1]},{JP[3]},{JP[0]}",
                                   "bounded": 1}))
    try:
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=40).read())
    except Exception as e:
        print("  nominatim err", e)
        return None
    for r in d:
        lat, lon = float(r["lat"]), float(r["lon"])
        if JP[0] <= lat <= JP[1] and JP[2] <= lon <= JP[3]:
            return lat, lon, "nominatim"
    return None


def main():
    path, target = sys.argv[1], sys.argv[2]
    data = json.load(open(path, encoding="utf-8"))
    hit = False
    for p in data:
        if p["name"] != target:
            continue
        hit = True
        q = p.get("q") or p.get("name_ja") or p["name"]
        r = overpass(q) or (time.sleep(1.2) or nominatim(q))
        if r:
            p["lat"], p["lng"], p["coord_status"] = r[0], r[1], r[2]
            print(f"OK   {p['name']} {r[0]:.6f} {r[1]:.6f} {r[2]}")
        else:
            print(f"MISS {p['name']} (q={q})")
    if not hit:
        sys.exit(f"找不到地點：{target}")
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("written", path)


if __name__ == "__main__":
    main()
