"""Retry the rate-limited queries with long backoff; fall back to DuckDuckGo lite."""
import urllib.request, urllib.parse, gzip, json, re, os, time, random

D = 'C:/Users/kevin/workspace/fukuoka/research/raw2'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

REMAIN = [
    ('sasebo', '佐世保 豪斯登堡 景點 攻略'),
    ('saga', '佐賀 自由行 景點 攻略'),
    ('karatsu', '唐津 呼子 一日遊 景點'),
    ('ureshino', '嬉野溫泉 武雄溫泉 一日遊'),
    ('beppu', '別府 溫泉 地獄巡 攻略'),
    ('yufuin', '由布院 湯布院 一日遊 攻略'),
    ('oita', '大分 自由行 景點 攻略'),
    ('shimonoseki', '下關 唐戶市場 一日遊'),
    ('yamaguchi', '山口 角島 元乃隅 自由行 攻略'),
    ('kitakyushu', '北九州 小倉 一日遊 景點 攻略'),
    ('aso', '阿蘇 黑川溫泉 一日遊 攻略'),
    ('shimabara', '島原 雲仙 一日遊 景點'),
    ('hita', '日田 豆田町 一日遊'),
    ('kurume', '久留米 八女 近郊 景點'),
    ('kyushu2h', '博多 出發 一日遊 近郊 推薦'),
    ('takeo', '武雄 有田 陶瓷 一日遊'),
    ('yanagawa2', '柳川 太宰府 一日遊 攻略'),
]

def fetch(url, referer=None):
    hdr = {'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml',
           'Accept-Language': 'zh-TW,zh;q=0.9,ja;q=0.8', 'Accept-Encoding': 'gzip'}
    if referer:
        hdr['Referer'] = referer
    try:
        req = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(req, timeout=35) as r:
            raw = r.read()
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        return raw.decode('utf-8', 'ignore')
    except Exception as e:
        return 'ERR ' + str(e)

def ddg(q):
    """DuckDuckGo html endpoint via POST."""
    data = urllib.parse.urlencode({'q': q, 'kl': 'tw-tzh'}).encode()
    req = urllib.request.Request('https://html.duckduckgo.com/html/', data=data, headers={
        'User-Agent': UA, 'Accept': 'text/html', 'Accept-Language': 'zh-TW,zh;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded', 'Accept-Encoding': 'gzip',
        'Origin': 'https://html.duckduckgo.com', 'Referer': 'https://html.duckduckgo.com/'})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            raw = r.read()
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        return raw.decode('utf-8', 'ignore')
    except Exception as e:
        return 'ERR ' + str(e)

BAD = re.compile(r'brave|torproject|hackerone|duckduckgo|bing\.com|google\.|/images/|'
                 r'\.(png|jpe?g|css|js|svg|ico|webp)($|\?)')

def extract(h):
    out = []
    for l in sorted(set(re.findall(r'href="(https?://[^"]+)"', h))):
        if 'uddg=' in l:  # ddg redirect wrapper
            m = re.search(r'uddg=([^&]+)', l)
            if m:
                l = urllib.parse.unquote(m.group(1))
        if not BAD.search(l):
            out.append(l)
    return sorted(set(out))

search = json.load(open(D + '/search.json', encoding='utf-8'))
for key, q in REMAIN:
    got = []
    # try brave with long sleep
    time.sleep(random.uniform(25, 35))
    h = fetch('https://search.brave.com/search?q=' + urllib.parse.quote(q),
              referer='https://search.brave.com/')
    got = extract(h)
    src = 'brave'
    if len(got) < 5:
        time.sleep(random.uniform(6, 10))
        h = ddg(q)
        got = extract(h)
        src = 'ddg'
    open(D + '/' + key + '.html', 'w', encoding='utf-8').write(h)
    search[key] = dict(query=q, links=got, src=src)
    print('%-12s %2d links (%s) | %s' % (key, len(got), src, q))

json.dump(search, open(D + '/search.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\ntotal unique:', len({l for v in search.values() for l in v['links']}))
