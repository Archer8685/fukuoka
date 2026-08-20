"""Pull real sentences about candidate spots from the corpus."""
import glob, json, os, re

TXT = 'C:/Users/kevin/workspace/fukuoka/research/text'

TARGETS = {
    '小倉城': ['小倉城'],
    'teamLab Forest': ['teamLab', 'チームラボ'],
    '能古島': ['能古島', 'のこのしま'],
    '皿倉山': ['皿倉山'],
    '住吉神社': ['住吉神社'],
    '天開稻荷社': ['天開稻荷', '天開稲荷'],
    '福岡塔': ['福岡塔'],
    'マリンワールド海之中道': ['マリンワールド', '海洋世界', '海之中道', '海の中道'],
    '竈門神社': ['竈門神社', '竃門神社', '寶滿宮'],
    '福岡市美術館': ['福岡市美術館'],
    '宮地嶽神社': ['宮地嶽', '宮地岳'],
    '旦過市場': ['旦過市場'],
    '南藏院': ['南藏院', '南蔵院', '涅槃'],
}

docs = {}
for f in sorted(glob.glob(TXT + '/b*.txt')):
    docs[os.path.basename(f)[:-4]] = open(f, encoding='utf-8').read()

SPLIT = re.compile(r'[\n。！？!?]')

result = {}
for name, aliases in TARGETS.items():
    snips, seen = [], set()
    for k, t in docs.items():
        for part in SPLIT.split(t):
            p = part.strip()
            if not (20 < len(p) < 220):
                continue
            if any(a in p for a in aliases):
                key = p[:40]
                if key in seen:
                    continue
                seen.add(key)
                snips.append((k, p))
    result[name] = snips[:14]

json.dump(result, open('C:/Users/kevin/workspace/fukuoka/research/spot_snippets.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

for name, snips in result.items():
    print('\n' + '=' * 12 + ' ' + name + ' (' + str(len(snips)) + ' snippets) ' + '=' * 12)
    for k, p in snips:
        print(' [' + k[:14] + '] ' + p)
