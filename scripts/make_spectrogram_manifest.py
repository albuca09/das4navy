from pathlib import Path
import json
import pandas as pd
import re

APP = Path(r"C:\Users\Luis\Desktop\das4navy")
SPEC_DIR = APP / "public" / "data" / "das_spectrograms"
OUT = APP / "public" / "data" / "spectrogram_manifest.json"

EVENT_START = pd.to_datetime("2021-11-01T17:48:15Z", utc=True)
EVENT_END   = pd.to_datetime("2021-11-01T18:16:04Z", utc=True)

pngs = sorted(SPEC_DIR.glob("*.png"))

if not pngs:
    raise RuntimeError(f"Nenhum PNG encontrado em {SPEC_DIR}")

total_sec = max(1.0, (EVENT_END - EVENT_START).total_seconds())
step_sec = total_sec / len(pngs)

rows = []

for i, p in enumerate(pngs):
    a = EVENT_START + pd.Timedelta(seconds=i * step_sec)
    b = EVENT_START + pd.Timedelta(seconds=(i + 1) * step_sec)

    ch = None
    m = re.search(r"_ch_(\d+)", p.name)
    if m:
        ch = int(m.group(1))

    prob = None
    m = re.search(r"_prob_([0-9.]+)", p.name)
    if m:
        try:
            prob = float(m.group(1).rstrip("."))
        except Exception:
            prob = None

    rows.append({
        "kind": "das_xai_spectrogram",
        "image_url": f"/data/das_spectrograms/{p.name}",
        "channel": ch,
        "probability": prob,
        "time_start_utc": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "time_end_utc": b.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": str(p)
    })

OUT.write_text(
    json.dumps({"spectrograms": rows}, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8"
)

print("OK")
print("Manifest:", OUT)
print("Spectrograms:", len(rows))
print("Primeiro:", rows[0])
print("Último:", rows[-1])
