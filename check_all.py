#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一鍵健檢：資料、座標、版號、行程邏輯全部檢查一遍。

    python check_all.py          # 有問題回傳 1，可直接掛 CI／commit hook

檢查項目
  1. data/*.json 合法、名稱不重複
  2. 每個地點都有座標，且落在九州＋下關的 bbox 內（擋掉配到外縣市的座標）
  3. data.js 與 data/*.json 同步（忘記跑 build_data.py 會被抓到）
  4. 版號 4 處一致（忘記跑 bump_version.py 會被抓到）
  5. trip.js 語法（需要 node；沒有 node 就跳過）
  6. 行程邏輯：12 天、日期↔星期符合 2027 年曆、每天時間遞增、
     住宿連續性與換宿次數、每個站點與備選都能在 data.js 找到
"""
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

# 九州＋下關（山口縣西端）；比行政區界寬一點，只用來擋「配到別的縣」
BBOX = (30.5, 128.5, 35.2, 134.2)
ERR, WARN = [], []


def err(m):
    ERR.append(m)
    print("❌", m)


def warn(m):
    WARN.append(m)
    print("⚠️ ", m)


def ok(m):
    print("✅", m)


def load_data_dir():
    places = []
    for f in sorted(glob.glob(os.path.join("data", "*.json"))):
        try:
            items = json.load(io.open(f, encoding="utf-8"))
        except Exception as e:
            err(f"{f} 不是合法 JSON：{e}")
            continue
        places += items
    return places


def check_data(places):
    dup = [n for n, c in Counter(p["name"] for p in places).items() if c > 1]
    if dup:
        err(f"data/*.json 有重複名稱：{dup}")
    else:
        ok(f"data/*.json 合法，{len(places)} 個地點、名稱無重複")

    no_coord = [p["name"] for p in places if p.get("lat") is None]
    if no_coord:
        err(f"{len(no_coord)} 個地點沒有座標（地圖上不會出現）：{no_coord[:5]}")
    # city="其他" 是刻意放在九州外的「跨區參考點」（廣島／宮島／倉敷／京都／大阪），
    # 對它們放寬到本州西部＋關西；九州內的守門維持原樣，才擋得住配錯縣市的座標。
    WIDE = (33.0, 128.5, 36.0, 136.2)
    def in_box(p, b):
        return b[0] <= p["lat"] <= b[2] and b[1] <= p["lng"] <= b[3]
    outside = [(p["name"], p["lat"], p["lng"]) for p in places
               if p.get("lat") is not None
               and not in_box(p, WIDE if p.get("city") == "其他" else BBOX)]
    if outside:
        err(f"{len(outside)} 個座標落在九州＋下關範圍外：{outside[:3]}")
    if not no_coord and not outside:
        ok("所有地點都有座標且落在九州＋下關範圍內")

    md = [p["name"] for p in places
          if "**" in json.dumps(p, ensure_ascii=False)]
    if md:
        warn(f"{len(md)} 個地點的文字含 markdown `**`，頁面用 innerHTML 輸出會顯示成星號：{md[:3]}")


def check_data_js(places):
    if not os.path.exists("data.js"):
        err("data.js 不存在——跑 python build_data.py")
        return
    raw = io.open("data.js", encoding="utf-8").read()
    try:
        head = "const PLACES = "
        js = json.loads(raw[raw.index(head) + len(head):raw.index(";\n\n// 日文")])
    except Exception as e:
        err(f"data.js 解析失敗：{e}")
        return
    key = lambda p: json.dumps(
        {k: v for k, v in p.items() if k not in ("q", "coord_source")},
        ensure_ascii=False, sort_keys=True)
    if sorted(map(key, js)) != sorted(map(key, places)):
        err("data.js 與 data/*.json 不同步——跑 python build_data.py")
    else:
        ok(f"data.js 與 data/*.json 同步（{len(js)} 筆）")


def check_version():
    if not os.path.exists("bump_version.py"):
        warn("找不到 bump_version.py，跳過版號檢查")
        return
    r = subprocess.run([sys.executable, "bump_version.py", "--check"],
                       capture_output=True, text=True)
    last = [l for l in r.stdout.strip().splitlines() if l.strip()][-1]
    if r.returncode != 0:
        err("版號不一致——跑 python bump_version.py（" + last.strip() + "）")
    else:
        ok(last.strip().lstrip("✅ "))


TRIP_CHECK_JS = r"""
const fs=require('fs');
// 必須在最外層直接 eval：包進函式裡 eval 出來的變數不會進到全域
eval(fs.readFileSync('data.js','utf8').replace(/^const /gm,'var '));
eval(fs.readFileSync('trip.js','utf8').replace(/^const /gm,'var '));
const out=[];const E=m=>out.push('ERR '+m);const W=m=>out.push('WARN '+m);
const WD=['日','一','二','三','四','五','六'];
const mins=t=>{const[a,b]=t.split(':').map(Number);return a*60+b};
if(TRIP.length!==12)E('天數 '+TRIP.length+'，應為 12');
TRIP.forEach((d,i)=>{
  if(d.d!==i+1)E('第 '+(i+1)+' 天 d='+d.d);
  const[m,dd]=d.date.split('/').map(Number);
  const wd=WD[new Date(Date.UTC(2027,m-1,dd)).getUTCDay()];
  if(wd!==d.wd)E(d.date+' 星期應為 '+wd+'，寫的是 '+d.wd);
  if(m!==2||dd!==i+1)E(d.date+' 與 Day '+d.d+' 不對應');
  const plans=d.variants?d.variants.map(v=>v.id):[null];
  plans.forEach(pl=>{
    const ss=d.stops.filter(s=>pl?s.plan===pl:true);
    if(!ss.length)E('D'+d.d+' 方案 '+pl+' 無站點');
    for(let i=1;i<ss.length;i++)
      if(mins(ss[i].t)<mins(ss[i-1].t))
        E('D'+d.d+(pl?'-'+pl:'')+' 時間逆行：'+ss[i-1].t+' → '+ss[i].t+' '+ss[i].name);
  });
  if(d.variants){const ids=new Set(d.variants.map(v=>v.id));
    d.stops.forEach(s=>{if(!s.plan)E('D'+d.d+' 站點缺 plan：'+s.name);
      else if(!ids.has(s.plan))E('D'+d.d+' plan='+s.plan+' 無對應方案：'+s.name);});}
  else d.stops.forEach(s=>{if(s.plan)E('D'+d.d+' 無方案卻有 plan：'+s.name)});
});
const names=new Set(PLACES.map(p=>p.name));
TRIP.forEach(d=>d.stops.forEach(s=>{
  if(!names.has(s.name))E('D'+d.d+' 站點不在 data.js：'+s.name);
  (s.alt||[]).forEach(a=>{if(!names.has(a))E('D'+d.d+' 備選不在 data.js：'+a)});
}));
const night=TRIP.map(d=>{const h=d.stops.filter(s=>s.kind==='hotel');return h.length?h[h.length-1].name:null});
night.slice(0,11).forEach((h,i)=>{if(!h)E('D'+(i+1)+' 找不到當晚住宿')});
const stay={};night.slice(0,11).forEach(h=>stay[h]=(stay[h]||0)+1);
const changes=night.slice(0,11).filter((h,i,a)=>i>0&&h!==a[i-1]).length;
out.push('INFO 住宿晚數 '+JSON.stringify(stay)+'，換宿 '+changes+' 次');
if(Object.values(stay).reduce((a,b)=>a+b,0)!==11)E('住宿晚數合計不是 11 晚');
console.log(out.join('\n'));
"""


def check_trip():
    node = shutil.which("node")
    if not node:
        warn("找不到 node，跳過 trip.js 語法與行程邏輯檢查")
        return
    r = subprocess.run([node, "--check", "trip.js"], capture_output=True, text=True)
    if r.returncode != 0:
        err("trip.js 語法錯誤：" + r.stderr.strip().splitlines()[0])
        return
    ok("trip.js 語法正確")
    r = subprocess.run([node, "-e", TRIP_CHECK_JS], capture_output=True, text=True)
    if r.returncode != 0:
        err("行程檢查腳本執行失敗：" + r.stderr.strip()[:200])
        return
    bad = False
    for line in r.stdout.strip().splitlines():
        if line.startswith("ERR "):
            err(line[4:]); bad = True
        elif line.startswith("WARN "):
            warn(line[5:])
        elif line.startswith("INFO "):
            print("   ", line[5:])
    if not bad:
        ok("行程邏輯正確（12 天、日期↔星期、時間遞增、站點名稱、住宿連續性）")


DUMP_STOPS_JS = r"""
const fs=require('fs');
const src=fs.readFileSync('trip.js','utf8');
const m=new Function(src+'; return {TRIP};')();
const out=[];
m.TRIP.forEach(d=>d.stops.forEach((s,i)=>out.push({
  day:d.d, date:d.date, wd:d.wd, t:s.t, name:s.name, kind:s.kind||'',
  go:s.go||'', last:i===d.stops.length-1,
})));
console.log(JSON.stringify(out));
"""


def dump_stops():
    """把 trip.js 的所有站點抓成 python list（trip.js 用 const，必須走 new Function）。"""
    node = shutil.which("node")
    if not node:
        return None
    r = subprocess.run([node, "-e", DUMP_STOPS_JS], capture_output=True, text=True,
                       encoding="utf-8")
    if r.returncode != 0:
        err("dump_stops 失敗：" + r.stderr.strip()[:200])
        return None
    return json.loads(r.stdout)


def _mins(t):
    a, b = t.split(":")
    return int(a) * 60 + int(b)


def travel_cost(go):
    """從 go 文字估移動時間。
    「或／則」代表替代方案（計程車 5 分 or 步行 20 分）→ 取最小的那個，
    同一方案內的多段（地鐵 11 分 ＋ 步行 12 分）才相加。"""
    if not go:
        return 0
    costs = []
    for alt in re.split(r"[，,]?\s*(?:或|則)\s*", go):
        n = [int(x) for x in re.findall(r"(\d+)\s*分", alt)]
        if n:
            costs.append(sum(n))
    return min(costs) if costs else 0


# 沒有 duration 欄位時的保底門檻（分鐘）——只抓明顯不合理的。
FALLBACK_MIN = {"spot": 25, "meal": 40, "shop": 20}

# 刻意短停、不需要告警的站（拍照點、外帶、轉乘、跳店採購）
SHORT_OK = {
    "銀河鐵道999 星野鐵郎銅像", "B-speak", "みっふぃー森のきっちん 由布院店",
    "あまおうチーズケーキファクトリー Kingberry（太宰府天滿宮本店）",
    "MARK IS 福岡ももち", "博多運河城", "Sanrio Gallery 運河城博多店",
    "JUMP SHOP 福岡店", "NEPENTHES HAKATA", "博多川端商店街", "ふくや 中洲本店",
    "あるあるCity", "櫻之馬場 城彩苑", "湯之坪街道",
}

# 目前行程已核可的停留基準線：audit/stay_baseline.json
# {"2/5|門司港復古區": 50, ...}
# 有些站是刻意壓縮的（門司港復古區 建議 120 分但只給 50），
# 這些現況一旦記為基準線，就不會每次都吵；
# 但只要之後任何改動讓它「比現在更短」，仍然會告警。
BASELINE_PATH = os.path.join("audit", "stay_baseline.json")


def load_baseline():
    if os.path.exists(BASELINE_PATH):
        try:
            return json.load(io.open(BASELINE_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {}


def need_minutes(place, kind):
    """這個地點「該待多久」。優先用 data/*.json 的 duration 欄位
    （例 '45 分'、'1.5–2 小時'、'2 小時'）——取區間下限；
    沒有 duration 才退回站別保底門檻。"""
    raw = (place or {}).get("duration") or ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:[–~-]\s*\d+(?:\.\d+)?\s*)?(小時|時間|分)", raw)
    if m:
        v = float(m.group(1))
        return int(v * 60) if m.group(2) in ("小時", "時間") else int(v)
    return FALLBACK_MIN.get(kind, 0)


def check_stay_duration(stops, places):
    """站點實際停留（到下一站的間隔扣掉移動時間）是否足夠。

    門檻 = min(該地點建議 duration, 已核可基準線)。
    這樣既能擋「改了某一站把後面那站擠爆」的回歸
    （例：三麗鷗延到 11:00，teamLab 只剩 40 分 < 建議 45 分），
    又不會對本來就刻意壓縮的站每次嘮叨。
    要重設基準線：python check_all.py --save-baseline"""
    if not stops:
        return
    byname = {p["name"]: p for p in (places or [])}
    base = load_baseline()
    save = "--save-baseline" in sys.argv
    newbase, bad = {}, 0
    for cur, nxt in zip(stops, stops[1:]):
        if cur["last"] or cur["kind"] in ("hotel", "move", ""):
            continue
        stay = _mins(nxt["t"]) - _mins(cur["t"]) - travel_cost(cur["go"])
        key = f"{cur['date']}|{cur['name']}"
        newbase[key] = stay
        if cur["name"] in SHORT_OK:
            continue
        need = need_minutes(byname.get(cur["name"]), cur["kind"])
        if not need:
            continue
        limit = min(need, base.get(key, need))
        if stay < limit:
            extra = "" if limit == need else f"（已核可基準 {limit} 分）"
            warn(f"{cur['date']}({cur['wd']}) {cur['t']} {cur['name']} "
                 f"實際只停 {stay} 分，建議 {need} 分{extra}")
            bad += 1
    if save:
        os.makedirs("audit", exist_ok=True)
        json.dump(newbase, io.open(BASELINE_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        ok(f"已寫入停留基準線 {BASELINE_PATH}（{len(newbase)} 站）")
    elif not bad:
        ok("每站停留時間符合建議／已核可基準（已扣除移動時間）")


WD_JA = {"一": "月曜日", "二": "火曜日", "三": "水曜日", "四": "木曜日",
         "五": "金曜日", "六": "土曜日", "日": "日曜日"}


def check_closed_days(stops):
    """比對「造訪當天的星期」與 Google 的定休日。

    營業時間來自 verify_places.py 產生的 audit/verify_places_*.json 快取
    （這支腳本不打 API，才能離線快速跑完）。
    快取過期或不存在就提醒去跑 verify_places.py。"""
    if not stops:
        return
    reports = sorted(glob.glob(os.path.join("audit", "verify_places_*.json")))
    if not reports:
        warn("找不到 audit/verify_places_*.json，無法檢查定休日——跑 python verify_places.py")
        return
    latest = reports[-1]
    try:
        data = json.load(io.open(latest, encoding="utf-8"))
    except Exception as e:
        warn(f"{latest} 解析失敗，跳過定休日檢查：{e}")
        return

    hours = {}
    seen = set()
    for r in data.get("results", []):
        seen.add((r.get("date"), r.get("name")))
        if r.get("hours"):
            hours.setdefault((r.get("date"), r.get("name")), r["hours"])

    tag = os.path.basename(latest).replace("verify_places_", "").replace(".json", "")
    hit = missing = unqueried = 0
    for s in stops:
        if s["last"] or s["kind"] in ("hotel", "move", ""):
            continue
        key = (s["date"], s["name"])
        if key not in seen:
            unqueried += 1          # 這站根本不在快取裡（行程改過、還沒重查）
            continue
        h = hours.get(key)
        if h is None:
            missing += 1            # 查過了，但 Google 沒提供營業時間（公園、街道、銅像）
            continue
        target = WD_JA.get(s["wd"], "")
        for line in h:
            if line.startswith(target) and re.search(r"定休|休業|Closed", line):
                err(f"{s['date']}({s['wd']}) {s['t']} {s['name']} 當天公休：{line}")
                hit += 1
    if not hit:
        ok(f"定休日與造訪星期無衝突（依 {tag} 的實查快取）")
    if unqueried:
        warn(f"{unqueried} 站不在 {tag} 快取中（行程改過）——跑 python verify_places.py 重查")
    if missing:
        print(f"    （另有 {missing} 站 Google 未提供營業時間，如公園／街道／銅像，無法檢查定休）")


DUMP_NOTES_JS = r"""
const fs=require('fs');
const src=fs.readFileSync('trip.js','utf8');
const m=new Function(src+'; return {TRIP};')();
const out=[];
m.TRIP.forEach(d=>d.stops.forEach(s=>out.push({
  date:d.date, t:s.t, name:s.name, note:s.note||'', alt:s.alt||[],
})));
console.log(JSON.stringify(out));
"""

def dump_notes():
    """從 trip.js 取出每站的 note 與 alt。"""
    r = subprocess.run(["node", "-e", DUMP_NOTES_JS],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        err(f"dump_notes 失敗：{(r.stderr or '').strip()[:200]}")
        return []
    return json.loads(r.stdout)


# note 裡出現這些字眼 = 把修改歷程寫進了給使用者看的行程頁。
# 使用者已為此清理過兩次（v65「清除全檔歷程語言」等），不該再犯。
HISTORY_WORDS = [
    "實查後換掉", "換掉了原本", "已從", "訂正（", "時間訂正", "開門時間訂正",
    "原本排的", "原本寫的", "先前寫的", "原版是", "本次修正", "已改成",
]


def check_note_history(notes):
    """站點 note 只該寫現況，不該寫修改歷程或日期戳記。"""
    if not notes:
        return
    bad = 0
    for s in notes:
        note = s["note"]
        hits = [w for w in HISTORY_WORDS if w in note]
        # 日期戳記通常是「我幾號查的」這種歷程語言，但「店家幾號回信確認」
        # 是真實事證，必須保留 → 只在日期附近沒有事證關鍵字時才告警。
        for m in re.finditer(r"20\d\d-\d\d-\d\d", note):
            ctx = note[max(0, m.start() - 25):m.end() + 25]
            if not re.search(r"回信|回覆|來信|確認|預約|訂位|公告|官網", ctx):
                hits.append(f"日期戳記({m.group(0)})")
        if hits:
            warn(f"{s['date']} {s['t']} {s['name']} note 含修改歷程語言：{'、'.join(hits)}")
            bad += 1
    if not bad:
        ok("站點 note 無修改歷程語言（只講現況）")


def check_alt_conflicts(notes, places):
    """備選清單裡不該出現「已知會撲空」的店。

    判斷依據：note 用「不要改去 X」「X 會吃閉門羹」點名的店，
    若同時還列在該站的 alt 裡，等於修了主站卻留著地雷備案。"""
    if not notes:
        return
    bad = 0
    for s in notes:
        for a in s["alt"]:
            if re.search(r"不要(改去|選)\s*[「『]?" + re.escape(a), s["note"]):
                err(f"{s['date']} {s['t']} {s['name']} note 說不要去「{a}」，"
                    f"卻仍列在 alt 備選中")
                bad += 1
    if not bad:
        ok("備選清單無已知會撲空的店")


def main():
    print("=== 福岡專案健檢 ===\n")
    places = load_data_dir()
    check_data(places)
    check_data_js(places)
    check_version()
    check_trip()
    stops = dump_stops()
    check_stay_duration(stops, places)
    check_closed_days(stops)
    notes = dump_notes()
    check_note_history(notes)
    check_alt_conflicts(notes, places)
    print(f"\n=== 錯誤 {len(ERR)}、警告 {len(WARN)} ===")
    sys.exit(1 if ERR else 0)


if __name__ == "__main__":
    main()
