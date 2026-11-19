# Motor: GSAP + render determinista (Hyperframes-style, Remotion o navegador)

## La idea que une GSAP, Remotion y Hyperframes

Un video renderizado no tiene reloj: cada frame es una **función pura del tiempo** (`frame = f(t)`). GSAP lo permite
si el timeline nace **en pausa** y alguien lo posiciona con `tl.time(t)`. Remotion lo exige (`useCurrentFrame`) y su
paquete `@remotion/gsap` hace justo eso; Hyperframes lo declara como protocolo de seek (`window.__hf`) y captura
con Puppeteer + FFmpeg. Este skill usa el mismo principio con un protocolo mínimo propio:

```js
MotionKit.expose(tl)  // define window.__seek(t), window.__duration, window.__labels
```

Todo lo que escribas contra `motion-kit.js` es portable a los tres.

## Reglas para que cualquier frame sea reproducible (y por qué)

1. **Timeline en pausa, sin ticker**: `gsap.timeline({ paused: true })`. Si algo avanza solo, el render sale distinto cada vez.
2. **Estado inicial con `tl.set(..., 0)` + `tl.to(...)` posterior** (no `fromTo` con `immediateRender:false`). Así,
   saltar directo al segundo 9 deja a cada elemento en el estado correcto aunque nunca haya pasado por el segundo 0.
   Los helpers del kit ya lo hacen.
3. **Nada de `Math.random`, `Date.now`, `performance.now`, timers, `requestAnimationFrame`, `repeat: -1`.**
   Si necesitas "azar", usa una tabla fija de desplazamientos. `validate_motion.py` lo detecta.
4. **Sin callbacks** (`onComplete`, `onUpdate`, `.call()`): se disparan al pasar la cabeza y se rompen al hacer seek hacia atrás.
5. **No mezcles `x/y` con `svgOrigin` en el mismo elemento SVG.** GSAP recalcula el origen y el elemento queda
   desplazado (se vio en AreMan: el cóndor terminaba 16 px más arriba). El kit separa en dos grupos: `g` (clip,
   opacidad, traslación) y `gs` (escala alrededor de un punto).
6. **Los tweens de color (`fill`) dejan `style="fill: rgb(...)"` al revertirse.** Es el mismo color; por eso la
   comparación de frames del validador tolera ruido de antialiasing y falla solo si cambia una parte visible.
7. **Termina en label `rest`**: `tl.addLabel('rest', t)`. Ahí el logo está completo y en su color canónico; el
   validador lo compara con el original.
8. **Última duración fija**: `tl.set({}, {}, end)` fija la duración total aunque el último tween termine antes.

## Técnicas SVG que sí valen la pena

| Necesidad | Herramienta | Nota |
|-----------|-------------|------|
| Revelar una forma con dirección | `kit.wipe(tl, node, 'up'\|'out-x'...)` | anima un `<rect>` de `clipPath`; funciona en cualquier navegador y renderizador |
| Crecer desde la raíz / el centro | `kit.grow` (escala con `svgOrigin`) | combínalo con `wipe` para que no "infle" desde un punto equivocado |
| Teñir forma + letra gemela | `kit.tint(tl, [nodoA, letra], color)` | vuelve solo al tinta original |
| Trazar contornos (efecto "dibujado") | `DrawSVGPlugin` | exige trazos, no rellenos: convierte la capa a `stroke` con `fill: none` primero |
| Transformar una forma en otra (montaña → A del nombre) | `MorphSVGPlugin` | `gsap.registerPlugin(MorphSVGPlugin)`; ambos paths con `fill-rule evenodd`; prueba con `shapeIndex` |
| Texto por letras | `SplitText` | solo para texto vivo; los logos ya traen sus letras como paths |
| Trayectorias | `MotionPathPlugin` | para estelas e índices (huella del movimiento) |

Desde GSAP 3.13 todos los plugins están en el paquete público de npm (`npm i gsap`); `new_scene.py` los copia a `vendor/`.

## Destinos de render

### A) Este skill (por defecto, sin build step)
```bash
python3 -I scripts/render_frames.py --scene project/scene.html --out out.mp4 --size 1080x1920 --fps 30
```
Playwright/Chromium hace seek → screenshot → FFmpeg. Idéntico en espíritu a `@hyperframes/engine`.
Requiere Chromium (`PLAYWRIGHT_BROWSERS_PATH`) y `ffmpeg`.

### B) Remotion (cuando el video vive dentro de un proyecto React)
**Probado.** `assets/templates/remotion/` monta el stage una vez (`useLayoutEffect`), construye el timeline en pausa con
el mismo `buildTimeline` de `timeline.js` y en un segundo `useLayoutEffect` (por frame) hace `tl.time(frame / fps, false)`; el seek debe ir en un efecto posterior al montaje, no en el cuerpo del render, o el primer render queda sin posicionar. Con AreMan el resultado
es idéntico píxel a píxel al renderer del skill. Instrucciones en su `README.md`. Para Chromium del sistema:
`npx remotion render ... --browser-executable=/ruta/a/chrome`.
`@remotion/gsap` (`useGsapTimeline`) es una alternativa válida pero no hace falta y no se probó aquí.

### C) Hyperframes
La escena es HTML + GSAP + un seek: es el destino más natural. Mapea `window.__seek` al adaptador de frames de
Hyperframes (o usa su skill `remotion-to-hyperframes` si ya tienes la escena en React). `npx hyperframes init` crea
el proyecto; pega `scene.html` como composición y conserva `layers.js`/`tokens.js`.

## Formatos

| Formato | Tamaño | Nota |
|---------|--------|------|
| Reel / Short / Story | 1080×1920 | respeta zonas seguras de UI: pasa `--safe 0.04,0.10,0.04,0.18` al validador |
| Cuadrado | 1080×1080 | feed |
| Horizontal | 1920×1080 | web, presentaciones |

El logo ocupa ~88 % del lado limitante. Para otro margen cambia `88` en la escena y pasa `--fill` al validador.
