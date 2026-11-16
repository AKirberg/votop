# Voto con Contenido

Sitio publicado en [votop.cl](https://votop.cl). Reparte tu margen de impuestos, vota proyectos sin saber quién los presentó y compara tus votos con los de cada senador.

## Datos

Votaciones nominales reales del Senado de Chile (período 2022–2026), tomadas de los datos abiertos en `tramitacion.senado.cl/wspublico`. El script verifica que los votos por senador sumen el total oficial de cada votación.

El partido de cada senador es la militancia que registra la Biblioteca del Congreso Nacional ([datos.bcn.cl](https://datos.bcn.cl/)) a la fecha de cada voto. Si la BCN no tiene registro para esa fecha, la página muestra "sin dato" en vez de completarlo con otra fuente.

No se usan los datos abiertos de la Cámara: hoy asignan mal los nombres de quienes votan (los totales cuadran, los nombres no).

## Regenerar

```bash
python3 scripts/build_senado.py data/raw data/senado.json
python3 scripts/build_page.py
node scripts/make_og.js   # solo si cambia la imagen para redes (og.png)
```

`build_senado.py` lee los XML del Senado (`votaciones.php`, `tramitacion.php`) y las militancias de la BCN guardadas en `data/raw/`, y escribe `data/senado.json`. `build_page.py` inyecta esos datos en `scripts/template.html` y genera `index.html` (sitio) y `dist/artifact.html` (versión para claude.ai).
