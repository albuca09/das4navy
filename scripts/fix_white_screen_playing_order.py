from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_fix_white_screen_playing_order")
backup.write_text(s, encoding="utf-8")

# Remove the stop guard wherever it was inserted.
guard_re = re.compile(
    r'\n\s*// Stop playback exactly at the final frame\.\s*'
    r'\n\s*// This keeps the red cursor as a single left-to-right passage\.\s*'
    r'\n\s*useEffect\(\(\)\s*=>\s*\{\s*'
    r'\n\s*if\s*\(!playing\s*\|\|\s*nFrames\s*<=\s*1\)\s*return;\s*'
    r'\n\s*if\s*\(frameIndex\s*>=\s*nFrames\s*-\s*1\)\s*\{\s*'
    r'\n\s*setPlaying\(false\);\s*'
    r'\n\s*setFrameIndex\(nFrames\s*-\s*1\);\s*'
    r'\n\s*\}\s*'
    r'\n\s*\},\s*\[frameIndex,\s*nFrames,\s*playing\]\);\s*',
    flags=re.MULTILINE
)

s, removed = guard_re.subn("\n", s)

guard = '''
  // Stop playback exactly at the final frame.
  // This keeps the red cursor as a single left-to-right passage.
  useEffect(() => {
    if (!playing || nFrames <= 1) return;

    if (frameIndex >= nFrames - 1) {
      setPlaying(false);
      setFrameIndex(nFrames - 1);
    }
  }, [frameIndex, nFrames, playing]);

'''

# Insert after the playing state declaration if possible.
patterns = [
    r'(const\s*\[\s*playing\s*,\s*setPlaying\s*\]\s*=\s*useState\([^\n]*\);\s*)',
    r'(const\s*\[\s*isPlaying\s*,\s*setPlaying\s*\]\s*=\s*useState\([^\n]*\);\s*)',
]

inserted = False

for pat in patterns:
    m = re.search(pat, s)
    if m:
        pos = m.end()
        s = s[:pos] + "\n" + guard + s[pos:]
        inserted = True
        break

if not inserted:
    raise RuntimeError("Could not find the playing/setPlaying useState declaration.")

p.write_text(s, encoding="utf-8")

print("OK — stop guard moved after playing state declaration.")
print("Old guard blocks removed:", removed)
print("Backup:", backup)
