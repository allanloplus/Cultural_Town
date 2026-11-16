/* 產生社群預覽圖與下載用的卡片圖片（需要 Node 與 Playwright；照片與字型要連網）
 *
 *   node tools/render.js                         全部 368 個鄉鎮＋首頁預覽圖
 *   node tools/render.js tainan-city/west-central yunlin-county/xiluo   只做指定的鄉鎮
 *
 * 會自己在本機開一個臨時的網頁伺服器，用瀏覽器開 tools/card.html 截圖：
 *   og/<縣市>/<鄉鎮>.jpg    1200×630，貼連結時的預覽圖
 *   card/<縣市>/<鄉鎮>.jpg  1080×1350，「下載卡片圖片」
 *   assets/og.jpg           首頁的預覽圖
 * 先跑過 python3 tools/build.py 再跑這支。 */
const http = require("http"), fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const ROOT = path.dirname(__dirname);
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".webp": "image/webp", ".jpg": "image/jpeg" };

(async () => {
  const server = http.createServer((req, res) => {
    const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0]));
    if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "Content-Type": MIME[path.extname(p)] || "application/octet-stream" });
    fs.createReadStream(p).pipe(res);
  });
  await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
  const base = "http://127.0.0.1:" + server.address().port;
  const index = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "index.json"), "utf8"));
  const want = process.argv.slice(2);
  const slugs = want.length ? want : index.towns.map((t) => t[0]);
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  async function shot(url, w, h, out) {
    await page.setViewportSize({ width: w, height: h });
    await page.goto(base + url);
    await page.waitForSelector("body[data-ready]", { timeout: 60000 });
    fs.mkdirSync(path.dirname(out), { recursive: true });
    await page.screenshot({ path: out, type: "jpeg", quality: 86 });
  }
  if (!want.length) await shot("/tools/card.html?mode=site", 1200, 630, path.join(ROOT, "assets", "og.jpg"));
  let n = 0;
  for (const s of slugs) {
    await shot("/tools/card.html?mode=og&slug=" + s, 1200, 630, path.join(ROOT, "og", s + ".jpg"));
    await shot("/tools/card.html?mode=card&slug=" + s, 1080, 1350, path.join(ROOT, "card", s + ".jpg"));
    if (++n % 20 === 0 || n === slugs.length) console.log("已完成 " + n + "／" + slugs.length);
  }
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
