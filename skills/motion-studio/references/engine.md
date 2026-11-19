# Motor: GSAP determinista + Chromium + ffmpeg

## Principio
Cada fotograma es función pura del tiempo. El timeline GSAP nace en pausa; `window.__seek(t)` lo posiciona; Playwright/Chromium captura PNG; ffmpeg codifica H.264 (+AAC). `MG.expose(tl)` publica `__seek`, `__duration`, `__labels`, `__cues`, `__ready`.

## Reglas probadas
1. Sin reloj ni azar: nada de `Math.random`, `Date.now`, timers, `repeat:-1` (lint del validador).
2. Estado inicial con `tl.set(..., 0)` y tweens `to` posteriores; no `from()` perezosos.
3. **Seek a t=0 exacto revierte los `set` de 0 y no los reaplica hacia adelante** → `__seek` clampa a ≥ 1e-4 y `expose` posiciona en 1e-4. Nunca dos `set` en t=0 sobre la misma propiedad.
4. **No uses `will-change` (ni capas forzadas) en contenedores animados**: Chromium compone/rasteriza distinto tras cierto punto y el texto cambia en antialiasing (0.4–0.6 % de píxeles) según el orden de seek. Quitarlo dejó el acceso aleatorio en 0.000 %.
5. Una transformación tardía `translate(0,0)` sobre una escena también cambia la capa: el kit fija `x:0,y:0` desde la construcción.
6. Callbacks solo con proxy + `onUpdate` (contadores, grano): GSAP los dispara también al hacer seek.
7. `x/y` + `svgOrigin` en el mismo nodo SVG desplaza el origen; usa un grupo interior.
8. Medidas del DOM (validador) solo en fotogramas *asentados* y descartando elementos tapados (`elementFromPoint`).

## Sonido
`make_sfx.py` arma la pista desde las señales `MG.cue`, con el **pico** de cada sonido en su `t` (medido por archivo, error < 4 ms).
- **Muestras reales** (`--sfx-source auto`, por defecto): `assets/sfx/index.json` → `hit` (impactSoft_heavy), `thud` (impactSoft_medium), `tick` (click), `step` (footstep_concrete), `pop` (drop), `shimmer` (impactBell_heavy). Kenney, **CC0** (`assets/sfx/LICENSE.md`): pueden viajar con el skill. Todas normalizadas al mismo pico; el balance lo dan `gain_db` del índice y el `gain` de la señal. Varias apariciones de una señal rotan sus variantes (determinista, sin repetir seguido). Elegidas por medición (duración, pico, brillo), **no por oído**.
- **Sintéticas** (numpy/scipy): `whoosh`, `riser`, `sub` siempre (Kenney no trae barridos ni graves sostenidos), y cualquier señal sin muestra. `--sfx-source synth` = todo sintético; `samples` = falla si falta una.
- **Biblioteca local**: `MOTION_STUDIO_SFX_DIR=/ruta` con un `index.json` del mismo formato (`{"cues": {"whoosh": [{"file": "w/a.wav", "peak": 0.31, "gain_db": -3}]}}`); sus señales ganan sobre las del skill. Para sonidos con licencia que **no** permite redistribuir (Sonniss GDC: uso comercial sí, redistribuir no): nunca los copies a `assets/sfx/`.
- Limitador suave (tanh), master a −14 LUFS en `render.py` (ganancia + limitador; si con golpes cortos no llega a ±1 LU, agrega un compresor rápido `COMP` y reajusta hasta 3 veces). **Nadie lo escucha**: avísalo al entregar. Cama musical opcional: `--music pista.mp3 --music-gain -18`.

## Render
`render.py --scene --out --size --fps --crf --audio auto|none --music --sfx-gain --still t`. Usa Chromium (Playwright). Para un solo fotograma, `--still`.

## Remotion (opcional)
Movido a `references/remotion.md` (montaje con `scripts/new_remotion.py`, medición, trampas y licencia) y `references/router.md` (cuándo usarlo).

## Three.js (MG.three)
`vendor/three.min.js` es un bundle IIFE (global `THREE`, con `RoomEnvironment` y `RoundedBoxGeometry`) generado con esbuild a partir del paquete npm `three`. `MG.three(sc,{...})` crea un canvas WebGL con `preserveDrawingBuffer`; `MG.expose` registra un `onUpdate` del timeline que redibuja DESPUÉS de que todos los tweens hayan fijado su estado (un tween-proxy dentro del timeline no sirve: GSAP renderiza los hijos en orden de inicio y dibujaría un estado viejo). Verificado: acceso aleatorio 0.0000 %. No uses `requestAnimationFrame`, `THREE.Clock` ni `controls` con inercia. Resolver `var(--fuente)` en texturas de texto lo hace `t3.textTexture`.

