# -*- coding: utf-8 -*-
"""
Build DAS4NAVY synchronized web data.

Entrada:
  public/data/das4navy_scene.json

Saída:
  public/data/das4navy_scene_web.json
  public/data/das_spectrograms/*.png

Objetivo:
  - manter cabos, AIS, estimativa DAS e eventos XAI;
  - copiar espectrogramas/Grad-CAM gerados pelo pipeline DAS/XAI;
  - criar uma linha temporal sincronizada para o app React.
"""

from pathlib import Path
import json
import shutil
import re
import math
import pandas as pd
import numpy as np


APP_ROOT = Path(r"C:\Users\Luis\Desktop\das4navy")

SCENE_IN = APP_ROOT / "public" / "data" / "das4navy_scene.json"
SCENE_OUT = APP_ROOT / "public" / "data" / "das4navy_scene_web.json"

ASSET_DIR = APP_ROOT / "public" / "data" / "das_spectrograms"
ASSET_URL_PREFIX = "/data/das_spectrograms"

XAI_ROOT = Path(r"D:\DAS\_das_xai_spectrogram_perturbations")

MAX_SPECTROGRAMS = 400
MAX_XAI_EVENTS_LIGHT = 50000
MAX_EVENTS_PER_SECOND = 20


def parse_time(x):
    return pd.to_datetime(x, utc=True, errors="coerce")


def clean_records(df):
    return json.loads(df.replace({np.nan: None}).to_json(orient="records"))


def latest_run_dir(root):
    if not root.exists():
        return None

    runs = [p for p in root.glob("run_*") if p.is_dir()]
    if not runs:
        return None

    return max(runs, key=lambda p: p.stat().st_mtime)


def safe_float(x):
    try:
        y = float(x)
        if math.isnan(y) or math.isinf(y):
            return None
        return y
    except Exception:
        return None


def copy_asset(src):
    src = Path(str(src))

    if not src.exists():
        return None

    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    dst = ASSET_DIR / src.name

    if not dst.exists():
        shutil.copy2(src, dst)

    return f"{ASSET_URL_PREFIX}/{dst.name}"


def parse_tdms_time_from_name(name):
    m = re.search(r"UTC_(\d{8})_(\d{6}(?:\.\d+)?)", str(name), re.IGNORECASE)
    if not m:
        return pd.NaT

    ymd = m.group(1)
    hms = m.group(2)

    if "." in hms:
        hms0, frac = hms.split(".", 1)
        frac = (frac + "000000")[:6]
    else:
        hms0 = hms
        frac = "000000"

    try:
        return pd.to_datetime(f"{ymd}{hms0}{frac}", format="%Y%m%d%H%M%S%f", utc=True)
    except Exception:
        return pd.NaT


