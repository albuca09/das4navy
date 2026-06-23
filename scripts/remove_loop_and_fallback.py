from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_no_loop_no_fallback")
backup.write_text(s, encoding="utf-8")

# 1) Remove fallback de imagem, se existir.
fallback_re = re.compile(
    r'\n\s*onError=\{\(e\)\s*=>\s*\{\s*'
    r'\n\s*console\.warn\("Spectrogram image failed:",\s*e\.currentTarget\.src\);\s*'
    r'\n\s*e\.currentTarget\.style\.opacity\s*=\s*0\.15;\s*'
    r'\n\s*setFrameIndex\(\(v\)\s*=>\s*\{\s*'
    r'\n\s*if\s*\(!Array\.isArray\(frames\)\s*\|\|\s*frames\.length\s*<=\s*1\)\s*return\s*v;\s*'
    r'\n\s*return\s*\(v\s*\+\s*1\)\s*%\s*frames\.length;\s*'
    r'\n\s*\}\);\s*'
    r'\n\s*\}\}',
    flags=re.MULTILINE
)

s, n_fallback = fallback_re.subn("", s)

# 2) Troca qualquer loop restante por uma passagem única.
old = "return (v + 1) % frames.length;"
new = """const next = v + 1;

                  if (next >= frames.length - 1) {
                    setPlaying(false);
                    return frames.length - 1;
                  }

                  return next;"""

n_loop = s.count(old)
s = s.replace(old, new)

# 3) Também cobre variações com nFrames.
old2 = "return (v + 1) % nFrames;"
new2 = """const next = v + 1;

                  if (next >= nFrames - 1) {
                    setPlaying(false);
                    return nFrames - 1;
                  }

                  return next;"""

n_loop2 = s.count(old2)
s = s.replace(old2, new2)

p.write_text(s, encoding="utf-8")

print("OK — removed image fallback and forced play-once timeline.")
print("Fallback blocks removed:", n_fallback)
print("frames.length loop replacements:", n_loop)
print("nFrames loop replacements:", n_loop2)
print("Backup:", backup)
