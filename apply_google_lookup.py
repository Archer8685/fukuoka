#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 lookup.html（Google Places）查到的座標／地址／營業時間套進 data/*.json。

來源：audit/google_lookup_2026-08-19.json
     — 2026-08-19 對 data/street_style.json 的 65 個新地點（PTT Street_Style 板清單）
       跑 Google Places Text Search，一筆一個查詢字串（各筆的 q 欄位）。

這支和 apply_google_coords.py 的差別：
  apply_google_coords.py — 已經有座標，拿 Google 比距離後覆寫偏掉的
  這一支                 — 本來沒有座標，直接用 Google 的官方點位建立，
                           並且順手把 Google 的地址、營業時間、歇業狀態寫進去

⚠️ 不是全部照抄，SPECIAL 裡的項目是人工判斷後覆寫的，理由寫在該筆註解。

用法： python apply_google_lookup.py && python build_data.py
"""
import glob
import json
import os
import re

SRC = os.path.join("audit", "google_lookup_2026-08-19.json")

# 行程在福岡的日子：2/1(一) 2/2(二) 2/3(三) 2/4(四) 2/10(三) 2/11(四) 2/12(五)
# ——完全沒有週六、週日。所以「週末才開的店」這趟根本碰不到，要在 notes 講清楚。
TRIP_WEEKDAYS = [0, 1, 2, 3, 4]          # 週一～週五
DAY = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]

# 日文地址 → 本專案的 area 標籤（繁體、與既有資料一致）
WARD = {"中央区": "中央區", "博多区": "博多區", "西区": "西區",
        "東区": "東區", "南区": "南區", "城南区": "城南區", "早良区": "早良區"}
TOWN = {"薬院": "藥院", "渡辺通": "渡邊通", "桜井": "櫻井", "博多駅前": "博多站前",
        "博多駅中央街": "博多站", "九大新町": "九大新町", "店屋町": "店屋町",
        "今泉": "今泉", "警固": "警固", "大名": "大名", "天神": "天神",
        "赤坂": "赤坂", "清川": "清川", "白金": "白金", "住吉": "住吉",
        "小田": "小田", "周船寺": "周船寺"}

# 人工覆寫：Google 的第一筆不是我們要的，或需要補說明
SPECIAL = {
    # Google 第一筆給「コムデギャルソン」＝岩田屋本店地址的專櫃；
    # 板友講的是獨立店面，但獨立店（博多駅前1-28-8）Google 標示 CLOSED_PERMANENTLY。
    # 改用目前仍營業的獨立店「コムデギャルソン福岡店」（天神1-12-20 日之出天神ビル）。
    "Comme des Garçons 福岡": {
        "lat": 33.592192, "lng": 130.399528,
        "address": "福岡県福岡市中央区天神1-12-20 日之出天神ビルディング",
        "area": "中央區・天神",
        "notes": "⚠️ 板友文中「鄰近 NEPENTHES」的博多駅前獨立店，Google 已標示永久歇業；"
                 "這裡指的是目前營業中的天神店（天神1-12-20）。岩田屋本店 1F 另有 PLAY 專櫃。",
    },
    # Google 上沒有 1834 的獨立點位，回傳的是 LIGHT YEARS 本店。
    # 座標就先放 LIGHT YEARS（反正要先去那裡預約），notes 講明。
    "1834 FUKUOKA": {
        "notes": "⚠️ 需事前向 LIGHT YEARS 預約才能入場。Google 上查不到 1834 的獨立點位，"
                 "這個圖釘是 LIGHT YEARS 本店的位置——請以預約時對方給的地址為準。",
    },
    # 鞦韆本身不是 POI，Google 配到沙灘上的「釣船茶屋ざうお BBQ ガーデン」，
    # 位置就是鞦韆所在的那片海灘，採用；但行政區是福岡市西區小田，不是糸島市。
    "ヤシの木ブランコ": {
        "notes": "座標是沙灘上的「ざうお BBQ ガーデン」——鞦韆就在這片海灘上。"
                 "行政區屬福岡市西區小田（糸島海線的起點），不是糸島市。"
                 "假日排隊拍照；冬天海風很大，注意保暖。",
    },
    # 板友說「主要五六日營業」，但 Google 上寫每天 12:00–18:00——兩邊對不上，講明讓人自己確認。
    "ON AIR KEGO": {
        "notes": "⚠️ 板友說「主要五、六、日營業」，但 Google 上是每天 12:00–18:00——兩邊對不上。"
                 "本行程在福岡完全沒有週末，出發前務必查官方 Instagram 當週公告。",
    },
    # 週一、六、日才開，而本行程在福岡沒有週末 → 實際上只有 2/1（週一）碰得到。
    "Loopwheeler 福岡": {
        "notes": "⚠️ 只有週一、週六、週日營業，而本行程在福岡沒有週末——"
                 "整趟只有 2/1（週一）這天碰得到，而且 2/1 是抵達日（FUK 10:00 落地），週一只開到 17:00。"
                 "後方就是 LIVING STEREO，兩家一起排。",
    },
    # Google 現在的店名是「atmos AMU PLAZA Hakata」，Sports Lab 已整併進 atmos。
    "Sports Lab by atmos 博多": {
        "notes": "Google 上現在的店名是「atmos アミュプラザ博多店」（5F），"
                 "Sports Lab 已整併進 atmos——找店請用 atmos。",
    },
}


def clean_addr(a):
    """去掉郵遞區號與「日本、」前綴，全角數字轉半角，丁目號改成 - 好讀。"""
    if not a:
        return ""
    a = re.sub(r"^日本、", "", a)
    a = re.sub(r"〒\d{3}-\d{4}\s*", "", a)
    a = a.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    a = a.replace("丁目", "-").replace("−", "-").replace("番", "-")
    a = re.sub(r"-+", "-", a).replace(" -", " ").strip()
    return a


def area_from_addr(addr, fallback):
    """從 Google 地址推 area 標籤。糸島市 / 福岡市各區分開處理。"""
    m = re.search(r"糸島市([^\d\s]+)", addr)
    if m:
        town = m.group(1)
        town = re.sub(r"(志摩|前原)(.*)", r"\1\2", town)
        for ja, zh in (("桜井", "櫻井"),):
            town = town.replace(ja, zh)
        return "糸島市・" + town if town else "糸島市"
    m = re.search(r"福岡市(\w+?区)([^\d\s]+)", addr)
    if m:
        ward = WARD.get(m.group(1), m.group(1))
        town = m.group(2)
        for ja, zh in TOWN.items():
            if town.startswith(ja):
                town = zh
                break
        return "%s・%s" % (ward, town)
    return fallback


def fmt_hours(weekday_desc):
    """['月曜日: 13時00分～18時00分', ...] → '週一–週四 13:00–18:00｜週五 …｜週三休'"""
    if not weekday_desc:
        return "", []
    vals, closed = [], []
    for i, d in enumerate(weekday_desc):
        t = d.split(": ", 1)[1] if ": " in d else d
        if "定休" in t or "休業" in t:
            vals.append(None)
            closed.append(DAY[i])
        elif "24" in t and "時間" in t:
            vals.append("24 小時")
        else:
            t = t.replace("時", ":").replace("分", "").replace("～", "–")
            t = re.sub(r":(\d\d)(?=[–,]|$)", r":\1", t)
            vals.append(t)
    # 合併連續同時段的日子
    parts, i = [], 0
    while i < 7:
        if vals[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < 7 and vals[j + 1] == vals[i]:
            j += 1
        span = DAY[i] if i == j else "%s–%s" % (DAY[i], DAY[j])
        parts.append("%s %s" % (span, vals[i]))
        i = j + 1
    if closed:
        parts.append("、".join(closed) + "休")
    return "｜".join(parts), closed


# 本支自己產生的警語前綴：重跑時要先剝掉，否則會一層一層疊上去
GENERATED = ("⚠️ Google 標示", "🗓 定休：", "⚠️ 週一～週五全休")


def base_note(note):
    """把上一次執行產生的警語剝掉，只留人工寫的那段，讓這支可以重複執行。"""
    keep = [s for s in note.split("　") if s and not s.startswith(GENERATED)]
    return "　".join(keep)


def trip_warning(closed, status):
    """行程只會遇到週一～週五，把「這趟碰不到」講明。"""
    out = []
    if status == "CLOSED_PERMANENTLY":
        out.append("⚠️ Google 標示「永久歇業」——出發前務必再確認，可能已經收了。")
    elif status == "CLOSED_TEMPORARILY":
        out.append("⚠️ Google 標示「暫停營業」——出發前務必再確認。")
    if closed:
        hit = [d for d in closed if DAY.index(d) in TRIP_WEEKDAYS]
        if len(hit) >= 5:
            out.append("⚠️ 週一～週五全休，本行程（在福岡只有週一～週五）碰不到。")
        elif hit:
            out.append("🗓 定休：%s——本行程在福岡的日子是 2/1(一)、2/2(二)、2/3(三)、2/4(四)、"
                       "2/10(三)、2/11(四)、2/12(五)，排行程時避開。" % "、".join(hit))
    return out


def main():
    with open(SRC, encoding="utf-8") as f:
        raw = json.load(f)
    rows = {r[0]: r for r in raw["rows"]}

    applied, missing = 0, []
    for path in sorted(glob.glob(os.path.join("data", "*.json"))):
        with open(path, encoding="utf-8") as f:
            places = json.load(f)
        changed = False
        for p in places:
            r = rows.get(p["name"])
            if not r or r[1] is None:
                if p.get("lat") is None:
                    missing.append(p["name"])
                continue
            _, lat, lng, gname, gaddr, hours, status, _flag = r
            sp = SPECIAL.get(p["name"], {})

            p["lat"] = sp.get("lat", round(lat, 6))
            p["lng"] = sp.get("lng", round(lng, 6))
            p["coord_status"] = "google"
            p["coord_source"] = "Google Places 查詢 2026-08-19（%s）" % gname
            p["address"] = sp.get("address", clean_addr(gaddr))
            p["area"] = sp.get("area", area_from_addr(gaddr, p.get("area", "")))

            hstr, closed = fmt_hours(hours)
            if hstr:
                p["hours"] = hstr
            elif "hours" in p:
                p.pop("hours")
            if status and status != "OPERATIONAL":
                p["business_status"] = status

            note = sp.get("notes", base_note(p.get("notes", "")))
            warns = trip_warning(closed, status)
            p["notes"] = "　".join(warns + ([note] if note else []))
            if not p["notes"]:
                p.pop("notes")

            applied += 1
            changed = True
            print("  %-38s %-16s %s" % (p["name"][:38], p["area"], p["hours"] if hstr else "（無營業時間）"))
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(places, f, ensure_ascii=False, indent=1)
                f.write("\n")

    print("\n✅ 套用 %d 筆 Google 座標" % applied)
    if missing:
        print("⚠️ 仍然沒有座標：%s" % missing)


if __name__ == "__main__":
    main()