def build_spectrogram_timeline():
    run_dir = latest_run_dir(XAI_ROOT)

    if run_dir is None:
        print("[WARNING] Nenhum run XAI encontrado.")
        return [], None

    print(f"[XAI RUN] {run_dir}")

    tables = run_dir / "tables"
    figs = run_dir / "figures"

    xai_top = tables / "xai_top_detections.csv"
    patch_meta = tables / "xai_patch_metadata.csv"

    rows = []

    # Preferência: Grad-CAM/top detections, pois têm tempo de patch e imagem associada.
    if xai_top.exists():
        df = pd.read_csv(xai_top, low_memory=False)

        if "cnn_prob_perturbation" in df.columns:
            df = df.sort_values("cnn_prob_perturbation", ascending=False)

        df = df.head(MAX_SPECTROGRAMS).copy()

        for i, r in df.iterrows():
            img = r.get("xai_png", None)
            url = copy_asset(img) if img is not None else None

            if url is None:
                continue

            start = parse_time(r.get("patch_start_utc", None))
            end = parse_time(r.get("patch_end_utc", None))

            if pd.isna(start):
                start = parse_time(r.get("t0_utc", None))

            if pd.isna(end) and not pd.isna(start):
                end = start + pd.Timedelta(seconds=32)

            if pd.isna(start):
                continue

            rows.append({
                "kind": "xai_gradcam",
                "image_url": url,
                "channel": safe_float(r.get("channel", None)),
                "time_start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "time_end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ") if not pd.isna(end) else None,
                "probability": safe_float(r.get("cnn_prob_perturbation", None)),
                "weak_label": safe_float(r.get("weak_label", None)),
                "salient_time_min_sec": safe_float(r.get("salient_time_min_sec", None)),
                "salient_time_max_sec": safe_float(r.get("salient_time_max_sec", None)),
                "salient_freq_min_hz": safe_float(r.get("salient_freq_min_hz", None)),
                "salient_freq_max_hz": safe_float(r.get("salient_freq_max_hz", None)),
                "source_file": str(img),
            })

    # Fallback: espectrogramas brutos.
    if not rows:
        raw_dir = figs / "spectrograms_raw"

        if raw_dir.exists():
            pngs = sorted(raw_dir.glob("*.png"))[:MAX_SPECTROGRAMS]

            for p in pngs:
                url = copy_asset(p)
                t0 = parse_tdms_time_from_name(p.name)

                ch = None
                m_ch = re.search(r"_ch_(\d+)", p.name)
                if m_ch:
                    ch = int(m_ch.group(1))

                rows.append({
                    "kind": "raw_spectrogram",
                    "image_url": url,
                    "channel": ch,
                    "time_start_utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ") if not pd.isna(t0) else None,
                    "time_end_utc": (t0 + pd.Timedelta(seconds=32)).strftime("%Y-%m-%dT%H:%M:%SZ") if not pd.isna(t0) else None,
                    "probability": None,
                    "weak_label": None,
                    "source_file": str(p),
                })

    rows = sorted(rows, key=lambda x: x.get("time_start_utc") or "")
    print(f"[SPECTROGRAMS] {len(rows)} imagens copiadas.")
    return rows, str(run_dir)


def build_light_xai_events(scene):
    events = scene.get("xai_events", [])

    if not events:
        return []

    df = pd.DataFrame(events)

    if "time_utc" not in df.columns or "lat" not in df.columns or "lon" not in df.columns:
        return []

    df["_time"] = parse_time(df["time_utc"])
    df = df[df["_time"].notna()].copy()

    if df.empty:
        return []

    if "score" not in df.columns:
        df["score"] = 1.0

    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(1.0)
    df["_second"] = df["_time"].dt.floor("s")

    df = (
        df.sort_values(["_second", "score"], ascending=[True, False])
          .groupby("_second")
          .head(MAX_EVENTS_PER_SECOND)
          .sort_values("_time")
          .head(MAX_XAI_EVENTS_LIGHT)
          .copy()
    )

    df["time_utc"] = df["_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df = df.drop(columns=["_time", "_second"], errors="ignore")

    print(f"[XAI LIGHT] {len(df)} eventos selecionados para animação.")
    return clean_records(df)


def normalize_frames(scene):
    frames = scene.get("frames", [])

    if not frames:
        return frames

    df = pd.DataFrame(frames)

    if "time_utc" not in df.columns:
        return frames

    df["_time"] = parse_time(df["time_utc"])
    df = df[df["_time"].notna()].sort_values("_time").copy()
    df["time_utc"] = df["_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df = df.drop(columns=["_time"], errors="ignore")

    return clean_records(df)


def main():
    if not SCENE_IN.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {SCENE_IN}")

    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    scene = json.loads(SCENE_IN.read_text(encoding="utf-8"))

    spectrograms, xai_run = build_spectrogram_timeline()
    xai_light = build_light_xai_events(scene)
    frames = normalize_frames(scene)

    scene["frames"] = frames
    scene["spectrogram_timeline"] = spectrograms
    scene["xai_events_light"] = xai_light

    if "metadata" not in scene:
        scene["metadata"] = {}

    scene["metadata"]["xai_visual_run"] = xai_run
    scene["metadata"]["n_spectrogram_images"] = len(spectrograms)
    scene["metadata"]["n_xai_events_light"] = len(xai_light)
    scene["metadata"]["web_scene_file"] = str(SCENE_OUT)

    SCENE_OUT.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 100)
    print("OK — WEB DATA GERADO")
    print("=" * 100)
    print(f"Entrada : {SCENE_IN}")
    print(f"Saída   : {SCENE_OUT}")
    print(f"Assets  : {ASSET_DIR}")
    print(f"Spectrograms: {len(spectrograms)}")
    print(f"XAI light   : {len(xai_light)}")
    print(f"Frames      : {len(frames)}")


if __name__ == "__main__":
    main()
