# Voto con Contenido

Sitio publicado en [votop.cl](https://votop.cl). Reparte tu margen de impuestos, vota proyectos sin saber quién los presentó y compara tus votos con los de cada senador.

## Datos

Votaciones nominales reales del Senado de Chile (período 2022–2026), tomadas de los datos abiertos en `tramitacion.senado.cl/wspublico`. El script verifica que los votos por senador sumen el total oficial de cada votación.

No se usan los datos abiertos de la Cámara: hoy asignan mal los nombres de quienes votan (los totales cuadran, los nombres no).

## Regenerar

```bash
python3 scripts/build_senado.py data/raw data/senado.json
```

`build_senado.py` lee los XML descargados de `votaciones.php`, `tramitacion.php` y `senadores_vigentes.php`. Después se inyecta `data/senado.json` en `scripts/template.html` para producir `index.html`.
