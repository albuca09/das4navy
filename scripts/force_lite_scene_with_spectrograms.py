from pathlib import Path
import json
import pandas as pd
import re

APP = Path(r"C:\Users\Luis\Desktop\das4navy")

base_json_candidates = [
    APP / "public" / "data" / "das4navy_scene_web.json",
    APP / "public" / "data" / "das4navy_scene.json",
]

out_json = APP / "public" / "data" / "das4navy_scene_web_lite.json"
spec_dir = APP / "public" / "data" / "das_spectrograms"

EVENT_START = pd.to_datetime("2021-11-01T17:48:15Z", utc=True)
EVENT_END   = pd.to_datetime("2021-11-01T18:16:04Z", utc=True)

base_json = None
for p in base_json_candidates:
    if p.exists():
        base_json = p
        break

if base_json is None:
    raise FileNotFoundError("Nenhum JSON base encontrado em public/data.")

print("Lendo JSON base:", base_json)

scene = json.loads(base_json.read_text(encoding="utf-8"))

pngs = sorted(spec_dir.glob("*.png"))
if not pngs:
    raise RuntimeError(f"Nenhum PNG encontrado em: {spec_dir}")

print("PNG encontrados:", len(pngs))

# Mantém AIS completo, cabos e estimativa DAS.
# Filtra apenas os frames animados para a janela do evento DAS/XAI.
frames = scene.get("frames", [])
new_frames = []

for f in frames:
    t = pd.to_datetime(f.get("time_utc"), utc=True, errors="coerce")
    if pd.isna(t):
        continue
    if EVENT_START <= t <= EVENT_END:
        new_frames.append(f)

if new_frames:
    scene["frames"] = new_frames
else:
    print("WARNING: nenhum frame na janela; mantendo frames originais.")

# Força timeline dos espectrogramas a partir dos 300 PNGs existentes.
total_sec = max(1.0, (EVENT_END - EVENT_START).total_seconds())
step_sec = total_sec / len(pngs)

timeline = []

for i, p in enumerate(pngs):
    a = EVENT_START + pd.Timedelta(seconds=i * step_sec)
    b = EVENT_START + pd.Timedelta(seconds=(i + 1) * step_sec)

    channel = None
    m = re.search(r"_ch_(\d+)", p.name)
    if m:
        channel = int(m.group(1))

    prob = None
    m = re.search(r"_prob_([0-9.]+)", p.name)
    if m:
        try:
            prob = float(m.group(1).rstrip("."))
        except Exception:
            prob = None

    timeline.append({
        "kind": "das_xai_spectrogram",
        "image_url": "/data/das_spectrograms/" + p.name,
        "channel": channel,
        "time_start_utc": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "time_end_utc": b.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "probability": prob,
        "weak_label": None,
        "source_file": str(p),
    })

scene["spectrogram_timeline"] = timeline

# Remove camada pesada. O app usa xai_events_light.
scene["xai_events_full_count"] = len(scene.get("xai_events", []))
scene["xai_events"] = []

if "metadata" not in scene:
    scene["metadata"] = {}

scene["metadata"]["animation_start_utc"] = EVENT_START.strftime("%Y-%m-%dT%H:%M:%SZ")
scene["metadata"]["animation_end_utc"] = EVENT_END.strftime("%Y-%m-%dT%H:%M:%SZ")
scene["metadata"]["n_spectrogram_images"] = len(timeline)
scene["metadata"]["spectrogram_timeline_forced"] = True
scene["metadata"]["n_animation_frames_event_window"] = len(scene.get("frames", []))

out_json.write_text(
    json.dumps(scene, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8"
)

print("OK")
print("JSON leve salvo:", out_json)
print("Tamanho MB:", out_json.stat().st_size / 1024 / 1024)
print("Frames:", len(scene.get("frames", [])))
print("Spectrogram timeline:", len(scene.get("spectrogram_timeline", [])))
print("Primeiro image_url:", scene["spectrogram_timeline"][0]["image_url"])
print("Primeiro tempo:", scene["spectrogram_timeline"][0]["time_start_utc"])
print("Último tempo:", scene["spectrogram_timeline"][-1]["time_end_utc"])
