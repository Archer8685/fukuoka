"""Re-score trip stops against the COMBINED corpus, grouped by city segment."""
import glob, json, os, re
from collections import defaultdict

T1 = 'C:/Users/kevin/workspace/fukuoka/research/text'
T2 = 'C:/Users/kevin/workspace/fukuoka/research/text2'
docs = {}
for f in sorted(glob.glob(T1 + '/*.txt')) + sorted(glob.glob(T2 + '/*.txt')):
    docs[os.path.basename(f)[:-4]] = open(f, encoding='utf-8').read()
vm = json.load(open('C:/Users/kevin/workspace/fukuoka/research/raw/videos_meta.json', encoding='utf-8'))
for v in vm:
    docs['VID_' + v['key']] = (v.get('title') or '') + '\n' + (v.get('desc') or '')
seen, uniq = set(), {}
for k, t in docs.items():
    h = hash(t[:4000])
    if h not in seen:
        seen.add(h); uniq[k] = t
docs = uniq
N = len(docs)

trip = open('C:/Users/kevin/workspace/fukuoka/trip.js', encoding='utf-8').read()
main = trip[:trip.index('const BACKUPS')]
days = re.findall(r'\{d:(\d+), date:"([^"]+)", wd:"([^"]+)", city:"([^"]+)", title:"([^"]*)"(.*?)\n \]\}', main, re.S)
STOP = re.compile(r'\{t:"([^"]+)", kind:"([^"]+)", name:"([^"]+)", label:"([^"]*)"')

KEYMAP = json.load(open('C:/Users/kevin/workspace/fukuoka/research/raw/keymap.json', encoding='utf-8'))
SKIP_KIND = {'hotel', 'move'}

bycity = defaultdict(list)
for d, date, wd, city, title, body in days:
    for t, kind, name, label in STOP.findall(body):
        if kind in SKIP_KIND:
            continue
        keys = KEYMAP.get(name, [name])
        hits = sum(1 for tx in docs.values() if any(k in tx for k in keys))
        bycity[city].append((hits, date, wd, t, kind, name, label))

print('combined corpus N = %d docs\n' % N)
out = {}
for city in bycity:
    rows = sorted(bycity[city])
    out[city] = [dict(hits=h, date=dt, time=t, kind=k, name=n, label=l)
                 for h, dt, wd, t, k, n, l in rows]
    print('=' * 60)
    print('【%s】 %d stops   median=%d' % (city, len(rows), rows[len(rows) // 2][0]))
    print('=' * 60)
    for h, dt, wd, t, k, n, l in rows:
        print('%4d  %s %s %-5s %s  %s' % (h, dt, t, k, n, l))
    print()

json.dump(out, open('C:/Users/kevin/workspace/fukuoka/research/trip_scores2.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
