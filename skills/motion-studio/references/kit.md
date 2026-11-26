# Kit `MG` — referencia completa (`assets/lib/mg.js`)

`timeline.js` define `window.SCENE = { bg, build(MG,T,S,tl) }` y `build` devuelve la duración total. Parte siempre de una plantilla (`assets/templates/*`), no de cero.

| Necesidad | Llamada |
|---|---|
| Escenario / escena | `MG.stage` (ya lo hace el loader), `S.scene(name,{bg})`, `MG.show(tl,sc,at,until)` |
| Elementos | `MG.text(sc,{text,x,y,w,size,weight,split:'words|lines|chars',font,color})`, `MG.box`, `MG.shape`, `MG.image`, `MG.icon`, `MG.barChart`, `MG.lineChart`, `MG.ring` |
| Entrar / salir / énfasis | `MG.in(tl,t,{how:rise|fade|pop|scale|slide-left|slide-right|mask,at,dur,ease,stagger})`, `MG.out`, `MG.emph(pulse|shake|wiggle)` |
| Datos | `MG.growBars`, `MG.drawLine`, `MG.counter`, `MG.typewriter`, `MG.draw` (trazo SVG) |
| Entre escenas | `MG.transition(tl,A,B,{type:cut|fade|push-left|push-up|wipe-right|wipe-left|zoom|iris|zoom-through|brush})` — `zoom-through`: la cámara se zambulle en una ventana de A (`rect` o `el`) hasta que B, que vive dentro, llena el cuadro. `brush`: pinceladas gruesas cubren, cambian las escenas debajo y se retiran |
| Continuidad (algo sobrevive al corte) | `MG.morph(tl,caja,destino,{at,dur})`: una caja crece/se mueve y se vuelve el contenedor del siguiente golpe (anima left/top/width/height, el texto queda nítido). `MG.carry(tl,el,destino,{at,dur,arc})`: lleva un elemento a otro lugar (FLIP), p. ej. la palabra que se vuelve título. Ambos cuentan para el check `continuity` |
| Curvas | `ease: MG.spring({bounce:.25, wobbles})`: resorte determinista. Elige curvas por t80 (tiempo hasta el 80 % del recorrido): expo.out ≈ .23 (golpe seco), spring .2–.3 (aterriza), power3.out ≈ .41, sine.inOut ≈ .70 (deriva). Una sola curva S suave en todo hace que todo se vea igual |
| Ambiente | `MG.camera`, `MG.operator(tl,S,{amp,holds,hits})` (mano de camarógrafo encima de la cámara: flotación lenta, quieta en `holds`, sacudón en `hits`; llamar una vez, después de las llaves de cámara), `MG.grain`, `MG.vignette`, `MG.bgDrift` |
| Look dibujado a mano | `MG.boil(el,{amp,fps:12,seed})` (la línea tiembla y se redibuja 12 veces por segundo; una semilla por elemento), `MG.paper(S,{color,opacity})` (textura de papel; se rasteriza una vez, no frena la captura), `MG.stepped(12)` (toda la pieza "a dos cuadros", antes de `expose`) |
| Encuadre | `MG.inFrame(el,'whole')`: marca algo que nunca puede salir del cuadro (el check `framing` falla si sale) |
| 3D | `MG.three(sc,{…})` → `t3.studio()`, `t3.env()`, `t3.mat(k)`, `t3.ground()`, `t3.ao()`, `t3.softShadow()`, `t3.bloom()`, `t3.rig()`, `t3.ortho()`, `t3.textTexture()`, `t3.look`, `t3.pre(fn)`; se anima con tweens sobre `mesh.position/rotation/scale`, `t3.camera.position`, o con `t3.rig()`; azar solo `MG.rng(semilla)` |
| Sonido | `MG.cue('hit|thud|whoosh|pop|tick|step|riser|sub|shimmer', t, {gain,dur})` — el pico del sonido cae exacto en `t`. `hit` golpe grave, `thud` golpe corto, `tick` clic, `step` pisada, `pop` gota/aparición, `shimmer` campana de remate |

## Reglas de uso del kit

- No escribas animaciones a mano con `tl.to` sobre propiedades ya cubiertas por el kit: pierdes el clamp de `__seek`, el stagger y la continuidad.
- `MG.show` es lo que hace visible una escena en su ventana de tiempo; una escena sin `MG.show` no aparece en el render aunque tenga elementos.
- Todo golpe visual necesita su `MG.cue` en el mismo `t`; el check `audio-cues` cuenta cues y el render los mezcla.
- Si cambias `assets/lib/mg.js`, recopia el archivo a los proyectos existentes (los proyectos lo llevan vendorizado en `lib/`).
