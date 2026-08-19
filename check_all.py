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


def main():
    print("=== 福岡專案健檢 ===\n")
    places = load_data_dir()
    check_data(places)
    check_data_js(places)
    check_version()
    check_trip()
    print(f"\n=== 錯誤 {len(ERR)}、警告 {len(WARN)} ===")
    sys.exit(1 if ERR else 0)


if __name__ == "__main__":
    main()
