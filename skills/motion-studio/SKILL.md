---
name: motion-studio
description: Motion graphics en video (MP4 con sonido) desde texto, datos o imágenes — tipografía cinética, reels, explicadores, gráficos de datos, 3D (Three.js), títulos, lower thirds, promos, UI animada; con Remotion, también clips, voz y subtítulos. Úsala siempre que pidan "una animación", "un video animado", "motion graphics", un reel/short animado, un explainer o un intro/outro. Es la skill de motion por defecto: prefiérela a hyperframes, motion-graphics y general-video salvo que el usuario nombre HyperFrames o su estudio. NO para logos LogocodeX (logocodex-motion), video/imagen con IA, ni editar metraje sin gráficos.
---

# motion-studio

Motion graphics por código: cada fotograma es una función pura del tiempo, así que el render es idéntico en cualquier máquina y cualquier fotograma puede pedirse en cualquier orden. Un mismo kit sirve para formatos distintos; lo que cambia es el **formato** (estructura), la **personalidad** (tempo, curvas, rebote) y el **contenido**.

## ¿Esta skill u otra?

| El pedido | Skill |
|---|---|
| Animación, reel, explainer, dato animado, 3D, título, lower third, promo, UI animada | **esta** (por defecto) |
| Lo mismo, pero con clips de video, voz en off o subtítulos | **esta**, motor Remotion (`references/router.md`) |
| Nombra HyperFrames, quiere su estudio o su catálogo de bloques, o portar código Remotion | `hyperframes` / `remotion-to-hyperframes` |
| Logo con análisis semiótico LogocodeX | `logocodex-motion` |
| Video o imágenes generados con IA, editar metraje sin gráficos | fuera de alcance: dilo |

## Modo rápido (pieza ≤ 6 s con todo el contenido dado: lower third, título, sting, un dato)

Sáltate SPEC.md, el router y `entity_qa`: motor GSAP, tesis en una línea (mensaje · formato · personalidad) y 3–5 cifras de estilo escritas como comentario al inicio de `timeline.js` (fondo, tinta, acento, curva, duración). **El storyboard (paso 2c) no se salta**: aquí basta con 2–4 filas. Luego pasos 5 → 6 → 7 → 8 → 9. **El paso 7 (validar y mirar la hoja de contactos) no se salta nunca.** Si el pedido crece (más de 6 s, contenido que falta, varias escenas), vuelve al flujo completo.

## Flujo completo (no te saltes el paso 1)

0. **Entorno (una vez)**: `python3 scripts/setup.py` crea un venv privado (`~/.cache/motion-studio/venv`) con playwright, numpy, scipy, pillow y Chromium (`--check` solo informa; no actualiza nada salvo `--upgrade`). **Todos los demás scripts corren con el python de ese venv**: `PY=$(python3 scripts/setup.py --print)` y luego `$PY -I scripts/…` (con el `python3` del sistema fallan: no ve playwright).

1. **Tesis de movimiento** — antes de escribir código, fija en 3 líneas y muéstralas si el pedido es ambiguo:
   - *Mensaje*: qué debe entender el espectador (una sola idea).
   - *Para quién / dónde se verá*: formato y proporción (reel 1080x1920, cuadrado 1080x1080, horizontal 1920x1080), duración objetivo.
   - *Personalidad*: una de `playful, premium, corporate, energetic, calm, impact` (ver `assets/personalities.json`). Si el usuario no la nombra, deduce desde marca/tono; no preguntes salvo que cambie mucho el resultado.
   Todo dato, cifra, cita o nombre sale del encargo. Si falta, deja un marcador visible `(indicar)`; **nunca inventes estadísticas**.
