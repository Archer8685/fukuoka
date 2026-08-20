"""Extract Kumamoto day-trip feasibility evidence from the corpus."""
import glob, os, re

FILES = sorted(glob.glob('C:/Users/kevin/workspace/fukuoka/research/text2/kumamoto*.txt')) + \
        sorted(glob.glob('C:/Users/kevin/workspace/fukuoka/research/text2/kyushu2h*.txt')) + \
        sorted(glob.glob('C:/Users/kevin/workspace/fukuoka/research/text2/aso*.txt')) + \
        sorted(glob.glob('C:/Users/kevin/workspace/fukuoka/research/text/*.txt'))

SPLIT = re.compile(r'[\n。！？!?]')

# what we need: transport time, day-trip phrasing, opening hours, spot clusters
PATS = {
    'TRANSPORT': re.compile(r'熊本.{0,30}(新幹線|櫻島號|さくら|みずほ|巴士|高速バス).{0,40}(分|小時|鐘)|'
                            r'(新幹線|高速バス|高速巴士).{0,30}熊本.{0,30}(分|小時)'),
    'DAYTRIP':   re.compile(r'熊本.{0,20}(一日遊|一日|日歸|當天往返|來回)|'
                            r'(博多|福岡).{0,15}熊本.{0,20}(一日|日歸)'),
    'CASTLE':    re.compile(r'熊本城.{0,60}(開|閉|時間|門票|入園|天守|復原|特別)'),
    'KUMAMON':   re.compile(r'(熊本熊|くまモン|KUMAMON).{0,60}(辦公室|部長|廣場|スクエア|表演|時間)'),
    'CLUSTER':   re.compile(r'熊本.{0,10}(景點|行程).{0,80}'),
    'SUIZENJI':  re.compile(r'水前寺.{0,60}'),
    'ASODAY':    re.compile(r'阿蘇.{0,20}(一日遊|一日|包車|租車|JR|巴士).{0,40}'),
}

found = {k: [] for k in PATS}
for f in FILES:
    tag = os.path.basename(f)[:-4][:22]
    txt = open(f, encoding='utf-8').read()
    for part in SPLIT.split(txt):
        p = ' '.join(part.split())
        if not (12 < len(p) < 240):
            continue
        for k, rx in PATS.items():
            if rx.search(p):
                key = p[:45]
                if key not in [x[1][:45] for x in found[k]]:
                    found[k].append((tag, p))

for k in PATS:
    print('\n' + '=' * 16 + ' ' + k + ' (' + str(len(found[k])) + ') ' + '=' * 16)
    for tag, p in found[k][:16]:
        print(' [' + tag + '] ' + p)
