#!/usr/bin/env python3
"""Pone el TEXTO EXACTO del guion sobre los tiempos de palabra de cualquier transcripción. Sin dependencias.

    python3 -I script_to_captions.py --words palabras.json --text guion.txt --out captions.json

`palabras.json`: lista de palabras con tiempos en segundos, de donde sea (ElevenLabs Scribe vía el conector, Whisper, etc.). Acepta
objetos con `text` o `word`, y `start`/`end` (o `start_time`/`end_time`); ignora lo que traiga `type` distinto de "word" (espacios,
eventos de audio). También acepta un objeto con la lista en `words`.

Cómo funciona: normaliza (minúsculas, sin acentos ni signos) y alinea la secuencia del guion con la de la transcripción (difflib). Cada
palabra del guion que coincide toma los tiempos de su palabra transcrita. Las que el reconocedor cambió o se comió ("sabes" → "sabe")
se emparejan 1 a 1 cuando el tramo tiene el mismo largo; si no, se reparten en el hueco entre sus vecinas. Imprime cuántas son exactas,
cuántas emparejadas por posición y cuántas interpoladas: **las dos últimas categorías son las que hay que revisar de oído**.
El texto sale tal cual está en el guion (puntuación y mayúsculas incluidas), en el formato `Caption` de Remotion.
"""
import argparse
import difflib
import json
import pathlib
import re
import sys
import unicodedata


def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", w)


def load_words(path):
    data = json.loads(pathlib.Path(path).read_text())
    if isinstance(data, dict):
        data = data.get("words") or data.get("transcripts", [{}])[0].get("words") or []
    out = []
    for w in data:
        if w.get("type", "word") != "word":
            continue
        t = w.get("text", w.get("word", "")).strip()
        s = w.get("start", w.get("start_time", w.get("startMs", None)))
        e = w.get("end", w.get("end_time", w.get("endMs", None)))
        if "startMs" in w:
            s, e = w["startMs"] / 1000, w["endMs"] / 1000
        if t and s is not None and e is not None:
            out.append((t, float(s), float(e)))
    if not out:
        raise SystemExit("no encontré palabras con tiempos en " + str(path))
    return out


def map_script(script, words):
    """Devuelve (lista [(palabra_del_guion, inicio, fin, categoría)], contadores)."""
    a = [norm(x) for x in script]
    b = [norm(x[0]) for x in words]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    res = [None] * len(script)
    for tag, i0, i1, j0, j1 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i1 - i0):
                res[i0 + k] = (words[j0 + k][1], words[j0 + k][2], "exacta")
        elif tag == "replace" and (i1 - i0) == (j1 - j0):
            for k in range(i1 - i0):
                res[i0 + k] = (words[j0 + k][1], words[j0 + k][2], "posición")
    # interpolar los huecos entre vecinas con tiempo
    i = 0
    n = len(res)
    while i < n:
        if res[i] is None:
            j = i
            while j < n and res[j] is None:
                j += 1
            t0 = res[i - 1][1] if i > 0 else 0.0
            t1 = res[j][0] if j < n else (words[-1][2] if words else t0)
            t1 = max(t1, t0 + 0.05 * (j - i))
            k = j - i
            for m in range(k):
                res[i + m] = (t0 + (t1 - t0) * m / k, t0 + (t1 - t0) * (m + 1) / k, "interpolada")
            i = j
        else:
            i += 1
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--words", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    script = pathlib.Path(a.text).read_text().split()
    words = load_words(a.words)
    res = map_script(script, words)
    caps, cnt = [], {"exacta": 0, "posición": 0, "interpolada": 0}
    for w, (s, e, cat) in zip(script, res):
        cnt[cat] += 1
        caps.append({"text": " " + w, "startMs": round(s * 1000), "endMs": round(e * 1000),
                     "timestampMs": round((s + e) / 2 * 1000), "confidence": {"exacta": 1.0, "posición": 0.6, "interpolada": 0.3}[cat]})
    for p, c in zip(caps, caps[1:]):        # monotonía
        if p["endMs"] > c["startMs"]:
            p["endMs"] = max(p["startMs"] + 50, c["startMs"])
    pathlib.Path(a.out).write_text(json.dumps(caps, ensure_ascii=False, indent=1))
    print(f"{len(script)} palabras del guion vs {len(words)} transcritas: {cnt['exacta']} exactas, {cnt['posición']} emparejadas por posición, "
          f"{cnt['interpolada']} interpoladas -> {a.out}")
    dudosas = [w for w, (s, e, c) in zip(script, res) if c != "exacta"]
    if dudosas:
        print("revisa de oído:", ", ".join(dudosas[:20]) + (" …" if len(dudosas) > 20 else ""))


if __name__ == "__main__":
    sys.exit(main())
