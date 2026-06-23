from pathlib import Path

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_stop_at_final_frame")
backup.write_text(s, encoding="utf-8")

if "Stop playback exactly at the final frame" not in s:
    marker = '''  }, [frameIndex, nFrames]);'''

    insert = '''  }, [frameIndex, nFrames]);

  // Stop playback exactly at the final frame.
  // This keeps the red cursor as a single left-to-right passage.
  useEffect(() => {
    if (!playing || nFrames <= 1) return;

    if (frameIndex >= nFrames - 1) {
      setPlaying(false);
      setFrameIndex(nFrames - 1);
    }
  }, [frameIndex, nFrames, playing]);'''

    if marker not in s:
        raise RuntimeError("Could not find cursorPct closing marker.")

    s = s.replace(marker, insert, 1)

p.write_text(s, encoding="utf-8")

print("OK — final-frame stop guard added.")
print("Backup:", backup)
