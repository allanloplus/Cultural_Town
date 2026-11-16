# 鄉鎮文資性格卡

選一個鄉鎮市區，得到一張用文化資產資料算出來的「性格卡」，可以分享。是「Allan Lo 和你逛文化」的第五個姊妹站。

- 網址：https://cultural-town.123hi.org/
- 規劃設計：Allan Lo，https://www.123hi.org，2026年11月

| 網站 | 內容 | Repo |
|---|---|---|
| https://cultural.123hi.org/ | 文資知識網站第一站（13 縣市＋共用程式） | allanloplus/Cultural_Heritage |
| https://cultural2.123hi.org/ | 文資知識網站第二站（9 縣市） | allanloplus/Cultural_Heritage2 |
| https://cultural-visit.123hi.org/ | 文資達人訪查 | allanloplus/Cultural_Heritage_Master |
| https://cultural-atlas.123hi.org/ | 文資地圖集 | allanloplus/Cultural_Atlas |
| https://cultural-rail.123hi.org/ | 搭火車逛文資 | allanloplus/Cultural_Rail |
| https://cultural-town.123hi.org/ | 鄉鎮文資性格卡（本 repo） | allanloplus/Cultural_Town |

## 目前的進度

368 個鄉鎮市區的資料、固定網址頁、社群預覽圖與下載用卡片都已產生，首頁、類型總覽與說明也已完成。圖片共 736 張，約 111 MB（`og/` 42 MB、`card/` 69 MB）；GitHub Pages 每個網站上限 1 GB。

## 內容

- **首頁**（`/`）：文字搜尋、縣市與鄉鎮選單、「用我的位置」、隨便抽一張，以及 19 種類型的總覽。
- **鄉鎮頁**（`/t/<縣市>/<鄉鎮>/`，例如 `/t/tainan-city/west-central/`）：性格卡（類型、一句話、時代組成、類型組成）、Allan 與阿拉蕾的對話、代表文資（附照片）、最老的一處、意外的事實、無形文資、跟你最像的鄉鎮與鄰居、區內的臺鐵車站、「為什麼是這個類型」、全部文資清單。
- **類型總覽**（`/#/types`、`/#/types/OF`）：每一種類型有哪些鄉鎮。
- **說明**（`/#/about`）：算法、限制、資料來源。

每處文資連回知識網站的 `<縣市網址>/#map/<景點 id>`；有臺鐵車站的鄉鎮連到鐵道版的車站頁。

## 性格怎麼算

全部在 `tools/build.py`，門檻是檔案開頭的常數。

1. **主調**：每處文資歸到信仰／生活／產業／官方／考古其中一類。先看官方的建築類型（`TYPE_DOMAIN`）；類型是「其他設施」或空白的，改看知識網站的主題（`THEME_DOMAIN`，用關鍵字比對）。
2. **3 處以上（性格十二型）**：時代重心 × 主調。清領以前占 34% 以上且不少於戰後 →「清領以前」；否則戰後占 30% 以上 →「戰後」；其餘「日治」。主調取四類中處數最多的，同數時取相對全臺平均更突出的。
3. **1–2 處（獨苗系列，5 種）**：以一處當主角（古蹟優先，其次有照片、年代早），依主角的主調分類。
4. **0 處（留白系列，2 種）**：對得上無形文資的是「無形派掌門」，都沒有的是「等待被發現」。
5. **徽章**（不影響類型）：處數（30／10 處為界）與古蹟占比（3 處以上鄉鎮的上下四分位數，建置時重算）。

類型的名稱與一句話寫在 `TYPES`；卡片上其他句子（描述、事實、為什麼、對話）都由資料組出來：`describe()`、`facts()`、`why()`、`similar()`、`talk()`。阿拉蕾的俏皮話是 `QUIP` 裡的固定句子，依鄉鎮代稱固定挑一句。

- **意外的事實**：`facts()` 列出候選（全臺排名、全縣占比、某建築類型全臺最多、主調集中、時代單一、沒有古蹟、全是古蹟、國定古蹟數、全縣最老、鄰居反差、時間跨度等），各有分數，取最高的三則。
- **跟你最像的鄉鎮**：比時代比例、主調比例、古蹟比例與處數，優先找不同縣市、同類型的。
- **鄰居**：用鄉鎮界線的共用邊判斷；離島沒有陸地鄰居時取中心點最近的三個。
- **最近的文資**：直線距離；零文資的鄉鎮從行政區的幾何中心起算。

## 架構

純靜態網站，沒有後台與資料庫，沒有使用外部函式庫（字型與知識網站相同，取自 Google Fonts）。

