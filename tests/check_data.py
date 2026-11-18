"""Verifica los datos publicados sin descargar nada.

    python3 tests/check_data.py

Revisa que data/senado.json sea coherente con data/seleccion.json, que en cada votación los votos
por senador sumen el total oficial y que index.html y dist/artifact.html lleven exactamente esos datos.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errores = []


def check(cond, msg):
    if not cond:
        errores.append(msg)


d = json.load(open(os.path.join(ROOT, "data", "senado.json"), encoding="utf-8"))
sel = json.load(open(os.path.join(ROOT, "data", "seleccion.json"), encoding="utf-8"))
check([p["id"] for p in d["periodos"]] == [p["id"] for p in sel["periodos"]], "Los períodos de data/senado.json no son los de data/seleccion.json")
check(sum(1 for p in d["periodos"] if p["actual"]) <= 1, "Hay más de un período marcado como actual")
total_v, total_s = 0, 0
for per, sp in zip(d["periodos"], sel["periodos"]):
    bills, sens = per["bills"], per["sens"]
    total_v += len(bills); total_s += len(sens)
    tag = f"[{per['id']}]"
    # La selección y los datos coinciden, en el mismo orden
    esperadas = [(a["area"], v["boletin"], v["fecha"], v["titulo_breve"]) for a in sp["areas"] for v in a["votaciones"]]
    tenemos = [(b["area"], b["bol"].split("-")[0], b["fecha"], b["short"]) for b in bills]
    check(esperadas == tenemos, f"{tag} data/senado.json no coincide con data/seleccion.json: corre scripts/actualizar.py")
    check(len({(b["bol"], b["fecha"]) for b in bills}) == len(bills), f"{tag} hay votaciones repetidas")
    # Cada votación dentro del período y con conteos que cuadran
    for i, b in enumerate(bills):
        check(per["desde"] <= b["fecha"] <= per["hasta"], f"{tag} {b['bol']}: fecha {b['fecha']} fuera del período")
        votos = [s["v"][i] for s in sens]
        for val, campo in ((1, "si"), (-1, "no"), (0, "ab")):
            check(votos.count(val) == b[campo], f"{tag} {b['bol']}: {votos.count(val)} votos '{campo}' por senador, el total oficial es {b[campo]}")
        check(b["short"].strip() and b["titulo"].strip(), f"{tag} {b['bol']}: falta título")
    # Senadores
    nombres = [s["n"] for s in sens]
    check(len(nombres) == len(set(nombres)), f"{tag} hay senadores con el mismo nombre")
    for s in sens:
        check(len(s["v"]) == len(bills) and len(s["pv"]) == len(bills), f"{tag} {s['n']}: largo de votos distinto al de votaciones")
        check(all(v in (1, -1, 0, None) for v in s["v"]), f"{tag} {s['n']}: voto con valor desconocido")
        check(any(v is not None for v in s["v"]) or s["pareo"] > 0, f"{tag} {s['n']}: no tiene ningún voto ni pareo")
# Una votación no puede estar en dos períodos
claves = [(b["bol"], b["fecha"]) for p in d["periodos"] for b in p["bills"]]
check(len(claves) == len(set(claves)), "Una misma votación aparece en dos períodos")

# Las páginas generadas llevan exactamente estos datos
for f in ("index.html", os.path.join("dist", "artifact.html")):
    html = open(os.path.join(ROOT, f), encoding="utf-8").read()
    m = re.search(r"var DATA = (\{.*?\});\n</script>", html, re.S)
    check(m is not None, f"{f}: no se encontraron los datos incrustados")
    if m:
        check(json.loads(m.group(1).replace("<\\/", "</")) == d, f"{f}: los datos no son los de data/senado.json; corre scripts/build_page.py")
    check(not re.search(r"__[A-Z]+__", html), f"{f}: quedó un marcador sin reemplazar")

if errores:
    print("Falló la verificación de datos:")
    for e in errores:
        print("  - " + e)
    sys.exit(1)
print(f"Datos correctos: {len(d['periodos'])} períodos, {total_v} votaciones, {total_s} registros de senadores, conteos cuadrados con los totales oficiales.")
