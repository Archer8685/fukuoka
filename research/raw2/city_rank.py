"""Rank nearby cities by how often Fukuoka-trip guides recommend them.

IMPORTANT metric choice:
  The regional corpus (text2/) was collected with per-city queries, so raw hit
  counts there are biased (each city guaranteed ~8 docs about itself).
  For an UNBIASED city ranking we use ONLY the Fukuoka-centric corpus
  (text/ = 38 blogs + 15 videos), which was queried as "福岡攻略/行程".
  How often those docs mention a nearby city == how strongly Fukuoka trip
  planners actually push that city as a side trip. That is the right signal.
  The regional corpus is then used only for depth (how many spots per city).
"""
import glob, json, os, re
from collections import defaultdict

T1 = 'C:/Users/kevin/workspace/fukuoka/research/text'
T2 = 'C:/Users/kevin/workspace/fukuoka/research/text2'

# --- unbiased base: Fukuoka-centric docs only ---
base = {}
for f in sorted(glob.glob(T1 + '/*.txt')):
    base[os.path.basename(f)[:-4]] = open(f, encoding='utf-8').read()
vm = json.load(open('C:/Users/kevin/workspace/fukuoka/research/raw/videos_meta.json', encoding='utf-8'))
for v in vm:
    base['VID_' + v['key']] = (v.get('title') or '') + '\n' + (v.get('desc') or '')
seen, uniq = set(), {}
for k, t in base.items():
    h = hash(t[:4000])
    if h not in seen:
        seen.add(h); uniq[k] = t
base = uniq
NB = len(base)

# city -> (hours from Hakata, transport, aliases)
CITIES = {
    '太宰府':   (0.5, '西鐵 30 分',        ['太宰府']),
    '北九州/小倉': (0.3, '新幹線 16 分',    ['小倉', '北九州']),
    '門司港':   (1.3, 'JR 1.5 小時',       ['門司港']),
    '柳川':     (1.0, '西鐵 50 分',        ['柳川']),
    '糸島':     (0.7, 'JR+車 40 分',       ['糸島']),
    '熊本':     (0.7, '新幹線 40 分',      ['熊本']),
    '由布院':   (2.2, '特急 2 小時',       ['由布院', '湯布院']),
    '別府':     (2.2, '特急 2 小時',       ['別府']),
    '長崎':     (2.0, '新幹線+特急 2 小時', ['長崎']),
    '佐世保/豪斯登堡': (1.7, '特急 1.7 小時', ['豪斯登堡', 'ハウステンボス', '佐世保']),
    '下關':     (1.5, 'JR+船 1.5 小時',    ['下關', '下関', '唐戶市場', '唐戸市場']),
    '佐賀':     (1.0, 'JR 1 小時',         ['佐賀']),
    '唐津/呼子': (1.3, '地鐵直通 1.3 小時', ['唐津', '呼子']),
    '武雄/嬉野': (1.4, '西九州新幹線',      ['武雄', '嬉野']),
    '有田':     (1.5, 'JR 1.5 小時',       ['有田焼', '有田陶', '有田町']),
    '鹿兒島':   (1.6, '新幹線 1.6 小時',    ['鹿兒島', '鹿児島']),
    '阿蘇':     (2.5, '新幹線+車 2.5 小時', ['阿蘇']),
    '黑川溫泉': (3.0, '巴士 3 小時',        ['黑川溫泉', '黒川温泉']),
    '日田':     (1.5, '特急 1.5 小時',      ['日田', '豆田']),
    '山口/角島': (2.5, '新幹線+車 2.5 小時', ['角島', '元乃隅', '秋芳洞']),
    '雲仙/島原': (2.5, '2.5 小時以上',      ['雲仙', '島原']),
    '久留米':   (0.7, '新幹線 17 分',       ['久留米']),
    '八女':     (1.2, '巴士 1.2 小時',      ['八女']),
    '福津':     (0.8, 'JR+巴士 50 分',      ['宮地嶽', '宮地岳', '福津']),
}

# depth: how many distinct notable spots per city (from regional_stats)
rs = json.load(open('C:/Users/kevin/workspace/fukuoka/research/regional_stats.json', encoding='utf-8'))
CITYMAP = {
    '太宰府': '太宰府', '北九州': '北九州/小倉', '下關': '下關', '山口': '山口/角島',
    '柳川': '柳川', '篠栗': '太宰府', '福津': '福津', '久留米': '久留米', '八女': '八女',
    '佐賀': '佐賀', '鹿島': '佐賀', '唐津': '唐津/呼子', '嬉野': '武雄/嬉野',
    '武雄': '武雄/嬉野', '有田': '有田', '太良': '佐賀', '長崎': '長崎',
    '佐世保': '佐世保/豪斯登堡', '雲仙': '雲仙/島原', '島原': '雲仙/島原',
    '由布院': '由布院', '別府': '別府', '日田': '日田', '熊本': '熊本',
    '阿蘇': '阿蘇', '黑川': '黑川溫泉', '小國': '黑川溫泉', '高森': '阿蘇',
    '鹿兒島': '鹿兒島', '指宿': '鹿兒島', '霧島': '鹿兒島', '糸島': '糸島',
}
depth = defaultdict(list)
for r in rs:
    c = CITYMAP.get(r['city'])
    if c and r['hits'] >= 10:
        depth[c].append((r['hits'], r['name']))

rows = []
for city, (hrs, how, aliases) in CITIES.items():
    hits = sum(1 for t in base.values() if any(a in t for a in aliases))
    pct = 100.0 * hits / NB
    sp = sorted(depth.get(city, []), reverse=True)
    rows.append((hits, pct, city, hrs, how, sp))

rows.sort(reverse=True)
print('unbiased base corpus = %d Fukuoka-guide docs\n' % NB)
print('%-18s %5s %6s  %-18s %s' % ('city', 'docs', 'share', 'access', 'notable spots (>=10 hits)'))
print('-' * 110)
for hits, pct, city, hrs, how, sp in rows:
    names = '、'.join('%s(%d)' % (n, h) for h, n in sp[:5]) or '—'
    print('%-18s %4d  %4.0f%%  %-18s %s' % (city, hits, pct, how, names))

json.dump([dict(city=c, docs=h, share=round(p, 1), hours=x, access=w,
                spots=[dict(name=n, hits=hh) for hh, n in s])
           for h, p, c, x, w, s in rows],
          open('C:/Users/kevin/workspace/fukuoka/research/city_ranking.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
