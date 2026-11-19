# Mediciones y evidencia (2026-11-15) — NO se empaqueta en el .skill

> Copia íntegra de references/remotion.md y router.md tal como estaban antes de adelgazarlos. Datos de esta máquina (i7-6700, 7 GB) y de piezas concretas.

# Remotion: nativo e híbrido

Remotion es **opcional**. Elige con `references/router.md`. Las reglas generales de Remotion las mantiene su equipo en sus skills
oficiales (`remotion-markup`, `remotion-render`, …; instálalas con `npx remotion skills add` en el proyecto, o consulta
`remotion.dev/docs`). Aquí solo está lo que esas skills no dicen: cómo se une a este kit y lo que se midió en esta máquina.

## Camino híbrido: la misma `timeline.js` dentro de Remotion

```bash
PY=$(python3 scripts/setup.py --print)
$PY -I scripts/new_remotion.py --from proy --out proy/remotion --size 1080x1920 --personality impact --install
cd proy/remotion && npx remotion render src/index.ts Scene out.mp4 --image-format=png --is-production=false
```

`new_remotion.py` copia `timeline.js`, `tokens.js`, `lib/mg.js`, `fonts/` y `fonts.css`, mide la duración de la escena y escribe
`src/Root.tsx` desde `assets/remotion/Root.tsx.tpl`. Cada fotograma es `window.__seek(frame / fps)`: función pura del fotograma.
Editas `timeline.js` en `proy/` y la recopias a `proy/remotion/src/` (o enlázala).

### Medido (2026-11-15, escena `kinetic` 1080×1920, 138 fotogramas, concurrencia 2)
- **Tiempo:** Remotion 16,4–17,0 s; `render.py` (`--workers 2 --audio none`) 16,5 s. Empate.
- **RAM extra:** ~1,4–1,75 GB en ambos.
- **Píxeles frente a `render.py`** (fotogramas 10, 40, 75, 120): 0,16–0,65 % de píxeles difieren en más de 8 niveles, **todos en los bordes
  del texto y del botón**; fondo y grano coinciden exactamente. Es el suavizado de tipografía de otro Chromium (Remotion trae el suyo),
  no una diferencia de movimiento. No esperes igualdad bit a bit; sí esperas igualdad de posición y color.
- **`validate.py` funciona sin cambios** sobre la misma `timeline.js` usando `proy/scene.html`. No ve capas propias de Remotion.

### Escena real: `erp-southsoft-v2` (2026-11-15; 44,9 s, 1080×1920, 1349 fotogramas, 311 elementos DOM, 41 señales de sonido)
- **Tiempo:** Remotion 54,0 s; `render.py` 56,8 s (2 navegadores, sin audio). **RAM extra:** 1,68 GB frente a 1,76 GB. Empate otra vez.
- **Píxeles:** 10 fotogramas repartidos por el video, comparados desde los MP4: ≤ 0,74 % de píxeles difieren en más de 24 niveles
  (suavizado de texto y compresión); el primer fotograma es idéntico.
- **Sonido:** `scripts/add_audio.py --scene proy/scene.html --video remotion.mp4 --out final.mp4` mezcla las `MG.cue` con la misma
  ruta de `render.py`. El audio decodificado es **idéntico** (mismo md5) al de `render.py --audio auto`; −14,7 LUFS, pico −1,3 dBTP.
- **Validación sobre `scene.html`:** `validate.py` (0 FAIL; 2 WARN reales de la pieza: tramo estático final de 3,6 s y tiempo de
  lectura corto) y `entity_qa.py` (311 elementos, 1 texto vacío que nunca se ve, sin investigar) corren igual que para `render.py`.
- **Lo que falló la primera vez (y ya está arreglado):** la escena usa `MG.image src:'assets/logo-color.png'`. `new_remotion.py` no copiaba
  `assets/` y la ruta relativa no resolvía en Remotion. Ahora copia `assets/` a `public/assets/` y la plantilla añade un `<base>` apuntando
  a `public/`. Una imagen que falta no da error: sale un hueco.

