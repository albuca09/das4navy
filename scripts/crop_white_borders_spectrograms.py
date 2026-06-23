from pathlib import Path
from PIL import Image
import shutil

ROOT = Path(r"C:\Users\Luis\Desktop\das4navy\public\data\das_spectrograms")
BACKUP = Path(r"C:\Users\Luis\Desktop\das4navy\public\data\das_spectrograms_backup_white_border")

WHITE_THR = 245  # pixels quase brancos
ALPHA_THR = 5

def is_white_pixel(px):
    if len(px) == 4:
        r, g, b, a = px
        if a <= ALPHA_THR:
            return True
        return r >= WHITE_THR and g >= WHITE_THR and b >= WHITE_THR
    else:
        r, g, b = px[:3]
        return r >= WHITE_THR and g >= WHITE_THR and b >= WHITE_THR

def crop_white_border(img):
    img = img.convert("RGBA")
    w, h = img.size
    pix = img.load()

    top = 0
    while top < h:
        if any(not is_white_pixel(pix[x, top]) for x in range(w)):
            break
        top += 1

    bottom = h - 1
    while bottom >= 0:
        if any(not is_white_pixel(pix[x, bottom]) for x in range(w)):
            break
        bottom -= 1

    left = 0
    while left < w:
        if any(not is_white_pixel(pix[left, y]) for y in range(h)):
            break
        left += 1

    right = w - 1
    while right >= 0:
        if any(not is_white_pixel(pix[right, y]) for y in range(h)):
            break
        right -= 1

    if left >= right or top >= bottom:
        return img, (0, 0, w, h), False

    cropped = img.crop((left, top, right + 1, bottom + 1))
    changed = (left > 0 or top > 0 or right < w - 1 or bottom < h - 1)
    return cropped, (left, top, right + 1, bottom + 1), changed

def main():
    if not ROOT.exists():
        raise FileNotFoundError(ROOT)

    BACKUP.mkdir(parents=True, exist_ok=True)

    files = sorted(ROOT.glob("*.png"))
    print("=" * 100)
    print("CROPPING WHITE BORDERS FROM SPECTROGRAMS")
    print("=" * 100)
    print("Files found:", len(files))

    changed_count = 0

    for i, fp in enumerate(files, 1):
        img = Image.open(fp)
        cropped, box, changed = crop_white_border(img)

        backup_fp = BACKUP / fp.name
        if not backup_fp.exists():
            shutil.copy2(fp, backup_fp)

        if changed:
            cropped.save(fp)
            changed_count += 1

        if i <= 10 or i % 50 == 0:
            print(f"[{i:03d}/{len(files):03d}] {fp.name} | changed={changed} | box={box}")

    print("\nDONE")
    print("Changed files:", changed_count)
    print("Backup dir:", BACKUP)
    print("Root:", ROOT)

if __name__ == "__main__":
    main()
