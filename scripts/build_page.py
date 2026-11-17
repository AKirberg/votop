"""Genera index.html (sitio) y dist/artifact.html (versión para claude.ai) desde la plantilla y data/senado.json."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(f"{ROOT}/data/senado.json", encoding="utf-8"))
t = open(f"{ROOT}/scripts/template.html", encoding="utf-8").read()
y, m, dd = d["built"].split("-")
NUMS = {1: "una", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve", 10: "diez"}
areas = list(dict.fromkeys(b["area"] for b in d["bills"]))
t = t.replace("__NV__", str(len(d["bills"]))).replace("__NA__", NUMS.get(len(areas), str(len(areas))))
body = t.replace("__BUILT__", f"{int(dd)}/{int(m)}/{y}").replace("__DATA__", json.dumps(d, ensure_ascii=False).replace("</", "<\\/"))
os.makedirs(f"{ROOT}/dist", exist_ok=True)
open(f"{ROOT}/dist/artifact.html", "w", encoding="utf-8").write(body)
head = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="Vota proyectos del Senado de Chile sin saber quién los presentó y mira con qué senadores coincides.">
<link rel="canonical" href="https://votop.cl/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Voto con Contenido">
<meta property="og:title" content="Voto con Contenido">
<meta property="og:description" content="Vota proyectos del Senado de Chile sin saber quién los presentó y mira con qué senadores coincides.">
<meta property="og:url" content="https://votop.cl/">
<meta property="og:image" content="https://votop.cl/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="es_CL">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%232F4BDB'/%3E%3Cpath d='M9 16.5l4.5 4.5L23 11.5' stroke='white' stroke-width='3.2' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
"""
i = body.index('<main class="wrap">')
open(f"{ROOT}/index.html", "w", encoding="utf-8").write(head + body[:i] + "</head>\n<body>\n" + body[i:] + "\n</body>\n</html>\n")
print("index.html y dist/artifact.html generados")