### Varias escenas en una composición (2026-11-15)
```bash
$PY -I scripts/new_remotion.py --scene hook=./proyA --scene cierre=./proyB@premium --out ./combo --install
cd combo && npx remotion render src/index.ts Main combo.mp4 --image-format=png --is-production=false
$PY -I scripts/add_audio.py --scene proyA/scene.html@0 --scene proyB/scene.html@4.6 --video combo.mp4 --out final.mp4   # @inicio en segundos
```
Cada escena es un componente `<GsapScene>` dentro de un `<Series>` (`src/Main.tsx`); una tras otra, no solapadas. Para recortar una escena baja
su `durationInFrames`; para intercalar un clip o subtítulos nativos añade otra `<Series.Sequence>` con `<Video>` de `@remotion/media`
(y actualiza `TOTAL`). Si recortas una escena, pasa `@inicio:largo` a `add_audio.py` para descartar sus señales posteriores.
- **Fuentes por escena:** las variables `--font-display/--font-body` de cada `fonts.css` se aplican solo al contenedor de su escena; dos
  escenas con tipografías distintas no se pisan (Bebas Neue/Inter junto a Outfit, comprobado).
- **Estado compartido de `MG`:** las escenas comparten una sola copia de `mg.js` (señales y finalizadores se acumulan entre montajes). En esta
  prueba no causó ningún defecto: los fotogramas de la 2.ª y la 3.ª escena coinciden con su render aislado. Si algún día una escena
  "hereda" algo de la anterior, ese es el primer sospechoso. `<GsapScene>` guarda `window.__seek` en un ref al construir, porque la
  escena siguiente lo pisa.
- **Medido** (kinetic 4,6 s + clip nativo 3 s + primeros 10 s de `p1-dimensiones`, 528 fotogramas): 34,0 s (50 s la primera vez, en frío);
  la escena aislada y por separado tarda ~17 s (incluye ~10 s fijos de empaquetado y navegador). El tramo con `<Video>` es el
  caro en RAM (+2,2 GB). Fotogramas de cada escena vs su render aislado: 0,38–0,92 % de píxeles distintos (>24 niveles).
- **Con `new_remotion.py --scene`** (kinetic 4,6 s + `p1-dimensiones` completo, 1416 fotogramas, 47,2 s): 72,4 s de render (19,6 fps).
  `add_audio.py` puso 24 señales: la correlación cruzada con el audio de cada escena sintetizado aparte da el desfase esperado
  exacto (0,000 s y 4,600 s). El aviso `qa black frames` sale porque `p1-dimensiones` tiene fondo negro a propósito.

### Trampas (medidas, cada una costó un render en blanco)
1. **`setMounted(true)` dentro del layout effect de montaje, síncrono y antes de la promesa de fuentes.** Sin él el fotograma sale vacío.
   Con el `setState` solo después de construir la escena también sale vacío (81 % de píxeles distintos). Causa exacta desconocida:
   no lo quites. Está en la plantilla.
2. El seek va en un **segundo** `useLayoutEffect([frame, fps])`, nunca en el cuerpo del render.
3. Usa `MG.expose(tl)` y `window.__seek` (no `tl.time()` suelto): `__seek` clampa a ≥1e-4 y reasienta el grano.
4. Un PNG de Remotion es RGBA: **transparente se ve blanco** en un visor y negro al convertir a RGB. Antes de medir tiempos o píxeles,
   mira UN fotograma: una medición sobre fotogramas vacíos parece ¡mucho más rápida! (pasó: 9,9 s en blanco frente a 16,5 s real).
5. **Espacio en `/tmp`**: Remotion escribe temporales ahí. Si `/tmp` es `tmpfs` (RAM, 3,6 GB en este servidor) y está casi lleno, el render
   llega al 100 % y **falla al final** (`ffmpeg ... exit code 134` en el paso `faststart`) sin decir que falta espacio. Pasó con 778 MB libres:
   `df -h /tmp` antes. No instales `node_modules` de Remotion (~0,8 GB) dentro de `/tmp` más de una vez a la vez.
6. `window.SCENE` y `window.TOKENS` son globales: **una escena por página** con `--from`. Para varias, usa `--scene` (arriba): convierte cada
   `window.SCENE =` en un `export default` y evita el global.

### Licencia (decisión pendiente tuya, no la tomes por el usuario)
Remotion es gratis para una persona o una empresa de hasta 3 personas; si no, hay licencia de pago (Automators: 0,01 USD por render
con mínimo 100 USD/mes; Creators: 25 USD/mes por asiento). Fuente: `remotion.dev/docs/license/pricing`. Si SouthSoft u otro cliente
va a usar esto, confirma el tamaño del equipo antes. Con `--is-production=false` las pruebas no cuentan como renders facturables;
para renders reales con licencia gratis, `--license-key=free-license`.

