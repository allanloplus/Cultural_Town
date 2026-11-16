"""鄉鎮文資性格卡：產生全部靜態資料與每個鄉鎮的固定網址頁

用法：
  python3 tools/build.py
只用 Python 標準函式庫。會找本 repo 旁邊的 Cultural_Atlas、Cultural_Heritage、Cultural_Heritage2、Cultural_Rail
（或用環境變數 ATLAS_DIR、CH1_DIR、CH2_DIR、RAIL_DIR 指定），只讀取、不修改。

輸出：
  data/index.json            全站索引：類型定義、縣市、368 個鄉鎮市區（代稱、處數、類型、中心點）
  data/town/<縣市>/<鄉鎮>.json 每個鄉鎮的卡片內容
  t/<縣市>/<鄉鎮>/index.html   每個鄉鎮的固定網址（帶社群預覽用的 meta）
  data/towns-topo.json        鄉鎮界線（「用我的位置」才會下載）
  reports/town-check.csv      鄉鎮名稱與座標的檢查清單

性格怎麼算（門檻都是下面的常數，改了要重跑）：
  1. 每處文資先歸到一個「主調」：信仰／生活／產業／官方／考古。先看官方的建築類型（TYPE_DOMAIN），
     類型是「其他設施」或空白的，改看知識網站的主題（THEME_DOMAIN）。
  2. 3 處以上的鄉鎮：時代重心（老／日治／新）× 主調（四類中處數最多的）= 12 種類型。
  3. 1–2 處的鄉鎮：「獨苗系列」，依主角那一處的主調分 5 種。
  4. 0 處的鄉鎮：「留白系列」，對得上無形文資的是一種，都沒有的是另一種。
"""
import json, os, re, sys, math, csv, collections, datetime, hashlib, html, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT = os.path.dirname(HERE)
SITE = "https://cultural-town.123hi.org"
RAIL_URL = "https://cultural-rail.123hi.org/"

# ---- 可調的門檻 ----
FULL_MIN = 3          # 幾處以上算一般類型
OLD_SHARE = 0.34      # 清領以前占比達到這個數（且不少於戰後）→「老」
NEW_SHARE = 0.30      # 戰後占比達到這個數 →「新」
DENSE = (30, 10)      # 徽章：30 處以上「文資大戶」、10 處以上「小有規模」
REPS = 3              # 代表文資幾處


def find(env, names):
    d = os.environ.get(env)
    if d:
        return os.path.abspath(d)
    for n in names:
        p = os.path.join(PARENT, n)
        if os.path.isdir(p):
            return p
    sys.exit("找不到 %s，請設定環境變數 %s" % (names[0], env))


ATLAS = find("ATLAS_DIR", ["Cultural_Atlas", "cultural_atlas"])
CH1 = find("CH1_DIR", ["Cultural_Heritage", "cultural_heritage"])
CH2 = find("CH2_DIR", ["Cultural_Heritage2", "cultural_heritage2"])
RAIL = find("RAIL_DIR", ["Cultural_Rail", "cultural_rail"])


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, separators=(",", ":"))


# ---- 主調分類 ----
DOMS = [["F", "信仰", "信仰與祭祀", "寺廟、祠堂、教堂、墓葬、牌坊、碑碣"],
        ["L", "生活", "家宅與街市", "宅第、街屋、商店、市場、聚落"],
        ["I", "產業", "產業與交通", "工廠、倉庫、車站、橋樑、水利、燈塔"],
        ["G", "官方", "官署與公共", "衙署、廳舍、學校、宿舍、軍事設施、醫院"],
        ["A", "考古", "考古遺址", "考古遺址"],
        ["X", "其他", "其他", "無法歸類"]]
DOM_NAME = {d[0]: d[1] for d in DOMS}
TYPE_DOMAIN = {"F": "寺廟 祠堂 教堂 墓葬 牌坊 碑碣 宗教景觀 神話傳說之場域",
               "L": "宅第 商店 市場 戲劇院 漢人街庄 原住民部落 眷村 歷史名園 集會堂",
               "I": "產業 車站 橋樑 燈塔 水利設施 堤閘 工業地景 農林漁牧景觀 交通地景 銀行",
               "G": "衙署 辦公廳舍 機關 學校 官邸 關塞 城郭 醫院 軍事設施 書院 近代宿舍 博物館"}
T2D = {t: k for k, v in TYPE_DOMAIN.items() for t in v.split()}
THEME_DOMAIN = [("F", r"宗教|信仰|宗祠|墓葬|碑碣|教會|神社|牌坊|天主|石塔|風獅|摩崖"),
                ("I", r"產業|鐵道|水利|糖|礦|林業|茶|橋|港|燈塔|漁|鹽|窯|農|電力|石油|菸酒|金融|交通|通訊|廣播|磚|陶"),
                ("G", r"公共建築|職務宿舍|教育|軍事|戰|官署|警|醫療|砲|礮|城|坑道|省府|司法|防空|書院|孔廟|行政|人權|民主|領事|陵寢|海防"),
                ("L", r"宅第|古厝|洋樓|故居|店屋|老街|聚落|眷村|市場|商業|石頭屋|部落|移民|溫泉|公園|客家|原住民")]
# 拿來比「全臺最多」的官方建築類型
RANK_TYPES = "寺廟 祠堂 教堂 墓葬 牌坊 碑碣 車站 橋樑 燈塔 產業 學校 衙署 關塞 書院 宅第 商店".split()


def domain(s):
    if s["rawCategory"] == "考古遺址":
        return "A"
    for t in s["types"]:
        if t in T2D:
            return T2D[t]
    for th in s["themes"]:
        for k, p in THEME_DOMAIN:
            if re.search(p, th):
                return k
    return "X"


