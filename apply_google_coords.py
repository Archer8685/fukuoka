#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 verify.html（Google Places）稽核出來的座標套用到 data/*.json。

來源：2026-08-19 用 verify.html 對全部 286 個地點跑 Google Places Text Search，
比對我們的座標與 Google 回傳位置的距離，取出差距 >= 100m 的 167 筆。

⚠️ 不是全部照抄。SKIP 裡的項目<b>刻意不套用</b>，理由見該清單的註解——
Google Places 是「用名字找店」，遇到下面兩種情況會給出正確但不是我們要的答案：
  1. 概念性地點（「離飯店最近的那家便利商店」）——Google 只會回傳某一家同名分店
  2. 同名的另一家店／另一座山的中心點

套用後 coord_status 設為 "google"，geocode.py 與 area_fallback.py 都不會再覆蓋。

用法： python apply_google_coords.py && python build_data.py
"""
import glob
import json
import os

DATA = os.path.join("audit", "google_verify_2026-08-19.json")

# 刻意不套用，以及為什麼
SKIP = {
    "阿蘇山火口": "Google 回傳的是「阿蘇山」整座山的中心點，不是中岳火口；套用反而更不準",
    "トルコレストラン・エルトゥールル": "Google 指到小倉（北九州），但我們的 city/area 標的是福岡市中央區——先確認到底是哪一家再改",
    "西友 長崎": "Google 配到「サニー道の尾店」，是完全另一家店",
    "地鶏家（別府）": "Google 配到「地鶏屋」，店名不同，無法確認是同一家",
    "ローソン（長崎駅Ⅲ 最近）": "概念性地點（最近的一家）；Google 回傳長崎昭和町店（4km 外）。⚠️ 且住宿已改 Ⅰ 館，這筆本身要重做",
    "ローソン（東急ステイ博多 樓下）": "概念性地點（樓下那家）；Google 回傳另一家博多店，套用就失去意義",
    "ファミリーマート（博多・24 小時）": "同上，概念性地點",
    "セブン-イレブン（博多駅南）": "同上，概念性地點",
}


def main():
    with open(DATA, encoding="utf-8") as f:
        fixes = {r[0]: (r[1], r[2], r[3], r[4]) for r in json.load(f)}

    applied, skipped, notfound = 0, [], []
    seen = set()
    for path in sorted(glob.glob(os.path.join("data", "*.json"))):
        with open(path, encoding="utf-8") as f:
            places = json.load(f)
        changed = False
        for p in places:
            fx = fixes.get(p["name"])
            if not fx:
                continue
            seen.add(p["name"])
            if p["name"] in SKIP:
                skipped.append((p["name"], fx[2], SKIP[p["name"]]))
                continue
            lat, lng, dist, oldst = fx
            print(f"  {dist:>6}m  {p['name'][:28]:28s} [{oldst}] -> google ({lat}, {lng})")
            p["lat"], p["lng"] = lat, lng
            p["coord_status"] = "google"
            p["coord_source"] = f"Google Places 稽核 2026-08-19（原 {oldst}，差 {dist}m）"
            applied += 1
            changed = True
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(places, f, ensure_ascii=False, indent=1)
                f.write("\n")

    notfound = sorted(set(fixes) - seen)
    print(f"\n✅ 已套用 {applied} 筆")
    if skipped:
        print(f"\n⏭  刻意跳過 {len(skipped)} 筆：")
        for n, d, why in sorted(skipped, key=lambda x: -x[1]):
            print(f"   {d:>6}m  {n}\n            → {why}")
    if notfound:
        print(f"\n⚠️ 稽核表裡有但 data 找不到的名稱（可能已改名）：{notfound}")


if __name__ == "__main__":
    main()
