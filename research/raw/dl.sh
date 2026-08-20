UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
xargs -P 8 -n 2 -a <(tr '\t' '\n' < urls.tsv) sh -c 'curl -sL --compressed -A "'"$UA"'" -H "Accept-Language: zh-TW,zh;q=0.9" "$1" --max-time 40 -o "$0.html"'