2. **SPEC.md con números** (`references/spec.md`): convierte cada adjetivo del encargo en una cifra (fondo, tinta, acento, tamaños, curvas, tomas, sonido) y nombra lo PROHIBIDO. Las plantillas son estructura, no estilo: sin SPEC caen en los defaults genéricos (fondo oscuro, todo centrado, píldora, fade-up). Pieza > 15 s que cuenta algo: antes, tres argumentos distintos en palabras para que el usuario elija.
2b. **Router de motor** (`references/router.md`): GSAP + `render.py` por defecto. Remotion solo si el encargo trae clips o audio de archivo, voz con subtítulos sincronizados, muchas variantes desde datos o pide editar en un estudio; híbrido si mezcla eso con gráficos. Di en una línea qué motor elegiste y por qué. Si no es GSAP puro, agrega al SPEC la tabla de escenas (ver router) y **pregunta por la licencia de Remotion si es para una empresa**.
2c. **Storyboard aprobado — siempre, antes de escribir código.** Escribe `storyboard.md` en el proyecto con una fila por golpe: `segundos | qué se ve | movimiento (y por qué) | sonido`, más formatos de salida y duración total. Muéstraselo al usuario resumido y **espera un sí** (o sus cambios). Cambiar una fila cuesta un mensaje; cambiar un render cuesta minutos. Solo sigues sin esperar si el usuario dijo explícitamente que no preguntes o si ya entregó él mismo el storyboard con tiempos (entonces lo reescribes en el archivo y lo dices en una línea). Si te llaman sin persona al otro lado (otro agente), entrega el storyboard como propuesta y detente.
3. **Elige formato** (`references/formats.md` tiene la receta de cada uno): `kinetic` (mensaje en golpes), `data` (un número que importa), `explainer` (pasos → resultado), `three` (objeto 3D héroe con Three.js), `blank` (lo demás: título, lower third, promo, UI).
4. **Color y marca** — si hay logo, captura o referencia visual: `$PY -I scripts/measure_palette.py imagen.png` y usa los hex medidos (bg/fg/accent). No adivines colores. Si hay un **video de referencia**: `$PY -I scripts/analyze_ref.py ref.mp4 --out ana/` mide cortes, largo de tomas y su variación, quietud, ráfagas, curvas (t80), desenfoque y paleta; esos números van al SPEC. Si el encargo nombra un look sin referencia, ver `references/style-extraction.md` (catálogo de estilos local). Tipografías: máximo 2 familias, vienen de npm (`@fontsource`).
5. **Andamio**: `$PY -I scripts/new_project.py --project ./proy --format kinetic|data|explainer|three|blank --size 1080x1920 --personality impact --fonts bebas-neue:400,inter:500,700`
   Crea `scene.html`, `timeline.js` (aquí se trabaja), `lib/mg.js`, `vendor/gsap`, fuentes y tokens.
6. **Escribe `timeline.js`** con el kit `MG` (tabla abajo). Un elemento héroe a la vez, una señal de sonido por cada golpe visual (`MG.cue`), y un final quieto. **Diseña en relativo** (`S.w`, `S.h`, `u = Math.min(S.w,S.h)/1080`, `portrait = S.h > S.w`; en 3D aleja la cámara en cuadros angostos, ver plantilla `three`): así la misma escena sale en cualquier formato.
6b. **Vista previa en vivo** (opcional, para el usuario): `$PY -I scripts/preview.py --scene proy/scene.html` imprime una URL (en la IP de Tailscale si existe). Barra de tiempo, play, cuadro a cuadro (← →), selector de formato, marcas de las señales de sonido; se recarga sola al guardar `timeline.js` y vuelve al mismo segundo. Usa el mismo `__seek` que el render: lo que se ve en un instante es ese cuadro. Déjala corriendo en segundo plano y dale la URL al usuario; no reemplaza el paso 7.
7. **Valida**: `$PY -I scripts/validate.py --scene proy/scene.html --size 1080x1920 --sheet hoja.png --report r.json`
   Mira la hoja de contactos (`Read` sobre el PNG) — los números no sustituyen el ojo. Corrige FAIL; los WARN se justifican o se arreglan. Comprueba además `text-overlap` (textos montados), `text-gap` (>1 s sin texto: un hueco entre títulos), `read-time` (frases que no alcanzan a leerse), `continuity` (los golpes se reemplazan como diapositivas en vez de transformarse), `rhythm` (tomas de largo parejo, como metrónomo), `fast-move` (algo viaja >80 px por cuadro: renderiza con `--shutter`) y `framing`. Lo que el validador NO ve: texto del DOM tapado por geometría 3D o etiquetas que caen sobre un objeto del canvas; eso solo lo ve la hoja de contactos (y `render.py --still t` en los instantes dudosos).
