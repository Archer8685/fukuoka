"""Expanded search via urllib (no bash dependency)."""
import urllib.request, urllib.parse, gzip, json, re, os, time

D = 'C:/Users/kevin/workspace/fukuoka/research/raw2'
os.makedirs(D, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'

QUERIES = [
    ('kumamoto', '熊本 自由行 景點 攻略 2025'),
    ('kagoshima', '鹿兒島 自由行 景點 攻略'),
    ('nagasaki', '長崎 自由行 景點 攻略 2025'),
    ('sasebo', '佐世保 豪斯登堡 景點 攻略'),
    ('saga', '佐賀 自由行 景點 攻略'),
    ('karatsu', '唐津 呼子 一日遊 景點'),
    ('ureshino', '嬉野溫泉 武雄溫泉 一日遊'),
    ('beppu', '別府 溫泉 地獄巡 攻略'),
    ('yufuin', '由布院 湯布院 一日遊 攻略 2025'),
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
    ('yanagawa2', '柳川 太宰府 一日遊 攻略 2025'),
]

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': UA,
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-TW,zh;q=0.9,ja;q=0.8',
                'Accept-Encoding': 'gzip',
            })
            with urllib.request.urlopen(req, timeout=35) as r:
                raw = r.read()
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return raw.decode('utf-8', 'ignore')
        except Exception as e:
            if i == tries - 1:
                return 'ERR ' + str(e)
            time.sleep(8)
    return ''

BAD = re.compile(r'brave|torproject|hackerone|duckduckgo|bing\.com|google\.|/images/|\.(png|jpe?g|css|js|svg|ico|webp)($|\?)')
results = {}
for key, q in QUERIES:
    enc = urllib.parse.quote(q)
    h = fetch('https://search.brave.com/search?q=' + enc)
    open(D + '/' + key + '.html', 'w', encoding='utf-8').write(h)
    links = [l for l in sorted(set(re.findall(r'href="(https?://[^"]+)"', h))) if not BAD.search(l)]
    results[key] = dict(query=q, links=links)
    print('%-12s %2d links | %s' % (key, len(links), q))
    time.sleep(5)

json.dump(results, open(D + '/search.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\ntotal unique:', len({l for v in results.values() for l in v['links']}))
