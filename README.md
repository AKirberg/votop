# Voto con Contenido

Sitio publicado en [votop.cl](https://votop.cl). Reparte tu margen de impuestos, vota proyectos sin saber quién los presentó y compara tus votos con los de cada senador.

## Datos

Votaciones nominales reales del Senado de Chile (período 2022–2026), tomadas de los datos abiertos en `tramitacion.senado.cl/wspublico`. El script verifica que los votos por senador sumen el total oficial de cada votación.

El partido de cada senador es la militancia que registra la Biblioteca del Congreso Nacional ([datos.bcn.cl](https://datos.bcn.cl/)) a la fecha de cada voto. Si la BCN no tiene registro para esa fecha, la página muestra "sin dato" en vez de completarlo con otra fuente.

No se usan los datos abiertos de la Cámara: hoy asignan mal los nombres de quienes votan (los totales cuadran, los nombres no).

## Agregar o quitar votaciones

La lista está en `data/seleccion.json`: cada votación se identifica por boletín y fecha, con su área y un título breve. El orden de las áreas en ese archivo es el orden en la página.

## Actualizar

```bash
python3 scripts/actualizar.py
```

Descarga del Senado y de la BCN, verifica que los conteos cuadren, regenera `index.html` y `dist/artifact.html` y muestra qué cambió respecto de la versión anterior. Si algo falla, no cambia nada en el repo. Con `--sin-descargar` solo regenera desde `data/raw/`.

Por dentro llama a `scripts/build_senado.py` (arma `data/senado.json`) y `scripts/build_page.py` (inyecta los datos en `scripts/template.html`). La imagen para redes se regenera aparte con `node scripts/make_og.js`.

## Pruebas

```bash
npm install
npm test
```

- `tests/check_data.py` (sin dependencias): la selección y los datos coinciden, los votos por senador suman el total oficial y las páginas llevan exactamente esos datos.
- `tests/pagina.js`: en un navegador real, en modo claro y oscuro, prueba votar, retomar tras recargar, ver resultados, buscar, compartir (sin votos ni montos) y borrar, y audita accesibilidad con axe-core. Requiere Playwright con Chromium; si el Chromium está en otra ruta, indícala con `CHROMIUM_PATH`.
