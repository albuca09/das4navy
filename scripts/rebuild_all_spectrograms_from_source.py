from pathlib import Path
import json
import re
import shutil

APP = Path(r"C:\Users\Luis\Desktop\das4navy")
DEST_DIR = APP / "public" / "data" / "das_spectrograms"
MANIFEST = APP / "public" / "data" / "spectrogram_manifest.json"
SCENE = APP / "public" / "data" / "das4navy_scene_web_lite.json"

# Ajuste se quiser apontar direto para um run específico:
PREFERRED_SOURCE = Path(
    r"D:\DAS\_das_xai_spectrogram_perturbations\run_20260621_175420"
)

def valid_png(p: Path) -> bool:
    if not p.exists() or p.stat().st_size < 100:
        return False
    try:
        with open(p, "rb") as f:
            sig = f.read(8)
        return sig == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False

def find_source_pngs():
    roots = []

    if PREFERRED_SOURCE.exists():
        roots.append(PREFERRED_SOURCE)

    generic_root = Path(r"D:\DAS\_das_xai_spectrogram_perturbations")
    if generic_root.exists() and generic_root not in roots:
        roots.append(generic_root)

    pngs = []

    for root in roots:
        for p in root.rglob("*.png"):
            name = p.name.lower()
            # Aceita os formatos mais prováveis do pipeline XAI
            if (
                "xai_rank_" in name
                or "spectrogram" in name
                or "gradcam" in name
            ):
                if valid_png(p):
                    pngs.append(p)

    # remove duplicados por nome + tamanho
    uniq = {}
    for p in pngs:
        key = (p.name.lower(), p.stat().st_size)
        if key not in uniq:
            uniq[key] = p

    out = list(uniq.values())

    # ordena por rank se existir no nome
    def rank_key(p):
        m = re.search(r"xai_rank_(\d+)", p.name.lower())
        if m:
            return (0, int(m.group(1)), p.name.lower())
        return (1, 10**9, p.name.lower())

    out.sort(key=rank_key)
    return out

def parse_name(name):
    stem = Path(name).stem
    m_rank = re.search(r"xai_rank_(\d+)", stem, re.IGNORECASE)
    m_ch = re.search(r"_ch_(\d+)", stem, re.IGNORECASE)
    m_prob = re.search(r"_prob_([0-9.]+)", stem, re.IGNORECASE)

    rank = int(m_rank.group(1)) if m_rank else None
    ch = int(m_ch.group(1)) if m_ch else None
    prob = float(m_prob.group(1)) if m_prob else None
    return rank, ch, prob

def load_old_manifest():
    if not MANIFEST.exists():
        return {}
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        rows = data.get("spectrograms", [])
        by_name = {}
        for r in rows:
            url = r.get("image_url", "")
            name = Path(url).name
            by_name[name] = r
        return by_name
    except Exception:
        return {}

def main():
    print("=" * 100)
    print("REBUILD ALL SPECTROGRAMS FROM SOURCE")
    print("=" * 100)

    source_pngs = find_source_pngs()
    print("Valid source PNGs found:", len(source_pngs))

    if not source_pngs:
        raise RuntimeError(
            "Nenhum PNG válido foi encontrado na pasta fonte do pipeline XAI."
        )

    old_meta = load_old_manifest()

    if DEST_DIR.exists():
        shutil.rmtree(DEST_DIR)
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    for p in source_pngs:
        dest = DEST_DIR / p.name
        shutil.copy2(p, dest)

        rank, ch, prob = parse_name(p.name)

        old = old_meta.get(p.name, {})

        row = {
            "kind": old.get("kind", "das_xai_spectrogram"),
            "image_url": f"/data/das_spectrograms/{p.name}",
            "channel": old.get("channel", ch),
            "probability": old.get("probability", prob),
            "time_start_utc": old.get("time_start_utc"),
            "time_end_utc": old.get("time_end_utc"),
            "source_file": str(dest),
        }
        rows.append(row)

    manifest_data = {"spectrograms": rows}
    MANIFEST.write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    if SCENE.exists():
        scene = json.loads(SCENE.read_text(encoding="utf-8"))
        scene["spectrogram_timeline"] = rows
        scene.setdefault("metadata", {})
        scene["metadata"]["n_spectrograms"] = len(rows)
        SCENE.write_text(
            json.dumps(scene, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8"
        )

    print("Destination:", DEST_DIR)
    print("Manifest:", MANIFEST)
    print("Scene updated:", SCENE.exists())
    print("Total copied:", len(rows))
    print("First:", rows[0]["image_url"])
    print("Last :", rows[-1]["image_url"])

if __name__ == "__main__":
    main()
