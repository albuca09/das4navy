from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_move_stop_guard_after_nframes")
backup.write_text(s, encoding="utf-8")

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

marker = "  }, [frameIndex, nFrames]);"

if marker not in s:
    raise RuntimeError("Could not find the cursorPct closing marker.")

s = s.replace(marker, marker + "\n" + guard, 1)

p.write_text(s, encoding="utf-8")

print("OK — stop guard moved after nFrames/cursorPct.")
print("Old guard blocks removed:", removed)
print("Backup:", backup)