# ---- 類型定義：[代碼, 名稱, 一句話, 系列, 時代, 主調] ----
TYPES = [
    ["OF", "香火老街坊", "廟比街還老，街是跟著廟長出來的。", "full", "O", "F"],
    ["OL", "古厝大家族", "老宅一棟接一棟，家族的故事寫在門楣上。", "full", "O", "L"],
    ["OI", "老本行守護者", "清代就開工的營生，到今天還留著痕跡。", "full", "O", "I"],
    ["OG", "城門老將", "城牆、砲臺、衙門，守了一百多年還站著。", "full", "O", "G"],
    ["JF", "日治祈福派", "神社、教堂與廟宇，在日治年間一起落腳。", "full", "J", "F"],
    ["JL", "街屋生活家", "街屋與宅院，日治時代的日子都住在裡面。", "full", "J", "L"],
    ["JI", "鐵道產業派", "車站、工廠、倉庫，是靠產業長大的地方。", "full", "J", "I"],
    ["JG", "官廳宿舍控", "廳舍、學校與宿舍，當年的公家單位都還在。", "full", "J", "G"],
    ["NF", "新香火接班人", "戰後才出現的信仰地標，也已經列入文資。", "full", "N", "F"],
    ["NL", "戰後新住戶", "戰後的宅院與眷舍，把新故事住成了歷史。", "full", "N", "L"],
    ["NI", "現代建設咖", "戰後的工程與產業設施，老到值得保存了。", "full", "N", "I"],
    ["NG", "戰後公務員", "戰後的機關、學校與營舍，是這裡的主角。", "full", "N", "G"],
    ["SF", "一廟定江山", "文資不多，主角是一處信仰地標。", "solo", "", "F"],
    ["SL", "一宅撐全場", "文資不多，主角是一處家宅或街屋。", "solo", "", "L"],
    ["SI", "一技走天下", "文資不多，主角是一處產業或交通設施。", "solo", "", "I"],
    ["SG", "一官守一方", "文資不多，主角是一處官署或公共建築。", "solo", "", "G"],
    ["SA", "地底藏一手", "文資不多，主角埋在地底下：考古遺址。", "solo", "", "A"],
    ["BI", "無形派掌門", "沒有登錄的建築，文資活在人的手藝與祭典裡。", "blank", "", ""],
    ["BW", "等待被發現", "目前沒有任何登錄的文資，名單上還是空白。", "blank", "", ""],
]
TYPE = {t[0]: t for t in TYPES}
ERA3 = {"O": "清領以前", "J": "日治", "N": "戰後"}
SERIES = {"full": "性格十二型", "solo": "獨苗系列", "blank": "留白系列"}

# ---- 讀文資主檔，補上知識網站的類型、主題、照片 ----
atlas = load(os.path.join(ATLAS, "data", "sites.json"))
F = atlas["meta"]["fields"]
COUNTIES = atlas["counties"]
ERAS = atlas["eras"]
CATS = atlas["cats"]
CAT_SHORT = ["國定古蹟", "市縣定古蹟", "歷史建築", "紀念建築", "聚落建築群", "文化景觀", "考古遺址"]
official = load(os.path.join(HERE, "data", "raw", "towns-official.json"))["towns"]
CODE = {(t["county"], t["town"]): t["code"] for t in official}
warn = []

cdata = {}
for c in COUNTIES:
    base = os.path.join(CH1 if "cultural.123hi" in c["base"] else CH2, c["slug"], "data")
    cdata[c["slug"]] = {
        "off": {s["id"]: s for s in load(os.path.join(base, "sites-official.json"))},
        "con": {s["id"]: s for s in load(os.path.join(base, "sites-content.json"))},
        "img": load(os.path.join(base, "images.json")),
        "ich": load(os.path.join(base, "ich.json")) if os.path.exists(os.path.join(base, "ich.json")) else {"items": [], "venues": []},
    }

SITES = []
town_fixed = 0
for row in atlas["sites"]:
    s = dict(zip(F, row))
    c = COUNTIES[s["county"]]
    cd = cdata[c["slug"]]
    o, k = cd["off"][s["id"]], cd["con"][s["id"]]
    s["cname"], s["cslug"], s["base"] = c["name"], c["slug"], c["base"]
    s["types"] = o.get("types") or []
    s["themes"] = k.get("themes") or []
    s["address"] = o.get("address") or ""
    if not s["town"]:  # 主檔沒有鄉鎮（目前是嘉義市 54 處）：從官方地址開頭取
        m = re.match(r"(?:%s)?([一-鿿]{1,3}?[鄉鎮市區])" % c["name"], s["address"])
        if m and (c["name"], m.group(1)) in CODE:
            s["town"] = m.group(1)
            town_fixed += 1
    if (c["name"], s["town"]) not in CODE:
        warn.append("%s／%s：鄉鎮「%s」不在官方清單，這一處不會出現在任何卡片" % (c["name"], s["name"], s["town"]))
        continue
    s["dom"] = domain(s)
    im = (cd["img"].get(s["id"]) or [None])[0]
    s["photo"] = None
    if im:
        if im.get("local"):
            p = {"l": c["base"] + im["local"], "s": c["base"] + (im.get("small") or im["local"])}
        else:
            p = {"l": im["thumb"], "s": im["thumb"]}
        p.update({"a": im.get("artist") or "", "lic": im.get("license") or "", "lu": im.get("licenseUrl") or "", "pg": im.get("page") or ""})
        s["photo"] = p
    SITES.append(s)

NAT_N = len(SITES)
NAT_DOM = collections.Counter(s["dom"] for s in SITES)

# ---- 鄉鎮界線（TopoJSON）：中心點、相鄰關係、點在哪個鄉鎮 ----
topo = load(os.path.join(HERE, "data", "raw", "towns-10t.json"))
sx, sy = topo["transform"]["scale"]
tx, ty = topo["transform"]["translate"]
ARCS = []
for a in topo["arcs"]:
    x = y = 0
    pts = []
    for dx, dy in a:
        x += dx
        y += dy
        pts.append((x * sx + tx, y * sy + ty))
    ARCS.append(pts)


def ring(idx):
    out = []
    for i in idx:
        pts = ARCS[i] if i >= 0 else ARCS[~i][::-1]
        out.extend(pts if not out else pts[1:])
    return out


