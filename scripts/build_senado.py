"""Arma senado.json: votaciones nominales reales del Senado (período 2022-2026) para el piloto.
Fuente: tramitacion.senado.cl/wspublico (votaciones.php, tramitacion.php, senadores_vigentes.php)."""
import re, json, sys, datetime, html
RAW, OUT = sys.argv[1], sys.argv[2]
# (área, boletín, fecha de la votación, título breve). La votación se identifica por boletín + fecha + tipo general/única.
PICK = [
 ("Pensiones y trabajo", "15480", "2025-01-27", "Reforma de pensiones: nuevo sistema mixto y seguro social"),
 ("Pensiones y trabajo", "15864", "2023-05-17", "Alza del ingreso mínimo y ampliación de la asignación familiar"),
 ("Pensiones y trabajo", "17080", "2025-03-05", "Convenio 155 de la OIT sobre seguridad y salud de los trabajadores"),
 ("Salud", "12662", "2022-06-01", "Seguro de salud catastrófico en Fonasa (libre elección)"),
 ("Salud", "14211", "2022-10-05", "Prohibir informar las deudas contraídas por atenciones de salud"),
 ("Seguridad", "14870", "2023-04-04", "Más protección legal para policías y Gendarmería"),
 ("Seguridad", "14015", "2022-08-09", "Cárcel por usurpación de inmuebles y detención más fácil de ocupantes"),
 ("Seguridad", "16132", "2025-09-09", "Prevención del delito y apoyo a víctimas a cargo de los gobiernos regionales"),
 ("Educación", "16743", "2025-06-04", "Facilitar la creación de nuevos colegios"),
 ("Educación", "15715", "2023-09-05", "Un solo sistema de evaluación y desarrollo profesional docente"),
 ("Medio ambiente", "16553", "2025-09-30", "Fortalecer la fiscalización de la Superintendencia del Medio Ambiente"),
 ("Transporte", "14532", "2025-05-06", "Más competencia en el cabotaje marítimo"),
]
def G(t, s):
    m = re.search(rf"<{t}>(.*?)</{t}>", s, re.S); return html.unescape(m.group(1)).strip() if m else ""
def iso(d): return datetime.datetime.strptime(d, "%d/%m/%Y").date().isoformat()
def disp(raw):  # "Allende B., Isabel" -> "Isabel Allende B."
    raw = re.sub(r"\s+", " ", raw).strip()
    ap, _, nom = raw.partition(",")
    ap = ap.replace(" .", "").strip()
    return f"{nom.strip()} {ap}".strip()

vig = open(f"{RAW}/sen_vig.xml", encoding="utf-8", errors="replace").read()
PARTY = {}
for s in re.findall(r"<senador>(.*?)</senador>", vig, re.S):
    PARTY[(G("PARLAPELLIDOPATERNO", s).strip().lower(), G("PARLNOMBRE", s).split()[0].lower())] = G("PARTIDO", s)

bills, votes = [], {}
for area, bol, fecha, short in PICK:
    d = open(f"{RAW}/sen/{bol}.xml", encoding="utf-8", errors="replace").read()
    cands = [v for v in re.findall(r"<votacion>(.*?)</votacion>", d, re.S)
             if iso(G("FECHA", v)) == fecha and G("TIPOVOTACION", v) in ("Discusión general", "Discusión única")]
    v = max(cands, key=lambda v: v.count("<VOTO>"))
    t = open(f"{RAW}/tram/{bol}.xml", encoding="utf-8", errors="replace").read()
    ingreso = iso(G("fecha_ingreso", t))
    autores = [disp(a) for a in re.findall(r"<PARLAMENTARIO>(.*?)</PARLAMENTARIO>", G("autores", t) or "")]
    ini = G("iniciativa", t)
    gob = ("Gobierno de Sebastián Piñera" if ingreso < "2022-03-11" else "Gobierno de Gabriel Boric") if ini == "Mensaje" else None
    i = len(bills)
    bills.append({"area": area, "bol": G("boletin", t), "short": short, "titulo": G("titulo", t), "tema": G("TEMA", v),
        "fecha": fecha, "tipo": G("TIPOVOTACION", v), "etapa": G("ETAPA", v), "quorum": G("QUORUM", v),
        "si": int(G("SI", v)), "no": int(G("NO", v)), "ab": int(G("ABSTENCION", v)), "pareo": int(G("PAREO", v) or 0),
        "ini": ini, "gob": gob, "autores": autores, "ingreso": ingreso, "ley": G("leynro", t), "estado": G("estado", t)})
    for p, sel in re.findall(r"<PARLAMENTARIO>(.*?)</PARLAMENTARIO>\s*<SELECCION>(.*?)</SELECCION>", v, re.S):
        val = {"Si": 1, "No": -1, "Abstencion": 0}.get(sel.strip())  # Pareo: no vota
        key = re.sub(r"\s+", " ", p).strip()
        votes.setdefault(key, {})[i] = val if val is not None else "p"
    # control: los conteos nominales deben cuadrar con los totales oficiales
    cnt = [sum(1 for k in votes if votes[k].get(i) == x) for x in (1, -1, 0)]
    assert cnt == [bills[-1]["si"], bills[-1]["no"], bills[-1]["ab"]], (bol, cnt)

sens = []
for raw, vv in votes.items():
    ap = raw.split(",")[0].split()[0].lower(); nom = raw.split(",")[1].split()[0].lower()
    sens.append({"n": disp(raw), "p": PARTY.get((ap, nom)), "v": [vv.get(i) if vv.get(i) != "p" else None for i in range(len(bills))],
                 "pareo": sum(1 for x in vv.values() if x == "p")})
sens.sort(key=lambda s: s["n"].split(" ", 1)[1])
json.dump({"bills": bills, "sens": sens, "built": datetime.date.today().isoformat()}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(len(bills), "votaciones,", len(sens), "senadores;", sum(1 for s in sens if s["p"]), "con partido según el Senado")
for b in bills: print(b["bol"], b["fecha"], f'{b["si"]}-{b["no"]}-{b["ab"]}', b["ini"], b["gob"] or b["autores"][:2], "|", b["tema"][-60:])
