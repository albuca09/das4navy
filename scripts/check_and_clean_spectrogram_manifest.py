from pathlib import Path
import json
import shutil

APP = Path(r"C:\Users\Luis\Desktop\das4navy")

MANIFEST = APP / "public" / "data" / "spectrogram_manifest.json"
SCENE = APP / "public" / "data" / "das4navy_scene_web_lite.json"

PUBLIC_DATA = APP / "public" / "data"
DIST_DATA = APP / "dist" / "data"

def local_path_from_url(url, base):
    if not url:
        return None
    u = str(url).replace("\\", "/")
    u = u.split("?")[0]
    u = u.lstrip("/")
    if u.startswith("das4navy/"):
        u = u[len("das4navy/"):]
    if u.startswith("data/"):
        u = u[len("data/"):]
    return base / u

def is_valid_png(path):
    if not path or not path.exists():
        return False
    if path.stat().st_size < 100:
        return False
    try:
        with open(path, "rb") as f:
            sig = f.read(8)
        return sig == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False

print("=" * 100)
print("CHECKING SPECTROGRAM MANIFEST")
print("=" * 100)

data = json.loads(MANIFEST.read_text(encoding="utf-8"))
specs = data.get("spectrograms", [])

print("Manifest:", MANIFEST)
print("Total entries:", len(specs))

valid = []
missing = []
invalid_png = []

for item in specs:
    url = item.get("image_url")
    p = local_path_from_url(url, PUBLIC_DATA)

    if p is None or not p.exists():
        missing.append((url, p))
        continue

    if not is_valid_png(p):
        invalid_png.append((url, p))
        continue

    valid.append(item)

print("Valid PNGs:", len(valid))
print("Missing files:", len(missing))
print("Invalid/corrupted PNGs:", len(invalid_png))

if missing:
    print("\nMISSING EXAMPLES:")
    for url, p in missing[:20]:
        print(" -", url, "=>", p)

if invalid_png:
    print("\nINVALID PNG EXAMPLES:")
    for url, p in invalid_png[:20]:
        print(" -", url, "=>", p, "size=", p.stat().st_size if p and p.exists() else None)

# Backup and write clean manifest.
backup = MANIFEST.with_suffix(".json.bak_before_clean")
shutil.copy2(MANIFEST, backup)

data["spectrograms"] = valid
MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

print("\nClean manifest written:", MANIFEST)
print("Backup:", backup)

# Also clean scene spectrogram_timeline if present.
if SCENE.exists():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    old = scene.get("spectrogram_timeline", [])
    clean_scene_specs = []

    for item in old:
        url = item.get("image_url")
        p = local_path_from_url(url, PUBLIC_DATA)
        if is_valid_png(p):
            clean_scene_specs.append(item)

    scene["spectrogram_timeline"] = clean_scene_specs

    scene_backup = SCENE.with_suffix(".json.bak_before_clean_specs")
    shutil.copy2(SCENE, scene_backup)

    scene["metadata"] = scene.get("metadata", {})
    scene["metadata"]["n_valid_spectrogram_images"] = len(clean_scene_specs)

    SCENE.write_text(json.dumps(scene, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print("Scene spectrogram_timeline:", len(old), "=>", len(clean_scene_specs))
    print("Scene backup:", scene_backup)

print("\nDONE")
