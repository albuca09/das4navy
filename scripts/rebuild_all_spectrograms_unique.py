from pathlib import Path
import json
import re
import shutil
import hashlib
import pandas as pd

APP = Path(r"C:\Users\Luis\Desktop\das4navy")

SOURCE_ROOT = Path(r"D:\DAS\_das_xai_spectrogram_perturbations\run_20260621_175420")
DEST_DIR = APP / "public" / "data" / "das_spectrograms"
MANIFEST = APP / "public" / "data" / "spectrogram_manifest.json"
SCENE = APP / "public" / "data" / "das4navy_scene_web_lite.json"

EVENT_START = pd.to_datetime("2021-11-01T17:48:15Z", utc=True)
EVENT_END   = pd.to_datetime("2021-11-01T18:16:04Z", utc=True)

def valid_png(p: Path) -> bool:
    if not p.exists() or p.stat().st_size < 100:
        return False
    try:
        with open(p, "rb") as f:
            return f.read(8) == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False

def parse_name(name):
    stem = Path(name).stem

    m_rank = re.search(r"xai_rank_(\d+)", stem, re.IGNORECASE)
    m_ch = re.search(r"_ch_(\d+)", stem, re.IGNORECASE)
    m_prob = re.search(r"_prob_([0-9.]+)", stem, re.IGNORECASE)

    rank = int(m_rank.group(1)) if m_rank else None
    ch = int(m_ch.group(1)) if m_ch else None

    prob = None
    if m_prob:
        try:
            prob = float(m_prob.group(1).rstrip("."))
        except Exception:
            prob = None

    return rank, ch, prob

def source_kind(p: Path) -> str:
    parts = [x.lower() for x in p.parts]

    if "xai_gradcam" in parts:
        return "xai_gradcam"
    if "spectrograms_raw" in parts:
        return "raw_spectrogram"
    if "spectrogram" in p.name.lower():
        return "spectrogram"
    return "das_xai_frame"

def unique_name(p: Path) -> str:
    kind = source_kind(p)
    h = hashlib.sha1(str(p).encode("utf-8")).hexdigest()[:8]
    return f"{kind}_{h}_{p.name}"

def main():
    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(SOURCE_ROOT)

    print("=" * 100)
    print("REBUILDING ALL SPECTROGRAMS WITH UNIQUE FILENAMES")
    print("=" * 100)

    pngs = []

    for p in SOURCE_ROOT.rglob("*.png"):
        name = p.name.lower()
        if (
            "xai_rank_" in name
            or "spectrogram" in name
            or "gradcam" in name
        ):
            if valid_png(p):
                pngs.append(p)

    def sort_key(p):
        rank, ch, prob = parse_name(p.name)
        kind = source_kind(p)
        kind_order = {
            "raw_spectrogram": 0,
            "xai_gradcam": 1,
            "spectrogram": 2,
            "das_xai_frame": 3,
        }.get(kind, 9)

        return (
            999999 if rank is None else rank,
            kind_order,
            999999 if ch is None else ch,
            p.name.lower(),
            str(p).lower(),
        )

    pngs = sorted(pngs, key=sort_key)

    print("Valid source PNGs:", len(pngs))

    if DEST_DIR.exists():
        shutil.rmtree(DEST_DIR)

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    total_sec = max(1.0, (EVENT_END - EVENT_START).total_seconds())
    step_sec = total_sec / max(1, len(pngs))

    rows = []

    for i, src in enumerate(pngs):
        dst_name = unique_name(src)
        dst = DEST_DIR / dst_name

        shutil.copy2(src, dst)

        rank, ch, prob = parse_name(src.name)

        t0 = EVENT_START + pd.Timedelta(seconds=i * step_sec)
        t1 = EVENT_START + pd.Timedelta(seconds=(i + 1) * step_sec)

        rows.append({
            "kind": source_kind(src),
            "rank": rank,
            "image_url": f"/data/das_spectrograms/{dst_name}",
            "channel": ch,
            "probability": prob,
            "time_start_utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time_end_utc": t1.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_file": str(src),
            "copied_file": str(dst),
        })

    MANIFEST.write_text(
        json.dumps({"spectrograms": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    if SCENE.exists():
        scene = json.loads(SCENE.read_text(encoding="utf-8"))
        scene["spectrogram_timeline"] = rows
        scene.setdefault("metadata", {})
        scene["metadata"]["n_spectrograms"] = len(rows)
        scene["metadata"]["spectrograms_unique_filenames"] = True
        scene["metadata"]["spectrogram_source_root"] = str(SOURCE_ROOT)

        SCENE.write_text(
            json.dumps(scene, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8"
        )

    print("Copied PNGs:", len(list(DEST_DIR.glob('*.png'))))
    print("Manifest entries:", len(rows))
    print("Destination:", DEST_DIR)
    print("Manifest:", MANIFEST)
    print("First:", rows[0]["image_url"])
    print("Last :", rows[-1]["image_url"])

if __name__ == "__main__":
    main()
