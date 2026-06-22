from pathlib import Path
import json
import re
import shutil
import hashlib
from datetime import datetime, timezone, timedelta

APP = Path(r"C:\Users\Luis\Desktop\das4navy")

SOURCE_ROOT = Path(r"D:\DAS\_das_xai_spectrogram_perturbations")
DEST_DIR = APP / "public" / "data" / "das_spectrograms"
MANIFEST = APP / "public" / "data" / "spectrogram_manifest.json"
SCENE = APP / "public" / "data" / "das4navy_scene_web_lite.json"

EVENT_START = datetime(2021, 11, 1, 17, 48, 15, tzinfo=timezone.utc)
EVENT_END   = datetime(2021, 11, 1, 18, 16, 4, tzinfo=timezone.utc)

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
    channel = int(m_ch.group(1)) if m_ch else None

    probability = None
    if m_prob:
        try:
            probability = float(m_prob.group(1).rstrip("."))
        except Exception:
            probability = None

    return rank, channel, probability

def source_kind(p: Path) -> str:
    low = str(p).lower()
    if "grad" in low or "cam" in low or "xai" in low:
        return "xai_gradcam"
    if "raw" in low:
        return "raw_spectrogram"
    return "spectrogram"

def unique_name(p: Path) -> str:
    rel = str(p.relative_to(SOURCE_ROOT)).replace("\\", "/")
    h = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:10]
    return f"{source_kind(p)}_{h}_{p.name}"

def main():
    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(SOURCE_ROOT)

    print("=" * 100)
    print("REBUILDING ALL SPECTROGRAMS FROM ALL RUNS")
    print("=" * 100)
    print("Source root:", SOURCE_ROOT)

    pngs = []

    for p in SOURCE_ROOT.rglob("*.png"):
        name = p.name.lower()

        if not (
            "xai_rank_" in name
            or "spectrogram" in name
            or "gradcam" in name
            or "grad_cam" in name
        ):
            continue

        if valid_png(p):
            pngs.append(p)

    # Remove apenas duplicação exata de caminho resolvido.
    seen = set()
    unique_pngs = []

    for p in pngs:
        rp = str(p.resolve()).lower()
        if rp not in seen:
            seen.add(rp)
            unique_pngs.append(p)

    def sort_key(p):
        rank, ch, prob = parse_name(p.name)
        return (
            999999 if rank is None else rank,
            999999 if ch is None else ch,
            source_kind(p),
            str(p).lower()
        )

    unique_pngs = sorted(unique_pngs, key=sort_key)

    print("Valid source PNGs:", len(unique_pngs))

    # Inventário por pasta.
    folder_counts = {}
    for p in unique_pngs:
        folder = str(p.parent)
        folder_counts[folder] = folder_counts.get(folder, 0) + 1

    print("\nFolders found:")
    for folder, count in sorted(folder_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {count:5d}  {folder}")

    if not unique_pngs:
        raise RuntimeError("No valid PNG files found.")

    if DEST_DIR.exists():
        shutil.rmtree(DEST_DIR)

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    total_sec = max(1.0, (EVENT_END - EVENT_START).total_seconds())
    step_sec = total_sec / max(1, len(unique_pngs))

    rows = []

    for i, src in enumerate(unique_pngs):
        dst_name = unique_name(src)
        dst = DEST_DIR / dst_name
        shutil.copy2(src, dst)

        rank, channel, probability = parse_name(src.name)

        t0 = EVENT_START + timedelta(seconds=i * step_sec)
        t1 = EVENT_START + timedelta(seconds=(i + 1) * step_sec)

        rows.append({
            "kind": source_kind(src),
            "rank": rank,
            "image_url": f"/data/das_spectrograms/{dst_name}",
            "channel": channel,
            "probability": probability,
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

    copied = len(list(DEST_DIR.glob("*.png")))

    print("\nCopied PNGs:", copied)
    print("Manifest entries:", len(rows))
    print("Destination:", DEST_DIR)
    print("Manifest:", MANIFEST)
    print("First:", rows[0]["image_url"])
    print("Last :", rows[-1]["image_url"])

    if copied != len(rows):
        raise RuntimeError(f"Mismatch: copied={copied}, manifest={len(rows)}")

if __name__ == "__main__":
    main()
