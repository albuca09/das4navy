from pathlib import Path
import json
import pandas as pd

APP = Path(r"C:\Users\Luis\Desktop\das4navy")

json_candidates = [
    APP / "public" / "data" / "das4navy_scene_web_lite.json",
    APP / "public" / "data" / "das4navy_scene_web.json",
    APP / "public" / "data" / "das4navy_scene.json",
]

spec_dir = APP / "public" / "data" / "das_spectrograms"

out_lite = APP / "public" / "data" / "das4navy_scene_web_lite.json"
out_full = APP / "public" / "data" / "das4navy_scene_web.json"

# Escolhe o primeiro JSON existente.
src = None
for p in json_candidates:
    if p.exists():
        src = p
        break

if src is None:
    raise FileNotFoundError("Nenhum JSON de cena encontrado em public/data.")

print("Lendo:", src)

scene = json.loads(src.read_text(encoding="utf-8"))

frames = scene.get("frames", [])
if not frames:
    raise RuntimeError("O JSON não tem frames de animação.")

frame_times = [
    pd.to_datetime(f.get("time_utc"), utc=True, errors="coerce")
    for f in frames
]
frame_times = [t for t in frame_times if not pd.isna(t)]

if not frame_times:
    raise RuntimeError("Os frames não têm time_utc válido.")

pngs = sorted(spec_dir.glob("*.png"))

if not pngs:
    raise RuntimeError(f"Nenhuma imagem PNG encontrada em: {spec_dir}")

print("PNG encontrados:", len(pngs))

# Distribui os espectrogramas ao longo da janela temporal dos frames.
t0 = min(frame_times)
t1 = max(frame_times)

if t1 <= t0:
    t1 = t0 + pd.Timedelta(seconds=len(pngs))

total_sec = max(1.0, (t1 - t0).total_seconds())
step_sec = total_sec / max(1, len(pngs))

timeline = []

for i, p in enumerate(pngs):
    a = t0 + pd.Timedelta(seconds=i * step_sec)
    b = t0 + pd.Timedelta(seconds=(i + 1) * step_sec)

    # Tenta extrair canal do nome.
    channel = None
    name = p.name
    import re
    m = re.search(r"_ch_(\d+)", name)
    if m:
        channel = int(m.group(1))

    timeline.append({
        "kind": "spectrogram_image",
        "image_url": f"/data/das_spectrograms/{p.name}",
        "channel": channel,
        "time_start_utc": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "time_end_utc": b.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "probability": None,
        "weak_label": None,
        "source_file": str(p),
    })

scene["spectrogram_timeline"] = timeline

if "metadata" not in scene:
    scene["metadata"] = {}

scene["metadata"]["n_spectrogram_images"] = len(timeline)
scene["metadata"]["spectrogram_timeline_forced"] = True

# Remove camada pesada no lite.
scene_lite = dict(scene)
scene_lite["xai_events_full_count"] = len(scene_lite.get("xai_events", []))
scene_lite["xai_events"] = []

out_lite.write_text(
    json.dumps(scene_lite, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8"
)

# Também atualiza o full, mas preservando xai_events se existirem.
out_full.write_text(
    json.dumps(scene, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8"
)

print("OK")
print("Lite salvo:", out_lite)
print("Full salvo:", out_full)
print("Spectrogram timeline:", len(timeline))
print("Primeiro:", timeline[0])
print("Último:", timeline[-1])
