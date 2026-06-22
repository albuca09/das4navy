# -*- coding: utf-8 -*-
"""
Busca o CSV correto de estimativa DAS para o evento JEANOAH.

Procura CSVs em D:\DAS com colunas de tempo + lat/lon,
compara cada trajetória candidata com o AIS MMSI 366959080
e lista os melhores candidatos por distância mediana DAS x AIS.
"""

from pathlib import Path
import re
import json
import math
import numpy as np
import pandas as pd


APP = Path(r"C:\Users\Luis\Desktop\das4navy")

OUT_REPORT = APP / "_debug_das_candidate_tracks.csv"

AIS_CSV = Path(r"D:\AIS_2021_EXP\EXT\AIS_2021_11_01\AIS_2021_11_01.csv")
MMSI = 366959080

EVENT_START = pd.to_datetime("2021-11-01T17:48:15Z", utc=True)
EVENT_END   = pd.to_datetime("2021-11-01T18:16:04Z", utc=True)
PAD = pd.Timedelta(minutes=30)

SEARCH_ROOTS = [
    Path(r"D:\DAS\_ship_position_estimation_from_das_noais"),
    Path(r"D:\DAS\_ship_position_estimation_from_das"),
    Path(r"D:\DAS"),
]

NAME_KEYWORDS = [
    "estimated",
    "estimate",
    "track",
    "trajectory",
    "ship",
    "offcable",
    "noais",
    "eval",
    "matched",
]


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def find_col(cols, candidates):
    nmap = {norm(c): c for c in cols}

    for cand in candidates:
        nc = norm(cand)
        if nc in nmap:
            return nmap[nc]

    for c in cols:
        nc = norm(c)
        for cand in candidates:
            if norm(cand) in nc:
                return c

    return None


def parse_time(s):
    return pd.to_datetime(s, utc=True, errors="coerce")


