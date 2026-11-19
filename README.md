# motion-skills

Dos skills de Claude para generar motion graphics en video de forma determinista (cada fotograma es función pura del tiempo: GSAP + Chromium + ffmpeg).

| Skill | Para qué |
|---|---|
| `skills/motion-studio` | Motion graphics generales: tipografía cinética, datos, explicadores, objetos 3D (Three.js), lower thirds, con sonido sintético y validación automática. |
| `skills/logocodex-motion` | Animación de logotipos guiada por semiótica LogocodeX (arquetipos, tipomorfía como guía oculta). |

**Fuente única:** `skills/` es la única copia editable. La skill instalada en Claude Code (`~/.claude/skills/motion-studio`) es un enlace simbólico a `skills/motion-studio`, así que no hay nada que sincronizar. `dist/` trae los `.skill` empaquetados; se regeneran con `python3 build.py` después de cualquier cambio (la copia de claude.ai solo se actualiza subiendo de nuevo `dist/motion-studio.skill`).

`dist/` queda listo para instalar. `examples/hermes-sistema-agentes` es el `timeline.js` y el `SPEC.md` del video 3D del sistema de agentes (versión corregida 2026-10-28: 15 perfiles, etiquetas sin solaparse, sin huecos de título).

## Uso rápido (motion-studio)
```bash
python3 skills/motion-studio/scripts/setup.py            # una vez: venv privado + Chromium
PY=$(python3 skills/motion-studio/scripts/setup.py --print)   # usa $PY en lugar de python3 abajo
$PY -I skills/motion-studio/scripts/new_project.py --project ./proy --format three --size 1080x1920 --personality premium --fonts bebas-neue:400,inter:500,700
$PY -I skills/motion-studio/scripts/validate.py --scene proy/scene.html --size 1080x1920 --sheet hoja.png
$PY -I skills/motion-studio/scripts/render.py --scene proy/scene.html --out video.mp4 --size 1080x1920
```
`render.py` elige solo cuántos navegadores usar según la RAM libre (≈0,9 GB por navegador a 1080p, ≈2 GB a 4K, dejando 1,5 GB libres).
Requisitos: Python 3, Node/npm, ffmpeg. Lo demás (numpy, scipy, Pillow, playwright + Chromium) lo instala `setup.py`.

Validaciones (`validate.py`, 14 comprobaciones): lint de determinismo, acceso aleatorio, gancho, final quieto, tramo estático, zona segura, tamaño, contraste, textos montados, huecos sin texto, señales de sonido, continuidad, movimiento rápido y tiempo de lectura; más `entity_qa.py` (cada elemento, fotograma a fotograma).

Tras cambiar el kit, una plantilla o el validador: `$PY -I skills/motion-studio/scripts/smoke_test.py` (`--matrix` para personalidades y formatos) y luego `python3 build.py`.

`docs/` guarda mediciones y material que **no** se empaqueta en el `.skill` (datos de esta máquina y de piezas concretas).

## Estado y límites
- El sonido es sintético y no ha sido auditado por una persona.
- No hay evaluación comparativa formal ni descripción optimizada para activación automática.
- No exporta a HyperFrames (ver `skills/motion-studio/references/engine.md`).
- Remotion es opcional (clips, voz con subtítulos, varias escenas): `references/router.md`, `remotion.md`, `subtitulos.md`. Su licencia depende del tamaño de la empresa.
- Sin historial de versiones: el directorio no es un repositorio git.

Ver `NOTICE.md` para créditos y licencias de terceros.
