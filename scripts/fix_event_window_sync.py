from pathlib import Path
import json
import pandas as pd
import re

APP = Path(r"C:\Users\Luis\Desktop\das4navy")

json_files = [
    APP / "public" / "data" / "das4navy_scene_web_lite.json",
    APP / "public" / "data" / "das4navy_scene_web.json",
]

spec_dir = APP / "public" / "data" / "das_spectrograms"

EVENT_START = pd.to_datetime("2021-11-01T17:48:15Z", utc=True)
EVENT_END   = pd.to_datetime("2021-11-01T18:16:04Z", utc=True)

for json_path in json_files:
    if not json_path.exists():
        continue

    print("Corrigindo:", json_path)

    scene = json.loads(json_path.read_text(encoding="utf-8"))

    # Mantém AIS completo como trajetória estática,
    # mas restringe a animação à janela DAS/XAI.
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
        print("Frames filtrados:", len(new_frames))
    else:
        print("WARNING: nenhum frame encontrado na janela; frames preservados.")

    # Recria a linha temporal dos espectrogramas somente na janela do evento.
    pngs = sorted(spec_dir.glob("*.png"))

    if not pngs:
        raise RuntimeError(f"Nenhum PNG encontrado em {spec_dir}")

    total_sec = (EVENT_END - EVENT_START).total_seconds()
    step_sec = total_sec / max(1, len(pngs))

    timeline = []

    for i, p in enumerate(pngs):
        a = EVENT_START + pd.Timedelta(seconds=i * step_sec)
        b = EVENT_START + pd.Timedelta(seconds=(i + 1) * step_sec)

        channel = None
        m = re.search(r"_ch_(\d+)", p.name)
        if m:
            channel = int(m.group(1))

        prob = None
        m_prob = re.search(r"_prob_([0-9.]+)", p.name)
        if m_prob:
            try:
                prob = float(m_prob.group(1).rstrip("."))
            except Exception:
                prob = None

        timeline.append({
            "kind": "das_xai_spectrogram",
            "image_url": f"/data/das_spectrograms/{p.name}",
            "channel": channel,
            "time_start_utc": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_end_utc": b.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "probability": prob,
            "weak_label": None,
            "source_file": str(p),
        })

    scene["spectrogram_timeline"] = timeline

    if "metadata" not in scene:
        scene["metadata"] = {}

    scene["metadata"]["animation_start_utc"] = EVENT_START.strftime("%Y-%m-%dT%H:%M:%SZ")
    scene["metadata"]["animation_end_utc"] = EVENT_END.strftime("%Y-%m-%dT%H:%M:%SZ")
    scene["metadata"]["n_animation_frames_event_window"] = len(scene.get("frames", []))
    scene["metadata"]["n_spectrogram_images"] = len(timeline)
    scene["metadata"]["spectrogram_timeline_event_window"] = True

    json_path.write_text(
        json.dumps(scene, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )

    print("Spectrograms:", len(timeline))
    print("Primeiro:", timeline[0]["time_start_utc"], timeline[0]["image_url"])
    print("Último   :", timeline[-1]["time_end_utc"], timeline[-1]["image_url"])
    print()

print("OK — sincronização corrigida para a janela DAS/XAI.")
