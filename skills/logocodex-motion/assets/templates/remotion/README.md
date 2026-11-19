# Destino Remotion (probado)

Mismo `timeline.js` que `scene.html`: aquí solo cambia el montaje. Verificado con Remotion 4.0.538: los frames 120, 240 y 480 de AreMan salen idénticos (0 % de píxeles distintos) al renderer
Chromium+FFmpeg del skill.

1. Copia esta carpeta a tu proyecto y añade `src/motion-kit.js` (de `assets/lib/`), `src/timeline.js` (tu escena),
   `src/layers.json` y `src/motion-tokens.json` (de `assets/`).
2. Ajusta `ARCHETYPE`, y `durationInFrames` = ceil(duración × fps) + 1 (la duración la imprime `validate_motion.py`).
3. `npm i && npx remotion render src/index.ts LogoScene out.mp4` (si no hay Chrome de Remotion:
   `--browser-executable=/ruta/a/chrome`).

No usa `useGsapTimeline`: basta `tl.time(frame/fps, false)` sobre un timeline en pausa, que es lo mismo en esencia y
evita su restricción de callbacks.
