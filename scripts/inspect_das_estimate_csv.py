from pathlib import Path
import pandas as pd

p = Path(r"D:\DAS\_ship_position_estimation_from_das_noais\run_20260613_222353\tables\estimated_ship_track_offcable_das_only.csv")

print("=" * 100)
print("INSPEÇÃO DO CSV DE ESTIMATIVA DAS")
print("=" * 100)
print("Arquivo:", p)
print("Existe :", p.exists())

if not p.exists():
    raise FileNotFoundError(p)

df = pd.read_csv(p, nrows=20, low_memory=False)

print("\n" + "=" * 100)
print("COLUNAS")
print("=" * 100)

for i, c in enumerate(df.columns, 1):
    print(f"{i:03d} | {c}")

print("\n" + "=" * 100)
print("PRIMEIRAS LINHAS")
print("=" * 100)
print(df.head(10).to_string(index=False))

print("\n" + "=" * 100)
print("POSSÍVEIS COLUNAS DE LAT/LON")
print("=" * 100)

lat_cols = [c for c in df.columns if "lat" in c.lower()]
lon_cols = [c for c in df.columns if "lon" in c.lower() or "lng" in c.lower()]

print("LAT candidates:")
for c in lat_cols:
    print(" -", c)

print("\nLON candidates:")
for c in lon_cols:
    print(" -", c)

print("\n" + "=" * 100)
print("POSSÍVEIS COLUNAS DE TEMPO/CANAL/CABO")
print("=" * 100)

for key in ["time", "utc", "channel", "cable", "side", "score", "distance", "error"]:
    cols = [c for c in df.columns if key in c.lower()]
    if cols:
        print(f"\n{key.upper()}:")
        for c in cols:
            print(" -", c)
