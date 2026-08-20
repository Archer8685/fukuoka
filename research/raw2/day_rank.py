"""Rank the 12 days by strength, and compare against a Kumamoto day-trip.

Metric per day: for each AREA, take the MAX spot score in that area (the area's
headline draw) and sum across areas. Using max-per-area rather than sum avoids
rewarding days that merely list many low-value stops in one place.
Also report the day's single strongest stop and whether the day is date-locked.
"""
import re, json, glob, os

t = open('C:/Users/kevin/workspace/fukuoka/trip.js', encoding='utf-8').read()
main = t[:t.index('const BACKUPS')]
days = re.findall(r'\{d:(\d+), date:"([^"]+)", wd:"([^"]+)", city:"([^"]+)", title:"([^"]*)"(.*?)\n \]\}',
                  main, re.S)
STOP = re.compile(r'\{t:"([^"]+)", kind:"([^"]+)", name:"([^"]+)", label:"([^"]*)"')
sc = json.load(open('C:/Users/kevin/workspace/fukuoka/research/trip_scores2.json', encoding='utf-8'))
score = {r['name']: r['hits'] for rows in sc.values() for r in rows}

ns = {}
exec(open('C:/Users/kevin/workspace/fukuoka/research/raw2/areas.py', encoding='utf-8')
     .read().split('print(')[0], ns)
AREA = ns['AREA']

# date-locked reasons (things that only exist on that specific date)
LOCK = {
    '1': '抵達日（班機）',
    '2': 'KKday 豪斯登堡巴士團已訂',
    '3': '節分厄除大祭（2/3 限定）',
    '5': '長崎燈會開幕夜（2/5 限定）',
    '6': '長崎燈會＋初一',
    '7': '移動日（ゆふいんの森指定席）',
    '8': '由布院住宿（金鱗湖晨霧只有住這才看得到）',
    '11': '柳川雛祭開幕日（2/11 限定）',
    '12': '回程日（班機）',
}

rows = []
for d, date, wd, city, title, body in days:
    st = [(tt, k, n, l) for tt, k, n, l in STOP.findall(body) if k not in ('hotel', 'move')]
    areas = {}
    for tt, k, n, l in st:
        a = AREA.get(n, '?' + n)
        areas.setdefault(a, []).append((n, score.get(n, 0)))
    day_score = sum(max(s for _, s in v) for v in areas.values())
    best = max(((n, s) for v in areas.values() for n, s in v), key=lambda x: x[1])
    rows.append((day_score, d, date, wd, city, title, areas, best, LOCK.get(d)))

rows.sort()
print('=== 12 天按「地區主打分」由弱到強 ===\n')
for day_score, d, date, wd, city, title, areas, best, lock in rows:
    print('%3d分  D%-3s %s(%s) [%s]  %d地區   %s' % (
        day_score, d, date, wd, city, len(areas), '🔒 ' + lock if lock else '🔓 可動'))
    for a, v in areas.items():
        print('        %-8s max=%-3d  %s' % (a, max(s for _, s in v),
                                             '、'.join('%s%d' % (n, s) for n, s in v)))
    print()

# --- Kumamoto day trip candidate ---
KUMA = {
    '熊本城': ['熊本城', '櫻之馬場城彩苑', '加藤神社'],
    '上下通': ['熊本熊部長辦公室', '上下通商店街'],
    '水前寺': ['水前寺成趣園'],
}
rstats = {r['name']: r['hits'] for r in
          json.load(open('C:/Users/kevin/workspace/fukuoka/research/regional_stats.json', encoding='utf-8'))}
print('=== 熊本一日遊（候選）===')
ktot = 0
for a, names in KUMA.items():
    vals = [(n, rstats.get(n, 0)) for n in names]
    m = max(s for _, s in vals)
    ktot += m
    print('        %-8s max=%-3d  %s' % (a, m, '、'.join('%s%d' % (n, s) for n, s in vals)))
print('  熊本一日總分 = %d（3 地區，新幹線 40 分）' % ktot)
print('  ⚠️ 熊本城/城彩苑/加藤神社 的分數來自區域語料（142篇），與行程分數同尺規者僅熊本城')
