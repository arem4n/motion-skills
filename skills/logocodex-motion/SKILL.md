---
name: logocodex-motion
description: Genera videos de motion graphics a partir de un logo usando la metodología LogocodeX™ (semiótica Peirce/Barthes + arquetipos de marca) con un motor híbrido GSAP + render determinista (compatible con Remotion y Hyperframes). Úsalo siempre que el usuario quiera animar un logo, hacer un logo reveal, una intro/outro de marca, un reel o video de identidad, "motion graphics" de una marca, o mencione LogocodeX, tipomorfía, arquetipos aplicados a animación, GSAP, Remotion o Hyperframes junto con un logo o identidad visual — aunque no pida explícitamente un "skill" ni diga "LogocodeX". También cuando traiga un logo (PNG/SVG) y pida "ponle movimiento", "anímalo" o "hazme un video con esto".
---

# LogocodeX Motion

Convierte un logo en un video de motion graphics **con intención**: cada capa del logo entra en el orden en que el
manual LogocodeX™ dice que se lee (denotación → connotación → mito), con el tempo y la curva de movimiento del
arquetipo de la marca, y el último frame es el logo exacto. La animación no decora el símbolo; **cuenta el análisis
semiótico que ya lo sostiene**.

Motor: timelines **GSAP en pausa** + seek por frame. Es el mismo principio de Remotion (`@remotion/gsap`) y de
Hyperframes (HTML + GSAP + seek), así que lo que se escribe aquí se porta a cualquiera de los dos. Render por defecto:
Chromium headless + FFmpeg, sin build step.

## Flujo de trabajo

Sigue estos pasos en orden; los pasos 1–2 son lo que hace distinto el resultado, no los saltes.

### 1 · Brief LogocodeX (antes de tocar código)
Rellena la plantilla del punto 8 de `references/storyboard-from-semiotics.md`. Necesitas:
- **Arquetipo primario (y secundario)** de la marca. Si el usuario trae el caso de estudio del manual, tómalo de ahí;
  si no, dedúcelo del manual de la marca o pregunta en una sola pregunta. Mapa de arquetipo → movimiento en
  `assets/motion-tokens.json` (léelo con `references/archetypes-to-motion.md`).
- **Qué significa cada capa** del logo y qué letras esconde (tipomorfía). De ahí sale el storyboard.
- **Formato y duración** (por defecto reel 1080×1920, 30 fps, 10–16 s) y **paleta** del manual de la marca.

Si falta el análisis, haz una versión breve tú mismo (capas, significado, arquetipo) y muéstrasela al usuario en 5–6
líneas antes de animar; es barato y evita rehacer.

### 2 · Separar el logo en capas con significado
El logo suele venir como un solo bloque de píxeles. Se separa por regiones y se vectoriza cada capa:
```bash
python3 -I scripts/grid_preview.py --image logo.png --out grid.png            # rejilla con coordenadas del lienzo de trabajo (ancho 2000)
python3 -I scripts/split_logo_layers.py --image logo.png --config layers.config.json --out layers.json --js layers.js --preview layers_preview.png
```
- Mira `grid.png` (Read) y define polígonos/rectángulos en `layers.config.json` (formato en la cabecera del script;
  ejemplo real: `examples/areman/layers.config.json`).
- Una capa = un significado. **Si una forma cumple dos funciones (la montaña que es la letra A) no la partas.**
- Abre `layers_preview.png` (cada capa en un color) para confirmar que ninguna se llevó píxeles ajenos.
  Usa `overlap: 2` en la capa que se pinta encima para esconder la costura de antialiasing entre capas vecinas.
- **Logo blanco/claro sobre PNG transparente** (se ve blanco sobre blanco): pon `"mode": "alpha"` en la config (la tinta es la parte opaca), usa `ink: '#fff'` y fondo oscuro en `scene.html`, y valida con `--source-mode alpha`. Caso: `examples/tommybox/`.
- Si el usuario tiene el SVG, se puede usar directamente separando por grupos; el flujo anterior es para PNG.

Dependencias: `pip install potracer opencv-python pillow --break-system-packages`.