### Nivel 1: material, reflejo, cámara, sombra, bloom
Todo lo que hace que un objeto 3D no parezca un cubo de plástico, sin escribir un pase de postproceso ni tocar shaders:

- **`t3.mat(k, o)`** — presets calibrados: `matte`, `soft` (tela con sheen), `metal`, `chrome`, `ceramic` (clearcoat), `iridescent`, `glass` (transparencia + clearcoat; no usa `transmission`, que cuesta un render extra de la escena) y `emissive`. Cualquier clave de `o` pisa el preset, así que `t3.mat('ceramic', {color: C.hero, roughness: 0.3})` es el caso normal: el preset da la física, tú das el color de marca. Un metal o un vidrio **necesitan `t3.env()`** para tener qué reflejar; sin entorno, `chrome` sale gris muerto (verificado: mismo anillo, entorno oscuro → casi negro; entorno claro → plata legible).
- **`t3.env(colores | {colors, glow, intensity, bg})`** — cielo vertical con un parche brillante opcional, horneado a PMREM; las reflexiones llevan la paleta de la marca. **Llámalo antes de crear mallas** (si lo mueves después, hay que recompilar materiales). El `glow` es la única fuente de especular fuerte que verán los objetos: ponlo donde quieras el brillo. `intensity` (0.85 por defecto) es el mando de "cuánto refleja".
- **`t3.rig({from, to, look, start, end, orbit, fov, fovEnd, ease})`** — la cámara como función pura del tiempo del timeline: deriva/dolly de `from` a `to` entre `start` y `end`, con órbita opcional (radianes) alrededor del punto mirado y fov interpolado. Sustituye un tween de `cam.position` cuando quieres que el encuadre sea reproducible cuadro a cuadro sin estado; dentro de `pre()` corre **después** de que el render fijó la cámara, así que el último que escribe gana.
- **`t3.ortho(escala)`** — cambia a cámara ortográfica desde la pose actual (`escala` = unidades de mundo visibles en vertical). Es el look isométrico/plano; conserva `t3.look` y los anclajes siguen funcionando (el proyecto de anclajes usa `t3.camera`, no la cámara original).
- **`t3.softShadow({res, bounds, radius, samples})`** — sube el mapa de sombras (2048) y **aprieta el frustum** al tamaño de la escena: mismo número de téxeles repartidos sobre menos metros = borde de sombra limpio. Requiere `t3.studio()` antes.
- **`t3.ao(radio, opacidad)`** — oclusión falsa: un sprite radial oscuro tumbado en el suelo. Es lo que hace que un objeto se apoye en vez de flotar, y cuesta un quad.
- **`t3.bloom({amount, blur, threshold, gain, saturate})`** — glow real **sin pase extra de WebGL**: un segundo canvas encima del primero con los mismos píxeles, aislados por umbral de brillo (`feComponentTransfer` en SVG), desenfocados por CSS y sumados con `mix-blend-mode: screen`. Se dibuja en `t3._post`, después del render. `threshold` (0.7) es lo que separa un bloom de una neblina: sin umbral el blend aclara **todo** el cuadro (medido: +2 a +4 niveles en 295 437 píxeles, o sea lavado global, no halo); con umbral el halo se queda en las altas luces. Necesita algo brillante que aislar (`emissive`, texto blanco, especular) — en un fondo claro un bloom suave no se ve.

Regla de composición: **un** héroe por escena. Los helpers de arriba se encadenan (`t3.env(...).softShadow(...).bloom(...)`) y todos devuelven `t3`.

## Relación con HyperFrames (HeyGen, Apache-2.0)
Mismo principio (HTML + línea de tiempo en pausa + seek por fotograma + ffmpeg), distinto empaque. HyperFrames aporta un CLI (`init`, `check`, `snapshot`, `render`), un estudio de edición, un catálogo de bloques ya hechos y un contrato más estricto (`class="clip"`, `data-start/duration`, `window.__timelines[id] = tl`, zonas 90 %/80 %). Este skill es más ligero y trae sus propias validaciones de legibilidad, sonido sintético y plantillas, pero **no** genera proyectos HyperFrames ni los lee. Camino de migración (NO probado): cada `timeline.js` ya es HTML + GSAP determinista, así que puede alojarse como "Hosted" registrando su timeline en `window.__timelines`; si el usuario quiere editar en el estudio de HyperFrames, usa su skill `hyperframes` (y `remotion-to-hyperframes` para código Remotion).
