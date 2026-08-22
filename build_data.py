#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 data/*.json 合併成單一 data.js（PLACES / J2T）。

    python build_data.py

輸出 data.js 供 map.html 與 itinerary.html 載入。改完 data/*.json 後重跑即可。
記得同步把 map.html / itinerary.html 裡的 ?v=N 與 sw.js 的 APP_CACHE 版號 +1。
"""
import json
import glob
import os
import sys
from collections import Counter

# 日文新字體 → 繁體，搜尋時兩邊都正規化成繁體，
# 這樣輸入「天滿宮」找得到「天満宮」，輸入「温泉」也找得到「溫泉」。
J2T = {
    "満": "滿", "温": "溫", "図": "圖", "広": "廣", "桜": "櫻", "浜": "濱",
    "県": "縣", "楼": "樓", "蔵": "藏", "豊": "豐", "鉄": "鐵", "関": "關",
    "雑": "雜", "静": "靜", "亀": "龜", "竜": "龍", "塩": "鹽", "沢": "澤",
    "変": "變", "駅": "驛", "円": "圓", "学": "學", "会": "會", "気": "氣",
    "帰": "歸", "国": "國", "黒": "黑", "参": "參", "実": "實", "写": "寫",
    "寿": "壽", "従": "從", "焼": "燒", "乗": "乘", "数": "數", "声": "聲",
    "対": "對", "単": "單", "断": "斷", "点": "點", "転": "轉", "伝": "傳",
    "灯": "燈", "当": "當", "独": "獨", "読": "讀", "発": "發", "麦": "麥",
    "宝": "寶", "万": "萬", "麺": "麵", "薬": "藥", "様": "樣", "来": "來",
    "覧": "覽", "歴": "歷", "湾": "灣", "区": "區", "経": "經", "継": "繼",
    "芸": "藝", "号": "號", "済": "濟", "斉": "齊", "児": "兒", "辞": "辭",
    "収": "收", "渋": "澀", "浅": "淺", "双": "雙", "壮": "壯", "総": "總",
    "荘": "莊", "装": "裝", "属": "屬", "続": "續", "帯": "帶", "択": "擇",
    "担": "擔", "団": "團", "弾": "彈", "昼": "晝", "庁": "廳", "徴": "徵",
    "聴": "聽", "党": "黨", "縄": "繩", "覇": "霸", "拝": "拜", "廃": "廢",
    "抜": "拔", "弁": "辯", "舗": "舖", "崩": "崩", "毎": "每", "免": "免",
    "黙": "默", "訳": "譯", "与": "與", "誉": "譽", "謡": "謠", "頼": "賴",
    "乱": "亂", "涙": "淚", "齢": "齡", "暦": "曆", "恋": "戀", "錬": "鍊",
    "炉": "爐", "労": "勞", "録": "錄", "厳": "嚴", "験": "驗", "権": "權",
    "証": "證", "説": "說", "銭": "錢", "険": "險", "隠": "隱", "顔": "顏",
    "髪": "髮", "亜": "亞", "悪": "惡", "圧": "壓", "囲": "圍", "医": "醫",
    "栄": "榮", "営": "營", "縁": "緣", "応": "應", "横": "橫", "欧": "歐",
    "仮": "假", "価": "價", "画": "畫", "壊": "壞", "懐": "懷", "絵": "繪",
    "覚": "覺", "楽": "樂", "巻": "卷", "観": "觀", "犠": "犧", "旧": "舊",
    "拠": "據", "挙": "舉", "虚": "虛", "峡": "峽", "狭": "狹", "郷": "鄉",
    "暁": "曉", "駆": "驅", "撃": "擊", "呉": "吳", "効": "效", "剤": "劑",
    "湿": "濕", "舎": "舍", "釈": "釋", "獣": "獸", "縦": "縱", "処": "處",
    "将": "將", "嬢": "孃", "畳": "疊", "譲": "讓", "醸": "釀", "触": "觸",
    "寝": "寢", "尽": "盡", "粋": "粹", "酔": "醉", "随": "隨", "枢": "樞",
    "摂": "攝", "繊": "纖", "禅": "禪", "曽": "曾", "捜": "搜", "巣": "巢",
    "争": "爭", "増": "增", "堕": "墮", "滞": "滯", "滝": "瀧", "胆": "膽",
    "遅": "遲", "鋳": "鑄", "逓": "遞", "盗": "盜", "稲": "稻", "闘": "鬥",
    "徳": "德", "悩": "惱", "脳": "腦", "蛮": "蠻", "払": "拂", "仏": "佛",
    "塀": "堊", "豚": "豚", "駐": "駐", "顕": "顯",
}

CATEGORY_ORDER = ["景點", "祭典", "動漫", "溫泉", "購物", "餐飲", "住宿", "交通"]


def main():
    files = sorted(glob.glob(os.path.join("data", "*.json")))
    if not files:
        sys.exit("data/*.json 不存在")

    places, seen = [], {}
    for path in files:
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
        for p in items:
            name = p["name"].strip()
            if name in seen:
                print(f"  ! 重複略過：{name}（{os.path.basename(path)}）")
                continue
            seen[name] = True
            p["name"] = name
            p.pop("q", None)          # 只在 geocode.py 用，不需送到前端
            p.pop("coord_source", None)
            places.append(p)

    places.sort(key=lambda p: (
        CATEGORY_ORDER.index(p["category"]) if p["category"] in CATEGORY_ORDER else 99,
        p.get("city", ""), p["name"],
    ))

    no_coord = [p["name"] for p in places if not p.get("lat")]
    cats = Counter(p["category"] for p in places)
    cities = Counter(p.get("city", "?") for p in places)

    # newline="\n" 可避免 Windows 依 os.linesep 產生 CRLF；專案由
    # .gitattributes 統一使用 LF，build 後不應出現換行轉換警告。
    with open("data.js", "w", encoding="utf-8", newline="\n") as f:
        f.write("// 由 build_data.py 從 data/*.json 產生 — 請勿手改，改 data/*.json 後重跑\n")
        f.write("const PLACES = ")
        json.dump(places, f, ensure_ascii=False, indent=1)
        f.write(";\n\n// 日文新字體 → 繁體：搜尋正規化用\n")
        f.write("const J2T = ")
        json.dump(J2T, f, ensure_ascii=False)
        f.write(";\n")

    print(f"\n寫出 data.js：{len(places)} 個地點")
    print("  分類：", dict(cats))
    print("  城市：", dict(cities))
    if no_coord:
        print(f"  ⚠️ {len(no_coord)} 個地點沒有座標，地圖上不會出現：")
        for n in no_coord:
            print(f"      - {n}")
        print("     跑 python geocode.py 或手動填 lat/lng（coord_status 設 manual）")


if __name__ == "__main__":
    main()
