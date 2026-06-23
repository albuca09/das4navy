from pathlib import Path

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
lines = p.read_text(encoding="utf-8").splitlines()

backup = p.with_suffix(".jsx.bak_fix_unexpected_token_227")
backup.write_text("\n".join(lines) + "\n", encoding="utf-8")

target = "}, [currentSpec, currentTimeMs]);"
matches = [i for i, line in enumerate(lines) if target in line]

if not matches:
    print("No dangling block found with:", target)
else:
    idx = matches[0]

    # Remove the whole leftover fragment immediately above this dangling hook close.
    start = idx
    while start > 0 and lines[start - 1].strip() != "":
        start -= 1

    removed = lines[start:idx + 1]
    lines = lines[:start] + lines[idx + 1:]

    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("OK — dangling old cursor fragment removed.")
    print("Removed lines:")
    for line in removed:
        print("  " + line)
    print("Backup:", backup)
