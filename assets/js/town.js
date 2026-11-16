/* 鄉鎮文資性格卡 — 網頁程式
 * 首頁（index.html）：#/ 查鄉鎮　#/types 類型總覽　#/types/<類型代碼>　#/about 說明
 * 鄉鎮頁（t/<縣市>/<鄉鎮>/index.html）：<body data-town="縣市/鄉鎮">，每個鄉鎮一個固定網址
 * 資料：data/index.json（類型、縣市、鄉鎮清單）、data/town/<縣市>/<鄉鎮>.json（卡片內容），皆由 tools/build.py 產生。
 * 這裡只負責畫面，不做任何性格計算。 */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var IDX = null, TY = {}, DOM = {};
  var ERA_SHORT = ["史前", "荷西", "明鄭", "清領", "日治", "戰後"];

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function getJSON(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  function yearText(o) { return (o.y < 0 ? "西元前 " + (-o.y) : o.y) + " 年" + (o.e ? "（推估）" : ""); }
  function turl(slug) { return "/t/" + slug + "/"; }
  function pct(a, b) { return b ? Math.round(100 * a / b) : 0; }
  function say(who, mood, text, i) {
    return '<div class="say say-' + who + '" style="--i:' + (i || 0) + '"><img src="/assets/characters/' + (who === "R" ? "arale-" : "allan-") + mood + '.webp" alt="" width="64" height="64" loading="lazy"><p><b>' +
      (who === "R" ? "阿拉蕾" : "Allan") + "</b>" + esc(text) + "</p></div>";
  }
  function duo(a, r) {
    return '<div class="duo" aria-label="Allan 和阿拉蕾"><div class="duo-b"><p class="bub bub-A"><b>Allan</b>' + a + '</p><p class="bub bub-R"><b>阿拉蕾</b>' + r + "</p></div>" +
      '<div class="duo-p"><img src="/assets/characters/allan-wave.webp" alt="Allan" width="560" height="657"><img src="/assets/characters/arale-wave.webp" alt="阿拉蕾" width="311" height="640"></div></div>';
  }
  function ticket(o) {
    return '<span class="tk lv' + o.k + '" aria-hidden="true"><b>' + Math.abs(o.y) + "</b><i>" + esc(IDX.eras[o.r]) + "</i></span>";
  }
  document.addEventListener("error", function (e) { /* 照片載入失敗 → 換成票卡樣式 */
    var t = e.target;
    if (t.tagName === "IMG" && t.dataset.fb) {
      var w = document.createElement("span"); w.innerHTML = ticket(JSON.parse(t.dataset.fb));
      var fig = t.closest(".card-ph"), fc = fig && fig.querySelector("figcaption"); if (fc) fc.remove();
      t.replaceWith(w.firstChild);
    }
  }, true);
  function nav(name) { [].forEach.call(document.querySelectorAll(".top-nav a"), function (a) { a.classList.toggle("cur", a.dataset.nav === name); }); }
  function townObj(r) { return { slug: r[0], county: IDX.counties[r[1]].name, ci: r[1], name: r[2], n: r[3], type: r[4], lat: r[5], lng: r[6] }; }
  function lcStyle(typeId) { return ' style="--lc:' + TY[typeId].color + '"'; }
  function tchip(slug, label, n, typeId) {
    return '<a class="tchip" href="' + turl(slug) + '"' + lcStyle(typeId) + '><i></i>' + esc(label) + "<small>" + n + " 處</small></a>";
  }

  /* ================= 首頁 ================= */
  function typeTile(t, cur) {
    return '<li><a class="ty' + (cur === t.id ? " cur" : "") + '" href="#/types/' + t.id + '"' + lcStyle(t.id) + '><span class="ty-k">' +
      esc(t.series === "full" ? t.era + " × " + DOM[t.dom].name : IDX.series[t.series]) + "</span><h3>" + esc(t.name) + '</h3><p class="ty-t">' + esc(t.tag) +
      '</p><p class="ty-n"><b>' + t.n + "</b>個鄉鎮市區</p></a></li>";
  }
  function typeGrids(cur) {
    var g = { full: [], solo: [], blank: [] };
    IDX.types.forEach(function (t) { g[t.series].push(typeTile(t, cur)); });
    return '<div class="sec-h"><h2>性格十二型</h2><p>3 處以上文資的鄉鎮：時代重心 × 主調</p></div><ul class="ty-grid">' + g.full.join("") + "</ul>" +
      '<div class="sec-h" style="margin-top:28px"><h2>獨苗系列</h2><p>只有 1–2 處文資，由其中一處當主角</p></div><ul class="ty-grid g5">' + g.solo.join("") + "</ul>" +
      '<div class="sec-h" style="margin-top:28px"><h2>留白系列</h2><p>沒有有形文資的鄉鎮，也有一張卡</p></div><ul class="ty-grid g2">' + g.blank.join("") + "</ul>";
  }
  function home() {
    nav("home");
    document.title = "鄉鎮文資性格卡｜Allan 和阿拉蕾幫你的家鄉算性格";
    var m = IDX.meta;
    var copts = IDX.counties.map(function (c, i) { return '<option value="' + i + '">' + esc(c.name) + "</option>"; }).join("");
    app.innerHTML =
      '<section class="home-hero"><div class="wrap"><div>' +
      '<p class="kicker">全臺 ' + m.towns + " 個鄉鎮市區・" + m.sites.toLocaleString() + " 處文化資產</p>" +
      "<h1>你的家鄉，<br>是哪一種文資性格？</h1>" +
      '<p class="home-sub">選一個鄉鎮市區，領一張算出來的性格卡。</p>' +
      '<p class="lede">廟多、老宅多，還是工廠和宿舍多？我們把每個鄉鎮的古蹟與歷史建築攤開來數，照固定規則分成 <b>' + IDX.types.length + "</b> 種性格。沒有文資的鄉鎮也有一張。</p>" +
      '<div class="finder">' +
      '<div><label for="fq">直接搜尋</label><div class="f-search"><input id="fq" type="search" autocomplete="off" placeholder="輸入鄉鎮市區，例如：鹿港、中西區、田寮" aria-controls="fsug" aria-expanded="false"><div id="fsug" class="f-sug" role="listbox" hidden></div></div></div>' +
      '<div><label for="fc">或從選單挑</label><div class="f-row"><select id="fc" aria-label="縣市"><option value="">縣市</option>' + copts + '</select><select id="ft" aria-label="鄉鎮市區" disabled><option value="">鄉鎮市區</option></select><button class="btn btn-solid" id="fgo" type="button">看這張卡</button></div></div>' +
      '<div class="f-alt"><button class="btn" id="floc" type="button">用我的位置</button><button class="btn" id="frand" type="button">隨便抽一張</button><span class="f-msg" id="fmsg">位置只在你的瀏覽器裡比對，不會上傳。</span></div>' +
      "</div></div>" +
      duo("我是 Allan。每個鄉鎮留下來的文資不一樣，性格也就不一樣。先查查你的家鄉吧！", "我是阿拉蕾！我賭我家是「一廟定江山」，你家呢？查完記得貼給朋友比一比！") +
      "</div></section>" +
      '<section class="wrap sec">' + typeGrids() + '<p class="hint" style="margin-top:16px">按任何一種類型，看有哪些鄉鎮。類型是用資料照規則算的，算法寫在「說明」。</p></section>';
    var fc = document.getElementById("fc"), ft = document.getElementById("ft"), fq = document.getElementById("fq"), sug = document.getElementById("fsug"), msg = document.getElementById("fmsg");
    fc.onchange = function () {
      var ci = fc.value;
      ft.innerHTML = '<option value="">鄉鎮市區</option>' + (ci === "" ? "" : IDX.towns.filter(function (r) { return r[1] === +ci; }).map(function (r) { return '<option value="' + r[0] + '">' + esc(r[2]) + "（" + r[3] + " 處）</option>"; }).join(""));
      ft.disabled = ci === "";
    };
    ft.onchange = function () { if (ft.value) location.href = turl(ft.value); };
    document.getElementById("fgo").onclick = function () { if (ft.value) location.href = turl(ft.value); else (fc.value === "" ? fc : ft).focus(); };
    document.getElementById("frand").onclick = function () { location.href = turl(IDX.towns[Math.floor(Math.random() * IDX.towns.length)][0]); };
    function norm(s) { return s.replace(/台/g, "臺").replace(/\s/g, ""); }
    function search() {
      var q = norm(fq.value), hits = [];
      if (q) {
        IDX.towns.forEach(function (r) {
          var c = IDX.counties[r[1]].name, full = c + r[2], p = full.indexOf(q);
          if (p >= 0) hits.push([r[2].indexOf(q) === 0 ? 0 : (p === 0 ? 1 : 2), r]);
        });
        hits.sort(function (a, b) { return a[0] - b[0] || b[1][3] - a[1][3]; });
      }
      sug.innerHTML = hits.slice(0, 12).map(function (h, i) {
        var r = h[1];
        return '<a role="option" href="' + turl(r[0]) + '"' + (i === 0 ? ' class="cur"' : "") + "><span><b>" + esc(r[2]) + "</b>　" + esc(IDX.counties[r[1]].name) + "</span><small>" + esc(TY[r[4]].name) + "・" + r[3] + " 處</small></a>";
      }).join("") || (q ? '<a><span>找不到「' + esc(fq.value) + "」，試試只打兩個字</span></a>" : "");
      sug.hidden = !q; fq.setAttribute("aria-expanded", q ? "true" : "false");
    }
    fq.oninput = search;
    fq.onkeydown = function (e) { if (e.key === "Enter") { var a = sug.querySelector("a[href]"); if (a) location.href = a.getAttribute("href"); } if (e.key === "Escape") { sug.hidden = true; } };
    document.addEventListener("click", function (e) { if (!e.target.closest(".f-search")) sug.hidden = true; });
    document.getElementById("floc").onclick = function () {
      if (!navigator.geolocation) { msg.textContent = "這個瀏覽器不支援定位，請改用搜尋或選單。"; return; }
      msg.textContent = "定位中…";
      navigator.geolocation.getCurrentPosition(function (pos) {
        getJSON("/data/towns-topo.json").then(function (topo) {
          var code = townAt(topo, pos.coords.longitude, pos.coords.latitude);
          var r = code && IDX.towns.filter(function (x) { return x[7] === code; })[0];
          if (r) location.href = turl(r[0]); else msg.textContent = "你的位置不在任何一個鄉鎮市區的範圍內，請改用搜尋或選單。";
        }).catch(function () { msg.textContent = "界線資料載入失敗，請改用搜尋或選單。"; });
      }, function () { msg.textContent = "沒有取得位置（可能是沒有同意定位）。請改用搜尋或選單。"; }, { timeout: 10000, maximumAge: 600000 });
    };
  }
  /* 用鄉鎮界線（TopoJSON）判斷座標落在哪個鄉鎮；只在瀏覽器裡算 */
  function townAt(topo, lng, lat) {
    var sc = topo.transform.scale, tr = topo.transform.translate, arcs = {};
    function arc(i) {
      var k = i < 0 ? ~i : i;
      if (!arcs[k]) { var x = 0, y = 0; arcs[k] = topo.arcs[k].map(function (p) { x += p[0]; y += p[1]; return [x * sc[0] + tr[0], y * sc[1] + tr[1]]; }); }
      return i < 0 ? arcs[k].slice().reverse() : arcs[k];
    }
    function inRing(idx) {
      var pts = []; idx.forEach(function (i) { var a = arc(i); pts = pts.concat(pts.length ? a.slice(1) : a); });
      var ins = false;
      for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        if ((pts[i][1] > lat) !== (pts[j][1] > lat) && lng < (pts[j][0] - pts[i][0]) * (lat - pts[i][1]) / (pts[j][1] - pts[i][1]) + pts[i][0]) ins = !ins;
      }
      return ins;
    }
    var gs = topo.objects.towns.geometries;
    for (var g = 0; g < gs.length; g++) {
      var polys = gs[g].type === "MultiPolygon" ? gs[g].arcs : [gs[g].arcs];
      for (var p = 0; p < polys.length; p++) {
        if (inRing(polys[p][0]) && !polys[p].slice(1).some(inRing)) return gs[g].properties.TOWNCODE;
      }
    }
    return null;
  }

  /* ================= 類型總覽 ================= */
  function types(id) {
    nav("types");
    document.title = "性格類型總覽｜鄉鎮文資性格卡";
    var t = TY[id], list = "";
    if (t) {
      var by = {};
      IDX.towns.forEach(function (r) { if (r[4] === id) (by[r[1]] = by[r[1]] || []).push(r); });
      list = '<div class="ty-list" id="tylist"' + lcStyle(id) + '><p class="kicker">' + esc(IDX.series[t.series]) + (t.series === "full" ? "・" + esc(t.era) + " × " + esc(DOM[t.dom].long) : "") +
        "</p><h3>" + esc(t.name) + "</h3><p>" + esc(t.tag) + "共 " + t.n + ' 個鄉鎮市區。</p><dl style="margin-top:10px">' +
        Object.keys(by).map(function (ci) {
          return '<div class="ty-c"><dt>' + esc(IDX.counties[ci].name) + "</dt><dd>" + by[ci].sort(function (a, b) { return b[3] - a[3]; }).map(function (r) { return tchip(r[0], r[2], r[3], id); }).join("") + "</dd></div>";
        }).join("") + "</dl></div>";
    }
    app.innerHTML = '<section class="wrap sec"><p class="kicker">全臺 ' + IDX.meta.towns + " 個鄉鎮市區，" + IDX.types.length + ' 種性格</p><h1 style="font-size:clamp(32px,6vw,52px);margin:6px 0 14px">性格類型總覽</h1>' +
      '<div class="talk" style="margin-bottom:22px">' + say("A", "talk", "3 處以上的鄉鎮看兩件事：文資偏哪個時代、哪一類最多，組成十二型。只有 1–2 處或完全沒有的鄉鎮，另外有自己的系列。", 0) +
      say("R", "present", "按一種類型，就能看到全臺有哪些鄉鎮跟你同一國！", 1) + "</div>" +
      typeGrids(id) + list + "</section>";
    if (t) { var el = document.getElementById("tylist"); if (el) el.scrollIntoView({ block: "start" }); } else window.scrollTo(0, 0);
  }

  /* ================= 說明 ================= */
  function about() {
    nav("about");
    document.title = "說明｜鄉鎮文資性格卡";
    var m = IDX.meta, nd = m.natDom;
    app.innerHTML = '<article class="wrap about"><h1>說明</h1>' +
      "<p>「鄉鎮文資性格卡」把全臺 " + m.sites.toLocaleString() + " 處有形文化資產依所在的鄉鎮市區分組，用固定的規則算出每個鄉鎮的「性格」。性格只描述<b>已經指定或登錄的文化資產</b>，不代表當地歷史的全貌；沒有文資的鄉鎮，是名單上還沒有，不是沒有故事。</p>" +
      "<h2>性格怎麼算</h2><ul>" +
      "<li><b>主調</b>：每處文資先歸到信仰、生活、產業、官方、考古其中一類。先看官方登記的建築類型（寺廟、宅第、產業、衙署等）；登記為「其他設施」的，改看文資知識網站整理的主題。</li>" +
      "<li><b>3 處以上的鄉鎮（性格十二型）</b>：時代重心 × 主調。清領以前的文資占 " + Math.round(m.oldShare * 100) + "% 以上（而且不比戰後少）算「清領以前」；否則戰後占 " + Math.round(m.newShare * 100) + "% 以上算「戰後」；其餘算「日治」。主調取四類中處數最多的，同數時取相對全臺平均更突出的一類。</li>" +
      "<li><b>1–2 處的鄉鎮（獨苗系列）</b>：以其中一處當主角（古蹟優先，其次有照片、年代早），依主角的主調分五種。</li>" +
      "<li><b>沒有有形文資的鄉鎮（留白系列）</b>：對得上無形文資的是「無形派掌門」，都沒有的是「等待被發現」。</li>" +
      "<li><b>徽章</b>：" + m.dense[0] + " 處以上是「文資大戶」、" + m.dense[1] + " 處以上「小有規模」；古蹟占 " + Math.round(m.monHi * 100) + "% 以上是「金字招牌」、" + Math.round(m.monLo * 100) + "% 以下是「歷史建築為主」。</li></ul>" +
      "<p>全臺各主調的處數：" + IDX.doms.map(function (d) { return d.name + " " + nd[d.id]; }).join("、") + "。每張卡的「為什麼是這個類型」都列出該鄉鎮實際的數字。</p>" +
      "<h2>幾個要知道的限制</h2><ul>" +
      "<li>無形文資沒有鄉鎮欄位，是用場館地址與展演地點的文字比對鄉鎮名稱：" + m.ich + " 項中對得上 " + m.ichMapped + " 項。對不上的不會出現在卡片上。</li>" +
      "<li>「最近的文資」是直線距離；沒有文資的鄉鎮從行政區的幾何中心起算。</li>" +
      "<li>「跟你最像的鄉鎮」比的是時代比例、主調比例、古蹟比例與處數，優先找不同縣市、同一種類型的。</li>" +
      "<li>嘉義市的文資在主檔沒有填區，是從官方地址補上東區或西區。</li></ul>" +
      "<h2>資料來源與授權</h2><ul>" +
      "<li>文化資產清單、座標、年代、建築類型：文化部文化資產局國家文化資產網，經文資知識網站與文資地圖集整理（主檔日期 " + esc(m.atlasGenerated) + "）。</li>" +
      "<li>鄉鎮市區清單：內政部國土測繪中心。鄉鎮市區界線：內政部國土測繪中心「鄉鎮市區界線（TWD97 經緯度）」，取自 taiwan-atlas 2021.9.20 的簡化版。此開放資料依政府資料開放授權條款（Open Government Data License）進行公眾釋出，使用者於遵守本條款各項規定之前提下，得利用之。政府資料開放授權條款：<a href=\"https://data.gov.tw/license\" target=\"_blank\" rel=\"noopener\">https://data.gov.tw/license</a></li>" +
      "<li>照片：Wikimedia Commons，各張的作者與授權條款標示在照片上；下載的卡片圖片也印有照片的作者與授權。</li>" +
      "<li>車站連結：連到姊妹站「搭火車逛文資」。</li></ul>" +
      "<h2>隱私</h2><p>「用我的位置」只在你的瀏覽器裡把座標和鄉鎮界線比對，不會把位置傳到任何伺服器。本站沒有後台、沒有帳號，也不記錄你查了哪個鄉鎮。</p>" +
      '<p class="hint" style="margin-top:20px">資料產生日期：' + esc(m.generated) + "</p></article>";
    window.scrollTo(0, 0);
  }

  /* ================= 鄉鎮頁 ================= */
  function photoFig(o, flag) {
    var cap = o.p ? "<figcaption>攝影：" + (o.p.pg ? '<a href="' + esc(o.p.pg) + '" target="_blank" rel="noopener">' + esc(o.p.a || "Wikimedia Commons") + "</a>" : esc(o.p.a)) + "｜" +
      (o.p.lu ? '<a href="' + esc(o.p.lu) + '" target="_blank" rel="noopener">' + esc(o.p.lic) + "</a>" : esc(o.p.lic)) + "</figcaption>" : "";
    var im = o.p ? '<img src="' + esc(o.p.l) + '" alt="" loading="lazy" decoding="async" data-fb="' + esc(JSON.stringify({ k: o.k, y: o.y, r: o.r })) + '">' : ticket(o);
    return '<figure class="card-ph lv' + o.k + '">' + im + (flag ? '<span class="card-flag">' + esc(flag) + "</span>" : "") + cap + "</figure>";
  }
  function siteCard(o, i, flag, extra, lead) {
    return '<li class="card' + (lead ? " lead" : "") + '" style="--i:' + i + '">' + photoFig(o, flag) + '<div class="card-b"><p class="card-meta"><span class="lvt lv' + o.k + '">' + esc(IDX.cats[o.k]) + "</span><span>" +
      esc(yearText(o)) + "・" + esc(IDX.eras[o.r]) + "</span></p><h3>" + esc(o.n) + '</h3><p class="card-s">' + esc(o.s) + "</p>" + (extra || "") +
      '<p class="card-a"><a class="btn" href="' + esc(o.u) + '" target="_blank" rel="noopener">到知識網站看介紹</a></p></div></li>';
  }
  function chart(d) {
    if (!d.n) return "";
    var er = '<div class="ch"><h3>時代組成</h3><div class="stack" role="img" aria-label="' + esc(d.eras.map(function (e) { return IDX.eras[e[0]] + " " + e[1] + " 處"; }).join("、")) + '">' +
      d.eras.map(function (e) { return '<i style="flex:' + e[1] + ";--c:var(--e" + e[0] + ')"></i>'; }).join("") + '</div><ul class="lg">' +
      d.eras.map(function (e) { return '<li><i style="--c:var(--e' + e[0] + ')"></i>' + ERA_SHORT[e[0]] + " <b>" + e[1] + "</b></li>"; }).join("") + "</ul></div>";
    var max = Math.max.apply(null, d.doms.map(function (x) { return x[1]; }));
    var dm = '<div class="ch"><h3>類型組成</h3><ul class="bars">' + d.doms.map(function (x) {
      return '<li class="' + (x[1] === max ? "max" : "") + '"><span class="k">' + esc(DOM[x[0]].name) + '</span><span class="bar"><i style="--w:' + (100 * x[1] / max) + "%;--c:var(--d-" + x[0] + ')"></i></span><span class="v"><b>' + x[1] + "</b> 處・" + pct(x[1], d.n) + "%</span></li>";
    }).join("") + "</ul></div>";
    return er + dm;
  }
  function town(slug) {
    nav("");
    getJSON("/data/town/" + slug + ".json").then(function (d) {
      var t = TY[d.type], S = {};
      d.sites.forEach(function (o) { S[o.i] = o; });
      var mon = 0; d.cats.forEach(function (c) { if (c[0] <= 1) mon += c[1]; });
      var chips = (t.series === "full" ? ["時代重心：" + t.era, "主調：" + DOM[t.dom].name] : []).map(function (c) { return "<span>" + esc(c) + "</span>"; }).join("") +
        d.badges.map(function (b) { return '<span class="b2">' + esc(b) + "</span>"; }).join("");
      var right;
      if (d.n) {
        right = '<dl class="nums"><div><dt>有形文資</dt><dd><b>' + d.n + "</b>處</dd></div><div><dt>全" + esc(d.county.slice(-1)) + "排名</dt><dd><b>" + d.rank.county + "</b>／" + d.rank.countyN +
          "</dd></div><div><dt>古蹟</dt><dd><b>" + mon + "</b>處</dd></div>" + (d.ichN ? "<div><dt>無形文資</dt><dd><b>" + d.ichN + "</b>項</dd></div>" : "") + "</dl>" + chart(d);
      } else {
        right = '<dl class="nums"><div><dt>有形文資</dt><dd><b>0</b>處</dd></div><div><dt>無形文資</dt><dd><b>' + d.ichN + "</b>項</dd></div><div><dt>最近的文資</dt><dd><b>" + d.near[0].km.toFixed(1) + "</b>公里</dd></div></dl>" +
          '<p class="pc-empty">' + (d.ichN ? "這裡的文資不是房子，是人：祭典、手藝與表演，要在對的時間、跟著對的人才看得到。" : "卡片上沒有圖表，因為真的沒有資料可以畫。最近的文資在隔壁：") + "</p>" +
          '<ul class="nearl">' + (d.ichN ? d.ich.slice(0, 4).map(function (i) { return '<li><a href="' + esc(i.u || i.b) + '" target="_blank" rel="noopener">' + esc(i.n) + "</a><span>" + esc(i.t) + "</span></li>"; }) :
            d.near.map(function (o) { return '<li><a href="' + esc(o.u) + '" target="_blank" rel="noopener">' + esc(o.n) + "</a><span>" + esc(o.tn) + "・" + o.km.toFixed(1) + " 公里</span></li>"; })).join("") + "</ul>";
      }
      var html = '<div class="town"' + lcStyle(d.type) + '><div class="wrap"><a class="back" href="/">‹ 換一個鄉鎮</a>' +
        '<section class="pc" id="card"><div class="pc-a"><p class="pc-where"><span class="plate">' + esc(d.county) + '</span><span class="pc-series">' + esc(IDX.series[t.series]) + "</span></p>" +
        "<h1>" + esc(d.name) + '</h1><p class="pc-is">的文資性格是</p><p class="pc-type">' + esc(t.name) + '</p><p class="pc-tag">' + esc(t.tag) + "</p>" +
        (chips ? '<p class="pc-chips">' + chips + "</p>" : "") + '<p class="pc-desc">' + esc(d.desc) + "</p></div>" +
        '<div class="pc-b">' + right + '<p class="pc-foot"><span>鄉鎮文資性格卡</span><span>cultural-town.123hi.org</span></p></div></section>';

      /* 對話＋分享 */
      var url = location.origin + turl(d.slug), stxt = d.county + d.name + "的文資性格是「" + t.name + "」";
      html += '<div class="under"><div class="talk">' + d.talk.map(function (l, i) { return say(l[0], l[1], l[2], i); }).join("") + "</div>" +
        '<aside class="share" aria-label="分享這張卡"><h2>把這張卡貼出去</h2>' +
        '<a class="btn btn-lc" href="/card/' + esc(d.slug) + '.jpg" download="' + esc(d.county + d.name) + '-文資性格卡.jpg">下載卡片圖片</a>' +
        '<button class="btn" type="button" id="shcopy">複製連結</button>' +
        '<div class="share-row"><a class="btn" target="_blank" rel="noopener" href="https://social-plugins.line.me/lineit/share?url=' + encodeURIComponent(url) + '">LINE</a>' +
        '<a class="btn" target="_blank" rel="noopener" href="https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url) + '">Facebook</a></div>' +
        '<button class="btn" type="button" id="shmore" hidden>其他分享方式</button><p class="share-msg" id="shmsg" aria-live="polite"></p></aside></div>';

      /* 主角／代表文資 */
      var oldest = d.oldest && S[d.oldest];
      if (d.series === "full") {
        html += '<section class="sec"><div class="sec-h"><h2>代表文資</h2><p>先挑有照片的，再比是否屬於主調、等級、年代</p></div><ul class="cards">' +
          d.reps.map(function (id, i) { return siteCard(S[id], i, id === d.oldest ? "全區最老" : ""); }).join("") + "</ul></section>";
      } else if (d.series === "solo") {
        html += '<section class="sec"><div class="sec-h"><h2>' + (d.n === 1 ? "全區唯一的一處" : "全區僅有的兩處") + '</h2></div><ul class="cards ' + (d.n === 1 ? "one" : "") + '" style="' + (d.n === 2 ? "grid-template-columns:repeat(2,1fr)" : "") + '">' +
          d.reps.map(function (id, i) { return siteCard(S[id], i, i === 0 ? "主角" : "", "", i === 0); }).join("") + "</ul></section>";
      }
      /* 最老的一處＋意外的事實 */
      var facts = [];
      if (oldest && d.n > 1) {
        facts.push('<li><div class="fact" style="--i:0"><img class="fact-face" src="/assets/characters/allan-think.webp" alt="" loading="lazy"><span class="fact-k">最老的一處</span><span class="fact-big"><b>' +
          (oldest.y < 0 ? "前 " + (-oldest.y) : oldest.y) + "</b><i>年" + (oldest.e ? "（推估）" : "") + '</i></span><span class="fact-t"><a href="' + esc(oldest.u) + '" target="_blank" rel="noopener">' + esc(oldest.n) + "</a>：" + esc(oldest.yt || oldest.s) + "</span></div></li>");
      }
      var faces = ["arale-surprised", "allan-wink", "arale-think"];
      d.facts.slice(0, oldest && d.n > 1 ? 2 : 3).forEach(function (f, i) {
        facts.push('<li><div class="fact" style="--i:' + (i + 1) + '"><img class="fact-face" src="/assets/characters/' + faces[i] + '.webp" alt="" loading="lazy"><span class="fact-k">' + esc(i === 0 ? "沒想到吧・" + f.k : f.k) +
          '</span><span class="fact-big"><b>' + esc(f.big) + "</b><i>" + esc(f.unit) + '</i></span><span class="fact-t">' + esc(f.t) + "</span></div></li>");
      });
      if (facts.length) html += '<section class="sec"><div class="sec-h"><h2>' + (oldest && d.n > 1 ? "最老的一處，和你可能沒想到的事" : "你可能沒想到的事") + '</h2></div><ul class="facts">' + facts.join("") + "</ul></section>";

      /* 最近的文資（獨苗、留白） */
      var nearHtml = "";
      if (d.near.length) {
        nearHtml = '<section class="sec"><div class="sec-h"><h2>' + (d.n ? "想多看幾處？最近的在這裡" : "最近的文資在隔壁") + "</h2><p>直線距離，從" + (d.n ? "主角那一處" : "行政區的幾何中心") + '起算；每個鄉鎮只列最近的一處</p></div><ul class="cards">' +
          d.near.map(function (o, i) {
            return siteCard(o, i, o.tn, '<p class="card-km"><b>' + o.km.toFixed(1) + '</b>公里外・<a href="' + turl(o.ts) + '">看' + esc(o.tn) + "的性格卡</a></p>");
          }).join("") + "</ul></section>";
      }
      /* 無形文資 */
      var ichHtml = "";
      if (d.ich.length) {
        ichHtml = '<section class="sec"><div class="sec-h"><h2>在這裡傳承的無形文資</h2><p>共 ' + d.ichN + " 項" + (d.ichN > d.ich.length ? "，列出 " + d.ich.length + " 項" : "") + '；依場館地址與展演地點比對</p></div><ul class="ich">' +
          d.ich.map(function (i) { return '<li><a href="' + esc(i.u || i.b) + '" target="_blank" rel="noopener"><small>' + esc(i.t) + "</small><b>" + esc(i.n) + "</b><span>" + esc(i.s) + "</span></a></li>"; }).join("") + "</ul></section>";
      }
      html += d.n ? nearHtml + ichHtml : ichHtml + nearHtml; /* 沒有有形文資時，無形文資排前面 */
      /* 最像的鄉鎮＋鄰居 */
      if (d.similar) {
        var s = d.similar;
        html += '<section class="sec"><div class="sec-h"><h2>跟你最像的鄉鎮</h2><p>全臺性格最接近的另一個鄉鎮市區</p></div><div class="twin"><a class="twin-p" href="' + turl(s.slug) + '"' + lcStyle(s.type) + "><small>" + esc(s.c) + "</small><b>" + esc(s.n) +
          "</b><span>" + esc(TY[s.type].name) + '</span></a><div class="twin-t"><p>' + esc(s.why) + '</p><p class="hint">隔壁鄰居的性格：</p><p class="nbs">' +
          d.nb.map(function (x) { return tchip(x.slug, x.c + x.n + "・" + TY[x.type].name, x.cnt, x.type); }).join("") + "</p></div></div></section>";
      }
      /* 車站 */
      if (d.rail.length) {
        html += '<section class="sec"><div class="sec-h"><h2>搭火車來</h2><p>區內的臺鐵車站，連到姊妹站「搭火車逛文資」</p></div><p class="nbs">' +
          d.rail.map(function (r) { return '<a class="tchip" href="' + esc(r.u) + '" target="_blank" rel="noopener" style="--lc:var(--teal)"><i></i>' + esc(r.n) + "站<small>" + esc(r.ln) + "・步行 15 分鐘內 " + r.c + " 處</small></a>"; }).join("") + "</p></section>";
      }
      /* 為什麼＋全部文資 */
      html += '<section class="sec"><details class="why" open><summary>為什麼是這個類型</summary><dl class="why-b">' + d.why.map(function (w) { return "<dt>" + esc(w[0]) + "</dt><dd>" + esc(w[1]) + "</dd>"; }).join("") +
        '<p class="hint">規則對每個鄉鎮都一樣，完整算法見<a href="/#/about">說明</a>。</p></dl></details></section>';
      if (d.n > (d.series === "full" ? 0 : 99)) {
        html += '<section class="sec"><details class="why"' + (d.n <= 12 ? " open" : "") + "><summary>全部 " + d.n + ' 處文資</summary><ul class="rows">' + d.sites.map(function (o) {
          return '<li><a href="' + esc(o.u) + '" target="_blank" rel="noopener"><span class="lvt lv' + o.k + '">' + esc(IDX.cats[o.k]) + "</span><b>" + esc(o.n) + '<span class="s">' + esc(o.s) + '</span></b><span class="y">' + esc(yearText(o)) + "</span></a></li>";
        }).join("") + "</ul></details></section>";
      }
      html += "</div></div>";
      app.innerHTML = html;
      document.getElementById("shcopy").onclick = function () {
        var m = document.getElementById("shmsg");
        (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function () { m.textContent = "已複製，貼到聊天室會出現這張卡的預覽圖。"; }, function () { m.textContent = url; });
      };
      if (navigator.share) {
        var more = document.getElementById("shmore"); more.hidden = false;
        more.onclick = function () { navigator.share({ title: stxt, text: stxt + "，你的家鄉呢？", url: url }).catch(function () {}); };
      }
    }).catch(function () {
      app.innerHTML = '<div class="wrap about"><h1>找不到這張卡</h1>' + say("A", "scratch", "這個網址沒有對應的鄉鎮市區，可能是連結打錯了。", 0) + '<p style="margin-top:16px"><a class="btn btn-solid" href="/">回首頁查鄉鎮</a></p></div>';
    });
  }

  /* ================= 啟動 ================= */
  function route() {
    var h = (location.hash || "#/").slice(2).split("/");
    if (h[0] === "types") types(h[1]); else if (h[0] === "about") about(); else home();
  }
  getJSON("/data/index.json").then(function (d) {
    IDX = d;
    d.types.forEach(function (t) { TY[t.id] = t; });
    d.doms.forEach(function (x) { DOM[x.id] = x; });
    var slug = document.body.dataset.town;
    if (slug) town(slug); else { window.addEventListener("hashchange", route); route(); }
  }).catch(function () { app.innerHTML = '<p class="loading wrap">資料載入失敗，請重新整理。</p>'; });
})();
