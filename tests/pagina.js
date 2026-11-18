// Prueba la página en un navegador real: flujo de votación, progreso guardado, compartir y accesibilidad.
//
//   npm install          (instala axe-core)
//   npm test             (corre también tests/check_data.py)
//
// Requiere Playwright con Chromium. Si ya hay un Chromium instalado en otra ruta, se puede indicar con
// CHROMIUM_PATH=/ruta/al/chromium.
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.join(__dirname, "..");
const AXE = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const fallas = [];
const ok = (cond, msg) => { if (!cond) fallas.push(msg); };

(async () => {
  const html = fs.readFileSync(path.join(ROOT, "index.html"));
  const srv = http.createServer((q, r) => { r.writeHead(200, { "content-type": "text/html; charset=utf-8" }); r.end(html); });
  await new Promise((res) => srv.listen(0, res));
  const url = `http://localhost:${srv.address().port}/`;
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});

  try {
    for (const scheme of ["light", "dark"]) {
      const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: scheme, permissions: ["clipboard-read", "clipboard-write"] });
      const p = await ctx.newPage();
      const errores = [];
      p.on("pageerror", (e) => errores.push(e.message));
      const axe = async (paso) => {
        await p.addScriptTag({ content: AXE });
        const v = await p.evaluate(async () => (await axe.run(document, { runOnly: ["wcag2a", "wcag2aa", "wcag21aa", "best-practice"] })).violations.map((x) => x.id));
        ok(v.length === 0, `[${scheme}] accesibilidad en ${paso}: ${v.join(", ")}`);
      };
      const sinDesborde = async (paso) => ok(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `[${scheme}] desborde horizontal en ${paso}`);

      await p.goto(url);
      await axe("paso 1"); await sinDesborde("paso 1");

      // Paso 2: votar, avance y foco
      await p.click("#to2");
      ok(await p.evaluate(() => document.activeElement.id === "h2a"), `[${scheme}] el foco no pasa al título del paso 2`);
      const total = await p.$$eval(".bill", (b) => b.length);
      ok(total > 0, `[${scheme}] no hay votaciones en el paso 2`);
      for (const o of (await p.$$('.opt[data-val="1"]')).slice(0, 3)) await o.click();
      ok((await p.textContent("#prog")).includes(`Respondidas 3 de ${total}`), `[${scheme}] el avance no cuenta 3 respuestas`);
      await axe("paso 2"); await sinDesborde("paso 2");

      // Progreso guardado al recargar
      await p.reload();
      ok(await p.isVisible("#p2"), `[${scheme}] al recargar no vuelve al paso 2`);
      ok((await p.textContent("#prog")).includes("Respondidas 3"), `[${scheme}] al recargar se pierden las respuestas`);

      // Responder todo y ver resultados
      for (const o of await p.$$('.opt[data-val="-1"]')) await o.click();
      ok((await p.textContent("#prog")).includes("todas listas"), `[${scheme}] no marca todas las votaciones como respondidas`);
      await p.click("#to3");
      ok((await p.textContent("#summary")).includes(`tus ${total} votos`), `[${scheme}] el resumen no refleja ${total} votos`);
      ok((await p.$$(".leg")).length === 10, `[${scheme}] no muestra los 10 primeros senadores`);

      // Compartir: el texto no lleva votos ni impuestos, y se copia tal cual
      const txt = await p.inputValue("#shareText");
      ok(/^Voté \d+ proyectos/.test(txt) && txt.includes("https://votop.cl"), `[${scheme}] texto para compartir inesperado`);
      ok(!/\$|A favor|En contra/.test(txt), `[${scheme}] el texto para compartir incluye votos o montos`);
      await p.click("#shareBtn");
      const copiado = await p.evaluate(() => navigator.clipboard.readText()).catch(() => null);
      ok(copiado === null || copiado === txt, `[${scheme}] lo copiado no es igual al texto mostrado`);

      // Búsqueda
      await p.fill("#q", "provoste");
      ok((await p.$$(".leg")).length === 1, `[${scheme}] la búsqueda no encuentra a un solo senador`);
      await p.fill("#q", "");

      await p.click("#reveal summary"); await p.click("#como-funciona summary");
      await p.$$eval(".leg details", (ds) => ds.forEach((d) => (d.open = true)));
      await axe("paso 3"); await sinDesborde("paso 3");

      // Cambiar de período: cada período tiene sus propios votos y senadores
      const periodos = await p.$$eval('#period input', (xs) => xs.map((x) => x.value));
      ok(periodos.length >= 2 && (await p.isChecked(`#period input[value="${periodos[0]}"]`)), `[${scheme}] no abre en el primer período`);
      await p.click(`#period label:has(input[value="${periodos[1]}"])`);
      ok((await p.textContent("#summary")) === "" || (await p.isHidden("#summary")), `[${scheme}] el otro período muestra votos que no se respondieron`);
      await p.click('.step-btn[data-go="2"]');
      const total2 = await p.$$eval(".bill", (b) => b.length);
      ok((await p.textContent("#prog")).includes(`Respondidas 0 de ${total2}`), `[${scheme}] el segundo período no parte en cero`);
      ok((await p.textContent("#bannerN")) === String(total2), `[${scheme}] el aviso superior no cambia al cambiar de período`);
      await (await p.$('.opt[data-val="1"]')).click();
      await p.reload();
      ok(await p.isChecked(`#period input[value="${periodos[1]}"]`), `[${scheme}] al recargar no recuerda el período`);
      ok((await p.textContent("#prog")).includes("Respondidas 1"), `[${scheme}] al recargar se pierde el voto del segundo período`);
      await p.click(`#period label:has(input[value="${periodos[0]}"])`);
      ok((await p.textContent("#prog")).includes(`Respondidas ${total} de ${total}`), `[${scheme}] al volver al primer período se perdieron sus votos`);

      // Borrar respuestas (dos toques)
      await p.click('.step-btn[data-go="2"]');
      await p.click("#clearAns"); await p.click("#clearAns");
      ok((await p.textContent("#prog")).includes("Respondidas 0"), `[${scheme}] borrar no deja las respuestas en cero`);

      ok(errores.length === 0, `[${scheme}] errores de JavaScript: ${errores.join(" | ")}`);
      await ctx.close();
    }
  } finally {
    await browser.close();
    srv.close();
  }

  if (fallas.length) {
    console.log("Fallaron pruebas de la página:");
    fallas.forEach((f) => console.log("  - " + f));
    process.exit(1);
  }
  console.log("Página correcta: flujo, progreso guardado, compartir, búsqueda y accesibilidad (claro y oscuro).");
})();
