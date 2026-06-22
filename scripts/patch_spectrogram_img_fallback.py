from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_img_error_fallback")
backup.write_text(s, encoding="utf-8")

# Add onError to the spectrogram image if it is not already present.
if "Spectrogram image failed" not in s:
    s = s.replace(
        'alt="DAS/XAI spectrogram video frame"',
        '''alt="DAS/XAI spectrogram video frame"
              onError={(e) => {
                console.warn("Spectrogram image failed:", e.currentTarget.src);
                e.currentTarget.style.opacity = 0.15;
                setFrameIndex((v) => {
                  if (!Array.isArray(frames) || frames.length <= 1) return v;
                  return (v + 1) % frames.length;
                });
              }}'''
    )

p.write_text(s, encoding="utf-8")

print("OK — image error fallback added.")
print("Backup:", backup)
