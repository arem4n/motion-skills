# Piezas producidas

Qué se publicó, con qué se hizo y cómo se comprueba. Objetivo: que la afirmación «esto salió de motion-studio» sea verificable y no un recuerdo.

## Shorts verticales (1080x1920) — canal Meta Sergius

Datos de YouTube al 26 nov 2026. La correspondencia con el proyecto local se estableció por nombre del proyecto y por duración del render local (±0,4 s respecto del video publicado).

| Video | Publicado | Vistas | Likes | Proyecto local | Render | Duración YT / local |
|---|---|---|---|---|---|---|
| [Dimensiones](https://www.youtube.com/watch?v=QZfzxeR5Da0) | 13 nov 2026 | 1426 | 56 | `videos/metasergius-tiktok/p1-dimensiones-v2` | `out/p1-dimensiones-v4-tiktok.mp4` | 53 s / 52,9 s |
| [Intención](https://www.youtube.com/watch?v=CyJQdoJCIGo) | 13 nov 2026 | 1216 | 31 | `videos/metasergius-tiktok/p4-intencion` | `out/p4-intencion-tiktok.mp4` | 48 s / 48,3 s |
| [Polaridad](https://www.youtube.com/watch?v=jyoJ97BnKWo) | 13 nov 2026 | 1194 | 38 | `videos/metasergius-tiktok/p2-polaridad` | `out/p2-polaridad-tiktok.mp4` | 50 s / 49,9 s |
| [Consciencia](https://www.youtube.com/watch?v=yGRaMiUi9t4) | 14 nov 2026 | 1202 | 50 | `videos/metasergius-tiktok/p3-conciencia` | `out/p3-conciencia-tiktok.mp4` | 42 s / 42,4 s |
| [Entre frecuencias](https://www.youtube.com/watch?v=JVlRZtJjbcc) | 21 nov 2026 | 1313 | 37 | `videos/metasergius-tiktok/p5-espectro` | `out/p5-espectro-tiktok.mp4` | 42 s / 41,6 s |
| [El sonido fuera de cuadro y el Foley](https://www.youtube.com/watch?v=ernj8MJppGw) | 22 nov 2026 | 1108 | 23 | `videos/cine-espejo/anim/s03` | `shorts/03-el-sonido.mp4` | 52 s / 51,9 s |
| [Los saltos del ojo y el ritmo del corte](https://www.youtube.com/watch?v=PSzRwFBfgbE) | 22 nov 2026 | 1155 | 27 | `videos/cine-espejo/anim/s02` | `shorts/02-la-mirada.mp4` | 58 s / 57,7 s |
| [La ilusión del movimiento y el motion blur](https://www.youtube.com/watch?v=jSt4MWC0uLI) | 22 nov 2026 | 256 | 5 | `videos/cine-espejo/anim/s01` | `shorts/01-24-cuadros.mp4` | 53 s / 53,3 s |

Los ocho proyectos contienen `scene.html`, `timeline.js`, `tokens.js` y `lib/mg.js` — el kit de motion-studio vendorizado —, así que la pieza se generó con este motor. En los cinco de `metasergius-tiktok` la correspondencia es directa por nombre de proyecto; en los tres de `cine-espejo` está inferida por tema y duración, no por un registro escrito en su momento.

Resumen: 8 shorts publicados, 7 superan las 1.000 vistas, mediana 1.210.

## Largos

Pendiente de mapear uno a uno. En el canal hay 5: `El cine como espejo` (80 vistas), `Dualidad` (161), `Consciencia ¿Qué es y cómo funciona?` (194), `La conexión entre la metafísica, ciencia y espiritualidad` (542) y el discurso de Bashar subtitulado (3.200, no es producción propia).

## Piezas sin publicar (uso interno o commercial)

- `videos/erp-southsoft-v2` → `out/erp-southsoft-con-voz.mp4`, 45 s. Pieza corporativa SouthSoft.
- `videos/tommybox-logo-3d` y `-v2` → logo reveal 3D, 5,7 s y 5,0 s.
- `videos/hermes-sistema-agentes` → 31,8 s y 32,1 s (v2), 1080x1920. Los dos MP4 quedaron en `~/` (`hermes-sistema-agentes-9x16.mp4`, `-v2.mp4`), fuera de la carpeta del proyecto; por eso el primer inventario no los encontró.
- `videos/metasergius-ilusion-sombra` → 33,5 s.
- `videos/metasergius-percepcion-director` → **no es motion-studio**: está hecho con HyperFrames (`hyperframes.json`, `index.motion.json`). Sirve como comparación entre motores, no como evidencia de este.

## Por qué importa

Una reseña externa solo pudo evaluar documentación, porque el repo no contenía ni una pieza terminada. Esta tabla es el registro mínimo que convierte la metodología en algo comprobable: qué se hizo, con qué versión del kit y cuánta gente lo vio. Al agregar piezas nuevas, añade la fila — con la fecha, la versión del kit si cambió y el resultado real, incluido el malo.