7b. **QA por entidad**: `$PY -I scripts/entity_qa.py --scene proy/scene.html --size 1080x1920` — elementos muertos, fuera de cuadro, congelados o que saltan (`references/qa-por-entidad.md`). Declara con `data-entity` lo que debe cumplir.
8. **Renderiza**: `$PY -I scripts/render.py --scene proy/scene.html --out video.mp4 --size 1080x1920` (audio automático desde las `MG.cue`; `--audio none` para mudo; `--music pista.mp3` para cama musical). Con `--still 1.5` saca un solo fotograma.
   - **Borrador** sin desenfoque (rápido: ~0,16 s por cuadro y navegador). Si `validate.py` avisa `fast-move`, usa `--shutter 8` (desenfoque de movimiento real; cuesta 8 capturas por cuadro en movimiento y 2 por cuadro quieto). **Entrega**: `--final` (60 fps al doble de tamaño, implica `--shutter 6`) solo cuando el borrador esté aprobado.
   - Los navegadores en paralelo se eligen solos según la RAM libre y los núcleos (cada uno ocupa ~0,9 GB a 1080p y ~2 GB a 4K, y siempre se dejan 1,5 GB libres). No pases `--workers` salvo para bajarlo; un número mayor al que cabe se reduce solo.
   - **Varios formatos de una vez**: `$PY -I scripts/formats.py --scene proy/scene.html --out-dir proy/out --formats 9x16,16x9,1x1,4x5 [-- --shutter 8]` valida cada formato, arma `<nombre>-formatos.png` (un cuadro de cada uno, lado a lado: **míralo**, el validador no ve el 3D cortado en los bordes) y renderiza un MP4 por formato. `--only-sheet` para revisar antes de renderizar.
   - **Sonido**: las señales `hit`, `thud`, `tick`, `step`, `pop` y `shimmer` usan **muestras reales CC0** (Kenney, en `assets/sfx/`); `whoosh`, `riser` y `sub` siguen sintéticas. `--sfx-source synth` vuelve a todo sintético. Sonidos locales con otra licencia (p. ej. Sonniss): carpeta con su `index.json` en `MOTION_STUDIO_SFX_DIR`; ganan para esa señal y nunca se empaquetan (`references/engine.md`).
   - El audio sale masterizado a **−14 LUFS** con limitador a −1,5 dBTP (`--loudness -14` por defecto; `off` deja la mezcla cruda). Al terminar, el script revisa el MP4 final: cuadros negros y volumen/pico medidos. Un `WARN` ahí se corrige antes de entregar.
9. **Entrega** el MP4 y la hoja de contactos (con la herramienta de envío de archivos si la sesión tiene una, p. ej. `SendUserFile`; si no, da las rutas completas). Dilo corto, en el idioma del usuario: qué hiciste, duración, qué WARN quedaron y por qué, y que **el audio es sintético y no lo has escuchado** (pide que lo oigan antes de publicar).

## Cómo piensa el movimiento (resumen; detalle en `references/direction.md`)

