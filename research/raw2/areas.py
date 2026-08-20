"""Group trip stops into walkable AREAS and count areas per day (max 3)."""
import re, json

t = open('C:/Users/kevin/workspace/fukuoka/trip.js', encoding='utf-8').read()
main = t[:t.index('const BACKUPS')]
days = re.findall(r'\{d:(\d+), date:"([^"]+)", wd:"([^"]+)", city:"([^"]+)", title:"([^"]*)"(.*?)\n \]\}',
                  main, re.S)
STOP = re.compile(r'\{t:"([^"]+)", kind:"([^"]+)", name:"([^"]+)", label:"([^"]*)"')

sc = json.load(open('C:/Users/kevin/workspace/fukuoka/research/trip_scores2.json', encoding='utf-8'))
score = {r['name']: r['hits'] for rows in sc.values() for r in rows}

# name -> walkable area cluster
AREA = {
    # 福岡市內
    '天麩羅処 ひらお（天神店）': '天神', '天神・天神地下街': '天神',
    'VIORO': '天神', 'animate 福岡PARCO店': '天神',
    'DICE & DICE': '大名今泉', 'KAPITAL 福岡': '大名今泉', 'Kaddish': '大名今泉',
    '#FR2 福岡': '大名今泉', 'Loopwheeler 福岡': '藥院',
    'BIOTOP 福岡': '赤坂警固', '工藝風向': '赤坂警固',
    'F.I.L. FUKUOKA（visvim）': '赤坂警固', 'HUES': '赤坂警固',
    'もつ鍋 極味や 福岡赤坂店': '赤坂警固',
    '櫛田神社': '博多寺町', '東長寺': '博多寺町', 'かろのうろん': '博多寺町',
    '博多川端商店街': '博多寺町', 'ふくや 中洲本店': '中洲', '河太郎 中洲本店': '中洲',
    '中洲屋台街': '中洲', 'NEPENTHES HAKATA': '博多站', 'LIGHT YEARS': '博多站',
    '博多 魚蔵（都ホテル博多）': '博多站', '博多 喜多郎寿し': '博多站',
    'とり田 博多本店': '博多站', '寶可夢中心 福岡': '博多站',
    '博多運河城': '運河城', 'Sanrio Gallery 運河城博多店': '運河城',
    'JUMP SHOP 福岡店': '運河城',
    '福岡城跡・舞鶴公園': '大濠', '大濠公園': '大濠', '福岡市美術館': '大濠',
    '三麗鷗角色夢幻樂園': '百道', 'MARK IS 福岡ももち': '百道',
    '博多めんたいやまや食堂 MARK IS 福岡ももち店': '百道',
    'teamLab Forest': '百道', '福岡塔': '百道',
    'ららぽーと福岡': '竹下', '鋼彈公園福岡': '竹下', '實物大 ν 鋼彈立像': '竹下',
    '住吉神社': '博多站',
    # 太宰府
    '九州國立博物館': '太宰府', '太宰府天滿宮': '太宰府', 'かさの家（梅ヶ枝餅）': '太宰府',
    '竈門神社': '太宰府', '天開稻荷社': '太宰府',
    # 柳川
    '柳川雛祭 さげもんめぐり': '柳川', '柳川川下り 松月乘船場': '柳川',
    '御花（立花氏庭園）': '柳川', '若松屋（鰻魚蒸籠飯）': '柳川',
    # 北九州 / 下關
    '赤間神宮': '下關', '唐戶市場': '下關',
    '門司港站': '門司港', '門司港復古區': '門司港', '舊門司三井俱樂部': '門司港',
    '關門海峽博物館': '門司港', 'BEAR FRUITS（燒咖哩）': '門司港',
    '九州鐵道紀念館': '門司港',
    '銀河鐵道999 星野鐵郎銅像': '小倉站', 'あるあるCity': '小倉站',
    '小倉城': '小倉城', '旦過市場': '小倉城', '皿倉山': '皿倉山',
    # 長崎
    '豪斯登堡': '豪斯登堡', '豪斯登堡 園內美食': '豪斯登堡',
    '多姆托倫展望塔': '豪斯登堡', '光之王國（燈海）': '豪斯登堡',
    '割烹 とし': '長崎中心', '出島': '長崎中心', '眼鏡橋': '長崎中心',
    '長崎濱町商店街': '長崎中心', '長崎燈會 湊公園會場': '長崎中心',
    '長崎新地中華街': '長崎中心', '大阪屋 浜町店': '長崎中心',
    '福砂屋 本店': '長崎中心', '長崎燈會 中央公園會場': '長崎中心',
    '吉宗 本店': '長崎中心', '興福寺': '寺町', '崇福寺': '寺町',
    '大浦天主堂': '南山手', '哥拉巴園': '南山手', '荷蘭坂': '南山手',
    '孔子廟・中國歷代博物館': '南山手', '四海樓': '南山手',
    '稻佐山展望台': '稻佐山',
    '平和公園': '浦上', '長崎原爆資料館': '浦上',
    # 由布院
    '金鱗湖': '由布院', '佛山寺': '由布院', '宇奈岐日女神社': '由布院',
    '湯之坪街道': '由布院', 'COMICO ART MUSEUM YUFUIN': '由布院',
    '空想之森 アルテジオ': '由布院', '茶房 天井棧敷': '由布院',
    '由布まぶし 心': '由布院', 'B-speak': '由布院',
    # 熊本
    '熊本城': '熊本城', '櫻之馬場城彩苑': '熊本城', '加藤神社': '熊本城',
    '熊本熊部長辦公室': '上下通', '上下通商店街': '上下通', '水前寺成趣園': '水前寺',
}

print('=== 現行行程：每日「地區」數 ===\n')
for d, date, wd, city, title, body in days:
    st = [(tt, k, n, l) for tt, k, n, l in STOP.findall(body) if k not in ('hotel', 'move')]
    areas = []
    for tt, k, n, l in st:
        a = AREA.get(n, '?' + n)
        if a not in areas:
            areas.append(a)
    flag = '  <<< 超過 3 地區' if len(areas) > 3 else ''
    print('D%-3s %s(%s) [%s]  %d 地區%s' % (d, date, wd, city, len(areas), flag))
    for a in areas:
        pts = [(n, score.get(n, 0), k) for tt, k, n, l in st if AREA.get(n, '?' + n) == a]
        tot = sum(p[1] for p in pts)
        print('      %-8s (%d站/%d分)  %s' % (
            a, len(pts), tot, '、'.join('%s%d' % (n, s) for n, s, k in pts)))
    print()
