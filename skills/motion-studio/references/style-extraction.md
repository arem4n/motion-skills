# Extraer estilo de una referencia

Inspirado en Design DNA: medir, no adivinar; separar tres dimensiones.

1. **Sistema** — paleta, tipografía, espaciado. Mide la paleta: `$PY -I scripts/measure_palette.py ref.png` → bg/fg/accent/muted con contraste calculado. Tipografía: identifica familia o elige la fontsource más cercana (display condensada / grotesca / serif) y limita a 2.
2. **Estilo** — personalidad de movimiento: ¿rebota? ¿corta seco? Cuenta golpes por segundo y pausas en una referencia en video (`ffmpeg -vf fps=10` y mira la hoja de contactos) y mapea a una personalidad de `personalities.json`.
3. **Efectos** — grano, viñeta, cámara, transiciones. Actívalos solo si la referencia los tiene; si no, no los pongas.

**Si el encargo nombra un look y no trae referencia** ("como diario antiguo", "acuarela", "estilo película de los 50"), búscalo en el catálogo local: `python3 ~/referencias/code-animation-prompts/es/estilos.py buscar <palabras>` y luego `ver <código>`, que muestra el prompt y su imagen de referencia. 341 estilos con índice en español; la serie O (98 looks de películas) viene con cifras (paleta hex, grosores, grano, qué evitar). Pasa esas cifras al SPEC y elige un estilo principal, sin sumar las reglas de varios. Detalle en `~/referencias/code-animation-prompts/LEEME.md`.

Entregable de este paso: 5 líneas — colores (hex), fuentes, personalidad, efectos, formato — que alimentan el andamio (`--personality`, `--fonts`) y los tokens del timeline. No copies una obra concreta: toma principios, no la pieza.
