from pathlib import Path

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_red_cursor_full_width")
backup.write_text(s, encoding="utf-8")

old = 'style={{ left: `clamp(90px, ${cursorPct}%, calc(100% - 115px))` }}'
new = 'style={{ left: `${cursorPct}%` }}'

n = s.count(old)
s = s.replace(old, new)

p.write_text(s, encoding="utf-8")

print("OK — red cursor now moves from 0% to 100%.")
print("Replacements:", n)
print("Backup:", backup)
