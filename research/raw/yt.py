import json, urllib.request, concurrent.futures, gzip, re

VIDS = {
 "v01":"3UiKacxKyp8","v02":"fe4Eockm0HM","v03":"LpFSGtGw4X8","v04":"TJ76g5dchXs",
 "v05":"coiQ_4N3NAs","v06":"errXoxUmayE","v07":"igPlAUM7q7g","v08":"RkmqlLMywxM",
 "v09":"ldDw7eOJBno","v10":"4CKO_2N9A-Y","v11":"etTr7qwqaSc","v12":"fCPx7np0R4Q",
 "v13":"IpgjBsrd-rA","v14":"pf9D-PE8YEs","v15":"VXLt0wwNgbw",
}
json.dump(VIDS, open('videos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36'

RE_TITLE = re.compile(r'"title":"((?:[^"' + '\\\\' + r']|' + '\\\\' + r'.)*)"')
RE_DATE = re.compile(r'"uploadDate":"([^"]+)"')
RE_VIEWS = re.compile(r'"viewCount":"(\d+)"')
RE_CH = re.compile(r'"ownerChannelName":"([^"]*)"')
RE_DESC = re.compile(r'"shortDescription":"(.*?)","isCrawlable"', re.S)


def fetch(kv):
    k, vid = kv
    try:
        req = urllib.request.Request(
            'https://www.youtube.com/watch?v=' + vid,
            headers={'User-Agent': UA, 'Accept-Language': 'zh-TW', 'Accept-Encoding': 'gzip'})
        raw = urllib.request.urlopen(req, timeout=30).read()
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        t = raw.decode('utf-8', 'ignore')
        open(k + '_' + vid + '.html', 'w', encoding='utf-8').write(t)
        def g(rx, d='?'):
            m = rx.search(t)
            return m.group(1) if m else d
        desc = g(RE_DESC, '')
        desc = desc.encode().decode('unicode_escape', 'ignore') if desc else ''
        return dict(key=k, vid=vid, title=g(RE_TITLE), date=g(RE_DATE)[:10],
                    views=g(RE_VIEWS), channel=g(RE_CH), desc=desc[:1500])
    except Exception as e:
        return dict(key=k, vid=vid, title='ERR ' + str(e)[:60])


res = []
with concurrent.futures.ThreadPoolExecutor(6) as ex:
    for r in ex.map(fetch, VIDS.items()):
        res.append(r)
        print(r['key'], '|', r['vid'], '|', r.get('date'), '|', r.get('views'), '|', r.get('channel'), '|', r['title'][:80])

json.dump(res, open('videos_meta.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