### 3 · Crear el proyecto
```bash
python3 -I scripts/new_scene.py --project ./mi-video --layers layers.json --archetype sabio
```
Genera `scene.html` (cargador mínimo), `timeline.js` (la animación: `buildTimeline(kit, stg, T, tl)`), `lib/motion-kit.js`, `tokens.js`, `layers.js` y copia GSAP con todos sus plugins
(gratis en npm desde 3.13). Para partir de una escena terminada usa `--scene examples/areman/scene.html` (copia el `timeline.js` vecino).

### 4 · Escribir la escena
Edita `timeline.js`: exporta `buildTimeline(kit, stg, T, tl)`, agrega los tweens a `tl` (en pausa) y devuelve la duración total. `scene.html` solo lo monta y llama `kit.expose(tl)`; así el mismo archivo sirve para Remotion (`assets/templates/remotion/`, probado).
Usa los helpers del kit y los **tokens** (`T.d()` escala duraciones por el tempo del arquetipo, `T.ease.*`, `T.gap()`,
`T.hold`). Estructura en tres actos con comentarios que expliquen *por qué* entra cada cosa (ver `examples/areman/scene.html`).

| Helper | Qué hace |
|---|---|
| `kit.wipe(tl, node, dir, {at,dur,ease})` | revela abriendo un rectángulo de recorte: `up`, `down`, `left`, `right`, `out-x` (desde el eje, simetría heráldica), `out-y` |
| `kit.rise(tl, node, {dx,dy,at,dur})` | llega desde un desplazamiento |
| `kit.grow(tl, node, {sx,sy,origin:[x,y],at,dur})` | escala a su tamaño real alrededor de un punto (base del árbol, centro del cuello) |
| `kit.fade(tl, node, {at,dur})` | opacidad 0→1 |
| `kit.tint(tl, [nodos], color, {at,dur,hold,backDur})` | tiñe y vuelve al color canónico (beat tipomórfico: forma + letra gemela) |
| `kit.drift(tl, stg, {from,at,dur})` | asentamiento de cámara: termina en escala 1 exacta |
| `kit.sweep(tl, node, {from:[x,y], to:[x,y], width, at, dur, ease})` | revela con un borde recto que viaja a lo largo de un vector, como un trazo (las patas de la A que bajan desde el vértice) |
| `kit.unfold(tl, node, {origin, rot, sx, at, dur, easeRot})` | apertura articulada desde una junta (ala desde el hombro); con `back.out` pasa su reposo y se asienta |
| `kit.camera(tl, stg, [{from?,to,at,dur,ease}...])` | cámara encadenada sobre todo el escenario: empuje, golpe seco en el hit, asentamiento a escala 1 |
| `kit.window(tl, node, {top,bottom,left,right})` + `kit.rise(..., {inner:true})` | ventana de recorte fija por la que la forma asoma (una cabeza que sube desde el borde de una barra) |
| `kit.hide(tl, node, how)` | oculta hasta su entrada |
| `kit.stage / tokens / expose` | monta el SVG de capas, funde arquetipo + defaults, publica `__seek/__duration/__labels` |

Plugins de GSAP (MorphSVG, DrawSVG, MotionPath, SplitText) están en `vendor/`; cárgalos con `<script>` y
`gsap.registerPlugin(...)` cuando el storyboard los pida (p. ej. morph de la montaña a la A del nombre). Detalles y
trampas de determinismo: `references/determinism-and-engines.md`.

Siempre: `tl.addLabel('rest', t)` en el momento en que el logo está completo y en su color; la duración final con
`tl.set({}, {}, end)` (dentro de `buildTimeline`); y un asentamiento (`drift`) que acabe en escala 1.

### 5 · Validar y mirar
```bash
python3 -I scripts/validate_motion.py --scene mi-video/scene.html --size 1080x1920 \
  --source logo.png --sheet contact_sheet.png --report report.json
```
Comprueba contra las reglas del manual (§5 Manual de Aplicación Visual): lint de no-determinismo, acceso aleatorio,
**integridad del logo** (último frame vs original, ≤1 px), **integridad cromática** (ningún acento queda teñido),
**márgenes seguros** y tramos estáticos. Genera además una hoja de contacto: **ábrela con Read y revisa la historia**
(¿entra cada elemento de algo anterior?, ¿se lee la tipomorfía?, ¿el ritmo respeta al arquetipo?). Corrige hasta que
todo esté en PASS; un WARN de tramo estático en arquetipos lentos (sabio, gobernante, ancestro) suele ser intencional.

