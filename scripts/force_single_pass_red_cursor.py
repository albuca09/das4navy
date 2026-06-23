from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_single_pass_cursor")
backup.write_text(s, encoding="utf-8")

# Remove definições antigas de cursorPct, se existirem.
s = re.sub(
    r'\n\s*const cursorPct\s*=\s*useMemo\([\s\S]*?\);\n',
    '\n',
    s
)

s = re.sub(
    r'\n\s*const cursorPct\s*=\s*[^\n;]*;[^\n]*\n',
    '\n',
    s
)

# Insere nova definição baseada no progresso global da animação.
anchor = '  const nFrames = frames.length;'
block = r'''
  const nFrames = frames.length;

  // Single-pass global cursor:
  // the red line moves continuously from left to right only once
  // across the full animation timeline.
  const cursorPct = useMemo(() => {
    if (!Number.isFinite(frameIndex) || !Number.isFinite(nFrames) || nFrames <= 1) {
      return 0;
    }

    const p = (frameIndex / (nFrames - 1)) * 100;
    return Math.max(0, Math.min(100, p));
  }, [frameIndex, nFrames]);
'''

if anchor in s:
    s = s.replace(anchor, block, 1)
else:
    raise RuntimeError("Não encontrei a linha 'const nFrames = frames.length;' no JSX.")

p.write_text(s, encoding="utf-8")

print("OK — red cursor changed to a single-pass global timeline.")
print("Backup:", backup)
