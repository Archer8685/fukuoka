// 地圖底圖設定
//
// 預設底圖是「國土地理院」——官方、免金鑰、日本境內細節最好，不需要任何設定。
// 想改用 Google Map 當底圖，把你的 Google Maps JavaScript API 金鑰填進下面這行即可，
// 地圖右上角的圖層選單就會多出「Google 道路 / Google 衛星 / Google 地形」三個選項。
//
// 取得金鑰：
//   1. https://console.cloud.google.com/ 建立專案
//   2. 啟用「Maps JavaScript API」
//   3. 建立 API 金鑰
//   4. ⚠️ 一定要加「HTTP 參照網址」限制，只允許你自己的網域，例如：
//        https://archer8685.github.io/fukuoka/*
//        http://localhost:5173/*
//      這個金鑰會出現在網頁原始碼裡（靜態網站無法隱藏），
//      沒加限制別人撿去用會算在你的帳單上。
//   5. 再加「API 限制」只允許 Maps JavaScript API。
//
// ⚠️ 計費：Maps JavaScript API 需要在 Google Cloud 綁信用卡才會發金鑰。
//    個人行程網站的用量遠低於免費額度，實務上不會產生費用，但帳號本身要有計費設定。
//
// ⚠️ Google 圖磚不能離線快取（違反服務條款），
//    所以選 Google 底圖時「離線預載此區地圖」按鈕會停用；
//    要離線用請切回國土地理院或 OpenStreetMap。

const GMAPS_KEY = "AIzaSyDNfqqy0di91Cc-dXq-MtSVQ6N_t1AtGWg";
