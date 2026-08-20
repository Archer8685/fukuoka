"""Score every existing trip.js stop by corpus coverage."""
import glob, json, os, re

TXT = 'C:/Users/kevin/workspace/fukuoka/research/text'
trip = open('C:/Users/kevin/workspace/fukuoka/trip.js', encoding='utf-8').read()
i = trip.index('const BACKUPS')
main = trip[:i]

docs = {}
for f in sorted(glob.glob(TXT + '/b*.txt')):
    docs[os.path.basename(f)[:-4]] = open(f, encoding='utf-8').read()
vm = json.load(open('C:/Users/kevin/workspace/fukuoka/research/raw/videos_meta.json', encoding='utf-8'))
for v in vm:
    docs['VID_' + v['key']] = (v.get('title') or '') + '\n' + (v.get('desc') or '')

# dedupe
seen, uniq = set(), {}
for k, t in docs.items():
    h = hash(t[:4000])
    if h in seen:
        continue
    seen.add(h)
    uniq[k] = t
docs = uniq
N = len(docs)

# parse day / stop structure
days = re.findall(r'\{d:(\d+), date:"([^"]+)", wd:"([^"]+)", city:"([^"]+)", title:"([^"]*)"(.*?)\n \]\}', main, re.S)
STOP = re.compile(r'\{t:"([^"]+)", kind:"([^"]+)", name:"([^"]+)", label:"([^"]*)"')