```
index.html                    首頁（手寫；改頁首頁尾時要和 tools/town_template.html 一起改）
t/<縣市>/<鄉鎮>/index.html     每個鄉鎮的固定網址（build.py 產生，帶社群預覽用的 meta）
assets/css/town.css           樣式（配色、深色模式沿用鐵道版與知識網站的變數）
assets/js/town.js             畫面（不做任何性格計算）
assets/characters/            Allan 與阿拉蕾的圖檔（複製自 Cultural_Heritage，那邊更新時要再複製）
data/index.json               類型定義、縣市、368 個鄉鎮的索引
data/town/<縣市>/<鄉鎮>.json   每張卡的內容；`extra` 欄位是空的，預留給之後的單元（例如「人口與文資」）
data/towns-topo.json          鄉鎮界線，按「用我的位置」才下載
data/raw/                     抓一次就存檔的原始資料（鄉鎮清單、界線）
og/、card/                    社群預覽圖（1200×630）與下載用卡片（1080×1350）
reports/town-check.csv        座標與鄉鎮不一致的文資清單
tools/build.py                產生 data/、t/、reports/
tools/town_template.html      鄉鎮頁的樣板
tools/card.html、render.js    產生 og/、card/、assets/og.jpg
```

### 更新資料

知識網站或文資地圖集的資料有變動後（先在 Cultural_Atlas 跑過 `python3 tools/build_sites.py`）：

```bash
python3 tools/build.py
```

```bash
node tools/render.js
```

`build.py` 只用 Python 標準函式庫，會找本 repo 旁邊的 `Cultural_Atlas`、`Cultural_Heritage`、`Cultural_Heritage2`、`Cultural_Rail`（或用環境變數 `ATLAS_DIR`、`CH1_DIR`、`CH2_DIR`、`RAIL_DIR`），只讀取、不修改。執行後請看輸出的各類型鄉鎮數與「注意」訊息。

`render.js` 需要 Node 與 Playwright（`npm i -g playwright` 後 `npx playwright install chromium`），照片與字型要連網。全部 368 個鄉鎮約 736 張圖；只想重做幾張時把代稱接在後面，例如 `node tools/render.js tainan-city/west-central`。

### 鄉鎮名稱的檢查結果（2026-11-16）

- 官方清單 368 個鄉鎮市區，主檔 3,032 處全部對得上；沒有「臺／台」差異，也沒有舊制行政區名稱。
- 嘉義市 54 處的 `town` 是空的，建置時從官方地址開頭補上東區（41）或西區（13），原始資料不動。
- 界線檔的縣市名稱用「台」，建置時改用鄉鎮代碼對照，不受影響。
- `reports/town-check.csv`：40 處文資的座標落在主檔所寫鄉鎮的界線之外。界線經過簡化，多數是邊界附近的誤差或離島（例如彭佳嶼燈塔）；其餘可當作知識網站的校對清單。卡片一律以主檔的 `town` 為準。

### 無形文資

`ich.json` 沒有鄉鎮欄位。建置時先看場館地址，沒有再看「哪裡看」與保存者的文字裡有沒有完整的鄉鎮名稱（三個字以上）。624 項中對得上 485 項；對不上的不會出現在卡片上。連結指向國家文化資產網的該項頁面。

## 本機預覽

網頁用的是從根目錄起算的路徑（`/assets/…`），要在 repo 根目錄開伺服器：

```bash
python3 -m http.server 8000
```

開啟 http://localhost:8000/ 。字型與照片需要連網。

## 部署

GitHub Pages：Settings → Pages → Deploy from a branch，選 `main` 與 `/ (root)`。自訂網域寫在 `CNAME`（`cultural-town.123hi.org`），DNS 需要一筆 CNAME 記錄指向 `allanloplus.github.io`。因為路徑從根目錄起算，本站只能放在網域的根目錄。開發在工作分支進行，合併到 `main` 才上線。

## 資料來源與授權

- 文化資產清單、座標、年代、建築類型：文化部文化資產局國家文化資產網，經兩個知識網站與文資地圖集整理。
- 鄉鎮市區清單：內政部國土測繪中心 `api.nlsc.gov.tw` 的 ListCounty、ListTown1，2026-11-16 抓取，存在 `data/raw/towns-official.json`。這支 API 的授權頁尚未逐字核對；內容（名稱與代碼）與下一項界線資料集一致。
- 鄉鎮市區界線：內政部國土測繪中心「鄉鎮市區界線（TWD97 經緯度）」（政府資料開放平臺資料集 7441，政府資料開放授權條款第 1 版），使用 npm 套件 taiwan-atlas 2021.9.20 的簡化版 `towns-10t.json`（套件本身為 MIT 授權，`data/raw/taiwan-atlas.LICENSE.txt`）。官方下載點不接受自動程式下載，所以改用這份；之後若要換成最新的官方檔，改 `build.py` 讀界線的那一段即可。此開放資料依政府資料開放授權條款（Open Government Data License）進行公眾釋出，使用者於遵守本條款各項規定之前提下，得利用之。政府資料開放授權條款：https://data.gov.tw/license
- 照片：Wikimedia Commons，作者與授權條款標示在每張照片上，預覽圖與下載的卡片圖片上也有；資料取自知識網站各縣市的 `images.json`。
- 車站：姊妹站「搭火車逛文資」的資料（臺鐵車站地址來自交通部 PTX／臺鐵公司）。

---

Copyright © 2026 Allan Lo. 文字內容與程式碼版權所有；第三方資料依各自授權。
