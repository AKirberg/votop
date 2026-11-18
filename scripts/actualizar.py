"""Actualiza los datos y la página en un solo paso.

    python3 scripts/actualizar.py                 # descarga, verifica, regenera y muestra qué cambió
    python3 scripts/actualizar.py --sin-descargar # solo regenera desde data/raw

1. Descarga del Senado las votaciones y la tramitación de cada boletín de data/seleccion.json,
   y de la BCN las militancias de los senadores. Todo va primero a una carpeta temporal.
2. Arma los datos con build_senado.py, que se detiene si algún conteo por senador no cuadra
   con el total oficial de la votación.
3. Solo si todo salió bien reemplaza data/raw y data/senado.json, regenera index.html y
   dist/artifact.html, y muestra las diferencias con la versión anterior.
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "senado.json")
UA = {"User-Agent": "votop-actualizador/1.0 (+https://github.com/AKirberg/votop)"}
SENADO = "https://tramitacion.senado.cl/wspublico/{}.php?boletin={}"
SPARQL = "https://datos.bcn.cl/sparql"

# Militancias de quienes ocuparon el cargo de senador (cargo/2) con período vigente desde 2022.
Q_SENADORES = """PREFIX bio: <http://datos.bcn.cl/ontologies/bcn-biographies#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?per ?name ?idSenado ?partyLabel ?ini ?fin WHERE {
  ?per bio:hasPositionPeriod ?c . ?c bio:hasPosition <http://datos.bcn.cl/recurso/cl/cargo/2> ; bio:hasEnd ?ce .
  ?ce bio:originalDate ?cfin . FILTER(?cfin >= "2022-03-11")
  ?per foaf:name ?name .
  OPTIONAL { ?per bio:idSenado ?idSenado }
  OPTIONAL { ?per bio:hasMilitancy ?m . ?m bio:hasPoliticalParty ?pp . ?pp rdfs:label ?partyLabel .
             OPTIONAL { ?m bio:hasBeginning ?mb . ?mb bio:originalDate ?ini }
             OPTIONAL { ?m bio:hasEnd ?me . ?me bio:originalDate ?fin } }
}"""
# Senadores que la consulta anterior no trae porque su cargo no tiene fecha de término en la BCN.
APELLIDOS_EXTRA = ["Galilea", "Durana"]
Q_EXTRA = """PREFIX bio: <http://datos.bcn.cl/ontologies/bcn-biographies#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name ?partyLabel ?ini ?fin WHERE {
  ?per foaf:name ?name . FILTER(%s)
  OPTIONAL { ?per bio:hasMilitancy ?m . ?m bio:hasPoliticalParty ?pp . ?pp rdfs:label ?partyLabel .
             OPTIONAL { ?m bio:hasBeginning ?mb . ?mb bio:originalDate ?ini }
             OPTIONAL { ?m bio:hasEnd ?me . ?me bio:originalDate ?fin } } }""" % " || ".join(f'CONTAINS(?name,"{a}")' for a in APELLIDOS_EXTRA)


def get(url, data=None, accept=None, tries=4):
    headers = dict(UA)
    if accept:
        headers["Accept"] = accept
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:  # red inestable: reintenta con espera creciente
            if k == tries - 1:
                raise RuntimeError(f"No se pudo descargar {url}: {e}")
            time.sleep(2 ** k)


def sparql(q):
    return get(SPARQL + "?" + urllib.parse.urlencode({"query": q}), accept="text/csv")


def descargar(dest):
    sel = json.load(open(os.path.join(ROOT, "data", "seleccion.json"), encoding="utf-8"))
    bols = sorted({v["boletin"] for p in sel["periodos"] for a in p["areas"] for v in a["votaciones"]})
    print(f"Descargando {len(bols)} boletines del Senado…")
    for b in bols:
        for kind, prefix in (("votaciones", "sen"), ("tramitacion", "tram")):
            body = get(SENADO.format(kind, b))
            ET.fromstring(body)  # falla aquí si el Senado devolvió algo que no es XML
            if kind == "votaciones" and b"<votacion>" not in body:
                raise RuntimeError(f"El boletín {b} no trae votaciones en el Senado")
            open(os.path.join(dest, f"{prefix}_{b}.xml"), "wb").write(body)
    body = get("https://tramitacion.senado.cl/wspublico/senadores_vigentes.php")
    if b"<senador>" not in body:
        raise RuntimeError("El Senado no devolvió la lista de senadores vigentes")
    open(os.path.join(dest, "sen_vigentes.xml"), "wb").write(body)
    print("Descargando militancias de la BCN…")
    for name, q in (("bcn_militancias.csv", Q_SENADORES), ("bcn_militancias_extra.csv", Q_EXTRA)):
        body = sparql(q)
        if not body.startswith(b'"') or body.count(b"\n") < 2:
            raise RuntimeError(f"La BCN devolvió una respuesta inesperada para {name}")
        open(os.path.join(dest, name), "wb").write(body)


def diferencias(antes, ahora):
    if not antes:
        return ["Primera versión de los datos."]
    if "periodos" not in antes:  # formato antiguo, con un solo período
        antes = {"periodos": [{"id": "2022-2026", "bills": antes["bills"], "sens": antes["sens"]}]}
    out = []
    PA = {p["id"]: p for p in antes["periodos"]}
    for p in ahora["periodos"]:
        if p["id"] not in PA:
            out.append(f"+ Período nuevo: {p['nombre']} ({len(p['bills'])} votaciones, {len(p['sens'])} senadores)")
            continue
        out += [f"[{p['id']}] {x}" for x in diferencias_periodo(PA[p["id"]], p)]
    return out or ["Sin cambios en votos, partidos ni tramitación."]


def diferencias_periodo(antes, ahora):
    out = []
    A = {b["bol"] + "|" + b["fecha"]: b for b in antes["bills"]}
    for b in ahora["bills"]:
        k = b["bol"] + "|" + b["fecha"]
        if k not in A:
            out.append(f"+ Votación nueva: {b['short']} ({b['bol']}, {b['fecha']})")
            continue
        a = A.pop(k)
        for campo, nombre in (("si", "votos a favor"), ("no", "votos en contra"), ("ab", "abstenciones"),
                              ("estado", "estado"), ("ley", "ley"), ("publicado", "publicación"), ("etapaActual", "etapa")):
            if a.get(campo) != b.get(campo):
                out.append(f"~ {b['short']}: {nombre} {a.get(campo)!r} → {b.get(campo)!r}")
    for b in A.values():
        out.append(f"- Votación quitada: {b['short']} ({b['bol']}, {b['fecha']})")
    SA = {s["n"]: s for s in antes["sens"]}
    for s in ahora["sens"]:
        a = SA.pop(s["n"], None)
        if a is None:
            out.append(f"+ Senador nuevo en los datos: {s['n']}")
        elif a.get("p") != s.get("p"):
            out.append(f"~ {s['n']}: partido {a.get('p') or 'sin dato'} → {s.get('p') or 'sin dato'}")
        elif a["v"] != s["v"] and len(a["v"]) == len(s["v"]):
            out.append(f"~ {s['n']}: cambió algún voto registrado")
    for n in SA:
        out.append(f"- Senador que ya no aparece: {n}")
    return out


def main():
    sin_descargar = "--sin-descargar" in sys.argv
    antes = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else None
    with tempfile.TemporaryDirectory() as tmp:
        raw = RAW
        if not sin_descargar:
            raw = os.path.join(tmp, "data", "raw")
            os.makedirs(raw)
            shutil.copy(os.path.join(ROOT, "data", "seleccion.json"), os.path.join(tmp, "data", "seleccion.json"))
            descargar(raw)
        nuevo = os.path.join(tmp, "senado.json")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_senado.py"), raw, nuevo], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout + r.stderr)
            sys.exit("Los datos no pasaron la verificación. No se cambió nada en el repo.")
        print(r.stdout.strip().splitlines()[0])
        if not sin_descargar:  # recién ahora se reemplazan los datos crudos
            for f in os.listdir(raw):
                shutil.copy(os.path.join(raw, f), os.path.join(RAW, f))
        ahora = json.load(open(nuevo, encoding="utf-8"))
        shutil.copy(nuevo, OUT)
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_page.py")], check=True)
    print("\nCambios respecto de la versión anterior:")
    for line in diferencias(antes, ahora):
        print("  " + line)


if __name__ == "__main__":
    main()
