"""Genera index.html (sitio) y dist/artifact.html (versión para claude.ai) desde la plantilla y data/senado.json."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(f"{ROOT}/data/senado.json", encoding="utf-8"))
t = open(f"{ROOT}/scripts/template.html", encoding="utf-8").read()
y, m, dd = d["built"].split("-")
body = t.replace("__BUILT__", f"{int(dd)}/{int(m)}/{y}").replace("__DATA__", json.dumps(d, ensure_ascii=False).replace("</", "<\\/"))
os.makedirs(f"{ROOT}/dist", exist_ok=True)
open(f"{ROOT}/dist/artifact.html", "w", encoding="utf-8").write(body)
head = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="Vota proyectos del Senado de Chile sin saber quién los presentó y mira con qué senadores coincides.">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
"""
i = body.index('<div class="wrap">')
open(f"{ROOT}/index.html", "w", encoding="utf-8").write(head + body[:i] + "</head>\n<body>\n" + body[i:] + "\n</body>\n</html>\n")
print("index.html y dist/artifact.html generados")
