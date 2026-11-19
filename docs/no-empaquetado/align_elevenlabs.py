#!/usr/bin/env python3
"""Subtítulos con el TEXTO EXACTO del guion y tiempos de ElevenLabs, en el formato `Caption` de Remotion. Sin dependencias.

    # A) ya tienes el audio (web, API, lo que sea) y el guion: alineación forzada
    python3 -I align_elevenlabs.py align --audio voz.mp3 --text guion.txt --out captions.json

    # B) generas la voz por API: audio + tiempos de carácter en una sola llamada (GASTA créditos)
    python3 -I align_elevenlabs.py tts --text guion.txt --voice-id <ID> --out-audio voz.mp3 --out captions.json [--model eleven_multilingual_v2]

Clave: variable de entorno ELEVENLABS_API_KEY, o --key-file ruta (primera línea). Nunca se imprime ni se guarda.
Qué sale de tu máquina: en `align`, el audio y el guion; en `tts`, el guion. Ambos van a api.elevenlabs.io (--host para otra región).

  align  POST /v1/forced-alignment (multipart: file + text) -> words[{text,start,end,loss}]. Sirve para CUALQUIER audio, incluidos los
         que generaste en la web de ElevenLabs (esa pantalla no da tiempos). Imprime la pérdida media y las palabras con más pérdida.
  tts    POST /v1/text-to-speech/{voice_id}/with-timestamps -> audio_base64 + alignment (tiempos por carácter del texto ORIGINAL).
         Los caracteres se agrupan en palabras separando por espacios en blanco; los signos pegados a la palabra se quedan con ella.

El texto de los subtítulos sale del guion, no de un reconocedor: "no sabes si" se queda "no sabes si". Si el guion y el audio difieren
(un párrafo recortado, una palabra cambiada), `align` lo refleja en una pérdida alta en esas palabras: revísalas.
La cabecera de autenticación es `xi-api-key` (convención de ElevenLabs; la página de referencia no la nombra).
"""
import argparse
import base64
import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.request
import uuid


def read_key(a):
    if a.key_file:
        key = pathlib.Path(a.key_file).expanduser().read_text().splitlines()[0].strip()
    else:
        key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise SystemExit("falta la clave: define ELEVENLABS_API_KEY o pasa --key-file")
    return key


def post(url, key, body, content_type):
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": content_type, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        raise SystemExit(f"ElevenLabs respondió {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise SystemExit(f"no se pudo conectar: {e.reason}")


def multipart(fields, files):
    b = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, path in files.items():
        p = pathlib.Path(path)
        mt = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{p.name}"\r\nContent-Type: {mt}\r\n\r\n'.encode()
        out += p.read_bytes() + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"


def caption(text, start, end, conf=None):
    t = text if text.startswith(" ") else " " + text
    return {"text": t, "startMs": round(start * 1000), "endMs": round(end * 1000),
            "timestampMs": round((start + end) / 2 * 1000), "confidence": conf}


def chars_to_words(chars, starts, ends):
    """Agrupa caracteres con tiempos en palabras (separadas por espacio en blanco). Devuelve [(texto, inicio_s, fin_s)]."""
    if not (len(chars) == len(starts) == len(ends)):
        raise SystemExit("la alineación trae arreglos de largo distinto")
    words, cur, s0, s1 = [], "", None, None
    for ch, a, b in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append((cur, s0, s1))
            cur, s0, s1 = "", None, None
        else:
            cur += ch
            s0 = a if s0 is None else s0
            s1 = b
    if cur:
        words.append((cur, s0, s1))
    return words


def from_alignment_words(words):
    """Respuesta de forced-alignment: words[{text,start,end,loss}] -> Caption[] con confianza = 1/(1+pérdida)."""
    caps = []
    for w in words:
        t = w["text"].strip()
        if not t:
            continue
        loss = w.get("loss")
        caps.append(caption(t, float(w["start"]), float(w["end"]), None if loss is None else round(1 / (1 + float(loss)), 3)))
    return caps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("align", "tts"):
        p = sub.add_parser(name)
        p.add_argument("--text", required=True, help="archivo con el guion")
        p.add_argument("--out", required=True, help="captions.json de salida")
        p.add_argument("--key-file")
        p.add_argument("--host", default="https://api.elevenlabs.io")
    sub.choices["align"].add_argument("--audio", required=True)
    t = sub.choices["tts"]
    t.add_argument("--voice-id", required=True)
    t.add_argument("--out-audio", required=True)
    t.add_argument("--model", default="eleven_multilingual_v2")
    t.add_argument("--format", default="mp3_44100_128", help="output_format de la API")
    a = ap.parse_args()
    key = read_key(a)
    text = pathlib.Path(a.text).read_text().strip()
    if a.cmd == "align":
        body, ct = multipart({"text": text}, {"file": a.audio})
        res = post(f"{a.host}/v1/forced-alignment", key, body, ct)
        words = res.get("words") or []
        if not words:
            raise SystemExit("la respuesta no trae `words`: " + json.dumps(res)[:300])
        caps = from_alignment_words(words)
        pathlib.Path(a.out).write_text(json.dumps(caps, ensure_ascii=False, indent=1))
        worst = sorted(words, key=lambda w: -(w.get("loss") or 0))[:5]
        print(f"{len(caps)} palabras, {caps[-1]['endMs'] / 1000:.1f} s; pérdida media {res.get('loss')} -> {a.out}")
        print("mayor pérdida (revisa si el audio dice otra cosa que el guion):",
              ", ".join(f"{w['text'].strip()}={round(w.get('loss') or 0, 2)}" for w in worst))
    else:
        url = f"{a.host}/v1/text-to-speech/{a.voice_id}/with-timestamps?output_format={a.format}"
        res = post(url, key, json.dumps({"text": text, "model_id": a.model}).encode(), "application/json")
        al = res.get("alignment")
        if not res.get("audio_base64") or not al:
            raise SystemExit("la respuesta no trae audio_base64 y alignment: " + json.dumps(res)[:300])
        pathlib.Path(a.out_audio).write_bytes(base64.b64decode(res["audio_base64"]))
        words = chars_to_words(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"])
        caps = [caption(w, s, e) for w, s, e in words]
        pathlib.Path(a.out).write_text(json.dumps(caps, ensure_ascii=False, indent=1))
        print(f"{len(caps)} palabras, {caps[-1]['endMs'] / 1000:.1f} s -> {a.out}; audio -> {a.out_audio}")


if __name__ == "__main__":
    sys.exit(main())
