# Recetas por formato

Todos arrancan de `assets/templates/<formato>/`. Duraciones orientativas con tempo 1.0.
Las cinco plantillas pasan `validate.py` con 14/14 en 1080×1920 `corporate`, y sin FAIL en las 6 personalidades y en 1920×1080 y 1080×1080 (`smoke_test.py --matrix`). Avisos conocidos que no son fallos: `fast-move` en horizontal y con `playful` (render con `--shutter 8`), `hook` con `calm` (arranca a los 0,6–0,7 s).

## kinetic — mensaje en golpes (reels, ganchos, anuncios)
- Estructura: hook (2–3 líneas gigantes, una por golpe) → el hook sale y **la barra de acento crece hasta ser el botón** (`MG.morph`: algo sobrevive al cambio) → línea de apoyo + CTA. Una sola escena; si necesitas dos, usa una transición que lleve algo (`zoom-through`, `morph`, `carry`).
- Pide: titular (≤ 3 líneas de ~10 caracteres), apoyo (≤ 2 líneas), CTA, colores de marca.
- Tiempos: 4–6 s. Un cue `hit` por línea, `tick` al cerrar el gancho, `whoosh` en la transición, `pop` en el CTA.
- Errores: titulares largos (se achican y pierden golpe); más de 3 líneas; CTA fuera de la zona segura inferior.

## data — un número que importa
- Estructura: título que enuncia la conclusión (se queda quieto) → barras crecen y cuentan → la barra clave se resalta y el resto se atenúa a 0,55 (no menos: bajo ~0,5 se lee como desaparecido) → *takeaway* + fuente (≥ 2,8 % del lado corto, dentro de la zona segura).
- Pide: serie de datos real, unidad, periodo y **fuente**. Si falta algo, deja `(indicar)`; jamás inventes cifras.
- Tiempos: 5–7 s. `tick` por barra, `hit` al resaltar.
- Variante línea: `MG.lineChart` + `MG.drawLine` para series temporales. Un solo mensaje por gráfico.
- Errores: más de ~7 barras, colores sin significado, título que describe en vez de concluir.

## explainer — pasos → resultado
- Estructura: título → 3 tarjetas (número, icono dibujado, título, texto) con conectores → `zoom-through` hacia dentro de la última tarjeta → resultado (check + frase). La pausa antes del salto se calcula con el largo del texto (caracteres/15 + 1,5 s).
- Pide: 3 pasos (verbo + 1 línea), resultado, tono.
- Tiempos: 6–9 s. Iconos con `MG.draw`.
- Errores: pasos largos (el texto debe leerse en 1 s), más de 4 pasos (divide en dos piezas).

## three — un objeto 3D héroe (Three.js)
- Estructura: el objeto cae/entra y aterriza con golpe (squash + rebote proporcional a su masa) → la cámara hace UN recorrido (inmersión/dolly) → leyenda en DOM sobre el canvas. Plantilla: `assets/templates/three`.
- Reglas (adaptadas de la guía 3D de HyperFrames y del skill de Three.js): un solo héroe (≥ 40 % del cuadro); entra *dentro*, no solo orbites (un recorrido vale diez giros); luz clave cálida + contraluz frío + reflejos tenues de sala (`t3.studio()`) y sombra de contacto (`t3.ground()`); sin bloom salvo en los puntos más brillantes; metal brillante: rugosidad ≥ 0.45 y `env` ≈ 0.5; la UI de producto nunca se inclina en 3D, solo el contenido generado.
- Determinismo: todo se anima con tweens sobre propiedades (`pivot.rotation`, `cam.position`, `t3.look`, materiales); el kit redibuja tras cada seek. Simulaciones (física, partículas): se calculan UNA vez al construir en arrays y luego se consultan por `t` (`t3.pre(function(t){…})`); azar solo con `MG.rng(semilla)`. Un píxel NaN ennegrece el cuadro vía bloom: acota divisiones.
- Etiquetas ligadas a objetos: `t3.anchor(obj,{offset:[x,y,z],dx,dy})` devuelve un div que sigue al objeto proyectado; mete dentro `MG.text(a,{x:0,…})`. `shiftY:0.15` en `MG.three` sube la imagen para dejar libre el tercio inferior (leyendas). Trampas probadas en piezas largas (video del sistema de agentes, ver `examples/`):
  - Cámara cenital (y alto): un offset de etiqueta «hacia arriba» en mundo apenas se mueve en pantalla y el texto cae SOBRE el objeto. Coloca la etiqueta en pantalla con `dy` (debajo del cubo, `dy≈+90*u`), no solo con `offset` 3D.
  - Un cable/tubo que pasa por detrás de una etiqueta la ensucia: ancla la etiqueta al lado opuesto del trazado.
  - Etiqueta anclada detrás de una pantalla/lid (portátil) queda invisible: sácala por delante (`offset:[0,0,+z]` + `dy`).
  - Objetos grandes que reaparecen mientras la cámara aún viaja cruzan los títulos: haz `pop` solo cuando la cámara haya terminado su `go()`.
  - Relevo de títulos: el `until` de uno = el `at` del siguiente − 0.4 s (fundido listo cuando entra el otro); si no, quedan pantallas sin título (`text-gap`).
  - Con N elementos en anillo (N≥12) sube el radio/aleja la cámara y revisa el margen lateral; etiquetas ≥40 px en 1080 de ancho.
  - Las etiquetas que salen del margen mientras la cámara retrocede: retíralas ANTES del `go()`.
  - Cifras (herramientas, perfiles, versiones) se verifican contra la fuente antes de ponerlas; si no, marcador `(indicar)`.
- En vertical el ancho visible es estrecho: usa fov ~42 y aleja la cámara (ancho ≈ 0.43·distancia); retira lo que sobre (escala a 0) en vez de apretar todo en cuadro.
- Texto: DOM encima del canvas (nítido y animable con `MG.in`); texto dentro del objeto con `t3.textTexture` (las fuentes ya cargadas por `MG.ready`).
- Costes: WebGL va por GPU si el proceso puede abrir `/dev/dri/renderD128` (automático; `MOTION_STUDIO_GPU=0|1` lo fuerza) y si no, por software (SwiftShader), unas 3–4 veces más lento; sombras suaves y mallas grandes pesan sobre todo en software. El resultado es estable entre corridas en ambos modos, pero GPU y software no dan los mismos píxeles exactos (diferencia invisible, ~53 dB PSNR): no compares cuadros de uno contra el otro. Prueba con `--still` antes de renderizar entero.
- Modelos GLTF/texturas: no incluidos en el kit; si hacen falta, cárgalos en el build con `MG.ready` extendido y registra la promesa antes de exponer (aún sin plantilla: avísalo).

## blank — todo lo demás
Títulos de apertura, lower thirds, promos de producto, pantallas de UI animadas, countdowns. Compón con `MG.text/box/image/icon`, elige un héroe por escena y aplica los cuatro actos. Para capturas de pantalla: `MG.image` con `fit:'contain'`, entrada `scale`/`rise` suave y un solo foco (resalta con `emph`, no animes toda la UI).

## Proporciones
Retrato 1080x1920 (reels/stories/shorts), cuadrado 1080x1080 (feed), horizontal 1920x1080 (YouTube/presentación). Los tamaños escalan con `u = min(w,h)/1080`; revisa siempre la zona segura del formato.

## Duración y tamaño de entrega
30 fps por defecto (`--fps 60` si hay movimiento rápido de texto fino). CRF 18 por defecto; sube a 14 solo si hay degradados grandes con bandas.