def haversine_km(lat1, lon1, lat2, lon2):
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lon1 = np.radians(np.asarray(lon1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    lon2 = np.radians(np.asarray(lon2, dtype=float))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(a))


def load_ais():
    if not AIS_CSV.exists():
        raise FileNotFoundError(AIS_CSV)

    chunks = []

    for ch in pd.read_csv(AIS_CSV, chunksize=300_000, low_memory=False):
        if "MMSI" not in ch.columns:
            continue

        sub = ch[pd.to_numeric(ch["MMSI"], errors="coerce") == MMSI].copy()

        if sub.empty:
            continue

        time_col = find_col(sub.columns, ["BaseDateTime", "time_utc", "timestamp", "datetime"])
        lat_col = find_col(sub.columns, ["LAT", "lat", "latitude"])
        lon_col = find_col(sub.columns, ["LON", "lon", "longitude"])

        if time_col is None or lat_col is None or lon_col is None:
            continue

        out = pd.DataFrame()
        out["time_utc"] = parse_time(sub[time_col])
        out["lat"] = pd.to_numeric(sub[lat_col], errors="coerce")
        out["lon"] = pd.to_numeric(sub[lon_col], errors="coerce")

        for c_out, cands in {
            "sog": ["SOG", "sog"],
            "cog": ["COG", "cog"],
            "heading": ["Heading", "heading"],
        }.items():
            c = find_col(sub.columns, cands)
            out[c_out] = pd.to_numeric(sub[c], errors="coerce") if c is not None else np.nan

        out = out[
            out["time_utc"].notna()
            & out["lat"].between(-90, 90)
            & out["lon"].between(-180, 180)
        ].copy()

        out = out[
            (out["time_utc"] >= EVENT_START - PAD)
            & (out["time_utc"] <= EVENT_END + PAD)
        ].copy()

        if not out.empty:
            chunks.append(out)

    if not chunks:
        raise RuntimeError("Não encontrei AIS do MMSI 366959080 próximo da janela do evento.")

    ais = pd.concat(chunks, ignore_index=True)
    ais = ais.sort_values("time_utc").drop_duplicates("time_utc").reset_index(drop=True)

    if len(ais) < 2:
        raise RuntimeError("AIS insuficiente para interpolação.")

    print("=" * 100)
    print("AIS JEANOAH")
    print("=" * 100)
    print("Pontos AIS:", len(ais))
    print("Tempo:", ais["time_utc"].min(), "→", ais["time_utc"].max())
    print("Lat:", ais["lat"].min(), "→", ais["lat"].max())
    print("Lon:", ais["lon"].min(), "→", ais["lon"].max())

    return ais


def candidate_csv_files():
    seen = set()
    files = []

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        for p in root.rglob("*.csv"):
            sp = str(p).lower()

            if p in seen:
                continue

            if any(k in sp for k in NAME_KEYWORDS):
                files.append(p)
                seen.add(p)

    files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
    return files


def latlon_pairs(cols):
    pairs = []

    explicit = [
        ("est_ship_lat", "est_ship_lon"),
        ("est_lat", "est_lon"),
        ("estimated_lat", "estimated_lon"),
        ("lat_est", "lon_est"),
        ("ship_lat_est", "ship_lon_est"),
        ("closest_ship_lat", "closest_ship_lon"),
        ("ais_lat", "ais_lon"),
        ("lat", "lon"),
        ("LAT", "LON"),
    ]

    for a, b in explicit:
        ca = find_col(cols, [a])
        cb = find_col(cols, [b])
        if ca is not None and cb is not None:
            pairs.append((ca, cb))

    # Também tenta todos os pares lat/lon.
    lat_cols = [c for c in cols if "lat" in norm(c)]
    lon_cols = [c for c in cols if "lon" in norm(c) or "lng" in norm(c)]

    for la in lat_cols:
        for lo in lon_cols:
            if (la, lo) not in pairs:
                pairs.append((la, lo))

    return pairs


def score_csv(path, ais):
    try:
        head = pd.read_csv(path, nrows=3, low_memory=False)
    except Exception:
        return []

    cols = list(head.columns)

    time_col = find_col(cols, [
        "time_utc",
        "timestamp",
        "datetime",
        "utc",
        "closest_time_utc",
        "ais_time_utc",
        "estimated_time_utc",
        "BaseDateTime",
    ])

    if time_col is None:
        return []

    pairs = latlon_pairs(cols)

    if not pairs:
        return []

    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        return []

    if time_col not in df.columns:
        return []

    df["_time"] = parse_time(df[time_col])
    df = df[df["_time"].notna()].copy()

    # Precisa tocar a janela do evento.
    df = df[
        (df["_time"] >= EVENT_START - PAD)
        & (df["_time"] <= EVENT_END + PAD)
    ].copy()

    if len(df) < 3:
        return []

    ais_cmp = ais[["time_utc", "lat", "lon"]].copy()
    ais_cmp = ais_cmp.rename(columns={
        "time_utc": "_ais_time",
        "lat": "_ais_lat",
        "lon": "_ais_lon",
    }).sort_values("_ais_time")

    results = []

    channel_col = find_col(cols, [
        "est_channel",
        "channel",
        "nearest_cable_channel",
        "das_channel",
        "est_channel_argmax",
    ])

    cable_col = find_col(cols, ["est_cable", "cable", "cable_id", "side"])

    for lat_col, lon_col in pairs:
        if lat_col not in df.columns or lon_col not in df.columns:
            continue

        sub = df.copy()
        sub["_lat"] = pd.to_numeric(sub[lat_col], errors="coerce")
        sub["_lon"] = pd.to_numeric(sub[lon_col], errors="coerce")

        sub = sub[
            sub["_lat"].between(-90, 90)
            & sub["_lon"].between(-180, 180)
        ].copy()

        if len(sub) < 3:
            continue

        sub = sub.sort_values("_time")

        merged = pd.merge_asof(
            sub,
            ais_cmp,
            left_on="_time",
            right_on="_ais_time",
            direction="nearest",
            tolerance=pd.Timedelta(minutes=10)
        )

        merged = merged[merged["_ais_lat"].notna()].copy()

        if len(merged) < 3:
            continue

        d = haversine_km(
            merged["_lat"].to_numpy(),
            merged["_lon"].to_numpy(),
            merged["_ais_lat"].to_numpy(),
            merged["_ais_lon"].to_numpy(),
        )

        ch_min = np.nan
        ch_max = np.nan

        if channel_col is not None and channel_col in merged.columns:
            chs = pd.to_numeric(merged[channel_col], errors="coerce")
            ch_min = float(np.nanmin(chs)) if chs.notna().any() else np.nan
            ch_max = float(np.nanmax(chs)) if chs.notna().any() else np.nan

        cable_values = ""
        if cable_col is not None and cable_col in merged.columns:
            cable_values = ",".join(sorted(set(merged[cable_col].dropna().astype(str).head(10))))

        results.append({
            "path": str(path),
            "filename": path.name,
            "modified_time": pd.to_datetime(path.stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M:%S"),
            "time_col": time_col,
            "lat_col": lat_col,
            "lon_col": lon_col,
            "channel_col": channel_col,
            "channel_min": ch_min,
            "channel_max": ch_max,
            "cable_col": cable_col,
            "cable_values": cable_values,
            "n_rows_window": int(len(sub)),
            "n_matched_ais": int(len(merged)),
            "csv_time_min": str(sub["_time"].min()),
            "csv_time_max": str(sub["_time"].max()),
            "median_km": float(np.nanmedian(d)),
            "mean_km": float(np.nanmean(d)),
            "p90_km": float(np.nanpercentile(d, 90)),
            "min_km": float(np.nanmin(d)),
        })

    return results


def main():
    ais = load_ais()

    files = candidate_csv_files()

    print("\n" + "=" * 100)
    print("CSV CANDIDATOS")
    print("=" * 100)
    print("Total:", len(files))

    all_results = []

    for i, p in enumerate(files, 1):
        if i % 50 == 0:
            print(f"Processados {i}/{len(files)}...")

        rows = score_csv(p, ais)

        if rows:
            all_results.extend(rows)

    if not all_results:
        print("Nenhum CSV candidato com lat/lon e tempo foi encontrado.")
        return

    res = pd.DataFrame(all_results)
    res = res.sort_values(["median_km", "mean_km", "p90_km"]).reset_index(drop=True)

    res.to_csv(OUT_REPORT, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 100)
    print("TOP 30 CANDIDATOS MAIS PRÓXIMOS DO AIS")
    print("=" * 100)

    cols = [
        "median_km",
        "mean_km",
        "p90_km",
        "min_km",
        "n_matched_ais",
        "lat_col",
        "lon_col",
        "channel_min",
        "channel_max",
        "cable_values",
        "csv_time_min",
        "csv_time_max",
        "path",
    ]

    print(res[cols].head(30).to_string(index=False))
    print("\nRelatório salvo em:", OUT_REPORT)


if __name__ == "__main__":
    main()
