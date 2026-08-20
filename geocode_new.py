#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只替 data/v60_new.json 補座標，不動其他檔案。

geocode.py 會一次掃全部 data/*.json，中途逾時會把既有的 area 座標清成 missing，
所以新增地點改用這支獨立腳本。查法與 geocode.py 相同（Overpass → Nominatim，
都用 city bbox 驗證），HTTP 一律走 curl。
"""
import json
import subprocess
import sys
import time
import urllib.parse

UA = "fukuoka-trip-site/1.0 (personal itinerary project)"
TARGET = "data/v60_new.json"

CITY_BBOX = {
    "福岡":   (33.05, 130.00, 33.80, 130.70),
    "長崎":   (32.55, 129.30, 33.30, 130.30),
    "大分":   (33.00, 130.85, 33.60, 131.80),
    "北九州": (33.80, 130.60, 34.45, 131.20),
    "熊本":   (32.50, 130.40, 33.20, 131.30),
    "佐賀":   (33.10, 129.90, 33.40, 130.40),
    "鹿兒島": (31.00, 130.20, 32.00, 131.00),
}

OVERPASS = "https://overpass-api.de/api/interpreter"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


def curl(url, post_data=None, timeout=45):
    cmd = ["curl", "-sS", "-m", str(timeout), "-A", UA]
    if post_data is not None:
        cmd += ["--data-binary", post_data]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")


def in_bbox(lat, lng, b):
    return b[0] <= lat <= b[2] and b[1] <= lng <= b[3]


def overpass_lookup(name, bbox):
    s, w, n, e = bbox
    esc = name.replace("\\", "\\\\").replace('"', '\\"')
    q = f"""[out:json][timeout:40];
(
  node["name"="{esc}"]({s},{w},{n},{e});
  way["name"="{esc}"]({s},{w},{n},{e});
  relation["name"="{esc}"]({s},{w},{n},{e});
  node["name:ja"="{esc}"]({s},{w},{n},{e});
  way["name:ja"="{esc}"]({s},{w},{n},{e});
);
out center 3;"""
    raw = curl(OVERPASS, post_data="data=" + urllib.parse.quote(q))
    if not raw:
        return None
    try:
        els = json.loads(raw).get("elements", [])
    except ValueError:
        return None
    for el in els:
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lng = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None:
            continue
        if in_bbox(lat, lng, bbox):
            return {"lat": round(lat, 6), "lng": round(lng, 6),
                    "status": "overpass", "src": f"OSM {el['type']}/{el['id']}"}
    return None


def nominatim_lookup(name, bbox):
    s, w, n, e = bbox
    qs = urllib.parse.urlencode({
        "q": name, "format": "json", "limit": "3",
        "viewbox": f"{w},{n},{e},{s}", "bounded": "1",
        "accept-language": "ja",
    })
    raw = curl(f"{NOMINATIM}?{qs}", timeout=30)
    if not raw:
        return None
    try:
        res = json.loads(raw)
    except ValueError:
        return None
    for r in res:
        lat, lng = float(r["lat"]), float(r["lon"])
        if in_bbox(lat, lng, bbox):
            return {"lat": round(lat, 6), "lng": round(lng, 6),
                    "status": "nominatim", "src": "Nominatim " + r.get("display_name", "")[:80]}
    return None


def main():
    places = json.load(open(TARGET, encoding="utf-8"))
    for p in places:
        if p.get("lat") is not None:
            continue
        bbox = CITY_BBOX[p["city"]]
        q = p.get("q") or p.get("name_ja") or p["name"]
        hit = overpass_lookup(q, bbox)
        if not hit:
            time.sleep(1.2)
            hit = nominatim_lookup(q, bbox)
        if hit:
            p["lat"] = hit["lat"]
            p["lng"] = hit["lng"]
            p["coord_status"] = hit["status"]
            p["coord_source"] = hit["src"]
            print("OK  ", p["name"], hit["lat"], hit["lng"], hit["status"])
        else:
            print("MISS", p["name"], "(q=" + q + ")")
        sys.stdout.flush()
        time.sleep(1.2)
    json.dump(places, open(TARGET, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("written", TARGET)


if __name__ == "__main__":
    main()
