"""Download and text-extract the regional (2h-radius) corpus."""
import urllib.request, urllib.parse, gzip, json, re, os, html as H, time
import concurrent.futures as cf

D = 'C:/Users/kevin/workspace/fukuoka/research/raw2'
T = 'C:/Users/kevin/workspace/fukuoka/research/text2'
os.makedirs(T, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

search = json.load(open(D + '/search.json', encoding='utf-8'))

# keep only real article pages
SKIP = re.compile(
    r'(facebook|instagram|twitter|x\.com|youtube\.com/@|pinterest|line\.me|threads\.net'
    r'|/tag/|/tags/|/category/|/author/|/page/\d|/search|\?s=|/feed|/wp-|/privacy|/about'
    r'|klook\.com/\w\w/(city|activity)/?$|kkday\.com/\w\w/?$|agoda|booking\.com|expedia'
    r'|tripadvisor\.com/(Hotel|Restaurant)|amazon\.|rakuten\.co\.jp/(?!travel)'
    r'|\.pdf$|/en/|/ja/|/ko/)', re.I)

cands = {}
for key, v in search.items():
    n = 0
    for l in v['links']:
        if SKIP.search(l):
            continue
        # one page per domain per city to maximise breadth
        dom = urllib.parse.urlparse(l).netloc
        tag = key + '|' + dom
        if tag in cands:
            continue
        cands[tag] = l
        n += 1
        if n >= 8:
            break
print('candidate pages:', len(cands))

def fetch(item):
    tag, url = item
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-TW,zh;q=0.9', 'Accept-Encoding': 'gzip'})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read(3_000_000)
            ct = r.headers.get('Content-Type', '')
        if 'html' not in ct.lower():
            return tag, url, None
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000], re.I)
        enc = (m.group(1).decode('ascii', 'ignore') if m else 'utf-8')
        try:
            return tag, url, raw.decode(enc, 'ignore')
        except LookupError:
            return tag, url, raw.decode('utf-8', 'ignore')
    except Exception:
        return tag, url, None

SC = re.compile(r'<(script|style|noscript|svg|nav|footer|header|form)[^>]*>.*?</\1>', re.S | re.I)
TAG = re.compile(r'<[^>]+>')

def to_text(h):
    t = SC.sub(' ', h)
    t = re.sub(r'<br\s*/?>|</(p|div|li|h\d|tr)>', '\n', t, flags=re.I)
    t = TAG.sub(' ', t)
    t = H.unescape(t)
    t = re.sub(r'[ \t\u00a0]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    return t.strip()

ok = 0
meta = []
with cf.ThreadPoolExecutor(max_workers=10) as ex:
    for tag, url, h in ex.map(fetch, cands.items()):
        if not h or len(h) < 3000:
            continue
        txt = to_text(h)
        # must look like a Chinese-language travel article
        if len(txt) < 1200:
            continue
        cjk = sum(1 for c in txt[:6000] if '\u4e00' <= c <= '\u9fff')
        if cjk < 400:
            continue
        city, dom = tag.split('|', 1)
        fn = city + '_' + re.sub(r'[^a-z0-9]', '', dom.replace('www.', ''))[:16]
        p = T + '/' + fn + '.txt'
        i = 2
        while os.path.exists(p):
            p = T + '/' + fn + str(i) + '.txt'
            i += 1
        ti = re.search(r'<title[^>]*>(.*?)</title>', h, re.S | re.I)
        title = H.unescape(TAG.sub('', ti.group(1))).strip() if ti else ''
        open(p, 'w', encoding='utf-8').write(url + '\n' + title + '\n\n' + txt)
        meta.append(dict(city=city, url=url, title=title, file=os.path.basename(p), chars=len(txt)))
        ok += 1

json.dump(meta, open('C:/Users/kevin/workspace/fukuoka/research/regional_meta.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('saved', ok, 'articles')
from collections import Counter
for c, n in sorted(Counter(m['city'] for m in meta).items()):
    print('  %-12s %d' % (c, n))
