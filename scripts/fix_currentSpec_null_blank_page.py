from pathlib import Path

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
lines = p.read_text(encoding="utf-8").splitlines()

backup = p.with_suffix(".jsx.bak_fix_currentSpec_null_blank_page")
backup.write_text("\n".join(lines) + "\n", encoding="utf-8")

removed = []
new_lines = []

for line in lines:
    stripped = line.strip()

    # Remove remaining old cursor fragment based on currentSpec time limits.
    if "Date.parse(currentSpec.time_start_utc)" in line:
        removed.append(line)
        continue

    if "Date.parse(currentSpec.time_end_utc)" in line:
        removed.append(line)
        continue

    if "currentSpec.time_start_utc" in line:
        removed.append(line)
        continue

    if "currentSpec.time_end_utc" in line:
        removed.append(line)
        continue

    if "currentSpec?.time_start_utc" in line and "currentSpec?.time_end_utc" in line and "return 50" in line:
        removed.append(line)
        continue

    if "Number.isFinite(a)" in line and "Number.isFinite(b)" in line:
        removed.append(line)
        continue

    new_lines.append(line)

s = "\n".join(new_lines) + "\n"

# Extra safety for nFrames.
s = s.replace(
    "const nFrames = frames.length;",
    "const nFrames = Array.isArray(frames) ? frames.length : 0;"
)

p.write_text(s, encoding="utf-8")

print("OK — removed unsafe currentSpec time access.")
print("Removed lines:")
for line in removed:
    print("  " + line)
print("Backup:", backup)
