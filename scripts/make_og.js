// Genera og.png (1200x630), la imagen que muestran las redes al compartir el enlace.
// Uso: node scripts/make_og.js   (requiere Playwright con Chromium)
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

(async () => {
  const root = path.join(__dirname, "..");
  const html = fs.readFileSync(path.join(__dirname, "og.html"), "utf8").replace("__PCT__", "87%");
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(root, "og.png") });
  await browser.close();
  console.log("og.png generado");
})();