def ring_area_centroid(r):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(r, r[1:]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if abs(a) < 1e-12:
        return 0, r[0][0], r[0][1]
    return abs(a / 2), cx / (3 * a), cy / (3 * a)


def in_ring(x, y, r):
    ins = False
    for (x0, y0), (x1, y1) in zip(r, r[1:]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            ins = not ins
    return ins


GEO = {}       # 代碼 → {polys, bbox, center, eng}
arc_owner = collections.defaultdict(set)
for g in topo["objects"]["towns"]["geometries"]:
    code = g["properties"]["TOWNCODE"]
    polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
    rings = [[ring(r) for r in p] for p in polys]
    best = max((ring_area_centroid(p[0]) for p in rings), key=lambda t: t[0])
    xs = [pt[0] for p in rings for pt in p[0]]
    ys = [pt[1] for p in rings for pt in p[0]]
    GEO[code] = {"polys": rings, "bbox": (min(xs), min(ys), max(xs), max(ys)), "center": (round(best[2], 5), round(best[1], 5)),
                 "eng": g["properties"]["TOWNENG"]}
    for p in polys:
        for r in p:
            for i in r:
                arc_owner[i if i >= 0 else ~i].add(code)
ADJ = collections.defaultdict(set)
for owners in arc_owner.values():
    for a in owners:
        ADJ[a] |= owners - {a}
miss = [k for k, v in CODE.items() if v not in GEO]
if miss:
    warn.append("界線檔缺少：%s" % miss)


def town_at(lng, lat):
    for code, g in GEO.items():
        b = g["bbox"]
        if b[0] <= lng <= b[2] and b[1] <= lat <= b[3]:
            for p in g["polys"]:
                if in_ring(lng, lat, p[0]) and not any(in_ring(lng, lat, h) for h in p[1:]):
                    return code
    return None


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


# ---- 鄉鎮清單與代稱 ----
CSLUG = {c["name"]: c["slug"] for c in COUNTIES}
TOWNS = {}
used = set()
for t in official:
    eng = GEO[t["code"]]["eng"] if t["code"] in GEO else t["code"]
    sl = re.sub(r"[^a-z0-9]+", "-", re.sub(r"\s+(District|Township|City)$", "", eng).lower()).strip("-")
    slug = CSLUG[t["county"]] + "/" + sl
    if slug in used:
        slug += "-" + t["code"][-3:]
    used.add(slug)
    TOWNS[t["code"]] = {"code": t["code"], "county": t["county"], "cslug": CSLUG[t["county"]], "name": t["town"], "slug": slug,
                        "center": GEO[t["code"]]["center"], "sites": []}
for s in SITES:
    TOWNS[CODE[(s["cname"], s["town"])]]["sites"].append(s)
BY_SLUG = {t["slug"]: t for t in TOWNS.values()}

# 座標檢查：文資座標落在哪個鄉鎮（界線經過簡化，邊界附近會有誤差，只當作校對清單）
check_rows = []
for s in SITES:
    want = CODE[(s["cname"], s["town"])]
    got = town_at(s["lng"], s["lat"])
    if got != want:
        g = TOWNS.get(got)
        check_rows.append([s["cname"], s["town"], s["name"], s["id"], s["lat"], s["lng"], (g["county"] + g["name"]) if g else "界線外（海上或離島邊緣）", s["address"]])
os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
with open(os.path.join(HERE, "reports", "town-check.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["縣市", "主檔的鄉鎮", "名稱", "id", "緯度", "經度", "座標落在", "官方地址"])
    w.writerows(check_rows)

# ---- 無形文資對到鄉鎮：先看場館地址，沒有再看「哪裡看」與保存者的文字 ----
ICH = collections.defaultdict(list)
ich_total = ich_mapped = 0
for c in COUNTIES:
    I = cdata[c["slug"]]["ich"]
    V = {v["id"]: v for v in I.get("venues", [])}
    names = [t["name"] for t in TOWNS.values() if t["county"] == c["name"]]
    for it in I.get("items", []):
        ich_total += 1
        hit = set()
        v = V.get(it.get("venueId"))
        if v:
            hit = {n for n in names if n in (v.get("address") or "")}
        if not hit:
            text = (it.get("whereToSee") or "") + (it.get("holder") or "")
            hit = {n for n in names if len(n) >= 3 and n in text}
        if hit:
            ich_mapped += 1
        for n in hit:
            ICH[CODE[(c["name"], n)]].append({"n": it["name"], "t": it.get("type") or "", "s": it.get("summary") or "", "h": it.get("holder") or "",
                                              "u": it.get("url") or "", "b": c["base"] + "#map"})

# ---- 鐵道版的車站 ----
STATIONS = collections.defaultdict(list)
try:
    addr = {s["StationID"]: s.get("StationAddress", "").replace("台", "臺") for s in load(os.path.join(RAIL, "data", "raw", "tra-station.json"))["Stations"]}
    seen = set()
    for ln in load(os.path.join(RAIL, "data", "index.json"))["lines"]:
        p = os.path.join(RAIL, "data", "lines", ln["id"] + ".json")
        if not os.path.exists(p):
            continue
        for st in load(p)["stations"]:
            if st["id"] in seen:
                continue
            a = addr.get(st["id"], "")
            for t in TOWNS.values():
                if t["county"] + t["name"] in a:
                    seen.add(st["id"])
                    STATIONS[t["code"]].append({"n": st["name"], "ln": ln["name"], "c": len(st["sites"]), "u": RAIL_URL + "#/line/%s/%s" % (ln["id"], st["id"])})
                    break
except (OSError, KeyError) as e:
    warn.append("讀不到鐵道版資料，卡片不會有車站連結：%s" % e)


# ---- 小工具 ----
def pct(a, b):
    return int(round(100 * a / b)) if b else 0


def ytxt(y):
    return ("西元前 %d 年" % -y) if y < 0 else ("%d 年" % y)


def pick(seed, arr):
    return arr[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(arr)]


def site_out(s):
    o = {"i": s["id"], "n": s["name"], "k": s["cat"], "y": s["year"], "e": s["estimated"], "yt": s["yearText"], "r": s["era"], "s": s["summary"],
         "d": s["dom"], "u": s["base"] + "#map/" + s["id"]}
    if s["photo"]:
        o["p"] = s["photo"]
    return o


def era3(s):
    return "O" if s["era"] <= 3 else ("J" if s["era"] == 4 else "N")


# ---- 第一輪：每個鄉鎮的統計與類型 ----
for t in TOWNS.values():
    L = t["sites"]
    n = t["n"] = len(L)
    t["ich"] = ICH.get(t["code"], [])
    t["e3"] = collections.Counter(era3(s) for s in L)
    t["dom"] = collections.Counter(s["dom"] for s in L)
    t["mon"] = sum(1 for s in L if s["cat"] <= 1)
    t["nat"] = sum(1 for s in L if s["cat"] == 0)
    if n >= FULL_MIN:
        old, new = t["e3"]["O"] / n, t["e3"]["N"] / n
        E = "O" if (old >= OLD_SHARE and old >= new) else ("N" if new >= NEW_SHARE else "J")
        D = max("FLIG", key=lambda x: (t["dom"][x], t["dom"][x] / n / (NAT_DOM[x] / NAT_N)))
        t["type"], t["era_key"], t["dom_key"] = E + D, E, D
        t["lead"] = None
    elif n:
        # 主角：等級高的優先，再來有照片的、年代早的
        t["lead"] = sorted(L, key=lambda s: (min(s["cat"], 2), 0 if s["photo"] else 1, s["year"]))[0]
        d = t["lead"]["dom"]
        t["type"] = "S" + (d if d in "FLIGA" else "G")
        t["dom_key"] = d
    else:
        t["lead"] = None
        t["type"] = "BI" if t["ich"] else "BW"
    t["series"] = TYPE[t["type"]][3]

ALL = list(TOWNS.values())
FULL = [t for t in ALL if t["series"] == "full"]
CTOWNS = collections.defaultdict(list)
for t in ALL:
    CTOWNS[t["county"]].append(t)
N_RANK = {t["code"]: i + 1 for i, t in enumerate(sorted(ALL, key=lambda t: -t["n"]))}
TYPE_N = collections.Counter(t["type"] for t in ALL)
TYPE_TOP = {}  # 官方建築類型 → 最多的鄉鎮
tc = collections.Counter()
for s in SITES:
    for ty in set(s["types"]):
        tc[(CODE[(s["cname"], s["town"])], ty)] += 1
for ty in RANK_TYPES:
    r = sorted(((v, k[0]) for k, v in tc.items() if k[1] == ty), reverse=True)
    if r and (len(r) == 1 or r[0][0] > r[1][0]):
        TYPE_TOP[ty] = r[0]
COUNTY_OLDEST = {}
for s in SITES:
    if s["cat"] != 6 and (s["cname"] not in COUNTY_OLDEST or s["year"] < COUNTY_OLDEST[s["cname"]]["year"]):
        COUNTY_OLDEST[s["cname"]] = s


def neighbors(t):
    """相鄰的鄉鎮；離島沒有陸地鄰居時，改取中心點最近的三個"""
    nb = [TOWNS[c] for c in ADJ.get(t["code"], []) if c in TOWNS]
    if not nb:
        nb = sorted((x for x in ALL if x is not t), key=lambda x: km(t["center"], x["center"]))[:3]
    return sorted(nb, key=lambda x: -x["n"])


def nearest_sites(t, origin, k=3):
    """不在本鄉鎮、離 origin 最近的文資，每個鄉鎮最多取一處"""
    out, seen = [], set()
    for s in sorted((s for s in SITES if CODE[(s["cname"], s["town"])] != t["code"]), key=lambda s: km(origin, (s["lat"], s["lng"]))):
        code = CODE[(s["cname"], s["town"])]
        if code in seen:
            continue
        seen.add(code)
        o = site_out(s)
        o.update({"km": round(km(origin, (s["lat"], s["lng"])), 1), "tn": (s["cname"] if s["cname"] != t["county"] else "") + s["town"], "ts": TOWNS[code]["slug"]})
        out.append(o)
        if len(out) == k:
            break
    return out


# ---- 讓人意外的事實：列出候選，挑分數最高的 ----
def facts(t):
    n, L, c = t["n"], t["sites"], t["county"]
    out = []
    cl = sorted(CTOWNS[c], key=lambda x: -x["n"])
    ctot = sum(x["n"] for x in cl)
    crank = [x["code"] for x in cl].index(t["code"]) + 1
    if N_RANK[t["code"]] <= 10:
        out.append((95 - N_RANK[t["code"]], "全臺排名", "第 %d" % N_RANK[t["code"]], "名", "%d 處文資，在全臺 368 個鄉鎮市區裡排第 %d。" % (n, N_RANK[t["code"]])))
    if crank == 1 and len(cl) > 1 and pct(n, ctot) >= 30:
        out.append((58 + pct(n, ctot) / 2, "全縣占比", "%d" % pct(n, ctot), "%", "%s %d 處文資，有 %d 處在這裡，是全%s第一。" % (c, ctot, n, c[-1])))
    elif crank == 1 and len(cl) > 1:
        out.append((50, "全縣排名", "第 1", "名", "%d 處文資是%s %d 個鄉鎮市區裡最多的。" % (n, c, len(cl))))
    for ty, (cnt, code) in TYPE_TOP.items():
        if code == t["code"] and cnt >= 3:
            out.append((80 + min(cnt, 15), "全臺最多", "%d" % cnt, "處" + ty, "官方登記為「%s」的文資有 %d 處，是全臺最多的鄉鎮市區。" % (ty, cnt)))
    if n >= 5:
        d, m = t["dom"].most_common(1)[0]
        if d in "FLIG" and m / n >= 0.6:
            rk = 1 + sum(1 for x in FULL if x["n"] >= 5 and x["dom"][d] / x["n"] > m / n)
            out.append((62 + 25 * m / n + (8 if rk <= 3 else 0), "主調集中", "%d" % pct(m, n), "%",
                        "%d 處裡有 %d 處是%s類（全臺平均 %d%%）%s。" % (n, m, DOM_NAME[d], pct(NAT_DOM[d], NAT_N), "，集中程度在 5 處以上的鄉鎮裡排第 %d" % rk if rk <= 10 else "")))
    if n >= 6 and len(t["e3"]) == 1:
        out.append((74, "時代單一", "%d" % n, "處全是" + ERA3[next(iter(t["e3"]))], "%d 處文資全部是%s時期的，沒有任何例外。" % (n, ERA3[next(iter(t["e3"]))])))
    if n >= 8 and t["mon"] == 0:
        out.append((64 + min(n, 20), "沒有古蹟", "0", "處古蹟", "%d 處文資沒有任何一處是古蹟，全部是歷史建築、文化景觀等其他類別。" % n))
    if n >= 4 and t["mon"] == n:
        out.append((82, "全是古蹟", "%d" % n, "處全是古蹟", "%d 處文資每一處都是古蹟等級，全臺 4 處以上的鄉鎮很少見。" % n))
    if t["nat"] >= 3:
        rk = 1 + sum(1 for x in ALL if x["nat"] > t["nat"])
        out.append((70 + t["nat"], "國定古蹟", "%d" % t["nat"], "處國定古蹟", "有 %d 處國定古蹟，數量排全臺第 %d。" % (t["nat"], rk)))
    co = COUNTY_OLDEST.get(c)
    if co and n >= 2 and co in L and len(cl) > 1:
        out.append((66, "全縣最老", ytxt(co["year"]).replace(" 年", ""), "年", "全%s最老的文資（考古遺址不算）就在這裡：%s，%s。" % (c, co["name"], ytxt(co["year"]))))
    nb = [x for x in neighbors(t) if x["code"] in ADJ.get(t["code"], ())]
    if nb and n >= 10:
        lo = min(nb, key=lambda x: x["n"])
        if n >= 5 * max(lo["n"], 1) and n - lo["n"] >= 10:
            out.append((54 + min(n - lo["n"], 30) / 2, "鄰居反差", "%d：%d" % (n, lo["n"]), "", "這裡有 %d 處，隔壁的%s%s。" % (n, lo["name"], "只有 %d 處" % lo["n"] if lo["n"] else "一處都沒有")))
    if nb and 1 <= n < 10:
        hi = nb[0]
        if hi["n"] >= 5 * n and hi["n"] - n >= 10:
            out.append((52 + min(hi["n"] - n, 30) / 2, "鄰居反差", "%d：%d" % (n, hi["n"]), "", "這裡只有 %d 處，隔壁的%s卻有 %d 處。" % (n, hi["name"], hi["n"])))
    if n >= 2:
        ys = sorted(s["year"] for s in L if s["cat"] != 6) or sorted(s["year"] for s in L)
        if ys[-1] - ys[0] >= 1:
            out.append((30 + min((ys[-1] - ys[0]) / 20, 15), "時間跨度", "%d" % (ys[-1] - ys[0]), "年", "最老的建於 %s，最新的建於 %s，前後相差 %d 年。" % (ytxt(ys[0]), ytxt(ys[-1]), ys[-1] - ys[0])))
    same = sum(1 for x in cl if x["series"] == t["series"])
    if t["series"] == "solo":
        out.append((40, "同縣同伴", "%d" % same, "個", "%s %d 個鄉鎮市區裡，有 %d 個和這裡一樣只有 1–2 處文資。" % (c, len(cl), same)))
    if t["series"] == "blank":
        zero = sum(1 for x in ALL if x["n"] == 0)
        out.append((45, "零的俱樂部", "%d" % same, "個", "全臺 %d 個鄉鎮市區沒有有形文資，%s就占了 %d 個（全%s共 %d 個鄉鎮市區）。" % (zero, c, same, c[-1], len(cl))))
    out.sort(key=lambda x: -x[0])
    return [{"k": k, "big": big, "unit": unit, "t": text} for _, k, big, unit, text in out]


# ---- 跟你最像的鄉鎮（優先不同縣市、同一種類型）----
def vec(t):
    n = t["n"]
    return [t["e3"]["O"] / n, t["e3"]["J"] / n, t["e3"]["N"] / n] + [t["dom"][d] / n for d in "FLIG"] + [t["mon"] / n, min(math.log(n) / math.log(150), 1) * 1.5]


def similar(t):
    pool = [x for x in ALL if x["type"] == t["type"] and x["county"] != t["county"]] or [x for x in ALL if x["series"] == t["series"] and x is not t]
    if not pool:
        return None
    if t["series"] == "full":
        v = vec(t)
        x = min(pool, key=lambda x: sum((a - b) ** 2 for a, b in zip(v, vec(x))))
        E, D = t["era_key"], t["dom_key"]
        why = "%s占比 %d% 對 %d%，%s類 %d% 對 %d%，古蹟比例 %d% 對 %d%。" .replace("% ", "%% ").replace("%，", "%%，").replace("%。", "%%。") % (
            ERA3[E], pct(t["e3"][E], t["n"]), pct(x["e3"][E], x["n"]), DOM_NAME[D], pct(t["dom"][D], t["n"]), pct(x["dom"][D], x["n"]),
            pct(t["mon"], t["n"]), pct(x["mon"], x["n"]))
    elif t["series"] == "solo":
        a = t["lead"]
        x = min(pool, key=lambda x: (0 if set(x["lead"]["types"]) & set(a["types"]) else 1, abs(x["n"] - t["n"]), abs(x["lead"]["year"] - a["year"])))
        b = x["lead"]
        common = (set(a["types"]) & set(b["types"])) - {"其他設施"}
        why = "兩地都只有 %s文資，主角%s：這裡是 %s的%s，那裡是 %s的%s。" % (
            "1 處" if t["n"] == x["n"] == 1 else "1–2 處", "都登記為「%s」" % sorted(common)[0] if common else "都是%s類" % DOM_NAME.get(t["dom_key"], "同一"),
            ytxt(a["year"]), a["name"], ytxt(b["year"]), b["name"])
    elif t["type"] == "BI":
        ks = collections.Counter(i["t"] for i in t["ich"])
        x = min(pool, key=lambda x: (-sum((ks & collections.Counter(i["t"] for i in x["ich"])).values()), abs(len(x["ich"]) - len(t["ich"]))))
        why = "兩地都沒有有形文資，但各有無形文資：這裡 %d 項，那裡 %d 項（%s）。" % (len(t["ich"]), len(x["ich"]), "、".join(i["n"] for i in x["ich"][:2]))
    else:
        d = t["near"][0]["km"]
        x = min(pool, key=lambda x: abs(x["near"][0]["km"] - d))
        why = "兩地都沒有任何登錄的文資；從這裡到最近的一處約 %.1f 公里，從那裡約 %.1f 公里。" % (d, x["near"][0]["km"])
    return {"slug": x["slug"], "c": x["county"], "n": x["name"], "cnt": x["n"], "type": x["type"], "why": why}


# ---- 為什麼是這個類型：每一條都對應到數字 ----
def why(t):
    n = t["n"]
    out = []
    if t["series"] == "full":
        E, D = t["era_key"], t["dom_key"]
        o, j, w = t["e3"]["O"], t["e3"]["J"], t["e3"]["N"]
        rule = {"O": "清領以前占 %d%%，達到 %d%% 的門檻，而且不比戰後少" % (pct(o, n), OLD_SHARE * 100),
                "N": "清領以前只占 %d%%，戰後占 %d%%，達到 %d%% 的門檻" % (pct(o, n), pct(w, n), NEW_SHARE * 100),
                "J": "清領以前占 %d%%（門檻 %d%%）、戰後占 %d%%（門檻 %d%%），都沒達到，其餘算日治" % (pct(o, n), OLD_SHARE * 100, pct(w, n), NEW_SHARE * 100)}[E]
        out.append(["時代重心：" + ERA3[E], "%d 處文資中，清領以前 %d 處、日治 %d 處、戰後 %d 處。%s。" % (n, o, j, w, rule)])
        ds = "、".join("%s %d" % (DOM_NAME[d], t["dom"][d]) for d in "FLIGAX" if t["dom"][d])
        tie = [d for d in "FLIG" if d != D and t["dom"][d] == t["dom"][D]]
        out.append(["主調：" + DOM_NAME[D], "各類處數：%s。%s類 %d 處最多，占 %d%%（全臺平均 %d%%）%s。" % (
            ds, DOM_NAME[D], t["dom"][D], pct(t["dom"][D], n), pct(NAT_DOM[D], NAT_N),
            "；與%s類同數，取相對全臺平均更突出的一類" % "、".join(DOM_NAME[d] for d in tie) if tie else "")])
    elif t["series"] == "solo":
        a = t["lead"]
        out.append(["獨苗系列", "有形文資只有 %d 處，不到 %d 處，不套用十二型，改以其中一處當主角。" % (n, FULL_MIN)])
        src = ("官方登記的類型是「%s」" % "、".join(a["types"])) if any(x in T2D for x in a["types"]) else ("知識網站的主題是「%s」" % "、".join(a["themes"]))
        out.append(["主角：" + a["name"], ("%s，%s，歸在%s類。" % (CAT_SHORT[a["cat"]], src, DOM_NAME[a["dom"]])) if a["dom"] != "A" else "類別是考古遺址。"])
        if n == 2:
            out.append(["怎麼選主角", "兩處之中，先比等級（古蹟優先），再比有沒有照片，最後比年代。"])
    else:
        out.append(["留白系列", "文資主檔 3,032 處有形文化資產裡，沒有任何一處位在這裡。" if NAT_N == 3032 else "文資主檔 %s 處有形文化資產裡，沒有任何一處位在這裡。" % format(NAT_N, ",")])
        out.append(["無形文資", ("知識網站的無形文資資料中，有 %d 項的場館地址或展演地點寫到這裡，所以是「無形派掌門」。" % len(t["ich"])) if t["ich"] else
                    "知識網站 %d 項無形文資的場館地址與展演地點，也都沒有寫到這裡，所以是「等待被發現」。" % ich_total])
    if t["series"] == "full":
        b = "文資大戶" if n >= DENSE[0] else ("小有規模" if n >= DENSE[1] else "小而精")
        out.append(["密度徽章：" + b, "%d 處，全臺排第 %d（%d 處以上是文資大戶、%d 處以上是小有規模、其餘小而精）。" % (n, N_RANK[t["code"]], DENSE[0], DENSE[1])])
        g = "金字招牌" if t["mon"] / n >= MON_HI else ("歷史建築為主" if t["mon"] / n <= MON_LO else "古蹟與歷建各半")
        out.append(["等級徽章：" + g, "古蹟（國定＋市縣定）%d 處，占 %d%%。全臺 3 處以上鄉鎮的前四分之一是 %d%% 以上，後四分之一是 %d%% 以下。" % (t["mon"], pct(t["mon"], n), MON_HI * 100, MON_LO * 100)])
    return out


def quart(v, q):
    v = sorted(v)
    return v[int(q * (len(v) - 1))]


MON_HI = round(quart([t["mon"] / t["n"] for t in FULL], 0.75), 2)
MON_LO = round(quart([t["mon"] / t["n"] for t in FULL], 0.25), 2)


def badges(t):
    n = t["n"]
    if t["series"] != "full":
        return []
    return ["文資大戶" if n >= DENSE[0] else ("小有規模" if n >= DENSE[1] else "小而精"),
            "金字招牌" if t["mon"] / n >= MON_HI else ("歷史建築為主" if t["mon"] / n <= MON_LO else "古蹟與歷建各半")]


# ---- 一段有數字的描述 ----
def describe(t):
    n = t["n"]
    if t["series"] == "full":
        E, D = t["era_key"], t["dom_key"]
        top = sorted(t["sites"], key=lambda s: (0 if s["dom"] == D else 1, s["cat"], s["year"]))[:2]
        return "%d 處文資裡，%s的占 %d%%；最多的是%s類，%d 處，像是%s。" % (n, ERA3[E], pct(t["e3"][E], n), DOM_NAME[D], t["dom"][D], "、".join(s["name"] for s in top))
    if t["series"] == "solo":
        a = t["lead"]
        rest = [s for s in t["sites"] if s is not a]
        return "全區的有形文資只有 %d 處。主角是%s（%s，%s）%s。" % (n, a["name"], CAT_SHORT[a["cat"]], ytxt(a["year"]), "，另一處是" + rest[0]["name"] if rest else "")
    if t["ich"]:
        return "沒有任何古蹟或歷史建築，但有 %d 項無形文資在這裡傳承：%s。" % (len(t["ich"]), "、".join(i["n"] for i in t["ich"][:3]))
    nr = t["near"][0]
    return "有形、無形文資都還沒有登錄。最近的一處文資是%s的%s，離區中心約 %.1f 公里。" % (nr["tn"], nr["n"], nr["km"])


# ---- Allan 和阿拉蕾的串場（依資料組句） ----
QUIP = {
    "F": ["難怪走到哪都聞得到香！我可以每間都拜一下嗎？", "神明的鄰居也太多了吧，這裡的土地公會不會很忙？", "所以這裡的導航應該寫「看到廟就右轉」！"],
    "L": ["這麼多老房子，我想每一間都敲門借住一晚！", "老宅這麼多，躲貓貓一定可以玩一整天！", "那我要去數門牌，看哪一家的門楣最漂亮！"],
    "I": ["原來這裡以前是上班的地方！那下班鐘聲還會響嗎？", "工廠、倉庫、車站……這裡的文資都好勤勞喔！", "嗶嗶！阿拉蕾產業調查隊，出發！"],
    "G": ["都是公家單位？那我進去要不要先抽號碼牌？", "宿舍這麼多，當年的公務員一定都走路上班！", "立正！稍息！這裡的文資感覺都好有紀律。"],
    "A": ["寶物埋在地底下？快借我鏟子……啊，不能亂挖喔？", "幾千年前就有人住這裡，那才是真正的老住戶！"],
    "X": ["這裡的文資很有個性，連分類都難不倒它！"],
}
ERA_SAY = {"O": "清朝以前就有的", "J": "日治時期的", "N": "戰後才出現的"}


def talk(t, fs, sim):
    name, n, sd = t["name"], t["n"], t["slug"]
    ty = TYPE[t["type"]]
    L = []
    if t["series"] == "full":
        E, D = t["era_key"], t["dom_key"]
        L.append(["A", pick(sd + "a", ["talk", "point", "smile"]), "%s的性格是「%s」。%d 處文資裡 %d%% 是%s，最多的是%s類，有 %d 處。" % (
            name, ty[1], n, pct(t["e3"][E], n), ERA_SAY[E], DOM_NAME[D], t["dom"][D])])
        L.append(["R", pick(sd + "r", ["laugh", "surprised", "thumb", "present"]), pick(sd + "q", QUIP[D])])
    elif t["series"] == "solo":
        a = t["lead"]
        L.append(["A", pick(sd + "a", ["talk", "point", "think"]), "%s的有形文資只有 %d 處，所以我們請%s當主角：%s。" % (name, n, a["name"], a["summary"] or CAT_SHORT[a["cat"]])])
        L.append(["R", pick(sd + "r", ["thumb", "present", "surprised"]), pick(sd + "s", ["一處就能代表全區，這叫做以一擋百！", "獨苗才珍貴，我要幫它多拍幾張照片！", "全區的希望都在它身上了，壓力好大喔！"]) + pick(sd + "q", QUIP.get(a["dom"], QUIP["X"]))])
    elif t["ich"]:
        i = t["ich"][0]
        L.append(["A", "talk", "%s沒有登錄的古蹟或歷史建築，可是有 %d 項無形文資，像是%s。" % (name, len(t["ich"]), i["n"])])
        L.append(["R", pick(sd + "r", ["surprised", "thumb", "present"]), pick(sd + "q", ["原來文資不一定是房子！那要看的時候得挑對日子。", "看不見、摸不著，可是會動、會響、會傳下去，好厲害！", "沒有門牌的文資，得跟著人走才找得到！"])])
    else:
        nr = t["near"][0]
        L.append(["A", "scratch", "老實說，%s目前沒有任何登錄的文資。最近的一處在%s，是%s，離這裡約 %.1f 公里。" % (name, nr["tn"], nr["n"], nr["km"])])
        L.append(["R", pick(sd + "r", ["think", "confused", "fight"]), pick(sd + "q", ["零不是沒有故事，只是名單上還沒有它！你家附近有老房子嗎？", "空白的卡片最適合許願：下一處文資會不會就在這裡？", "那我先記下來，等名單更新就回來補上第一處！"])])
    if fs:
        mood = "surprised" if fs[0]["k"] in ("鄰居反差", "全臺最多", "全臺排名", "全是古蹟", "沒有古蹟") else "wink"
        L.append(["A", mood, "還有一件事：" + fs[0]["t"]])
    if sim:
        L.append(["R", "explain", "我幫你找到失散的雙胞胎：%s%s，也是「%s」！" % (sim["c"], sim["n"], TYPE[sim["type"]][1])
                  if sim["type"] == t["type"] else "跟這裡最像的是%s%s喔！" % (sim["c"], sim["n"])])
    return L


# ---- 第二輪：組出每張卡 ----
for t in ALL:
    L = t["sites"]
    origin = (t["lead"]["lat"], t["lead"]["lng"]) if t["lead"] else t["center"]
    t["near"] = nearest_sites(t, origin) if t["series"] != "full" else []
for t in ALL:
    t["facts"] = facts(t)
    t["sim"] = similar(t)

today = datetime.date.today().isoformat()
shutil.rmtree(os.path.join(HERE, "data", "town"), ignore_errors=True)
shutil.rmtree(os.path.join(HERE, "t"), ignore_errors=True)
STUB = open(os.path.join(HERE, "tools", "town_template.html"), encoding="utf-8").read()
for t in ALL:
    L, n = t["sites"], t["n"]
    ty = TYPE[t["type"]]
    D = t.get("dom_key") or ""
    if t["series"] == "full":
        reps = sorted(L, key=lambda s: (0 if s["photo"] else 1, 0 if s["dom"] == D else 1, min(s["cat"], 2), s["year"]))[:REPS]
    else:
        reps = sorted(L, key=lambda s: s is not t["lead"])
    old = min(L, key=lambda s: s["year"]) if L else None
    card = {
        "slug": t["slug"], "code": t["code"], "county": t["county"], "cslug": t["cslug"], "name": t["name"], "n": n,
        "series": t["series"], "type": t["type"], "badges": badges(t), "desc": describe(t),
        "eras": [[i, c] for i, c in sorted(collections.Counter(s["era"] for s in L).items())],
        "doms": [[d, t["dom"][d]] for d in "FLIGAX" if t["dom"][d]],
        "cats": [[i, c] for i, c in sorted(collections.Counter(s["cat"] for s in L).items())],
        "reps": [s["id"] for s in reps], "oldest": old["id"] if old else None,
        "facts": t["facts"][:3], "why": why(t), "similar": t["sim"],
        "rail": STATIONS.get(t["code"], []), "ich": t["ich"][:6], "ichN": len(t["ich"]), "near": t["near"],
        "nb": [{"slug": x["slug"], "n": x["name"], "c": x["county"] if x["county"] != t["county"] else "", "cnt": x["n"], "type": x["type"]} for x in neighbors(t)[:8]],
        "rank": {"nat": N_RANK[t["code"]], "county": 1 + sum(1 for x in CTOWNS[t["county"]] if x["n"] > n), "countyN": len(CTOWNS[t["county"]]),
                 "countyTotal": sum(x["n"] for x in CTOWNS[t["county"]])},
        "talk": talk(t, t["facts"], t["sim"]),
        "sites": [site_out(s) for s in sorted(L, key=lambda s: (s["cat"], s["year"]))],
        "extra": {},  # 預留：之後的「人口與文資」等單元把資料放在這裡
    }
    dump(os.path.join(HERE, "data", "town", t["slug"] + ".json"), card)
    title = "%s%s的文資性格：%s" % (t["county"], t["name"], ty[1])
    page = (STUB.replace("{{TITLE}}", html.escape(title)).replace("{{DESC}}", html.escape(card["desc"]))
            .replace("{{SLUG}}", t["slug"]).replace("{{URL}}", "%s/t/%s/" % (SITE, t["slug"]))
            .replace("{{OG}}", "%s/og/%s.jpg" % (SITE, t["slug"])).replace("{{ALT}}", html.escape("%s%s的文資性格卡：%s。%s" % (t["county"], t["name"], ty[1], ty[2]))))
    p = os.path.join(HERE, "t", t["slug"], "index.html")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(page)

# ---- 全站索引 ----
COLOR = {"F": "#b23a3a", "L": "#a8714a", "I": "#1d6f73", "G": "#3b6ea8", "A": "#8a6a4a", "": "#6b5bb5"}
index = {
    "meta": {"generated": today, "sites": NAT_N, "towns": len(ALL), "withSites": sum(1 for t in ALL if t["n"]), "ich": ich_total, "ichMapped": ich_mapped,
             "atlasGenerated": atlas["meta"]["generated"], "fullMin": FULL_MIN, "oldShare": OLD_SHARE, "newShare": NEW_SHARE, "dense": DENSE,
             "monHi": MON_HI, "monLo": MON_LO, "natDom": {d: NAT_DOM[d] for d in "FLIGAX"}},
    "eras": [e["name"] for e in ERAS], "cats": CAT_SHORT,
    "doms": [{"id": d[0], "name": d[1], "long": d[2], "eg": d[3], "color": COLOR.get(d[0], "#6c6058")} for d in DOMS],
    "series": SERIES,
    "types": [{"id": x[0], "name": x[1], "tag": x[2], "series": x[3], "era": ERA3.get(x[4], ""), "dom": x[5],
               "color": "#6c6058" if x[0] == "BW" else COLOR[x[5]], "n": TYPE_N[x[0]]} for x in TYPES],
    "counties": [{"slug": c["slug"], "name": c["name"]} for c in COUNTIES],
    "towns": [[t["slug"], [c["name"] for c in COUNTIES].index(t["county"]), t["name"], t["n"], t["type"], t["center"][0], t["center"][1], t["code"]]
              for t in sorted(ALL, key=lambda t: t["code"])],
}
dump(os.path.join(HERE, "data", "index.json"), index)
shutil.copyfile(os.path.join(HERE, "data", "raw", "towns-10t.json"), os.path.join(HERE, "data", "towns-topo.json"))

# ---- 報告 ----
print("文資 %d 處；鄉鎮市區 %d 個，有文資的 %d 個。由地址補上鄉鎮：%d 處。" % (NAT_N, len(ALL), index["meta"]["withSites"], town_fixed))
b = collections.Counter("0 處" if t["n"] == 0 else "1–2 處" if t["n"] <= 2 else "3–9 處" if t["n"] <= 9 else "10–29 處" if t["n"] < 30 else "30 處以上" for t in ALL)
print("分布：", "、".join("%s %d 個" % (k, b[k]) for k in ["0 處", "1–2 處", "3–9 處", "10–29 處", "30 處以上"]))
print("各類型的鄉鎮數：")
for x in TYPES:
    eg = sorted((t for t in ALL if t["type"] == x[0]), key=lambda t: -t["n"])[:4]
    print("  %s %-8s %3d  %s" % (x[0], x[1], TYPE_N[x[0]], "、".join(t["county"] + t["name"] for t in eg)))
print("無形文資 %d 項，對得上鄉鎮的 %d 項。古蹟占比門檻：高 %.2f、低 %.2f。" % (ich_total, ich_mapped, MON_HI, MON_LO))
print("有車站連結的鄉鎮：%d 個。" % len(STATIONS))
print("座標與鄉鎮不一致：%d 處，清單在 reports/town-check.csv（界線經過簡化，邊界附近會有誤差）。" % len(check_rows))
for w in warn:
    print("注意：" + w)
