# Subtítulos sincronizados con la voz (Remotion)

Componente: `assets/remotion/Captions.tsx` (cópialo a `src/`; `npx remotion add @remotion/captions`). Recibe `Caption[]`
(`{text, startMs, endMs, timestampMs, confidence}`, una entrada por palabra, `text` con espacio inicial).

```tsx
<Audio src={staticFile("voz.mp3")} />                      {/* Audio de @remotion/media */}
<Captions captions={captionsJson as Caption[]} fontFamily="Outfit, sans-serif" />
```
Agrupa en frases cortas, enciende la palabra que se dice (solo cambia el color: la línea no salta) y escala con `u = lado corto / 1080`.
En vertical va por encima de la UI de la app (`bottom=420` por defecto; no bajes de 340). Carga la fuente antes (FontFace + `delayRender`).

## De dónde salen los tiempos (elige uno)

| Situación | Camino | Texto | Tiempos |
|---|---|---|---|
| Hay **guion** y un conector de ElevenLabs en la sesión | Scribe + `script_to_captions.py` | exacto, el del guion | límites de frase a ≤ 0,07 s de las pausas reales, sin ajuste |
| Sin conector, o el audio no debe salir de la máquina | `transcribe.py` (Whisper local) | el que oye Whisper (revísalo) | ajustados a los silencios reales; crudos se adelantan hasta ~0,8 s |
| Whisper + guion | `transcribe.py --no-snap` → `script_to_captions.py` | exacto | los de Whisper |

### A) ElevenLabs Scribe por el conector (herramientas `creative_*`; no es un script)
**Sube el audio a ElevenLabs y gasta créditos: pide permiso antes.** La estimación (`estimate_only`) puede quedarse muy corta
(visto: estimó 12,7 créditos y cobró 229 por 42 s): dilo al pedir el visto bueno.
1. `creative_create_flow` → `creative_create_asset_upload` (nombre, mime y tamaño exactos) → `PUT` de los bytes con `curl` (no leas el archivo
   en la conversación) → `creative_finalize_asset_upload` con el `flow_id` → `node_id`.
2. `creative_transcribe_audio` (`eleven_scribe_v1`, `connect_from: [node_id]`): primero `estimate_only: true`, enseña el costo, y solo entonces
   la llamada real. **Una sola vez**: reintentar cobra de nuevo.
3. `creative_get_flow_run_status` hasta `all_completed`; baja `words_download_url` a `palabras.json`
   (`{"words":[{"text","type":"word","start","end"}]}`, segundos).
4. `$PY -I scripts/script_to_captions.py --words palabras.json --text guion.txt --out src/captions.json`
   Alinea guion y transcripción; imprime cuántas palabras son exactas, emparejadas por posición o interpoladas. **Revisa de oído las dos últimas.**
5. El audio queda en un flow del canvas de ElevenLabs del usuario: avísale (se borra desde su web).

El conector no da alineación forzada ni tiempos al generar voz (`creative_generate_speech`): la voz generada se transcribe igual.

### B) Whisper local
```bash
python3 scripts/setup.py --with-whisper        # una vez: instala faster-whisper en el venv del skill
$PY -I scripts/transcribe.py --audio voz.mp3 --out src/captions.json --lang es --model small
```
- El modelo se baja una vez de Hugging Face (solo descarga). `HF_HUB_OFFLINE=1` lo impide si ya está en caché.
- Whisper estira palabras sobre las pausas; por eso el script **ajusta por defecto** a los silencios reales (`ffmpeg silencedetect`).
  `--no-snap` deja los tiempos crudos.
- Imprime las 5 palabras de menor confianza: compáralas con el guion. `--prompt` con nombres propios o jerga ayuda.

## Límites conocidos
- La precisión se midió contra las pausas reales (límites de frase). Dentro de una frase no hay verdad externa: escucha el resultado, o pide
  al usuario que lo haga, antes de entregar.
- Probado con una voz en español de ~40 s. Otros idiomas, música de fondo o varias voces: sin probar.