## Subtítulos con voz de ElevenLabs: texto exacto del guion
La cuenta de ElevenLabs de Sergio está conectada **por OAuth** (el conector de claude.ai), no por clave de API; en el servidor no hay
`ELEVENLABS_API_KEY`. El conector **no** expone la alineación forzada ni el TTS con tiempos de la API; sí expone
`creative_transcribe_audio` (modelo `eleven_scribe_v1`), que devuelve inicio y fin en segundos de cada palabra (`words`, y `words_download_url`).
Camino por OAuth, que se hace desde la sesión de Claude (no es un script):
1. `creative_create_flow`; `creative_create_asset_upload` (nombre, mime, tamaño exacto) → `PUT` de los bytes con `curl` (no leas el archivo en la conversación) →
   `creative_finalize_asset_upload` con el `flow_id` → `node_id`.
2. `creative_transcribe_audio` con `estimate_only: true` primero y **enseña el costo**; solo con el visto bueno, la llamada real (una sola: reintentar cobra de nuevo).
3. Consultar `creative_get_flow_run_status` hasta `all_completed`; guardar `words` (o bajar `words_download_url`) en `palabras.json`.
4. `python3 -I scripts/script_to_captions.py --words palabras.json --text guion.txt --out src/captions.json`: pone el **texto exacto del guion** sobre
   los tiempos de Scribe (alinea ambas secuencias con difflib; las palabras que el reconocedor cambió se emparejan por posición o se interpolan y
   se listan para revisarlas de oído).

Subir `voz.mp3` y transcribir **envía el audio a ElevenLabs y gasta créditos**: pídelo siempre antes.
Si la voz la generas con el conector (`creative_generate_speech`), la generación tampoco da tiempos: se transcribe el resultado igual.

**Medido con el conector real (2026-11-15, `voz.mp3` de 41,7 s, español, voz clonada, guion de 107 palabras):**
- **Formato de `words` confirmado:** `{"words":[{"text","type":"word","start","end"}]}` en segundos (también viene en `transcripts[].words` y en `words_download_url`).
  `script_to_captions.py` lo lee sin cambios.
- **Texto:** Scribe acertó las 107 palabras frente al guion (Whisper `small` acertó 104: "sabe/sabes", "una/un" ×2).
- **Tiempos frente a las 13 pausas reales del audio** (`silencedetect` −35 dB, ≥ 0,3 s; error = tiempo de la palabra − tiempo de la pausa):

  | | fin de la palabra previa − inicio de pausa | inicio de la palabra siguiente − fin de pausa | palabras con > 50 % dentro de una pausa |
  |---|---|---|---|
  | **Scribe** | −0,05 … +0,04 s (mediana +0,01) | 0,00 … +0,07 s (mediana +0,03) | 0 |
  | Whisper crudo | −0,19 … **+0,77** s | −0,18 … **+0,27** s | 4 |
  | Whisper + `snap` | −0,19 … 0 s | 0 … +0,02 s (*circular*: se ajustó a esas mismas pausas) | 0 |

  Scribe deja los 13 límites de frase a ≤ 0,07 s **sin ningún ajuste**; el ajuste de Whisper solo iguala eso por construcción. Fracción de cada palabra
  con voz (10 ms, −30 dB): Scribe 0,77; Whisper + snap 0,71; Whisper crudo 0,66.
- **Límite de la comparación:** solo mide los límites de frase (pausas). Dentro de una frase no hay verdad externa (solo escuchando).
- **Conclusión:** para voces de ElevenLabs, Scribe vía OAuth es el camino principal; Whisper local (`transcribe.py`, con `snap`) queda como respaldo gratis
  y sin subir el audio.
- **Costo: la estimación mintió.** `estimate_only` dio 12,7 créditos (≈ 0,25 centavos de dólar); la ejecución real cobró **229,24 créditos (≈ 4,6 centavos)**,
  unas 18 veces más. Sigue siendo muy barato, pero **no confíes en la estimación**: avisa al usuario de que puede ser mucho mayor.
- La subida crea un flow en el canvas de ElevenLabs del usuario ("Prueba subtítulos …") con el audio dentro; se borra desde su web.
- `script_to_captions.py` también se probó con casos forzados (palabras omitidas/extra): 4 interpoladas, error de inicio ≤ 27 ms contra la referencia.
- `scripts/align_elevenlabs.py` (alineación forzada `align` y TTS con tiempos `tts` por **API con clave**) queda como alternativa si algún día hay una
  `ELEVENLABS_API_KEY`: probado solo contra un servidor local simulado, nunca contra la API real. Aquí no aplica.
Whisper local (`transcribe.py`, abajo) queda como respaldo para audios sin guion o sin subir.

