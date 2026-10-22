#!/usr/bin/env python3
"""Transcribe un video/audio palabra por palabra con faster-whisper.

Genera:
  <salida>.json  -> captions en formato Remotion (@remotion/captions)
  <salida>.srt   -> subtítulos clásicos, una palabra por línea de tiempo

Uso:
  python3 tools/transcribe.py video.mp4 [--modelo small] [--salida videos/remotion/public/captions]
"""
import argparse, json, os
from faster_whisper import WhisperModel


def srt_time(ms):
    h, ms = divmod(int(ms), 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo")
    ap.add_argument("--modelo", default="small", help="tiny | base | small | medium | large-v3")
    ap.add_argument("--idioma", default="es")
    ap.add_argument("--salida", default="videos/remotion/public/captions")
    a = ap.parse_args()

    model = WhisperModel(a.modelo, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(a.archivo, language=a.idioma, word_timestamps=True, vad_filter=True)

    captions = []
    for seg in segments:
        for w in seg.words:
            # Remotion espera el espacio delante de cada palabra salvo la primera
            captions.append({
                "text": (" " if captions else "") + w.word.strip(),
                "startMs": round(w.start * 1000),
                "endMs": round(w.end * 1000),
                "timestampMs": round((w.start + w.end) * 500),
                "confidence": round(w.probability, 3),
            })

    os.makedirs(os.path.dirname(a.salida) or ".", exist_ok=True)
    with open(a.salida + ".json", "w", encoding="utf-8") as f:
        json.dump(captions, f, ensure_ascii=False, indent=1)
    with open(a.salida + ".srt", "w", encoding="utf-8") as f:
        for i, c in enumerate(captions, 1):
            f.write(f"{i}\n{srt_time(c['startMs'])} --> {srt_time(c['endMs'])}\n{c['text'].strip()}\n\n")
    print(f"{len(captions)} palabras -> {a.salida}.json / .srt")


if __name__ == "__main__":
    main()
