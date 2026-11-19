# Remotion: híbrido y nativo

Remotion es **opcional**; elige con `references/router.md`. Sus reglas generales las mantiene su equipo (skills oficiales: `npx remotion skills add`,
o `remotion.dev/docs`). Aquí solo está lo que esas skills no dicen: cómo se une a este kit y las trampas ya pagadas.
`$PY` es el python del venv (`PY=$(python3 scripts/setup.py --print)`).

## Híbrido: la misma `timeline.js` dentro de Remotion

```bash
# una escena, o varias en secuencia (NOMBRE=RUTA[@personalidad]; la personalidad por defecto es la de su scene.html)
$PY -I scripts/new_remotion.py --scene main=./proy --out ./proy/remotion --install
$PY -I scripts/new_remotion.py --scene hook=./proyA --scene cierre=./proyB@premium --out ./combo --install
cd combo && npx remotion render src/index.ts Main out.mp4 --image-format=png --is-production=false
# sonido MG.cue sobre el MP4 de Remotion (misma ruta de audio que render.py); @inicio en segundos, :largo si la escena va recortada
$PY -I scripts/add_audio.py --scene proyA/scene.html@0 --scene proyB/scene.html@4.6 --video out.mp4 --out final.mp4
```

- Cada proyecto pasa a `src/scenes/NOMBRE.js` (su `window.SCENE =` se vuelve `export default`) y se monta con `<GsapScene>` dentro de un
  `<Series>` en `src/Main.tsx`, a su duración medida. Cada fotograma es `seek(frame / fps)`: función pura del fotograma.
- Se copian `fonts/`, `fonts.css` y `assets/`; las rutas relativas de la escena (`MG.image src:'assets/x.png'`) resuelven contra `public/`.
  Una imagen que falta **no da error**: sale un hueco. Mira un fotograma.
- Las variables de fuente de cada escena se aplican solo a su contenedor: dos escenas con tipografías distintas no se pisan.
- Editar `Main.tsx`: recortar una escena (baja su `durationInFrames`), intercalar un clip o subtítulos nativos como otra
  `<Series.Sequence>` (`<Video>`/`<Audio>` de `@remotion/media`), y actualizar `TOTAL`.
- Tras editar `timeline.js` en el proyecto original, vuelve a correr `new_remotion.py` (o recopia el archivo a `src/scenes/`).
- La validación (`validate.py`, `entity_qa.py`) se hace sobre el `scene.html` de cada proyecto; no ve capas propias de Remotion.
- No soporta escenas con `MG.three` (el script las rechaza): no está probado.

**Qué esperar** (medido una vez, 1080×1920, 2 pestañas): mismo tiempo y RAM que `render.py` (una pieza de 45 s: 54 s frente a 57 s; ~1,7 GB extra).
Los fotogramas no son idénticos bit a bit: < 1 % de píxeles difiere, solo en bordes de texto (Remotion trae otro Chromium); posición y color coinciden.
El audio de `add_audio.py` es idéntico al de `render.py`. Un `<Video>` nativo sube la RAM (~+2 GB).

## Trampas (cada una costó un render en blanco)
1. **`setMounted(true)` en el layout effect de montaje, síncrono, antes de la promesa de fuentes.** Sin él (o con el `setState` solo después de
   construir) Remotion captura el fotograma vacío. Causa exacta desconocida; está en `GsapScene.tsx`: no lo quites.
2. El seek va en un **segundo** `useLayoutEffect([frame, fps])`, nunca en el cuerpo del render.
3. Usa `MG.expose(tl)` y guarda `window.__seek` en un ref al construir (la escena siguiente lo pisa). `MG.reset()` antes de cada `build`:
   el kit guarda estado de módulo (señales, finalizadores, `MG.stepped`) que si no se hereda de la escena anterior.
4. Un PNG de Remotion es RGBA: transparente se ve **blanco** en un visor y negro al pasar a RGB. Antes de medir nada, mira UN fotograma:
   un render vacío parece mucho más rápido.
5. **Espacio en `/tmp`**: Remotion escribe temporales ahí. Con `/tmp` en `tmpfs` y casi lleno, el render llega al 100 % y falla al final
   (`ffmpeg … exit code 134`) sin decir por qué. `df -h /tmp` antes; no dejes varios `node_modules` (~0,8 GB cada uno) en `/tmp`.
6. Con poca RAM deja `Config.setConcurrency(2)` (lo escribe el script; cada pestaña ~0,8 GB a 1080×1920).

## Licencia (decisión del usuario; no la tomes por él)
Remotion es gratis para una persona o una empresa de hasta 3 personas; si no, licencia de pago (`remotion.dev/docs/license/pricing`).
**Si la pieza es para un cliente o una empresa, pregunta el tamaño del equipo antes de renderizar.** Con `--is-production=false` las pruebas
no cuentan como renders facturables; para renders reales con licencia gratis, `--license-key=free-license`.

## Remotion nativo (clips, variantes)
- Proyecto base: `npx create-video@latest --yes --blank --no-tailwind <carpeta>`, o parte del que genera `new_remotion.py`.
- Lo esencial: animar solo con `useCurrentFrame()` + `interpolate()` (nada de `transition`/`animation` CSS); `output: 'perceptual-scale'`
  en escalas; `staticFile()` para `public/`; fuentes con `@remotion/google-fonts` o `@remotion/fonts`; en 3D `<ThreeCanvas>` y nada de `useFrame()`.
- Sin `validate.py`: saca fotogramas con `npx remotion render <id> out/ --frames=0,30,90 --image-format=png` (lista la carpeta: los nombra
  `element-NN.png`), míralos y revisa a mano zonas seguras, texto ≥ 2,8 % del lado corto y tiempo de lectura (`references/spec.md`).
- Probado aquí: un `<Video>` con texto encima y subtítulos con voz (`references/subtitulos.md`). **No probado:** variantes desde datos.