## Subtítulos sincronizados con la voz con Whisper local (respaldo; probado 2026-11-15)
```bash
# 1) transcribir EN LOCAL a Caption[] de Remotion (python con faster-whisper; en esta máquina, el de Hermes)
HF_HUB_OFFLINE=1 ~/.hermes/hermes-agent/venv/bin/python scripts/transcribe.py --audio voz.mp3 --out src/captions.json --lang es --model small
# 2) copiar el componente y usarlo
cp assets/remotion/Captions.tsx <proyecto>/src/   &&   (cd <proyecto> && npx remotion add @remotion/captions)
```
```tsx
<Audio src={staticFile("voz.mp3")} />                      {/* Audio de @remotion/media */}
<Captions captions={captionsJson as Caption[]} fontFamily="Outfit, sans-serif" />
```
`Captions.tsx` agrupa con `createTikTokStyleCaptions`, enciende la palabra que se dice (solo cambia el color: la línea no salta) y escala con
`u = lado corto / 1080`. En vertical déjalo por encima de 340 px del borde (UI de la app); por defecto `bottom=420`.

Medido con `voz.mp3` de `p1-dimensiones` (41,7 s, español, modelo `small`, CPU i7-6700):
- **Transcripción:** 14,7 s, 107 palabras, sin red (modelos `small` y `base` ya en `~/.cache/huggingface`).
- **Audio del render:** idéntico a `voz.mp3` (desfase 0,0000 s, correlación 1,000). El render completo de 1251 fotogramas con voz tardó 66 s.
- **Sincronía, con la salvedad de que no hay verdad externa:** los inicios de palabra tras cada pausa real quedan a ±0,15 s de su fin
  (11 de 13 pausas; una a +0,27 s). **Whisper estira palabras sobre las pausas** (crudo: "Suma" salía 0,6 s antes de decirse), y por eso
  `transcribe.py` **ajusta por defecto** a los silencios reales de `silencedetect` (18 de 107 palabras cambiaron; `--no-snap` lo desactiva).
  Fracción de cada palabra con voz (medida aparte, ventanas de 10 ms a −30 dB): 0,66 → 0,71. Mejora modesta: el ajuste hace que el subtítulo
  no se encienda antes de la voz, no que cada palabra quede al milisegundo. Visto en fotogramas: durante la pausa de 0,5 s antes de "Suma"
  queda el subtítulo anterior sin resaltar, y "Suma" se enciende a los 28,79 s.
- **El texto es el de Whisper, no el del guion** ("no sabe si" donde el guion dice "no sabes si"). El script imprime las 5 palabras de menor
  confianza: revísalas y corrige `captions.json` a mano si el texto debe ser exacto. `--prompt` con nombres propios o jerga ayuda.
- No se probó `@remotion/openai-whisper` / `whisper.cpp` de Remotion ni transcripción externa (que enviaría la voz fuera de la máquina).

## Remotion nativo (clips, subtítulos, variantes)
- Proyecto base: `npx create-video@latest --yes --blank --no-tailwind <carpeta>` (o reutiliza `~/remotion-videos`).
- Reglas esenciales que sí conviene recordar: animar solo con `useCurrentFrame()` + `interpolate()` (nada de `transition` ni `animation` CSS);
  `output: 'perceptual-scale'` en escalas; `staticFile()` para `public/`; fuentes con `@remotion/google-fonts` o `@remotion/fonts`;
  `<ThreeCanvas>` y nada de `useFrame()`; `Easing.bezier(...)` con las curvas de `assets/personalities.json`.
- Fija `Config.setConcurrency(2)` (7 GB de RAM; ver `references/engine.md` sobre la fuga de memoria y earlyoom).
- Validación: sin `validate.py`. Saca fotogramas con `npx remotion render <id> out/ --frames=0,30,90 --image-format=png`
  (los nombra `element-NN.png`; lista la carpeta) y mira una hoja de contactos con `scripts/analyze_ref.py`/ojo. Revisa a mano lo que
  `validate.py` revisaría: zonas seguras, tamaño mínimo de texto (2,8 % del lado corto) y tiempo de lectura (`references/spec.md`).

---

# Router de motor: GSAP, Remotion o híbrido

Decide el motor **antes** de escribir código y dile al usuario en una línea por qué (para que pueda corregirlo):
`Motor: GSAP — kinetic puro, sin clips ni audio de entrada.` / `Motor: híbrido — 2 clips de video con audio + títulos animados.`

## Criterios (en este orden; el primero que se cumple decide)

