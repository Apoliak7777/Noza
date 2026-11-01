/* Náhľady webu pre klienta + automatická kontrola (konzola, chýbajúce súbory, formulár, galéria, menu).
 *
 * Spustenie (web musí bežať, napr. cez SPUSTIT_WEB.bat):
 *   node nastroje\screenshoty.js            (BASE=http://localhost:8097 predvolene)
 *
 * Výstup: nahlady\ — celé stránky ako PNG (sk-desktop, sk-mobil, de-desktop, de-mobil), tie isté rozrezané na JPEG kusy
 *         pre WhatsApp (sk-desktop-1.jpg …), plus sk-mobil-menu.png a sk-galeria.png (lightbox)
 * Používa playwright-core z globálneho @playwright/cli (alebo mcp) a Chromium z %LOCALAPPDATA%\ms-playwright (Chrome na stroji nie je).
 */
const fs = require("fs");
const path = require("path");
function nacitajPlaywright() {
  const kandidati = ["playwright-core", "playwright"];
  for (const k of kandidati) { try { return require(k); } catch (e) { /* skús globálne */ } }
  const koren = path.join(process.env.APPDATA || "", "npm", "node_modules");
  for (const k of kandidati) {
    const g = path.join(koren, k);
    if (fs.existsSync(g)) return require(g);
  }
  // playwright-core býva zabalený vnútri globálneho @playwright/cli alebo @playwright/mcp
  const pw = path.join(koren, "@playwright");
  if (fs.existsSync(pw)) {
    for (const bal of fs.readdirSync(pw)) {
      for (const k of kandidati) {
        const g = path.join(pw, bal, "node_modules", k);
        if (fs.existsSync(g)) return require(g);
      }
    }
  }
  throw new Error("playwright-core sa nenašiel — nainštaluj: npm i -g playwright-core");
}
const { chromium } = nacitajPlaywright();

const BASE = process.env.BASE || "http://localhost:8097";
const OUT = path.join(__dirname, "..", "nahlady");
fs.mkdirSync(OUT, { recursive: true });

function najdiChromium() {
  if (process.env.CHROME) return process.env.CHROME;
  const koren = path.join(process.env.LOCALAPPDATA || "", "ms-playwright");
  if (!fs.existsSync(koren)) return undefined;
  const kandidati = fs.readdirSync(koren).filter((d) => d.startsWith("chromium-")).sort().reverse();
  for (const k of kandidati) {
    const exe = path.join(koren, k, "chrome-win", "chrome.exe");
    if (fs.existsSync(exe)) return exe;
    const exe2 = path.join(koren, k, "chrome-win64", "chrome.exe");
    if (fs.existsSync(exe2)) return exe2;
  }
  return undefined;
}

const chyby = [];

// stránku rozreže na JPEG kusy (na WhatsApp sa jeden 9000 px vysoký obrázok nedá pozerať)
async function kusy(page, sirka, vyska, krok, prefix) {
  for (const f of fs.readdirSync(OUT)) if (f.startsWith(prefix + "-") && f.endsWith(".jpg")) fs.unlinkSync(path.join(OUT, f));
  let n = 0;
  for (let y = 0; y < vyska; y += krok, n++) {
    const h = Math.min(krok, vyska - y);
    if (h < 120) break;
    await page.screenshot({ path: path.join(OUT, `${prefix}-${n + 1}.jpg`), type: "jpeg", quality: 88, fullPage: true, clip: { x: 0, y, width: sirka, height: h } });
  }
  console.log(`  ${prefix}-1..${n}.jpg`);
}
async function novaStranka(context) {
  const page = await context.newPage();
  page.on("console", (m) => {
    const url = (m.location() && m.location().url) || "";
    if (url.includes("kontakt.php")) return; // na lokálnom/statickom hostingu PHP nebeží, to je očakávané
    if (m.type() === "error" || m.type() === "warning") chyby.push(`[konzola ${m.type()}] ${m.text()}`);
  });
  page.on("pageerror", (e) => chyby.push(`[pageerror] ${e.message}`));
  page.on("requestfailed", (r) => { if (!r.url().startsWith("mailto:")) chyby.push(`[request failed] ${r.url()} ${r.failure() && r.failure().errorText} (stránka ${page.url()}, viewport ${JSON.stringify(page.viewportSize())})`); });
  page.on("response", (r) => { if (r.status() >= 400 && !r.url().endsWith("kontakt.php")) chyby.push(`[HTTP ${r.status()}] ${r.url()}`); });
  return page;
}