# short search keys for names that need trimming
KEYMAP = {
    '天麩羅処 ひらお（天神店）': ['ひらお'],
    'Loopwheeler 福岡': ['Loopwheeler'],
    'DICE & DICE': ['DICE'],
    'KAPITAL 福岡': ['KAPITAL'],
    'Kaddish': ['Kaddish'],
    '#FR2 福岡': ['#FR2', 'FR2'],
    '中洲屋台街': ['中洲屋台', '屋台'],
    '豪斯登堡 園內美食': ['豪斯登堡'],
    '多姆托倫展望塔': ['多姆托倫', 'ドムトールン'],
    '光之王國（燈海）': ['光之王國', '光の王国'],
    'NEPENTHES HAKATA': ['NEPENTHES'],
    'かろのうろん': ['かろのうろん'],
    'Sanrio Gallery 運河城博多店': ['Sanrio Gallery', '三麗鷗'],
    'JUMP SHOP 福岡店': ['JUMP SHOP'],
    'LIGHT YEARS': ['LIGHT YEARS'],
    '博多 魚蔵（都ホテル博多）': ['魚蔵'],
    '銀河鐵道999 星野鐵郎銅像': ['星野鐵郎', '銀河鐵道999', '松本零士'],
    'あるあるCity': ['あるあるCity', 'あるあるシティ'],
    '關門海峽博物館': ['關門海峽博物館', '海峽博物館'],
    'BEAR FRUITS（燒咖哩）': ['BEAR FRUITS', '燒咖哩', '焗烤咖'],
    '割烹 とし': ['割烹 とし', '卓袱'],
    '長崎燈會 湊公園會場': ['湊公園', '燈會'],
    '長崎濱町商店街': ['濱町', '浜町'],
    '大阪屋 浜町店': ['大阪屋'],
    '吉宗 本店': ['吉宗', '茶碗蒸'],
    '長崎原爆資料館': ['原爆資料館'],
    '孔子廟・中國歷代博物館': ['孔子廟'],
    '福砂屋 本店': ['福砂屋'],
    '稻佐山展望台': ['稻佐山', '稲佐山'],
    '長崎燈會 中央公園會場': ['中央公園', '燈會'],
    '由布まぶし 心': ['由布まぶし', 'まぶし'],
    'B-speak': ['B-speak', 'P-roll'],
    'COMICO ART MUSEUM YUFUIN': ['COMICO'],
    '空想之森 アルテジオ': ['アルテジオ', '空想之森'],
    '茶房 天井棧敷': ['天井棧敷', '天井桟敷'],
    '寶可夢中心 福岡': ['寶可夢中心', 'Pokémon Center', '寶可夢'],
    'かさの家（梅ヶ枝餅）': ['かさの家'],
    'もつ鍋 極味や 福岡赤坂店': ['極味や', '極味屋'],
    '三麗鷗角色夢幻樂園': ['三麗鷗', 'サンリオ'],
    '博多めんたいやまや食堂 MARK IS 福岡ももち店': ['やまや'],
    'MARK IS 福岡ももち': ['MARK IS'],
    'ららぽーと福岡': ['ららぽーと', 'LaLaport', '啦啦寶都'],
    '鋼彈公園福岡': ['鋼彈公園', 'GUNDAM SIDE-F', 'SIDE-F'],
    '實物大 ν 鋼彈立像': ['ν 鋼彈', 'ν鋼彈', 'RX-93', '鋼彈立像'],
    'とり田 博多本店': ['とり田'],
    '柳川雛祭 さげもんめぐり': ['雛祭', 'さげもん'],
    '柳川川下り 松月乘船場': ['柳川川下', '柳川遊船', 'こたつ舟'],
    '若松屋（鰻魚蒸籠飯）': ['若松屋'],
    '御花（立花氏庭園）': ['御花'],
    '天神・天神地下街': ['天神地下街'],
    'animate 福岡PARCO店': ['animate', 'アニメイト'],
    'VIORO': ['VIORO'],
    '博多 喜多郎寿し': ['喜多郎'],
    'BIOTOP 福岡': ['BIOTOP'],
    '工藝風向': ['工藝風向', '工芸風向'],
    'F.I.L. FUKUOKA（visvim）': ['F.I.L', 'visvim'],
    'HUES': ['HUES'],
    '河太郎 中洲本店': ['河太郎', '活イカ', '活花枝'],
    'ふくや 中洲本店': ['ふくや'],
    '博多川端商店街': ['川端商店街', '川端通'],
    '福岡城跡・舞鶴公園': ['福岡城', '舞鶴公園'],
    '大濠公園': ['大濠公園'],
    '宇奈岐日女神社': ['宇奈岐日女'],
    '佛山寺': ['佛山寺', '仏山寺'],
    '湯之坪街道': ['湯之坪', '湯の坪'],
    '金鱗湖': ['金鱗湖'],
    '唐戶市場': ['唐戶市場', '唐戸市場'],
    '赤間神宮': ['赤間神宮'],
    '門司港站': ['門司港站', '門司港駅'],
    '門司港復古區': ['門司港'],
    '舊門司三井俱樂部': ['三井俱樂部', '三井倶楽部'],
    '櫛田神社': ['櫛田神社'],
    '東長寺': ['東長寺', '福岡大佛'],
    '博多運河城': ['運河城', 'Canal City'],
    '出島': ['出島'],
    '眼鏡橋': ['眼鏡橋'],
    '興福寺': ['興福寺'],
    '崇福寺': ['崇福寺'],
    '荷蘭坂': ['荷蘭坂', 'オランダ坂'],
    '大浦天主堂': ['大浦天主堂'],
    '哥拉巴園': ['哥拉巴園', 'グラバー園'],
    '四海樓': ['四海樓'],
    '長崎新地中華街': ['新地中華街', '長崎中華街'],
    '平和公園': ['平和公園', '和平公園'],
    '九州國立博物館': ['九州國立博物館', '九州国立博物館', '九博'],
    '太宰府天滿宮': ['太宰府天滿宮', '太宰府天満宮'],
    '豪斯登堡': ['豪斯登堡', 'ハウステンボス'],
}

SKIP_KIND = {'hotel', 'move'}
rows = []
for d, date, wd, city, title, body in days:
    for t, kind, name, label in STOP.findall(body):
        if kind in SKIP_KIND:
            continue
        keys = KEYMAP.get(name, [name])
        hits = sum(1 for tx in docs.values() if any(k in tx for k in keys))
        rows.append((int(d), date, wd, t, kind, name, label, hits))

rows.sort(key=lambda r: r[7])
print('corpus N = %d docs\n' % N)
print('docs  day  time   kind   name')
for d, date, wd, t, kind, name, label, hits in rows:
    print('%3d   %s(%s) %s %-5s %s   %s' % (hits, date, wd, t, kind, name, label))
json.dump(rows, open('C:/Users/kevin/workspace/fukuoka/research/trip_scores.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