- **Tres pilares**: jerarquía (se mueve primero lo que importa), causalidad (todo movimiento tiene origen y dirección), carácter (la personalidad decide curvas y tempo).
- **Entradas desaceleran, salidas aceleran, el movimiento en pantalla va inout.** Usa `T.ease.in/out/move/pop` y `T.d(seg)`; no escribas curvas ni segundos sueltos: así un cambio de personalidad reescala toda la pieza.
- **Reglas de un tercio**: máximo un tercio de los elementos se anima a la vez; un tercio del tiempo es pausa (el ojo necesita leer).
- **Cuatro actos**: gancho (≤0.6 s hasta el primer cambio) → desarrollo → clímax/golpe → resolución quieta (≥0.5 s final sin movimiento).
- **Cada golpe visual tiene un sonido** exactamente en su fotograma; sin sonido en el vacío.
- Texto ≥ 2.8 % del lado corto, dentro de zonas seguras (retrato: 6 % lados, 10 % arriba, 14 % abajo), contraste ≥ 4.5:1.

## Kit `MG` (assets/lib/mg.js) — lo esencial

| Necesidad | Llamada |
|---|---|
| Escenario / escena | `MG.stage` (ya lo hace el loader), `S.scene(name,{bg})`, `MG.show(tl,sc,at,until)` |
| Elementos | `MG.text(sc,{text,x,y,w,size,weight,split:'words|lines|chars',font,color})`, `MG.box`, `MG.shape`, `MG.image`, `MG.icon`, `MG.barChart`, `MG.lineChart`, `MG.ring` |
| Entrar / salir / énfasis | `MG.in(tl,t,{how:rise|fade|pop|scale|slide-left|slide-right|mask,at,dur,ease,stagger})`, `MG.out`, `MG.emph(pulse|shake|wiggle)` |
| Datos | `MG.growBars`, `MG.drawLine`, `MG.counter`, `MG.typewriter`, `MG.draw` (trazo SVG) |
| Entre escenas | `MG.transition(tl,A,B,{type:cut|fade|push-left|push-up|wipe-right|wipe-left|zoom|iris|zoom-through|brush})`. `zoom-through`: la cámara se zambulle en una ventana de A (`rect` o `el`) hasta que B, que vive dentro, llena el cuadro. `brush`: pinceladas gruesas cubren, cambian las escenas debajo y se retiran |
| Continuidad (algo sobrevive al corte) | `MG.morph(tl,caja,destino,{at,dur})`: una caja crece/se mueve y se vuelve el contenedor del siguiente golpe (anima left/top/width/height, el texto queda nítido). `MG.carry(tl,el,destino,{at,dur,arc})`: lleva un elemento a otro lugar (FLIP), p. ej. la palabra que se vuelve título. Ambos cuentan para el check `continuity` |
| Curvas | `ease: MG.spring({bounce:.25, wobbles})`: resorte determinista. Elige curvas por t80 (tiempo hasta el 80 % del recorrido): expo.out ≈ .23 (golpe seco), spring .2–.3 (aterriza), power3.out ≈ .41, sine.inOut ≈ .70 (deriva). Una sola curva S suave en todo hace que todo se vea igual |
| Ambiente | `MG.camera`, `MG.operator(tl,S,{amp,holds,hits})` (mano de camarógrafo encima de la cámara: flotación lenta, quieta en `holds`, sacudón en `hits`; llamar una vez, después de las llaves de cámara), `MG.grain`, `MG.vignette`, `MG.bgDrift` |
| Look dibujado a mano | `MG.boil(el,{amp,fps:12,seed})` (la línea tiembla y se redibuja 12 veces por segundo; una semilla por elemento), `MG.paper(S,{color,opacity})` (textura de papel; se rasteriza una vez, no frena la captura), `MG.stepped(12)` (toda la pieza "a dos cuadros", antes de `expose`) |
| Encuadre | `MG.inFrame(el,'whole')`: marca algo que nunca puede salir del cuadro (el check `framing` falla si sale) |
| 3D | `MG.three(sc,{…})` → `t3.studio()`, `t3.env()`, `t3.mat(k)`, `t3.ground()`, `t3.ao()`, `t3.softShadow()`, `t3.bloom()`, `t3.rig()`, `t3.ortho()`, `t3.textTexture()`, `t3.look`, `t3.pre(fn)`; se anima con tweens sobre `mesh.position/rotation/scale`, `t3.camera.position`, o con `t3.rig()`; azar solo `MG.rng(semilla)` |
| Sonido | `MG.cue('hit|thud|whoosh|pop|tick|step|riser|sub|shimmer', t, {gain,dur})` — el pico del sonido cae exacto en `t`. `hit` golpe grave, `thud` golpe corto, `tick` clic, `step` pisada, `pop` gota/aparición, `shimmer` campana de remate |

