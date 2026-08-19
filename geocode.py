#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""座標稽核：補齊 data/*.json 的 lat/lng。

日本境內座標為 WGS-84，與 Leaflet／OSM／國土地理院圖磚一致，
不需要像中國那樣做 GCJ-02 偏移轉換。

三段查詢，每段都用「該城市的 bbox」限制範圍：
  1. Overpass  — OSM POI 名稱完全比對（最精確）
  2. Nominatim — OSM 全文檢索，bounded=1
  3. GSI       — 國土地理院地名／地址檢索（最後手段，只到地名級）
落在 bbox 外的結果一律丟棄並標記 missing。
日本有大量同名地點（例如福岡市也有「別府駅」、茨城縣也有「竹瓦」），
不做 bbox 驗證會配到完全另一個縣的地方。

HTTP 一律走 curl：本機 Python 的 CA bundle 已過期，urllib 對
overpass-api.de 會 CERTIFICATE_VERIFY_FAILED。

用法：
    python geocode.py            # 只補沒有座標的（增量）
    python geocode.py --all      # 全部重新查（覆蓋既有座標）
    python geocode.py --only 櫛田 # 只查名稱含關鍵字的項目
"""
import json
import glob
import os
import subprocess
import sys
import time
import urllib.parse

UA = "fukuoka-trip-site/1.0 (personal itinerary project)"

# 每個 city 的合理範圍：(south, west, north, east)
# 刻意收得比行政區界緊，寧可漏抓也不要配到同名的外縣市地點。
CITY_BBOX = {
    "福岡":   (33.05, 130.00, 33.80, 130.70),
    "長崎":   (32.55, 129.30, 33.30, 130.30),
    "大分":   (33.00, 130.85, 33.60, 131.80),   # 西邊要涵蓋日田（130.94），原本 131.10 會把日田配到大分市
    "北九州": (33.80, 130.60, 34.45, 131.20),
    "熊本":   (32.50, 130.40, 33.20, 131.30),
    "佐賀":   (33.10, 129.90, 33.40, 130.40),
    "鹿兒島": (31.00, 130.20, 32.00, 131.00),
    "其他":   (34.00, 132.00, 34.60, 132.80),
}

OVERPASS = "https://overpass-api.de/api/interpreter"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
GSI = "https://msearch.gsi.go.jp/address-search/AddressSearch"


def curl(url, post_data=None, timeout=60):
    cmd = ["curl", "-sS", "-m", str(timeout), "-A", UA]
    if post_data is not None:
        cmd += ["--data-binary", post_data]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")


def in_bbox(lat, lng, bbox):
    s, w, n, e = bbox
    return s <= lat <= n and w <= lng <= e


def overpass_lookup(name, bbox):
    s, w, n, e = bbox
    esc = name.replace("\\", "\\\\").replace('"', '\\"')
    q = f"""[out:json][timeout:50];
(
  node["name"="{esc}"]({s},{w},{n},{e});
  way["name"="{esc}"]({s},{w},{n},{e});
  relation["name"="{esc}"]({s},{w},{n},{e});
  node["name:ja"="{esc}"]({s},{w},{n},{e});
  way["name:ja"="{esc}"]({s},{w},{n},{e});
  node["alt_name"="{esc}"]({s},{w},{n},{e});
  way["alt_name"="{esc}"]({s},{w},{n},{e});
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
                    "detail": f"OSM {el['type']}/{el['id']}"}
    return None


def nominatim_lookup(name, bbox):
    s, w, n, e = bbox
    qs = urllib.parse.urlencode({
        "q": name, "format": "json", "limit": "3",
        "viewbox": f"{w},{n},{e},{s}", "bounded": "1",
        "accept-language": "ja",
    })
    raw = curl(f"{NOMINATIM}?{qs}", timeout=40)
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
                    "detail": "Nominatim " + r.get("display_name", "")[:60]}
    return None


def gsi_lookup(name, bbox):
    raw = curl(f"{GSI}?q={urllib.parse.quote(name)}", timeout=30)
    if not raw:
        return None
    try:
        feats = json.loads(raw)
    except ValueError:
        return None
    for f in feats:
        lng, lat = f["geometry"]["coordinates"][:2]
        if in_bbox(lat, lng, bbox):
            return {"lat": round(lat, 6), "lng": round(lng, 6),
                    "detail": "國土地理院 " + f.get("properties", {}).get("title", "")}
    return None


LOCK = os.path.join("audit", ".geocode.lock")


def acquire_lock():
    """避免兩個 geocode.py 同時跑：兩個 process 各持一份 data/*.json 快照互相覆寫，
    會讓已刪除的地點復活、已編輯的欄位被還原（2026/08/18 實際踩過）。"""
    os.makedirs("audit", exist_ok=True)
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        sys.exit(f"已有另一個 geocode.py 在跑（鎖檔 {LOCK}）；確認沒有其他 python geocode.py 在執行後，刪除該檔再重跑。")
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)


def release_lock():
    try:
        os.remove(LOCK)
    except OSError:
        pass


def main():
    redo_all = "--all" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    audit, stats = [], {"overpass": 0, "nominatim": 0, "gsi": 0, "missing": 0, "skip": 0}

    for path in sorted(glob.glob(os.path.join("data", "*.json"))):
        with open(path, encoding="utf-8") as f:
            places = json.load(f)
        changed = False
        for p in places:
            if only and only not in p["name"]:
                continue
            if not redo_all and p.get("lat") and p.get("coord_status") in ("overpass", "nominatim", "manual", "approx", "google"):
                stats["skip"] += 1
                continue
            bbox = CITY_BBOX.get(p.get("city"), (30.5, 128.5, 35.2, 133.0))
            queries = [q for q in (p.get("q"), p.get("name_ja")) if q]
            hit, src = None, "missing"
            for fn, tag in ((overpass_lookup, "overpass"),
                            (nominatim_lookup, "nominatim"),
                            (gsi_lookup, "gsi")):
                for q in queries:
                    hit = fn(q, bbox)
                    if hit:
                        src = tag
                        break
                    time.sleep(1.1)
                if hit:
                    break
            if hit:
                p["lat"], p["lng"] = hit["lat"], hit["lng"]
                p["coord_status"] = src
                p["coord_source"] = hit["detail"]
                print(f"  {p['name']}  ->  {src}: {hit['lat']}, {hit['lng']}  ({hit['detail']})")
            else:
                p.pop("lat", None)
                p.pop("lng", None)
                p["coord_status"] = "missing"
                p["coord_source"] = ""
                print(f"  {p['name']}  ->  MISSING（需手動補座標）")
            stats[src] += 1
            audit.append({"name": p["name"], "city": p.get("city"), "queries": queries,
                          "status": src, "lat": p.get("lat"), "lng": p.get("lng"),
                          "source": p.get("coord_source")})
            changed = True
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(places, f, ensure_ascii=False, indent=1)
                f.write("\n")
            print(f"  == 已更新 {path}")

    os.makedirs("audit", exist_ok=True)
    out = os.path.join("audit", "geocode_latest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print(f"\n稽核紀錄：{out}")
    print("統計：", stats)
    if stats["missing"]:
        print("⚠️ missing 項目需手動補座標（在 data/*.json 直接填 lat/lng "
              "並把 coord_status 設為 manual，重跑不會覆蓋）。")


if __name__ == "__main__":
    acquire_lock()
    try:
        main()
    finally:
        release_lock()
