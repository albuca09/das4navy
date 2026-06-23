from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_play_once_timeline")
backup.write_text(s, encoding="utf-8")

replacement = r'''setFrameIndex((v) => {
        const next = v + 1;

        if (next >= nFrames - 1) {
          setPlaying(false);
          return nFrames - 1;
        }

        return next;
      });'''

patterns = [
    r'setFrameIndex\(\((\w+)\)\s*=>\s*\(\s*\1\s*\+\s*1\s*\)\s*%\s*nFrames\s*\);',
    r'setFrameIndex\(\((\w+)\)\s*=>\s*\(\s*\1\s*\+\s*1\s*\)\s*%\s*frames\.length\s*\);',
    r'setFrameIndex\(\((\w+)\)\s*=>\s*\(\s*\1\s*\+\s*1\s*\)\s*%\s*Math\.max\(\s*1\s*,\s*nFrames\s*\)\s*\);',
]

total = 0
for pat in patterns:
    s, n = re.subn(pat, replacement, s)
    total += n

p.write_text(s, encoding="utf-8")

print("OK — timeline changed to play once and stop at the final frame.")
print("Replacements:", total)
print("Backup:", backup)

if total == 0:
    print("WARNING — no loop expression was found. Please inspect setFrameIndex manually.")