`timeline.js` define `window.SCENE = { bg, build(MG,T,S,tl) }` y `build` devuelve la duración total. Parte siempre de una plantilla (`assets/templates/*`), no de cero.

## Trampas de determinismo (cada una costó horas; detalle en `references/engine.md`)

- Prohibido `Math.random`, `Date.now`, timers, `repeat:-1`. El validador lo detecta (lint).
- Nunca `will-change` en contenedores animados: una capa compuesta se crea al pasar por ciertos tiempos y re-rasteriza el texto distinto → falla el acceso aleatorio.
- No dos `set` en t=0 sobre la misma propiedad; el kit ya clampa `__seek` a ≥1e-4.
- Callbacks solo vía proxy + `onUpdate` dentro del kit (contadores, grano).
- Si cambias `lib/mg.js` del skill, recopia a los proyectos existentes.
- Varias escenas en una misma página (Remotion): `MG.reset()` antes de cada `build`; sin él la segunda hereda señales, finalizadores y `MG.stepped` de la primera (`GsapScene.tsx` ya lo hace).

## Referencias (lee solo lo que necesites)

- `references/spec.md` — SPEC.md con números, defaults prohibidos, tres argumentos para piezas largas.
- `references/direction.md` — dirección de movimiento: pilares, capas, ley de vectores entre escenas, personalidades, lista de calidad.
- `references/formats.md` — receta por formato (estructura, tiempos, qué pedir al usuario, errores típicos).
- `references/anti-slop.md` — señales de piezas "de relleno" y cómo evitarlas.
- `references/engine.md` — GSAP/determinismo, audio, render.
- `references/router.md` — elegir GSAP / Remotion / híbrido, tabla de escenas del SPEC.
- `references/remotion.md` — montar una o varias escenas en Remotion (`new_remotion.py`, `add_audio.py`), trampas, licencia.
- `references/subtitulos.md` — subtítulos sincronizados con la voz (`Captions.tsx`, Scribe o Whisper local, texto exacto del guion).
- `references/qa-por-entidad.md` — `entity_qa.py`: verificar cada elemento fotograma a fotograma.
- `references/style-extraction.md` — extraer estilo de una referencia (paleta medida, ritmo, tipografía) y buscar un look con nombre en el catálogo local de 341 estilos (`~/referencias/code-animation-prompts`).

## Mantenimiento del skill (solo al modificarlo)

- Después de tocar el kit (`assets/lib/mg.js`), una plantilla o `validate.py`: `$PY -I scripts/smoke_test.py` (~3 min; `--matrix` añade personalidades y formatos, 10–20 min más). Crea las 5 plantillas, exige 14/14 en el validador y corre controles negativos (texto encimado, fuera de zona, `Date.now()`, reemplazo sin continuidad) y positivos (líneas apiladas con `split`, construcción bajo un titular) para que un cambio del validador no deje de ver lo real ni invente fallos. No cubre Remotion ni el sonido.
- `MG.text` con `split` envuelve cada palabra en una máscara con relleno invisible (0,14 em arriba, 0,18 em abajo, margen negativo). `validate.py` lo descuenta al medir (`MEASURE`). Si cambias ese envoltorio en el kit, ajusta también `MEASURE`.
- No dejes salidas del validador (`contact_sheet.png`, `validation_report.json`) dentro del skill: pasa siempre `--sheet` y `--report` hacia el proyecto.
