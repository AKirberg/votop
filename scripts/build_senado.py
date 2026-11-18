"""Arma senado.json: votaciones nominales reales del Senado, por período legislativo.
Fuentes: tramitacion.senado.cl/wspublico (votaciones.php, tramitacion.php, senadores_vigentes.php) y militancias de datos.bcn.cl.
Uso: python3 scripts/build_senado.py data/raw data/senado.json [--detalle]
La lista de votaciones está en data/seleccion.json.

Cada votación se identifica por boletín y fecha. Si ese día hubo más de una votación del proyecto completo
(en general, única o informe de Comisión Mixta), la entrada debe traer "tema_contiene" con un texto que
solo aparezca en la votación buscada; si no, el script se detiene en vez de elegir una."""
import re, json, sys, os, datetime, html, csv, unicodedata

RAW, OUT = sys.argv[1], sys.argv[2]
DETALLE = "--detalle" in sys.argv
SEL = json.load(open(os.path.join(os.path.dirname(os.path.abspath(RAW)), "seleccion.json"), encoding="utf-8"))
TIPOS = ("Discusión general", "Discusión única", "Discusión informe de Comisión Mixta")


def G(t, s):
    m = re.search(rf"<{t}>(.*?)</{t}>", s, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def iso(d):
    return datetime.datetime.strptime(d, "%d/%m/%Y").date().isoformat()


def disp(raw):  # "Allende B., Isabel" -> "Isabel Allende B."
    raw = re.sub(r"\s+", " ", raw).strip()
    ap, _, nom = raw.partition(",")
    return f"{nom.strip()} {ap.replace(' .', '').strip()}".strip()


def fold(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


def gobierno(ingreso):
    """Gobierno que envió un mensaje, según su fecha de ingreso."""
    if ingreso < "2018-03-11":
        return "Gobierno de Michelle Bachelet"
    if ingreso < "2022-03-11":
        return "Gobierno de Sebastián Piñera"
    if ingreso < "2026-03-11":
        return "Gobierno de Gabriel Boric"
    return "Gobierno en ejercicio desde marzo de 2026"


# Militancias con fecha, de la Biblioteca del Congreso Nacional (datos.bcn.cl).
SHORT = {"Partido Unión Demócrata Independiente": "UDI", "Partido Renovación Nacional": "RN", "Partido Socialista de Chile": "PS",
         "Partido Por la Democracia": "PPD", "Partido Demócrata Cristiano": "DC", "Partido Comunista de Chile": "PC",
         "Partido Evolución Política": "Evópoli", "Federación Regionalista Verde Social": "FRVS", "Revolución Democrática": "RD",
         "Partido Regionalista de los Independientes": "PRI", "Partido Republicano de Chile": "Republicano", "Partido Republicano": "Republicano",
         "Frente Amplio": "FA", "Partido Frente Amplio": "FA", "Partido Social Cristiano": "PSC", "Partido Nacional Libertario": "PNL",
         "Partido Radical de Chile": "PR", "Partido Liberal de Chile": "Liberal", "Demócratas": "Demócratas", "Partido Demócratas": "Demócratas",
         "Partido de la Gente": "PDG", "Independiente": "Independiente"}
MIL = {}
for f in ("bcn_militancias.csv", "bcn_militancias_extra.csv"):
    path = os.path.join(RAW, f)
    if not os.path.exists(path):
        continue
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["partyLabel"]:
            MIL.setdefault(r["name"], set()).add((r["ini"], r["fin"] or "9999-12-31", SHORT.get(r["partyLabel"], r["partyLabel"])))

# Partido que informa hoy el Senado, solo para el período en curso y solo donde la BCN no tiene dato.
VIG_SHORT = {"U.D.I.": "UDI", "R.N.": "RN", "P.S.": "PS", "P.P.D.": "PPD", "P.D.C.": "DC", "P.C": "PC", "P.C.": "PC",
             "F.R.E.V.S.": "FRVS", "Independiente": "Independiente"}
VIG = {}
vpath = os.path.join(RAW, "sen_vigentes.xml")
if os.path.exists(vpath):
    for s in re.findall(r"<senador>(.*?)</senador>", open(vpath, encoding="utf-8", errors="replace").read(), re.S):
        key = (fold(G("PARLAPELLIDOPATERNO", s)), fold(G("PARLAPELLIDOMATERNO", s))[:1], fold(G("PARLNOMBRE", s).split()[0]))
        p = G("PARTIDO", s)
        VIG[key] = VIG_SHORT.get(p, p)


def split_name(raw):  # "Castro P., Juan" -> ("castro", "p", "juan")
    ap, _, nom = raw.partition(",")
    bits = ap.replace(" .", "").split()
    pat = " ".join(b for b in bits if not b.endswith("."))
    mat = next((b[0] for b in bits if b.endswith(".")), "")
    first = nom.split()[0] if nom.split() else ""
    return pat, mat, first


def bcn_person(raw):
    pat, mat, first = split_name(raw)
    if pat == "Edwards" and first == "Rojo":
        first = "José Manuel"  # Rojo Edwards figura en la BCN como José Manuel Edwards Silva
    hits = [k for k in MIL if fold(first) in fold(k) and re.search(rf"\b{re.escape(fold(pat))} {fold(mat)}", fold(k))]
    return hits[0] if len(hits) == 1 else None


def party_at(person, date):
    if not person:
        return None
    m = [p for ini, fin, p in MIL[person] if ini <= date <= fin]
    return sorted(m)[0] if len(set(m)) == 1 else None


def vigente(raw):
    pat, mat, first = split_name(raw)
    return VIG.get((fold(pat), fold(mat), fold(first)))


def build_period(per):
    bills, votes = [], {}
    for area in per["areas"]:
        for e in area["votaciones"]:
            bol, fecha = e["boletin"], e["fecha"]
            d = open(os.path.join(RAW, f"sen_{bol}.xml"), encoding="utf-8", errors="replace").read()
            cands = [v for v in re.findall(r"<votacion>(.*?)</votacion>", d, re.S)
                     if "<VOTO>" in v and iso(G("FECHA", v)) == fecha and G("TIPOVOTACION", v) in TIPOS]
            if e.get("tema_contiene"):
                cands = [v for v in cands if e["tema_contiene"] in re.sub(r"\s+", " ", G("TEMA", v))]
            if len(cands) != 1:
                temas = "\n  ".join(re.sub(r"\s+", " ", G("TEMA", v))[:140] for v in cands) or "(ninguna)"
                sys.exit(f"{bol} {fecha}: {len(cands)} votaciones posibles; agrega o corrige 'tema_contiene' en data/seleccion.json.\n  {temas}")
            v = cands[0]
            t = open(os.path.join(RAW, f"tram_{bol}.xml"), encoding="utf-8", errors="replace").read()
            ingreso = iso(G("fecha_ingreso", t))
            ini = G("iniciativa", t)
            i = len(bills)
            bills.append({"area": area["area"], "bol": G("boletin", t), "short": e["titulo_breve"], "titulo": G("titulo", t),
                "tema": G("TEMA", v), "fecha": fecha, "tipo": G("TIPOVOTACION", v), "etapa": G("ETAPA", v), "quorum": G("QUORUM", v),
                "si": int(G("SI", v)), "no": int(G("NO", v)), "ab": int(G("ABSTENCION", v)), "pareo": int(G("PAREO", v) or 0),
                "ini": ini, "gob": gobierno(ingreso) if ini == "Mensaje" else None,
                "autores": [disp(a) for a in re.findall(r"<PARLAMENTARIO>(.*?)</PARLAMENTARIO>", G("autores", t) or "")],
                "ingreso": ingreso, "ley": G("leynro", t), "estado": G("estado", t),
                "publicado": iso(G("diariooficial", t)) if re.match(r"\d{2}/\d{2}/\d{4}", G("diariooficial", t)) else None,
                "etapaActual": G("etapa", t),
                "refundidos": [x.replace("*matriz*", "").strip() for x in G("refundidos", t).split("/") if x.strip() and "*matriz*" not in x]})
            if not (per["desde"] <= fecha <= per["hasta"]):
                sys.exit(f"{bol} {fecha}: la fecha está fuera del período {per['id']}")
            for p, sel in re.findall(r"<PARLAMENTARIO>(.*?)</PARLAMENTARIO>\s*<SELECCION>(.*?)</SELECCION>", v, re.S):
                val = {"Si": 1, "No": -1, "Abstencion": 0}.get(sel.strip())  # Pareo: no vota
                votes.setdefault(re.sub(r"\s+", " ", p).strip(), {})[i] = val if val is not None else "p"
            # control: los conteos nominales deben cuadrar con los totales oficiales
            cnt = [sum(1 for k in votes if votes[k].get(i) == x) for x in (1, -1, 0)]
            if cnt != [bills[-1]["si"], bills[-1]["no"], bills[-1]["ab"]]:
                sys.exit(f"{bol} {fecha}: los votos por senador {cnt} no cuadran con el total oficial "
                         f"{[bills[-1]['si'], bills[-1]['no'], bills[-1]['ab']]}")

    sens = []
    for raw, vv in votes.items():
        person = bcn_person(raw)
        pv = [party_at(person, bills[i]["fecha"]) if i in vv else None for i in range(len(bills))]
        fuente = "BCN"
        if per.get("actual"):  # en el período en curso, donde la BCN no tiene dato se usa lo que informa hoy el Senado
            hoy = vigente(raw)
            if hoy and any(i in vv and pv[i] is None for i in range(len(bills))):
                pv = [(pv[i] or hoy) if i in vv else None for i in range(len(bills))]
                fuente = "BCN y Senado" if any(party_at(person, bills[i]["fecha"]) for i in vv) else "Senado"
        last = max(vv, key=lambda i: bills[i]["fecha"])
        sens.append({"n": disp(raw), "p": pv[last], "pv": pv, "bcn": person, "fuente": fuente if pv[last] else None,
                     "v": [vv.get(i) if vv.get(i) != "p" else None for i in range(len(bills))],
                     "pareo": sum(1 for x in vv.values() if x == "p")})
    sens.sort(key=lambda s: s["n"].split(" ", 1)[1])
    out = {k: per[k] for k in ("id", "nombre", "desde", "hasta")}
    out.update({"actual": bool(per.get("actual")), "bills": bills, "sens": sens})
    return out


periodos = [build_period(p) for p in SEL["periodos"]]
json.dump({"built": datetime.date.today().isoformat(), "periodos": periodos}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
for p in periodos:
    con = sum(1 for s in p["sens"] if s["p"])
    print(f"{p['id']}: {len(p['bills'])} votaciones, {len(p['sens'])} senadores, {con} con partido")
    if DETALLE:
        for s in p["sens"]:
            print(f'  {s["n"]:32} {s["p"] or "—":14} {s["fuente"] or ""}  {s["bcn"] or "sin registro BCN"}')