| Si el encargo trae… | Motor | Por qué |
|---|---|---|
| **Clips de video o audio de archivo** que hay que recortar, mezclar o sincronizar | **Remotion** (`<Video>`/`<Audio>` de `@remotion/media`) | `render.py` no maneja video de entrada |
| **Subtítulos o palabras sincronizadas con la voz** | **Remotion** (`Captions.tsx` + tiempos: Scribe por el conector OAuth + `script_to_captions.py` si hay guion, o `transcribe.py` local) | Scribe (ElevenLabs/OAuth) probado con voz real: límites de frase ≤ 0,07 s; Whisper local como respaldo |
| **Muchas variantes** de una misma pieza desde datos (N productos, N personas) | **Remotion** (props + `calculateMetadata`, un render por fila) | props tipadas y duración calculada por dato |
| El usuario quiere **mover los cursores en un estudio** y editar a mano | **Remotion** (`npx remotion studio`) | Studio es el valor de Remotion |
| Algunas escenas son clips/subtítulos **y otras** tipografía cinética, logo, UI, 3D | **Híbrido** | Remotion como contenedor; las escenas de gráficos las pone GSAP |
| Todo lo demás: tipografía cinética, dato animado, explicador, objeto 3D, UI, título, lower third | **GSAP** (`render.py`) | camino por defecto, probado, con validador y sonido sintético |

**Alcance honesto:** lo probado y verificado aquí es el camino **híbrido de una escena GSAP** (`new_remotion.py` + `add_audio.py`), con una escena real de 45 s (`erp-southsoft-v2`) y con varias escenas GSAP y un clip nativo en secuencia (`--scene`). De Remotion nativo
se probó un `<Video>` con un texto animado encima y los subtítulos sincronizados con voz real (`transcribe.py` + `Captions.tsx`; el camino ElevenLabs/OAuth con Scribe probado en vivo); las variantes desde datos
quedan enrutadas pero **no probadas en este skill**; para el montaje usa las skills oficiales de Remotion
y las reglas de `references/remotion.md`. La descripción del skill sigue excluyendo video filmado: avisa al usuario si el encargo lo requiere.

**No elijas Remotion por gusto.** Costo medido (2026-11-15, escena kinetic 1080×1920, 138 fotogramas, 2 navegadores): mismo tiempo
(16,4–17,0 s Remotion frente a 16,5 s `render.py`) y mismo uso de RAM (~1,4–1,8 GB extra). El costo real es otro: un proyecto npm aparte
(~250 paquetes, 18–30 s de instalación, `node_modules` ~0,8 GB), la licencia (abajo) y que las validaciones de este skill solo ven la parte GSAP.

## Formato compartido: `scenes.json`

Escríbelo junto al `SPEC.md` cuando el motor no sea GSAP puro. Es una lista de escenas para el plan; **ningún script lo lee todavía**
(es disciplina de planificación, no configuración).

```json
{
  "salida": {"size": "1080x1920", "fps": 30, "formatos": ["9x16", "1x1"]},
  "escenas": [
    {"id": "hook",   "motor": "gsap",    "seg": [0, 2.4],  "heroe": "palabras en máscara", "contenido": "3 palabras",     "porque": "tipografía cinética"},
    {"id": "clip-a", "motor": "remotion","seg": [2.4, 9],  "heroe": "clip con subtítulos", "contenido": "clips/a.mp4",    "porque": "video de entrada + subtítulos"},
    {"id": "cierre", "motor": "gsap",    "seg": [9, 12],   "heroe": "logo + CTA",          "contenido": "brand.json",     "porque": "gráfico puro"}
  ]
}
```

Una línea por escena: qué motor, cuánto dura, **un** movimiento héroe, de dónde sale el contenido y por qué ese motor.

## Qué cubre cada camino

| | GSAP (`render.py`) | Remotion nativo | Híbrido (GSAP dentro de Remotion) |
|---|---|---|---|
| `validate.py` (legibilidad, pacing, safe-area, contraste…) | sí | **no** (usa fotogramas + ojo, ver `remotion.md`) | sí, sobre la parte GSAP vía `scene.html` |
| `entity_qa.py` | sí | no | sí, sobre la parte GSAP |
| Sonido sintético (`MG.cue` → `make_sfx.py`) | sí | no | sí: `scripts/add_audio.py` (audio idéntico bit a bit al de `render.py`) |
| Three.js (`MG.three`) | sí | `@remotion/three` (ver docs oficiales) | **no probado** |
| Vista previa interactiva | no (hoja de contactos) | `remotion studio` | `remotion studio` |

Detalle de montaje, trampas medidas y licencia: `references/remotion.md`.
