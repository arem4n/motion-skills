# Router de motor: GSAP, Remotion o híbrido

Decide el motor **antes** de escribir código y dile al usuario en una línea por qué (para que pueda corregirlo):
`Motor: GSAP — kinetic puro, sin clips ni audio de entrada.` / `Motor: híbrido — 2 clips de video con audio + títulos animados.`

## Criterios (en este orden; el primero que se cumple decide)

| Si el encargo trae… | Motor | Por qué |
|---|---|---|
| **Clips de video o audio de archivo** que hay que recortar, mezclar o sincronizar | **Remotion** (`<Video>`/`<Audio>` de `@remotion/media`) | `render.py` no maneja video de entrada |
| **Subtítulos o palabras sincronizadas con la voz** | **Remotion** (`Captions.tsx`; tiempos según `references/subtitulos.md`) | flujo probado con voz real |
| **Muchas variantes** de una misma pieza desde datos (N productos, N personas) | **Remotion** (props + `calculateMetadata`, un render por fila) | props tipadas y duración calculada por dato |
| El usuario quiere **mover los cursores en un estudio** y editar a mano | **Remotion** (`npx remotion studio`) | Studio es el valor de Remotion |
| Algunas escenas son clips/subtítulos **y otras** tipografía cinética, logo, UI, 3D | **Híbrido** | Remotion como contenedor; las escenas de gráficos las pone GSAP |
| Todo lo demás: tipografía cinética, dato animado, explicador, objeto 3D, UI, título, lower third | **GSAP** (`render.py`) | camino por defecto, probado, con validador y sonido sintético |

**Alcance honesto.** Probado: el híbrido (una o varias escenas GSAP en secuencia, con un clip nativo intercalado, `new_remotion.py` + `add_audio.py`)
y los subtítulos con voz. **No probado:** variantes desde datos, escenas `MG.three` dentro de Remotion. Si el encargo cae ahí, dilo antes de empezar.

**No elijas Remotion por gusto.** Rinde igual que `render.py` (mismo tiempo y RAM, medido). Su costo es otro: un proyecto npm aparte
(~250 paquetes, `node_modules` ~0,8 GB), una licencia que depende del tamaño de la empresa (`references/remotion.md`) y que las
validaciones de este skill solo ven la parte GSAP.

## Tabla de escenas (dentro del SPEC.md)

Cuando el motor no sea GSAP puro, el SPEC lleva esta tabla. Es un plan para ti y el usuario, no un archivo de configuración:
lo que se ejecuta son los `--scene` de `new_remotion.py` (`references/remotion.md`), que salen de aquí.

| Escena | Motor | Segundos | Héroe (un solo movimiento) | Contenido | Por qué ese motor |
|---|---|---|---|---|---|
| hook | gsap | 0–2,4 | palabras en máscara | 3 palabras | tipografía cinética |
| clip-a | remotion | 2,4–9 | clip con subtítulos | clips/a.mp4 | video de entrada + subtítulos |
| cierre | gsap | 9–12 | logo + CTA | brand.json | gráfico puro |

## Qué cubre cada camino

| | GSAP (`render.py`) | Remotion nativo | Híbrido (GSAP dentro de Remotion) |
|---|---|---|---|
| `validate.py` (legibilidad, pacing, safe-area, contraste…) | sí | **no** (usa fotogramas + ojo, ver `remotion.md`) | sí, sobre la parte GSAP vía `scene.html` |
| `entity_qa.py` | sí | no | sí, sobre la parte GSAP |
| Sonido sintético (`MG.cue` → `make_sfx.py`) | sí | no | sí: `scripts/add_audio.py` (audio idéntico bit a bit al de `render.py`) |
| Three.js (`MG.three`) | sí | `@remotion/three` (ver docs oficiales) | **no** (el script lo rechaza) |
| Vista previa interactiva | no (hoja de contactos) | `remotion studio` | `remotion studio` |

Montaje, trampas y licencia: `references/remotion.md`. Subtítulos: `references/subtitulos.md`.