async function odhal(page) {
  // odhaliť sekcie + dotiahnuť lenivé obrázky (celostránkový screenshot inak ukáže prázdne miesta)
  await page.evaluate(async () => {
    document.querySelectorAll(".reveal, .step").forEach((e) => e.classList.add("is-visible"));
    document.querySelectorAll("img[loading='lazy']").forEach((i) => { i.loading = "eager"; });
    const h = document.documentElement.scrollHeight;
    for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)); }
    window.scrollTo(0, 0);
    await Promise.all(Array.from(document.images).filter((i) => !i.complete).map((i) => new Promise((r) => { i.onload = i.onerror = r; })));
  });
  await page.waitForTimeout(500);
}

(async () => {
  const exe = najdiChromium();
  console.log("Chromium:", exe || "(z registra playwright-core)");
  const browser = await chromium.launch({ headless: true, executablePath: exe });

  for (const jazyk of ["sk", "de"]) {
    // desktop
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, locale: jazyk === "de" ? "de-DE" : "sk-SK" });
    const page = await novaStranka(ctx);
    await page.goto(`${BASE}/${jazyk}/`, { waitUntil: "networkidle" });
    await page.waitForTimeout(600);
    await odhal(page);
    await page.screenshot({ path: path.join(OUT, `${jazyk}-desktop.png`), fullPage: true });
    const vyska = await page.evaluate(() => document.documentElement.scrollHeight);
    console.log(`${jazyk}-desktop.png  výška stránky:`, vyska);
    await kusy(page, 1440, vyska, 1800, `${jazyk}-desktop`);

    if (jazyk === "sk") {
      // realizácie: karty na hlavnej stránke → stránka realizácie → lightbox
      const karty = await page.evaluate(() => Array.from(document.querySelectorAll(".projekty .projekt")).map((a) => a.getAttribute("href")));
      console.log("karty realizácií:", karty.length, karty.join(", "));
      const domov = page.url();
      for (const jazykProjekt of ["sk", "de"]) {
        const hlavna = `${BASE}/${jazykProjekt}/`;
        await page.goto(hlavna, { waitUntil: "networkidle" });
        const odkazy = await page.evaluate(() => Array.from(document.querySelectorAll(".projekty .projekt")).map((a) => a.href));
        for (const u of odkazy) {
          await page.goto(u, { waitUntil: "networkidle" });
          const info = await page.evaluate(() => ({ h1: document.querySelector("h1").textContent, fotky: document.querySelectorAll(".foto-grid a").length, lang: Array.from(document.querySelectorAll(".lang a")).map((a) => a.getAttribute("href")).join(" | ") }));
          console.log(`  ${u.replace(BASE, "")} → ${info.h1}, ${info.fotky} fotiek, jazyky: ${info.lang}`);
        }
      }
      await page.goto(domov, { waitUntil: "networkidle" });
      await page.click(".projekty .projekt");
      await page.waitForLoadState("networkidle");
      await odhal(page);
      const prvyProjekt = page.url().replace(BASE, "").replace(/\//g, "_").replace(/^_|_$/g, "");
      await page.screenshot({ path: path.join(OUT, `realizacia-desktop.png`), fullPage: true });
      await kusy(page, 1440, await page.evaluate(() => document.documentElement.scrollHeight), 1800, "realizacia-desktop");
      console.log("stránka realizácie:", prvyProjekt);
      await page.click(".foto-grid a");
      await page.waitForFunction(() => { const i = document.querySelector(".lightbox img"); return i && !i.classList.contains("is-loading") && i.complete; }, null, { timeout: 8000 });
      const lb = await page.evaluate(() => ({ otvoreny: document.querySelector(".lightbox").open, pocet: document.querySelector(".lb-pocet").textContent, img: document.querySelector(".lightbox img").getAttribute("src").split("/").pop(), sirka: document.querySelector(".lightbox img").naturalWidth, plne: document.querySelector(".lb-full").getAttribute("href").split("/").pop() }));
      console.log("lightbox:", JSON.stringify(lb));
      await page.waitForTimeout(500); // prechod z rozmazaného náhľadu na ostrú fotku
      await page.screenshot({ path: path.join(OUT, "sk-galeria.png") });
      await page.keyboard.press("ArrowRight");
      await page.waitForTimeout(400);
      console.log("po šípke:", await page.evaluate(() => document.querySelector(".lb-pocet").textContent));
      await page.keyboard.press("Escape");
      await page.waitForTimeout(300);
      console.log("lightbox zavretý:", !(await page.evaluate(() => document.querySelector(".lightbox").open)));
      await page.goto(domov, { waitUntil: "networkidle" });

      // formulár bez servera (GitHub Pages): neutrálna hláška (trieda info) s mailto odkazom a tlačidlami Gmail, Outlook, kopírovať
      await page.fill("#meno", "Test Tester");
      await page.fill("#email", "test@example.com");
      await page.fill("#sprava", "Skúšobná správa z automatickej kontroly.");
      await page.check("input[name='suhlas']");
      await page.click("form.form button[type='submit']");
      await page.waitForFunction(() => /ok|err|info/.test(document.querySelector(".form-msg").className), null, { timeout: 8000 });
      const stav = await page.evaluate(() => ({ trieda: document.querySelector(".form-msg").className, text: document.querySelector(".form-msg").textContent.trim(), mailto: (document.querySelector(".form-msg a") || {}).href,
        tlacidla: [...document.querySelectorAll(".form-msg-btns a, .form-msg-btns button")].map((e) => e.textContent + (e.href ? " → " + new URL(e.href).host : "")) }));
      console.log("formulár:", JSON.stringify(stav));
      if (!/^mailto:/.test(stav.mailto || "") || stav.tlacidla.length !== 3) chyby.push("[formulár] chýba mailto odkaz alebo tlačidlá Gmail/Outlook/kopírovať");
      // prepínač jazyka prenáša kotvu
      await page.goto(`${BASE}/sk/#o-nas`, { waitUntil: "networkidle" });
      console.log("odkaz DE z #o-nas:", await page.evaluate(() => document.querySelector(".lang a:not([aria-current])").getAttribute("href")));
    }
    await ctx.close();

    // mobil
    const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: jazyk === "de" ? "de-DE" : "sk-SK" });
    const mpage = await novaStranka(mctx);
    await mpage.goto(`${BASE}/${jazyk}/`, { waitUntil: "networkidle" });
    await mpage.waitForTimeout(600);
    await odhal(mpage);
    await mpage.screenshot({ path: path.join(OUT, `${jazyk}-mobil.png`), fullPage: true });
    await kusy(mpage, 390, await mpage.evaluate(() => document.documentElement.scrollHeight), 1100, `${jazyk}-mobil`);
    const pretecenie = await mpage.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    console.log(`${jazyk}-mobil.png  vodorovné pretečenie px:`, pretecenie);
    if (jazyk === "sk") {
      await mpage.click(".burger");
      await mpage.waitForTimeout(500);
      await mpage.screenshot({ path: path.join(OUT, "sk-mobil-menu.png") });
      console.log("menu otvorené:", await mpage.evaluate(() => document.body.classList.contains("menu-open")));
    }
    await mctx.close();
  }

  // právne stránky a koreň
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await novaStranka(ctx);
  for (const u of ["/sk/ochrana-osobnych-udajov.html", "/de/datenschutz.html", "/de/impressum.html", "/404.html"]) {
    await page.goto(BASE + u, { waitUntil: "networkidle" });
    console.log(u, "→", await page.title(), "| h1:", await page.evaluate(() => (document.querySelector("h1") || {}).textContent));
  }
  await page.goto(BASE + "/", { waitUntil: "load" });
  await page.waitForTimeout(800);
  console.log("koreň presmeroval na:", page.url());
  await ctx.close();
  await browser.close();

  console.log("\nCHYBY:", chyby.length ? "\n" + chyby.join("\n") : "žiadne");
})().catch((e) => { console.error("ZLYHANIE:", e); process.exit(1); });
