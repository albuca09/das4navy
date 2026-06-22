
from pathlib import Path
import json
import re
import math
import numpy as np
import pandas as pd


# =============================================================================
# CONFIGURAÇÃO PRINCIPAL
# =============================================================================

APP_ROOT = Path(r"C:\Users\Luis\Desktop\das4navy")
OUT_JSON = APP_ROOT / "public" / "data" / "das4navy_scene.json"

# Ajuste estes diretórios conforme sua máquina.
DAS_ROOT = Path(r"D:\DAS")
AIS_ROOT = Path(r"D:\AIS_2021_EXP")

# Navio de interesse
SHIP_NAME = "JEANOAH"
SHIP_MMSI = 366959080

# Janela do evento JEANOAH
START_TIME_UTC = "2021-11-01T17:48:15Z"
END_TIME_UTC = "2021-11-01T18:16:04Z"

# Arquivos de geometria dos cabos.
# O código também tenta localizar automaticamente caso o caminho direto não exista.
CABLE_FILES = {
    "south": DAS_ROOT / "south_DAS_latlondepth.txt",
    "north": DAS_ROOT / "north_DAS_latlondepth.txt",
}

# AIS do dia
AIS_CSV_CANDIDATES = [
    AIS_ROOT / "EXT" / "AIS_2021_11_01" / "AIS_2021_11_01.csv",
    AIS_ROOT / "AIS_2021_11_01.csv",
]

# Estimativa DAS sem AIS.
# Caso esse caminho não exista, o script procura o CSV mais recente.
DAS_ESTIMATE_CSV_CANDIDATES = [
    DAS_ROOT / "_ship_position_estimation_from_das_noais" / "run_20260613_222353" / "tables" / "estimated_ship_track_offcable_das_only.csv",
]

# Eventos XAI opcionais gerados pelo script de perturbação.
# Caso não exista, a camada XAI fica vazia.
XAI_EVENTS_CSV_CANDIDATES = [
    DAS_ROOT / "_das_xai_spectrogram_perturbations",
]


# =============================================================================
# UTILITÁRIOS
# =============================================================================

def norm_col(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())


def find_col(df: pd.DataFrame, candidates):
    lookup = {norm_col(c): c for c in df.columns}
    cand_norm = [norm_col(c) for c in candidates]

    for cn in cand_norm:
        if cn in lookup:
            return lookup[cn]

    for original in df.columns:
        no = norm_col(original)
        for cn in cand_norm:
            if cn in no:
                return original

    return None


def to_float_series(s):
    return pd.to_numeric(s, errors="coerce")


def clean_records(df: pd.DataFrame):
    return json.loads(df.replace({np.nan: None}).to_json(orient="records"))


