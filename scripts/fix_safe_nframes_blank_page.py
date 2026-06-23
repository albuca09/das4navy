from pathlib import Path

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_safe_nframes_blank_page")
backup.write_text(s, encoding="utf-8")

old = "const nFrames = frames.length;"
new = "const nFrames = Array.isArray(frames) ? frames.length : 0;"

count = s.count(old)
s = s.replace(old, new)

p.write_text(s, encoding="utf-8")

print("OK — nFrames is now safe when frames is undefined.")
print("Replacements:", count)
print("Backup:", backup)
