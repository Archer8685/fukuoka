#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_places.py — 用 Google Places API (New) 實查 trip.js 每一站，
產出「行程寫的」vs「Google 現況」的差異報告。

檢查項目
  1. 地點是否存在 / 是否已歇業（businessStatus）
  2. 營業時間 —— 特別檢查「該站排定的時間」是否落在營業時間內
  3. 定休日 —— 該站的星期幾是否公休
  4. 座標距離 —— data.js 記的座標 vs Google 官方點位（>300m 標記）
  5. 評分與評論數（拿來判斷熱門度）

輸出： audit/verify_places_<date>.json  +  終端摘要

用法： python verify_places.py            # 全部
       python verify_places.py 5 7        # 只查 2/5 與 2/7
"""
import json
import glob
import math
import os
import re
import subprocess
import sys
import time
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
REFERER = "https://archer8685.github.io/fukuoka/"
WD_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
# trip.js 的 wd 欄位（中文）→ Python weekday()
WD_MAP = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6}

FIELDS = ",".join([
    "id", "displayName", "formattedAddress", "location", "rating",
    "userRatingCount", "businessStatus", "regularOpeningHours",
    "editorialSummary", "primaryTypeDisplayName", "websiteUri",
])


CACHE = os.path.join(BASE, "audit", "places_cache.json")
CACHE_TTL_DAYS = 30   # 超過這個天數就重查；出發前記得用 --refresh 全部重驗


def load_cache():
    """以查詢字串（q）為 key 的地點快取。

    同一家店可能出現在多天，也可能在多次執行間重複查——這份快取讓
    Places API 對同一個 q 只打一次。行程改動只影響「哪些站要出現在報告裡」，
    不影響已經查過的店家資料，所以快取跨執行有效。"""
    try:
        d = json.load(open(CACHE, encoding="utf-8"))
        return d.get("places", {})
    except Exception:
        return {}


def save_cache(places):
    os.makedirs(os.path.join(BASE, "audit"), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8", newline=chr(10)) as f:
        json.dump({"updated": str(date.today()), "places": places},
                  f, ensure_ascii=False, indent=1, sort_keys=True)


def cache_age(entry):
    try:
        y, m, d = (int(x) for x in entry["fetched"].split("-"))
        return (date.today() - date(y, m, d)).days
    except Exception:
        return 10 ** 6


def get_place(q, lat, lng, cache, force):
    """回傳 (google_place_dict 或 None, fetched 日期, 是否命中快取)。"""
    hit = cache.get(q)
    if hit and not force and cache_age(hit) <= CACHE_TTL_DAYS:
        return hit.get("data"), hit.get("fetched"), True
    d = search(q, lat, lng)
    time.sleep(0.12)
    cand = (d.get("places") or [None])[0]
    cache[q] = {"fetched": str(date.today()), "data": cand}
    return cand, str(date.today()), False


def api_key():
    src = open(os.path.join(BASE, "config.js"), encoding="utf-8").read()
    m = re.search(r"AIza[A-Za-z0-9_-]+", src)
    if not m:
        sys.exit("config.js 找不到 Google API key")
    return m.group(0)


KEY = api_key()


def curl(args, payload=None):
    r = subprocess.run(args, input=payload.encode("utf-8") if payload else None,
                       capture_output=True)
    try:
        return json.loads(r.stdout.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {"_raw": r.stdout.decode("utf-8", "replace")[:400]}


def search(q, lat, lng, radius=20000.0):
    """searchText —— 必帶 regionCode JP + locationBias，否則會回台灣的店家。"""
    body = {"textQuery": q, "languageCode": "ja", "regionCode": "JP", "maxResultCount": 3}
    if lat and lng:
        body["locationBias"] = {"circle": {
            "center": {"latitude": lat, "longitude": lng},
            "radius": min(radius, 50000.0)}}   # radius 上限 50000
    return curl([
        "curl", "-s", "-X", "POST",
        "https://places.googleapis.com/v1/places:searchText",
        "-H", "Content-Type: application/json",
        "-H", "X-Goog-Api-Key: " + KEY,
        "-H", "Referer: " + REFERER,
        "-H", "X-Goog-FieldMask: " + ",".join("places." + f for f in FIELDS.split(",")),
        "--data-binary", "@-",
    ], json.dumps(body, ensure_ascii=False))


def haversine(a, b, c, d):
    R = 6371000.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def load_trip():
    """用 node 把 trip.js 的 TRIP 倒成 JSON（trip.js 不是合法 JSON，要靠 JS 執行）。"""
    js = ("const fs=require('fs');const src=fs.readFileSync('trip.js','utf8');"
          "const m=new Function(src+'; return {TRIP};')();"
          "process.stdout.write(JSON.stringify(m.TRIP));")
    # Windows Git Bash 的 `node` 包裝層偶爾會誤報 `stdin is not a tty`；
    # 明確呼叫 node.exe 可避開包裝層，其他平台仍使用 node。
    node = "node.exe" if os.name == "nt" else "node"
    r = subprocess.run([node, "-e", js], cwd=BASE, capture_output=True)
    if r.returncode:
        sys.exit("讀 trip.js 失敗：" + r.stderr.decode("utf-8", "replace"))
    return json.loads(r.stdout.decode("utf-8"))


def load_places():
    """以 data/*.json 為準（build_data.py 產生的 data.js 會丟掉 q 欄位，
    而 q 正是拿來對同名店消歧義的關鍵）。"""
    out = {}
    src = open(os.path.join(BASE, "data.js"), encoding="utf-8").read()
    for p in json.loads(src[src.index("["):src.rindex("]") + 1]):
        out[p["name"]] = p
    for fp in glob.glob(os.path.join(BASE, "data", "*.json")):
        for p in json.load(open(fp, encoding="utf-8")):
            if p.get("q"):
                out.setdefault(p["name"], {}).update({"q": p["q"]})
    return out


def parse_hhmm(s):
    m = re.match(r"^(\d{1,2}):(\d{2})$", s.strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def open_intervals(oh, weekday):
    """從 regularOpeningHours.periods 取出該 weekday 的營業區間（分鐘）。
    Google 的 day: 0=週日 … 6=週六；我們的 weekday: 0=週一 … 6=週日。"""
    periods = (oh or {}).get("periods", [])
    # 24/7 營業：Google 只回一個 {open:{day:0,hour:0,minute:0}}、沒有 close
    if len(periods) == 1 and "close" not in periods[0]:
        o = periods[0].get("open", {})
        if o.get("hour", 0) == 0 and o.get("minute", 0) == 0:
            return [(0, 24 * 60)]
    g_day = (weekday + 1) % 7
    out = []
    for p in periods:
        o, c = p.get("open"), p.get("close")
        if not o:
            continue
        start = o["hour"] * 60 + o.get("minute", 0)
        if o.get("day") == g_day:
            if c is None:
                out.append((start, 24 * 60))
            else:
                end = c["hour"] * 60 + c.get("minute", 0)
                if c.get("day") != g_day:      # 跨日打烊
                    end += 24 * 60
                out.append((start, end))
        elif c is not None and c.get("day") == g_day and o.get("day") == (g_day - 1) % 7:
            # 前一天開、跨到今天凌晨才打烊 → 今天凌晨這段也算營業
            out.append((0, c["hour"] * 60 + c.get("minute", 0)))
    return out


def main():
    args = sys.argv[1:]
    only = {int(x) for x in args if x.isdigit()}
    force = any(x in ("--refresh", "-f") for x in args)
    trip, places = load_trip(), load_places()
    cache = load_cache()
    n_api = n_hit = 0
    if force:
        print("（--refresh：忽略快取，全部重打 API）")
    results, issues = [], []

    for day in trip:
        if only and day["d"] not in only:
            continue
        weekday = WD_MAP.get(day.get("wd", ""))
        for st in day.get("stops", []):
            if st.get("kind") in ("hotel", "move"):
                continue
            name = st["name"]
            meta = places.get(name, {})
            # q 欄位優先（用來對同名店消歧義，例：ミディアムレア 有博多站南／西戶崎兩家）
            q = meta.get("q") or meta.get("name_ja") or name
            lat, lng = meta.get("lat"), meta.get("lng")
            gp, fetched, hit = get_place(q, lat, lng, cache, force)
            if hit:
                n_hit += 1
            else:
                n_api += 1
            cand = [gp] if gp else []
            rec = {"day": day["d"], "date": day["date"], "wd": day.get("wd"),
                   "time": st.get("t"), "name": name, "query": q,
                   "in_data_js": bool(meta), "fetched": fetched}
            if not cand:
                rec["status"] = "NOT_FOUND"
                issues.append((day["date"], st.get("t"), name, "❌ Google 查無此地點", ""))
                results.append(rec)
                continue

            g = cand[0]
            rec.update({
                "google_name": g.get("displayName", {}).get("text"),
                "address": g.get("formattedAddress"),
                "rating": g.get("rating"),
                "reviews": g.get("userRatingCount"),
                "business_status": g.get("businessStatus"),
                "type": (g.get("primaryTypeDisplayName") or {}).get("text"),
                "summary": (g.get("editorialSummary") or {}).get("text"),
                "hours": (g.get("regularOpeningHours") or {}).get("weekdayDescriptions"),
                "website": g.get("websiteUri"),
            })

            # 1) 歇業
            bs = g.get("businessStatus")
            if bs and bs != "OPERATIONAL":
                issues.append((day["date"], st.get("t"), name,
                               "❌ 狀態 " + bs, g.get("formattedAddress", "")))

            # 2) 座標距離
            loc = g.get("location") or {}
            if lat and lng and loc:
                dist = haversine(lat, lng, loc["latitude"], loc["longitude"])
                rec["dist_m"] = round(dist)
                if dist > 300:
                    issues.append((day["date"], st.get("t"), name,
                                   f"⚠️ 座標偏差 {dist:.0f} m", g.get("formattedAddress", "")))

            # 3) 營業時間 vs 排定時間
            oh = g.get("regularOpeningHours")
            tmin = parse_hhmm(st.get("t", ""))
            if oh and weekday is not None and tmin is not None:
                iv = open_intervals(oh, weekday)
                rec["intervals"] = iv
                if not iv:
                    issues.append((day["date"], st.get("t"), name,
                                   f"❌ {day['wd']} 公休", ""))
                elif not any(s <= tmin < e for s, e in iv):
                    txt = "／".join(f"{s // 60:02d}:{s % 60:02d}-{e // 60:02d}:{e % 60:02d}"
                                   for s, e in iv)
                    issues.append((day["date"], st.get("t"), name,
                                   f"❌ 抵達時未營業（{day['wd']} {txt}）", ""))
                else:
                    # 閉館前不足 45 分
                    end = max(e for s, e in iv if s <= tmin < e)
                    if end - tmin < 45:
                        issues.append((day["date"], st.get("t"), name,
                                       f"⚠️ 距打烊僅 {end - tmin} 分", ""))
            results.append(rec)
            print(f"  {day['date']} {st.get('t')} {name[:22]:24s} "
                  f"{rec.get('rating','-')}★ {rec.get('reviews',0) or 0:>6,}")

    save_cache(cache)
    os.makedirs(os.path.join(BASE, "audit"), exist_ok=True)
    out = os.path.join(BASE, "audit", f"verify_places_{date.today()}.json")

    # 部分執行（verify_places.py 5 7）不可以把當天的完整快取洗掉：
    # check_all.py 的定休日檢查靠這份快取，被截短就會漏檢。
    # 因此同日重跑時以站點為單位合併，只覆寫這次真的查過的站。
    partial = bool(only)
    # 部分執行時要接續「最近一份」報告，不只是今天那份——否則換一天再跑
    # verify_places.py 5 7 會產出只含兩天的報告，check_all 會把其餘站點
    # 全判成未實查（錯誤）。
    seed = out if os.path.exists(out) else None
    if partial and not seed:
        old = sorted(glob.glob(os.path.join(BASE, "audit", "verify_places_*.json")))
        old = [f for f in old if os.path.basename(f) != os.path.basename(out)]
        seed = old[-1] if old else None
    if partial and seed:
        try:
            prev = json.load(open(seed, encoding="utf-8"))
            fresh = {(r.get("date"), r.get("name")) for r in results}
            merged = [r for r in prev.get("results", [])
                      if (r.get("date"), r.get("name")) not in fresh]
            kept_days = {r.get("date") for r in merged}
            results = merged + results
            results.sort(key=lambda r: (r.get("day", 0), r.get("time") or ""))
            issues = [i for i in prev.get("issues", []) if i[0] in kept_days] + issues
            print(chr(10) + f"（部分執行：已接續 {os.path.basename(seed)} 的 {len(merged)} 站）")
        except Exception as e:
            print(f"\n⚠️  既有快取合併失敗，將只寫入本次結果：{e}")

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"generated": str(date.today()), "results": results, "issues": issues},
                  f, ensure_ascii=False, indent=1)

    errors = [i for i in issues if i[3].startswith("❌")]
    warnings = [i for i in issues if i[3].startswith("⚠️")]
    print("\n" + "=" * 72)
    print(f"共查 {len(results)} 站：錯誤 {len(errors)}、警告 {len(warnings)}")
    print(f"API 呼叫 {n_api} 次、快取命中 {n_hit} 次"
          f"（快取 {CACHE_TTL_DAYS} 天內有效；--refresh 可強制重查）")
    print("=" * 72)
    for dt, t, n, msg, extra in issues:
        print(f"{dt} {t or '--:--':6s} {n[:26]:28s} {msg}  {extra[:40]}")
    print(f"\n報告：{out}")
    # 真錯誤（查無地點、歇業、公休、抵達時未營業）必須讓 CI／呼叫端失敗；
    # 風險警告仍完整列出，但不等同驗證失敗。
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
