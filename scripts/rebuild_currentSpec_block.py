from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_rebuild_currentSpec_block")
backup.write_text(s, encoding="utf-8")

new_block = r'''  const currentSpec = useMemo(() => {
    const list = Array.isArray(spectrograms) ? spectrograms : [];

    if (list.length === 0) {
      return null;
    }

    if (!Number.isFinite(currentTimeMs)) {
      return list[0] || null;
    }

    let best = list[0] || null;
    let bestScore = Infinity;

    for (const sp of list) {
      if (!sp) continue;

      const a = ms(sp.time_start_utc);
      const b = ms(sp.time_end_utc);

      let score = Infinity;

      if (Number.isFinite(a) && Number.isFinite(b) && b > a) {
        if (currentTimeMs >= a && currentTimeMs <= b) {
          score = 0;
        } else {
          const center = 0.5 * (a + b);
          score = Math.abs(currentTimeMs - center);
        }
      } else if (Number.isFinite(a)) {
        score = Math.abs(currentTimeMs - a);
      }

      if (score < bestScore) {
        bestScore = score;
        best = sp;
      }
    }

    return best || list[0] || null;
  }, [spectrograms, currentTimeMs]);'''

# First try: replace normal useMemo block.
pattern = re.compile(
    r'  const currentSpec = useMemo\(\(\) => \{[\s\S]*?\n\s*\},\s*\[[^\]]*\]\);',
    flags=re.MULTILINE
)

s2, n = pattern.subn(new_block, s, count=1)

# Fallback: if the block is too broken for regex, replace from currentSpec
# until the next top-level const declaration.
if n == 0:
    lines = s.splitlines()
    start = None
    for i, line in enumerate(lines):
        if "const currentSpec = useMemo(() => {" in line:
            start = i
            break

    if start is None:
        raise RuntimeError("Could not find currentSpec block start.")

    end = None
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if j > start + 3 and line.startswith("  const ") and "currentSpec" not in line:
            end = j
            break

    if end is None:
        raise RuntimeError("Could not find end of broken currentSpec block.")

    lines = lines[:start] + new_block.splitlines() + [""] + lines[end:]
    s2 = "\n".join(lines) + "\n"
    n = 1

p.write_text(s2, encoding="utf-8")

print("OK — currentSpec useMemo block rebuilt safely.")
print("Replacements:", n)
print("Backup:", backup)