def latest_file(root: Path, pattern: str):
    if not root.exists():
        return None
    files = list(root.rglob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def resolve_first_existing(candidates):
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def parse_time_utc(series):
    return pd.to_datetime(series, utc=True, errors="coerce")


def safe_float(x):
    try:
        if x is None:
            return None
        y = float(x)
        if math.isnan(y) or math.isinf(y):
            return None
        return y
    except Exception:
        return None


# =============================================================================
# CABOS DAS
# =============================================================================

def auto_find_cable_file(cable_id: str):
    direct = CABLE_FILES.get(cable_id)
    if direct is not None and direct.exists():
        return direct

    patterns = [
        f"*{cable_id}*latlondepth*.txt",
        f"*{cable_id}*lat*lon*depth*.txt",
        f"*{cable_id}*.txt",
    ]

    for pat in patterns:
        found = latest_file(DAS_ROOT, pat)
        if found is not None:
            return found

    return None


def read_mixed_table(path: Path):
    # Primeiro tenta com cabeçalho.
    for sep in [r"\s+", ",", ";", "\t"]:
        try:
            df = pd.read_csv(path, sep=sep, engine="python")
            if df.shape[1] >= 2:
                return df
        except Exception:
            pass

    # Depois tenta sem cabeçalho.
    for sep in [r"\s+", ",", ";", "\t"]:
        try:
            df = pd.read_csv(path, sep=sep, engine="python", header=None)
            if df.shape[1] >= 2:
                return df
        except Exception:
            pass

    raise RuntimeError(f"Não foi possível ler tabela: {path}")


def read_cable_geometry(cable_id: str, path: Path):
    df = pd.read_csv(path, sep=r"\s+", engine="python", header=None).copy()

    # Caso sem cabeçalho: colunas numéricas 0,1,2,3...
    headerless = all(isinstance(c, int) for c in df.columns)

    if headerless:
        ncols = df.shape[1]

        if ncols >= 4:
            c0 = pd.to_numeric(df.iloc[:, 0], errors="coerce")
            # Heurística: canal geralmente é inteiro e maior que 100.
            if c0.dropna().median() > 100:
                df = df.rename(columns={
                    df.columns[0]: "channel",
                    df.columns[1]: "lat",
                    df.columns[2]: "lon",
                    df.columns[3]: "depth_m",
                })
            else:
                df = df.rename(columns={
                    df.columns[0]: "lat",
                    df.columns[1]: "lon",
                    df.columns[2]: "depth_m",
                    df.columns[3]: "channel",
                })

        elif ncols == 3:
            df = df.rename(columns={
                df.columns[0]: "lat",
                df.columns[1]: "lon",
                df.columns[2]: "depth_m",
            })
            df["channel"] = np.arange(len(df), dtype=int)

        elif ncols == 2:
            df = df.rename(columns={
                df.columns[0]: "lat",
                df.columns[1]: "lon",
            })
            df["depth_m"] = np.nan
            df["channel"] = np.arange(len(df), dtype=int)

    lat_col = find_col(df, ["lat", "latitude"])
    lon_col = find_col(df, ["lon", "lng", "longitude"])
    depth_col = find_col(df, ["depth", "depth_m", "z", "altitude"])
    channel_col = find_col(df, ["channel", "chan", "ch", "index", "idx"])

    if lat_col is None or lon_col is None:
        raise RuntimeError(
            f"Não consegui identificar colunas de latitude/longitude em {path}. "
            f"Colunas encontradas: {list(df.columns)}"
        )

    out = pd.DataFrame()
    out["channel"] = (
        pd.to_numeric(df[channel_col], errors="coerce")
        if channel_col is not None
        else np.arange(len(df), dtype=int)
    )

    out["lat"] = pd.to_numeric(df[lat_col], errors="coerce")
    out["lon"] = pd.to_numeric(df[lon_col], errors="coerce")
    out["depth_m"] = (
        pd.to_numeric(df[depth_col], errors="coerce")
        if depth_col is not None
        else np.nan
    )

    out = out.dropna(subset=["lat", "lon"]).copy()
    out["channel"] = out["channel"].fillna(method="ffill").fillna(0).astype(int)
    out["cable"] = cable_id

    # Remove pontos impossíveis.
    out = out[
        out["lat"].between(-90, 90) &
        out["lon"].between(-180, 180)
    ].copy()

    out = out.sort_values("channel").reset_index(drop=True)
    return out


def load_cables():
    cables = []

    for cable_id in ["south", "north"]:
        path = auto_find_cable_file(cable_id)

        if path is None:
            print(f"[WARNING] Cabo {cable_id} não encontrado.")
            continue

        print(f"[CABO] {cable_id}: {path}")
        df = read_cable_geometry(cable_id, path)

        cables.append({
            "id": cable_id,
            "source_file": str(path),
            "n_points": int(len(df)),
            "points": clean_records(df[["channel", "lat", "lon", "depth_m"]]),
        })

    return cables


# =============================================================================
# AIS DO JEANOAH
# =============================================================================

def resolve_ais_csv():
    p = resolve_first_existing(AIS_CSV_CANDIDATES)
    if p is not None:
        return p

    found = latest_file(AIS_ROOT, "AIS_2021_11_01.csv")
    if found is not None:
        return found

    found = latest_file(AIS_ROOT, "*.csv")
    return found


def load_ais_jeanoah():
    path = resolve_ais_csv()
    if path is None:
        print("[WARNING] Arquivo AIS não encontrado.")
        return [], None

    print(f"[AIS] {path}")

    start = pd.to_datetime(START_TIME_UTC, utc=True)
    end = pd.to_datetime(END_TIME_UTC, utc=True)

    selected = []

    for chunk in pd.read_csv(path, chunksize=200_000, low_memory=False):
        mmsi_col = find_col(chunk, ["MMSI", "mmsi"])
        name_col = find_col(chunk, ["VesselName", "BaseStation", "ship_name", "name", "vessel"])
        time_col = find_col(chunk, ["BaseDateTime", "time_utc", "timestamp", "datetime", "date_time", "UTC"])
        lat_col = find_col(chunk, ["LAT", "lat", "latitude"])
        lon_col = find_col(chunk, ["LON", "lon", "lng", "longitude"])
        sog_col = find_col(chunk, ["SOG", "speed", "speed_over_ground"])
        cog_col = find_col(chunk, ["COG", "course", "course_over_ground"])
        heading_col = find_col(chunk, ["Heading", "heading"])

        if time_col is None or lat_col is None or lon_col is None:
            continue

        mask = pd.Series(False, index=chunk.index)

        if mmsi_col is not None:
            mask = mask | (pd.to_numeric(chunk[mmsi_col], errors="coerce") == SHIP_MMSI)

        if name_col is not None:
            mask = mask | chunk[name_col].astype(str).str.upper().str.contains(SHIP_NAME, na=False)

        sub = chunk.loc[mask].copy()

        if sub.empty:
            continue

        sub["time_utc"] = parse_time_utc(sub[time_col])
        sub["lat"] = pd.to_numeric(sub[lat_col], errors="coerce")
        sub["lon"] = pd.to_numeric(sub[lon_col], errors="coerce")

        sub = sub[
            sub["time_utc"].notna() &
            sub["lat"].between(-90, 90) &
            sub["lon"].between(-180, 180)
        ].copy()

        # AIS completo do JEANOAH no arquivo do dia; sem filtro pela janela do evento`r`n        # sub = sub[(sub["time_utc"] >= start) & (sub["time_utc"] <= end)].copy()

        if sub.empty:
            continue

        sub["sog"] = pd.to_numeric(sub[sog_col], errors="coerce") if sog_col else np.nan
        sub["cog"] = pd.to_numeric(sub[cog_col], errors="coerce") if cog_col else np.nan
        sub["heading"] = pd.to_numeric(sub[heading_col], errors="coerce") if heading_col else np.nan
        sub["mmsi"] = SHIP_MMSI
        sub["ship_name"] = SHIP_NAME

        selected.append(sub[["time_utc", "lat", "lon", "sog", "cog", "heading", "mmsi", "ship_name"]])

    if not selected:
        print("[WARNING] Nenhum ponto AIS do JEANOAH encontrado na janela.")
        return [], str(path)

    ais = pd.concat(selected, ignore_index=True)
    ais = ais.drop_duplicates(subset=["time_utc", "lat", "lon"])
    ais = ais.sort_values("time_utc").reset_index(drop=True)
    ais["time_utc"] = ais["time_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return clean_records(ais), str(path)


# =============================================================================
# ESTIMATIVA DAS
# =============================================================================

def resolve_das_estimate_csv():
    p = resolve_first_existing(DAS_ESTIMATE_CSV_CANDIDATES)
    if p is not None:
        return p

    root = DAS_ROOT / "_ship_position_estimation_from_das_noais"
    found = latest_file(root, "estimated_ship_track_offcable_das_only.csv")
    if found is not None:
        return found

    found = latest_file(DAS_ROOT, "*estimated*track*.csv")
    return found


def load_das_estimate():
    path = resolve_das_estimate_csv()

    if path is None:
        print("[WARNING] CSV de estimativa DAS não encontrado.")
        return [], None

    print(f"[DAS ESTIMATE] {path}")

    df = pd.read_csv(path, low_memory=False)

    time_col = find_col(df, [
        "time_utc", "timestamp", "datetime", "utc",
        "ais_time_utc", "estimated_time_utc"
    ])

    lat_col = find_col(df, [
        "estimated_lat", "est_lat", "lat_est", "candidate_lat",
        "ship_lat_est", "lat"
    ])

    lon_col = find_col(df, [
        "estimated_lon", "est_lon", "lon_est", "candidate_lon",
        "ship_lon_est", "lon", "lng"
    ])

    channel_col = find_col(df, ["channel", "estimated_channel", "das_channel", "channel_est"])
    cable_col = find_col(df, ["cable", "cable_id", "side"])
    score_col = find_col(df, ["score", "confidence", "z_score", "energy", "probability"])
    error_col = find_col(df, ["error_m", "error_km", "ship_position_error_km"])

    if time_col is None or lat_col is None or lon_col is None:
        raise RuntimeError(
            "O arquivo de estimativa DAS foi encontrado, mas não consegui identificar "
            "colunas de tempo, latitude e longitude.\n"
            f"Arquivo: {path}\n"
            f"Colunas: {list(df.columns)}"
        )

    out = pd.DataFrame()
    out["time_utc"] = parse_time_utc(df[time_col])
    out["lat"] = pd.to_numeric(df[lat_col], errors="coerce")
    out["lon"] = pd.to_numeric(df[lon_col], errors="coerce")

    out["channel"] = pd.to_numeric(df[channel_col], errors="coerce") if channel_col else np.nan
    out["cable"] = df[cable_col].astype(str) if cable_col else ""
    out["score"] = pd.to_numeric(df[score_col], errors="coerce") if score_col else np.nan
    out["error"] = pd.to_numeric(df[error_col], errors="coerce") if error_col else np.nan

    start = pd.to_datetime(START_TIME_UTC, utc=True)
    end = pd.to_datetime(END_TIME_UTC, utc=True)

    out = out[
        out["time_utc"].notna() &
        out["lat"].between(-90, 90) &
        out["lon"].between(-180, 180)
    ].copy()

    out = out[(out["time_utc"] >= start) & (out["time_utc"] <= end)].copy()
    out = out.sort_values("time_utc").reset_index(drop=True)
    out["time_utc"] = out["time_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return clean_records(out), str(path)


# =============================================================================
# EVENTOS XAI OPCIONAIS
# =============================================================================

def resolve_xai_events_csv():
    for p in XAI_EVENTS_CSV_CANDIDATES:
        if p.exists() and p.is_file() and p.name == "weak_activated_events.csv":
            return p

        if p.exists() and p.is_dir():
            found = latest_file(p, "weak_activated_events.csv")
            if found is not None:
                return found

    return None


def build_channel_lookup(cables):
    rows = []

    for cable in cables:
        cable_id = cable["id"]
        for pt in cable["points"]:
            rows.append({
                "cable": cable_id,
                "channel": int(pt["channel"]),
                "lat": float(pt["lat"]),
                "lon": float(pt["lon"]),
                "depth_m": safe_float(pt.get("depth_m")),
            })

    if not rows:
        return pd.DataFrame(columns=["cable", "channel", "lat", "lon", "depth_m"])

    return pd.DataFrame(rows)


def load_xai_events(cables):
    path = resolve_xai_events_csv()

    if path is None:
        print("[INFO] Eventos XAI não encontrados. Camada XAI ficará vazia.")
        return [], None

    print(f"[XAI EVENTS] {path}")

    df = pd.read_csv(path, low_memory=False)

    time_col = find_col(df, ["time_utc", "timestamp", "datetime", "utc"])
    channel_col = find_col(df, ["channel", "ch", "das_channel"])
    score_col = find_col(df, ["z_score", "score", "probability", "confidence"])

    if time_col is None or channel_col is None:
        print("[WARNING] Eventos XAI sem colunas de tempo/canal.")
        return [], str(path)

    out = pd.DataFrame()
    out["time_utc"] = parse_time_utc(df[time_col])
    out["channel"] = pd.to_numeric(df[channel_col], errors="coerce")
    out["score"] = pd.to_numeric(df[score_col], errors="coerce") if score_col else np.nan

    out = out.dropna(subset=["time_utc", "channel"]).copy()
    out["channel"] = out["channel"].astype(int)

    lookup = build_channel_lookup(cables)

    if not lookup.empty:
        # Associa cada evento ao ponto de cabo mais próximo em número de canal.
        mapped = []

        for _, r in out.iterrows():
            ch = int(r["channel"])
            j = (lookup["channel"] - ch).abs().idxmin()
            ref = lookup.loc[j]

            rr = dict(r)
            rr["mapped_cable"] = ref["cable"]
            rr["mapped_channel"] = int(ref["channel"])
            rr["lat"] = float(ref["lat"])
            rr["lon"] = float(ref["lon"])
            rr["depth_m"] = safe_float(ref["depth_m"])
            mapped.append(rr)

        out = pd.DataFrame(mapped)
    else:
        out["lat"] = np.nan
        out["lon"] = np.nan
        out["mapped_cable"] = ""
        out["mapped_channel"] = np.nan
        out["depth_m"] = np.nan

    out = out[out["lat"].notna() & out["lon"].notna()].copy()
    out = out.sort_values("time_utc").reset_index(drop=True)
    out["time_utc"] = pd.to_datetime(out["time_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return clean_records(out), str(path)


# =============================================================================
# FRAMES PARA ANIMAÇÃO
# =============================================================================

def nearest_row_by_time(df: pd.DataFrame, t: pd.Timestamp):
    if df.empty:
        return None

    times = pd.to_datetime(df["time_utc"], utc=True, errors="coerce")
    idx = (times - t).abs().idxmin()

    if pd.isna(times.loc[idx]):
        return None

    return df.loc[idx]


def build_animation_frames(ais_records, das_records):
    ais_df = pd.DataFrame(ais_records)
    das_df = pd.DataFrame(das_records)

    all_times = []

    if not ais_df.empty:
        all_times.extend(pd.to_datetime(ais_df["time_utc"], utc=True, errors="coerce").dropna().tolist())

    if not das_df.empty:
        all_times.extend(pd.to_datetime(das_df["time_utc"], utc=True, errors="coerce").dropna().tolist())

    if not all_times:
        return []

    all_times = sorted(set(all_times))

    frames = []

    for t in all_times:
        frame = {
            "time_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ais": None,
            "das": None,
        }

        ar = nearest_row_by_time(ais_df, t) if not ais_df.empty else None
        dr = nearest_row_by_time(das_df, t) if not das_df.empty else None

        if ar is not None:
            frame["ais"] = {
                "lat": safe_float(ar.get("lat")),
                "lon": safe_float(ar.get("lon")),
                "sog": safe_float(ar.get("sog")),
                "cog": safe_float(ar.get("cog")),
                "heading": safe_float(ar.get("heading")),
            }

        if dr is not None:
            frame["das"] = {
                "lat": safe_float(dr.get("lat")),
                "lon": safe_float(dr.get("lon")),
                "channel": safe_float(dr.get("channel")),
                "score": safe_float(dr.get("score")),
                "cable": str(dr.get("cable", "")),
                "error": safe_float(dr.get("error")),
            }

        frames.append(frame)

    return frames


# =============================================================================
# MAIN
# =============================================================================

def main():
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 100)
    print("EXPORTANDO CENA CARTOGRÁFICA DAS4NAVY")
    print("=" * 100)

    cables = load_cables()
    ais_records, ais_source = load_ais_jeanoah()
    das_records, das_source = load_das_estimate()
    xai_records, xai_source = load_xai_events(cables)

    frames = build_animation_frames(ais_records, das_records)

    scene = {
        "metadata": {
            "ship_name": SHIP_NAME,
            "ship_mmsi": SHIP_MMSI,
            "start_time_utc": START_TIME_UTC,
            "end_time_utc": END_TIME_UTC,
            "ais_source": ais_source,
            "das_estimate_source": das_source,
            "xai_events_source": xai_source,
            "n_cables": len(cables),
            "n_ais_points": len(ais_records),
            "n_das_estimate_points": len(das_records),
            "n_xai_events": len(xai_records),
            "n_animation_frames": len(frames),
        },
        "cables": cables,
        "ais": ais_records,
        "das_estimate": das_records,
        "xai_events": xai_records,
        "frames": frames,
    }

    OUT_JSON.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 100)
    print("OK")
    print("=" * 100)
    print(f"Arquivo gerado: {OUT_JSON}")
    print(f"Cabos: {len(cables)}")
    print(f"AIS JEANOAH: {len(ais_records)} pontos")
    print(f"Estimativa DAS: {len(das_records)} pontos")
    print(f"Eventos XAI: {len(xai_records)}")
    print(f"Frames de animação: {len(frames)}")


if __name__ == "__main__":
    main()