### 6 · Render y entrega
```bash
python3 -I scripts/render_frames.py --scene mi-video/scene.html --out video.mp4 --size 1080x1920 --fps 30
python3 -I scripts/render_frames.py --scene mi-video/scene.html --still 7.5 --out frame.png --size 1080x1920   # un frame
```
Entrega el MP4 (SendUserFile), la hoja de contacto, y una frase sobre lo que cuenta la secuencia. Ofrece variantes
(otro arquetipo, 1:1, versión corta de 4 s) en lugar de adjuntar todas.

## La tipomorfía es guía, no efecto
Mostrar la letra escondida (teñirla, subrayarla) explica lo obvio y rebaja el símbolo. Úsala como **geometría que dirige
el movimiento**: la A de la montaña se *escribe* con dos trazos que bajan por sus pendientes (`sweep`); la M de las alas
es la pose más alta del despliegue (`unfold` con overshoot), y en ese mismo golpe caen las letras A y M del nombre y el
resto se arma alrededor. El espectador lo siente sin que se le explique. Para esto parte el símbolo en las capas que el
movimiento necesita (`examples/areman/layers.config.json`: mitades de la montaña, cabeza y alas separadas).

## Reglas de oro (con su porqué)

- **Cada frame es función del tiempo.** Sin `Math.random`, relojes, timers, callbacks ni `repeat:-1`; si no, el render
  no es reproducible y Remotion/Hyperframes lo rechazarían. El validador lo vigila.
- **No uses máscaras de borde recto sobre masas negras sólidas** (alas, torso): se leen como bloques. Para ellas, despliegue + fundido corto.
- **Nada flota solo.** Todo elemento nuevo nace de uno ya presente; es la cadena de asociaciones del método.
- **El símbolo no se deforma.** Solo escalas uniformes, traslaciones y recortes; el último frame es el original. Es el
  principio de consistencia del manual (§5.1) y lo que distingue esto de una plantilla de presets.
- **Color = significado.** Paleta del manual; en logos heráldicos Sable y Argent y un único acento para la capa oculta.
- **El arquetipo manda sobre el gusto.** Héroe asciende: la cabeza *sube*, no cae ni rebota. Un Sabio no rebota, un Bufón no se mueve en legato. `avoid` en los tokens.
- **No mezcles `x/y` con `svgOrigin` en el mismo elemento SVG:** GSAP desplaza el origen. El kit ya usa grupos separados.

## Problemas conocidos

| Síntoma | Causa | Arreglo |
|---|---|---|
| Un elemento termina desplazado unos px | `x/y` + `svgOrigin` en el mismo nodo | usar `grow` del kit (grupo `gs` aparte) |
| Línea fina entre dos capas vecinas | antialiasing de bordes compartidos | `overlap: 2` en la capa superior |
| `logo-integrity` falla | escala/offset o capa mal cortada | revisar que `drift` termine en 1 y el recorte de capas |
| `random-access` falla | callbacks, tweens que mutan el mismo prop en conflicto, estado inicial sin `set` | usar `set` en t=0 + `to` |
| Texto con otra fuente en el render | la tipografía no estaba cargada | usar paths (ya vienen vectorizados) o `document.fonts.ready` |
| Chromium no encontrado | falta `PLAYWRIGHT_BROWSERS_PATH` | `python3 -m playwright install chromium` |

## Referencias
- `references/storyboard-from-semiotics.md` — análisis → storyboard; tabla de actos; léxico de movimiento por signo; plantilla de brief.
- `references/archetypes-to-motion.md` — cómo leer los tokens, elegir arquetipo, ejemplos de los casos del manual.
- `references/determinism-and-engines.md` — reglas de determinismo, plugins GSAP, destinos de render (este skill, Remotion, Hyperframes).
- `examples/tommybox/` — logo claro sobre transparencia, arquetipo Héroe, 3,2 s: figura que se construye de abajo hacia arriba y el box que cierra.
- `examples/areman/` — caso completo: `layers.config.json`, `layers.json`, `scene.html` + `timeline.js` (escudo AreMan v2, arquetipo Ancestro, 6,4 s, 9:16; tipomorfía como guía).
