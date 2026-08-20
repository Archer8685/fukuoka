"""Cross-check ranked hot spots against the actual trip.js itinerary."""
import json, re

stats = json.load(open('C:/Users/kevin/workspace/fukuoka/research/spot_stats.json', encoding='utf-8'))
trip = open('C:/Users/kevin/workspace/fukuoka/trip.js', encoding='utf-8').read()

# split trip.js into TRIP section and BACKUPS section
i = trip.index('const BACKUPS')
trip_main, trip_backup = trip[:i], trip[i:]

SPOT_ALIASES = {
    '太宰府天滿宮': ['太宰府天滿宮'], '柳川遊船': ['柳川川下', '柳川雛祭'],
    '中洲屋台': ['中洲屋台'], '門司港懷舊區': ['門司港復古區', '門司港站'],
    '梅枝餅': ['梅ヶ枝餅'], '一蘭拉麵': ['一蘭'], '福岡塔': ['福岡塔'],
    '博多運河城': ['博多運河城'], '大濠公園': ['大濠公園'], '博多站/阪급': ['博多站'],
    '博多站/阪急': ['博多站', '阪急'], '天神地下街': ['天神地下街'],
    '櫛田神社': ['櫛田神社'], 'マリンワールド海之中道': ['マリンワールド', '海之中道'],
    '明太子': ['ふくや', '明太子'], '小倉城': ['小倉城'],
    '關門海峽/人行海底隧道': ['關門海峽'], '糸島': ['糸島'],
    'teamLab Forest': ['teamLab'], '竈門神社': ['竈門神社'],
    '福岡城跡': ['福岡城'], 'LaLaport福岡': ['ららぽーと福岡'],
    '阿蘇火山': ['阿蘇'], 'BOSS E・ZO FUKUOKA': ['BOSS E・ZO'],
    '柳川蒸籠鰻魚飯': ['若松屋', '本吉屋'], '九州國立博物館': ['九州國立博物館'],
    '牛腸鍋(もつ鍋)': ['もつ鍋'], '能古島': ['能古島'], '櫻井二見浦': ['二見浦'],
    '豪斯登堡': ['豪斯登堡'], '唐戶市場': ['唐戶市場'], '黑川溫泉': ['黑川溫泉'],
    '高千穗峽': ['高千穗'], '皿倉山': ['皿倉山'],
    '天神大丸/三越/PARCO': ['PARCO', 'VIORO'], 'ゆふいんの森': ['ゆふいんの森'],
    '藥院/白金': ['藥院'], 'PayPay巨蛋': ['PayPay', '福岡巨蛋'],
    '御花': ['御花'], '水炊雞湯鍋': ['水炊'],
    '三麗鷗彩虹樂園/HARMONYLAND': ['三麗鷗角色夢幻樂園', 'ハーモニーランド'],
    '川端商店街': ['川端商店街'], '旦過市場': ['旦過市場'],
    '東長寺': ['東長寺'], '宮地嶽神社': ['宮地嶽'], '住吉神社': ['住吉神社'],
    '舊門司三井俱樂部': ['三井俱樂部'], '南藏院': ['南藏院'],
    '呼子/唐津': ['呼子', '唐津'], '福岡市美術館': ['福岡市美術館'],
    '由布院金鱗湖': ['金鱗湖'], '熊本城': ['熊本城'], '嬉野溫泉': ['嬉野'],
    '湯之坪街道': ['湯之坪'], '白絲瀑布': ['白絲'],
    '博多利久牛舌': ['利久'], '河豚': ['河豚'], '河内藤園': ['河内藤園', '河內藤園'],
    '別府地獄巡禮': ['地獄巡', '海地獄'], '軍艦島': ['軍艦島'],
    '稻佐山夜景': ['稻佐山'], '志賀島': ['志賀島'], '天開稻荷社': ['天開稻荷'],
    '海濱百道公園': ['海濱百道', '百道濱'], '祐德稻荷神社': ['祐德稻荷'],
    '警固神社': ['警固神社'], '光明禪寺': ['光明禪寺'], '一幸舍': ['一幸舍'],
    'かさの家': ['かさの家'], 'Shin Shin拉麵': ['Shin-Shin'],
    '日田豆田町': ['豆田町', '日田'], '博多町家鄉土館': ['博多町家'],
    '角島大橋': ['角島'], '赤間神宮': ['赤間神宮'], '元乃隅神社': ['元乃隅'],
    'MARK IS 福岡ももち': ['MARK IS'], '別府纜車/鶴見岳': ['鶴見岳'],
    '草千里': ['草千里'], '北九州漫畫博物館': ['漫畫博物館'],
    '福岡市博物館': ['福岡市博物館'], '牡蠣小屋': ['牡蠣小屋'],
    '和平公園/原爆資料館': ['平和公園', '原爆資料館'], '眼鏡橋': ['眼鏡橋'],
    '九重夢大吊橋': ['九重'], '極味屋漢堡排': ['極味や'],
    '天婦羅ひらお': ['ひらお'], '承天寺': ['承天寺'],
    '長崎哥拉巴園': ['哥拉巴園'], '大浦天主堂': ['大浦天主堂'],
    '出島': ['出島'], '長崎新地中華街': ['新地中華街'],
    '長崎燈會': ['長崎燈會'], '吉野里遺跡': ['吉野'],
    '住吉/樂天地': ['樂天地'], '香椎宮': ['香椎宮'],
    '水鏡天滿宮': ['水鏡天滿宮'], '赤煉瓦文化館': ['赤煉瓦'],
    'PALM BEACH/天使之翼': ['PALM BEACH'], '芥屋大門': ['芥屋'],
    '由布院floral village': ['Floral Village'],
    'Fukuoka Open Top Bus': ['Open Top Bus'], '海響館': ['海響館'],
    '警固/今泉': ['今泉'], '福岡市郊': [],
}

rows = [r for r in stats['rows'] if r['docs'] >= 4]
out = []
for r in rows:
    al = SPOT_ALIASES.get(r['name'], [r['name']])
    in_trip = any(a in trip_main for a in al if a)
    in_bk = any(a in trip_backup for a in al if a)
    state = 'IN_TRIP' if in_trip else ('BACKUP' if in_bk else 'MISSING')
    out.append((state, r['docs'], r['mentions'], r['area'], r['name']))

print('=== MISSING (熱門但完全沒出現) ===')
for s, d, m, a, n in out:
    if s == 'MISSING':
        print('  docs=%2d  %-10s %s' % (d, a, n))
print()
print('=== BACKUP ONLY (只在備選清單) ===')
for s, d, m, a, n in out:
    if s == 'BACKUP':
        print('  docs=%2d  %-10s %s' % (d, a, n))
print()
print('=== IN_TRIP (已排) ===')
c = [n for s, d, m, a, n in out if s == 'IN_TRIP']
print('  %d 個: %s' % (len(c), '、'.join(c)))
json.dump(out, open('C:/Users/kevin/workspace/fukuoka/research/crosscheck.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
