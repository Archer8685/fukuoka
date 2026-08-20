"""Extract readable text from downloaded blog HTML files."""
import glob, os, re, html, json

OUT = 'C:/Users/kevin/workspace/fukuoka/research/text'
os.makedirs(OUT, exist_ok=True)

SCRIPT_RE = re.compile(r'<(script|style|noscript|svg|iframe)\b.*?</\1>', re.S | re.I)
TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'[ \t\xa0]+')
NL_RE = re.compile(r'\n{3,}')
TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.S | re.I)
DATE_RES = [
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"'),
    re.compile(r'property="article:published_time"\s+content="([^"]+)"'),
    re.compile(r'content="([^"]+)"\s+property="article:published_time"'),
    re.compile(r'"dateModified"\s*:\s*"([^"]+)"'),
]

rows = []
for f in sorted(glob.glob('C:/Users/kevin/workspace/fukuoka/research/raw/b*_*.html')):
    key = os.path.basename(f)[:-5]
    raw = open(f, encoding='utf-8', errors='ignore').read()
    title = TITLE_RE.search(raw)
    title = html.unescape(TAG_RE.sub('', title.group(1))).strip() if title else '?'
    date = '?'
    for rx in DATE_RES:
        m = rx.search(raw)
        if m:
            date = m.group(1)[:10]
            break
    body = SCRIPT_RE.sub(' ', raw)
    body = re.sub(r'<br\s*/?>|</p>|</div>|</h\d>|</li>', '\n', body, flags=re.I)
    body = TAG_RE.sub(' ', body)
    body = html.unescape(body)
    body = WS_RE.sub(' ', body)
    body = '\n'.join(ln.strip() for ln in body.split('\n') if ln.strip())
    body = NL_RE.sub('\n\n', body)
    open(os.path.join(OUT, key + '.txt'), 'w', encoding='utf-8').write(
        'TITLE: ' + title + '\nDATE: ' + date + '\n\n' + body)
    rows.append(dict(key=key, title=title, date=date, chars=len(body)))
    print(key, '|', date, '|', len(body), '|', title[:70])

json.dump(rows, open('C:/Users/kevin/workspace/fukuoka/research/blog_meta.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
