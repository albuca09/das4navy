# -*- coding: utf-8 -*-
"""
Corrige a cena DAS4NAVY:
- mantém AIS completo do JEANOAH;
- cria AIS segmentado na janela DAS/XAI;
- seleciona automaticamente a melhor trajetória DAS estimada;
- substitui a trajetória DAS bruta por apenas o trecho estimado válido;
- recria frames de animação com navio AIS + estimativa DAS sincronizados.
"""

from pathlib import Path
import json
import math
import re
import numpy as np
import pandas as pd


APP = Path(r"C:\Users\Luis\Desktop\das4navy")

SCENE = APP / "public" / "data" / "das4navy_scene_web_lite.json"

DAS_ESTIMATE_CANDIDATES = [
    Path(r"D:\DAS\_ship_position_estimation_from_das_noais\run_20260613_222353\tables\estimated_ship_track_offcable_das_only.csv"),
]

EVENT_START = pd.to_datetime("2021-11-01T17:48:15Z", utc=True)
EVENT_END   = pd.to_datetime("2021-11-01T18:16:04Z", utc=True)

MAX_FRAME_STEP_SEC = 3.0


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def find_col(df, names):
    cols = list(df.columns)
    nmap = {norm(c): c for c in cols}

    for name in names:
        if norm(name) in nmap:
            return nmap[norm(name)]

    for c in cols:
        nc = norm(c)
        for name in names:
            if norm(name) in nc:
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

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 6371.0088 * 2.0 * np.arcsin(np.sqrt(a))


def valid_latlon(df, lat_col, lon_col):
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    lon = pd.to_numeric(df[lon_col], errors="coerce")
    return lat.between(-90, 90) & lon.between(-180, 180)


def records(df):
    return json.loads(df.replace({np.nan: None}).to_json(orient="records"))


def resolve_das_csv():
    for p in DAS_ESTIMATE_CANDIDATES:
        if p.exists():
            return p

    root = Path(r"D:\DAS\_ship_position_estimation_from_das_noais")
    found = list(root.rglob("estimated_ship_track_offcable_das_only.csv")) if root.exists() else []

    if found:
        return max(found, key=lambda x: x.stat().st_mtime)

    raise FileNotFoundError("Não encontrei estimated_ship_track_offcable_das_only.csv")


def build_ais_event_track(scene):
    ais = pd.DataFrame(scene.get("ais", []))

    if ais.empty:
        raise RuntimeError("A cena não contém AIS.")

    ais["time_utc"] = parse_time(ais["time_utc"])
    ais["lat"] = pd.to_numeric(ais["lat"], errors="coerce")
    ais["lon"] = pd.to_numeric(ais["lon"], errors="coerce")

    ais = ais[
        ais["time_utc"].notna()
        & ais["lat"].between(-90, 90)
        & ais["lon"].between(-180, 180)
    ].copy()

    ais = ais.sort_values("time_utc").drop_duplicates("time_utc")

    # Trecho do evento. Se houver poucos pontos AIS exatamente na janela,
    # mantém os pontos próximos para permitir interpolação.
    pad = pd.Timedelta(minutes=20)
    near = ais[(ais["time_utc"] >= EVENT_START - pad) & (ais["time_utc"] <= EVENT_END + pad)].copy()

    if near.empty:
        raise RuntimeError("Não há AIS próximo da janela DAS/XAI.")

    # Interpola AIS a cada 3 s na janela do evento.
    frame_times = pd.date_range(EVENT_START, EVENT_END, freq=f"{int(MAX_FRAME_STEP_SEC)}s", tz="UTC")

    src_t = near["time_utc"].astype("int64").to_numpy(dtype=float)
    dst_t = frame_times.astype("int64").to_numpy(dtype=float)

    lat_interp = np.interp(dst_t, src_t, near["lat"].to_numpy(dtype=float))
    lon_interp = np.interp(dst_t, src_t, near["lon"].to_numpy(dtype=float))

    ais_event = pd.DataFrame({
        "time_utc": frame_times,
        "lat": lat_interp,
        "lon": lon_interp,
    })

    for col in ["sog", "cog", "heading"]:
        if col in near.columns:
            near[col] = pd.to_numeric(near[col], errors="coerce")
            vals = near[col].to_numpy(dtype=float)
            ok = np.isfinite(vals)

            if ok.sum() >= 2:
                ais_event[col] = np.interp(dst_t, src_t[ok], vals[ok])
            else:
                ais_event[col] = np.nan
        else:
            ais_event[col] = np.nan

    return ais, ais_event


def candidate_latlon_pairs(df):
    cols = list(df.columns)

    lat_cols = [c for c in cols if "lat" in norm(c)]
    lon_cols = [c for c in cols if ("lon" in norm(c) or "lng" in norm(c))]

    pairs = []

    for lat_col in lat_cols:
        nlat = norm(lat_col)

        # Tenta par por nomes parecidos.
        best = None
        best_score = -1

        for lon_col in lon_cols:
            nlon = norm(lon_col)
            base_lat = nlat.replace("latitude", "").replace("lat", "")
            base_lon = nlon.replace("longitude", "").replace("lon", "").replace("lng", "")
            score = len(set(base_lat) & set(base_lon))

            if score > best_score:
                best_score = score
                best = lon_col

        if best is not None:
            pairs.append((lat_col, best))

    # Pares explícitos comuns.
    explicit = [
        ("estimated_lat", "estimated_lon"),
        ("est_lat", "est_lon"),
        ("lat_est", "lon_est"),
        ("candidate_lat", "candidate_lon"),
        ("ship_lat_est", "ship_lon_est"),
        ("lat", "lon"),
    ]

    for a, b in explicit:
        ca = find_col(df, [a])
        cb = find_col(df, [b])
        if ca is not None and cb is not None:
            pairs.append((ca, cb))

    # Remove duplicatas.
    unique = []
    seen = set()
    for p in pairs:
        if p not in seen:
            unique.append(p)
            seen.add(p)

    return unique


def select_best_das_estimate(das_csv, ais_event):
    df = pd.read_csv(das_csv, low_memory=False)

    time_col = find_col(df, [
        "time_utc", "timestamp", "datetime", "utc",
        "ais_time_utc", "estimated_time_utc", "closest_time_utc"
    ])

    if time_col is None:
        raise RuntimeError(f"Não encontrei coluna de tempo no CSV DAS. Colunas: {list(df.columns)}")

    df["_time"] = parse_time(df[time_col])
    df = df[df["_time"].notna()].copy()
    df = df[(df["_time"] >= EVENT_START) & (df["_time"] <= EVENT_END)].copy()

    if df.empty:
        raise RuntimeError("CSV DAS não tem pontos dentro da janela do evento.")

    pairs = candidate_latlon_pairs(df)

    if not pairs:
        raise RuntimeError(f"Não encontrei pares lat/lon no CSV DAS. Colunas: {list(df.columns)}")

    possible_group_cols = [
        c for c in df.columns
        if any(tok in norm(c) for tok in ["side", "branch", "candidate", "normal", "solution"])
    ]

    ais_cmp = ais_event[["time_utc", "lat", "lon"]].copy()
    ais_cmp = ais_cmp.rename(columns={
        "time_utc": "_ais_time",
        "lat": "_ais_lat",
        "lon": "_ais_lon",
    })
    ais_cmp = ais_cmp.sort_values("_ais_time")

    trials = []

    for lat_col, lon_col in pairs:
        valid = valid_latlon(df, lat_col, lon_col)
        sub0 = df.loc[valid].copy()

        if sub0.empty:
            continue

        group_sets = [(None, None, sub0)]

        for gc in possible_group_cols:
            for gv, gdf in sub0.groupby(gc, dropna=False):
                if len(gdf) >= 3:
                    group_sets.append((gc, gv, gdf.copy()))

        for group_col, group_value, sub in group_sets:
            sub = sub.sort_values("_time").copy()
            sub["_lat"] = pd.to_numeric(sub[lat_col], errors="coerce")
            sub["_lon"] = pd.to_numeric(sub[lon_col], errors="coerce")

            merged = pd.merge_asof(
                sub,
                ais_cmp,
                left_on="_time",
                right_on="_ais_time",
                direction="nearest",
                tolerance=pd.Timedelta(seconds=90)
            )

            merged = merged[merged["_ais_lat"].notna()].copy()

            if len(merged) < 3:
                continue

            dist = haversine_km(
                merged["_lat"].to_numpy(),
                merged["_lon"].to_numpy(),
                merged["_ais_lat"].to_numpy(),
                merged["_ais_lon"].to_numpy()
            )

            med = float(np.nanmedian(dist))
            mean = float(np.nanmean(dist))
            p90 = float(np.nanpercentile(dist, 90))

            trials.append({
                "lat_col": lat_col,
                "lon_col": lon_col,
                "group_col": group_col,
                "group_value": group_value,
                "n": len(merged),
                "median_km": med,
                "mean_km": mean,
                "p90_km": p90,
                "data": merged,
            })

    if not trials:
        raise RuntimeError("Nenhuma trajetória DAS candidata pôde ser comparada com o AIS.")

    trials = sorted(trials, key=lambda x: (x["median_km"], x["mean_km"], -x["n"]))
    best = trials[0]

    selected = best["data"].copy()
    selected = selected.sort_values("_time").reset_index(drop=True)

    out = pd.DataFrame()
    out["time_utc"] = selected["_time"]
    out["lat"] = selected["_lat"]
    out["lon"] = selected["_lon"]

    for target, names in {
        "channel": ["channel", "estimated_channel", "das_channel", "nearest_cable_channel"],
        "cable": ["cable", "cable_id", "side", "mapped_cable"],
        "score": ["score", "confidence", "z_score", "probability", "perturbation_score"],
        "distance_to_ais_km": ["distance_to_ais_km"],
    }.items():
        col = find_col(selected, names)
        if col is not None:
            out[target] = selected[col]
        else:
            out[target] = np.nan

    # Distância ao AIS usada para validação visual.
    out["distance_to_ais_km"] = haversine_km(
        selected["_lat"].to_numpy(),
        selected["_lon"].to_numpy(),
        selected["_ais_lat"].to_numpy(),
        selected["_ais_lon"].to_numpy()
    )

    out = out[
        out["lat"].between(-90, 90)
        & out["lon"].between(-180, 180)
    ].copy()

    # Mantém apenas trecho consistente. Remove saltos absurdos se existirem.
    if len(out) >= 4:
        dstep = haversine_km(
            out["lat"].iloc[:-1].to_numpy(),
            out["lon"].iloc[:-1].to_numpy(),
            out["lat"].iloc[1:].to_numpy(),
            out["lon"].iloc[1:].to_numpy(),
        )
        keep = np.r_[True, dstep < max(2.0, np.nanpercentile(dstep, 95) * 3.0)]
        out = out.loc[keep].copy()

    out["time_utc"] = pd.to_datetime(out["time_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    report = {
        "das_csv": str(das_csv),
        "selected_lat_col": best["lat_col"],
        "selected_lon_col": best["lon_col"],
        "selected_group_col": best["group_col"],
        "selected_group_value": str(best["group_value"]),
        "n_points": int(len(out)),
        "median_distance_to_ais_km": best["median_km"],
        "mean_distance_to_ais_km": best["mean_km"],
        "p90_distance_to_ais_km": best["p90_km"],
        "all_trials": [
            {
                "lat_col": t["lat_col"],
                "lon_col": t["lon_col"],
                "group_col": t["group_col"],
                "group_value": str(t["group_value"]),
                "n": int(t["n"]),
                "median_km": t["median_km"],
                "mean_km": t["mean_km"],
                "p90_km": t["p90_km"],
            }
            for t in trials[:20]
        ]
    }

    return out, report


def interpolate_das_for_frames(das_seg, frame_times):
    d = das_seg.copy()
    d["time_utc"] = parse_time(d["time_utc"])
    d = d[d["time_utc"].notna()].sort_values("time_utc").copy()

    if d.empty:
        return [None] * len(frame_times)

    src_t = d["time_utc"].astype("int64").to_numpy(dtype=float)
    dst_t = frame_times.astype("int64").to_numpy(dtype=float)

    lat = np.interp(dst_t, src_t, pd.to_numeric(d["lat"], errors="coerce").to_numpy(dtype=float))
    lon = np.interp(dst_t, src_t, pd.to_numeric(d["lon"], errors="coerce").to_numpy(dtype=float))

    ch_col = "channel" if "channel" in d.columns else None

    out = []

    for i, t in enumerate(frame_times):
        # Só usa DAS dentro do intervalo real da estimativa.
        if t < d["time_utc"].min() or t > d["time_utc"].max():
            out.append(None)
            continue

        nearest_idx = int(np.argmin(np.abs(src_t - dst_t[i])))

        item = {
            "lat": float(lat[i]),
            "lon": float(lon[i]),
        }

        if ch_col:
            try:
                item["channel"] = float(pd.to_numeric(d[ch_col], errors="coerce").iloc[nearest_idx])
            except Exception:
                item["channel"] = None

        for col in ["cable", "score", "distance_to_ais_km"]:
            if col in d.columns:
                val = d[col].iloc[nearest_idx]
                if isinstance(val, (int, float, np.floating)):
                    item[col] = None if not np.isfinite(float(val)) else float(val)
                else:
                    item[col] = None if pd.isna(val) else str(val)

        out.append(item)

    return out


def main():
    if not SCENE.exists():
        raise FileNotFoundError(SCENE)

    scene = json.loads(SCENE.read_text(encoding="utf-8"))

    ais_full, ais_event = build_ais_event_track(scene)

    das_csv = resolve_das_csv()
    das_seg, report = select_best_das_estimate(das_csv, ais_event)

    frame_times = pd.date_range(EVENT_START, EVENT_END, freq=f"{int(MAX_FRAME_STEP_SEC)}s", tz="UTC")

    # Interpola AIS no frame.
    ais_event = ais_event.set_index("time_utc").reindex(frame_times, method=None)
    ais_event = ais_event.interpolate(method="time").reset_index().rename(columns={"index": "time_utc"})

    das_per_frame = interpolate_das_for_frames(das_seg, frame_times)

    frames = []

    for i, t in enumerate(frame_times):
        ar = ais_event.iloc[i]

        frames.append({
            "time_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ais": {
                "lat": None if pd.isna(ar["lat"]) else float(ar["lat"]),
                "lon": None if pd.isna(ar["lon"]) else float(ar["lon"]),
                "sog": None if pd.isna(ar.get("sog", np.nan)) else float(ar.get("sog", np.nan)),
                "cog": None if pd.isna(ar.get("cog", np.nan)) else float(ar.get("cog", np.nan)),
                "heading": None if pd.isna(ar.get("heading", np.nan)) else float(ar.get("heading", np.nan)),
            },
            "das": das_per_frame[i],
        })

    ais_event_out = ais_event.copy()
    ais_event_out["time_utc"] = pd.to_datetime(ais_event_out["time_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Mantém o AIS completo em scene["ais"].
    # Substitui a estimativa bruta por somente o trecho selecionado.
    scene["ais_event_segment"] = records(ais_event_out)
    scene["das_estimate_segment"] = records(das_seg)
    scene["das_estimate"] = records(das_seg)
    scene["frames"] = frames

    if "metadata" not in scene:
        scene["metadata"] = {}

    scene["metadata"]["das_estimate_selection"] = report
    scene["metadata"]["n_das_estimate_segment_points"] = len(das_seg)
    scene["metadata"]["n_ais_event_segment_points"] = len(ais_event_out)
    scene["metadata"]["animation_uses_das_segment_only"] = True

    SCENE.write_text(
        json.dumps(scene, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8"
    )

    print("=" * 100)
    print("OK — trajetória DAS corrigida e animação AIS/DAS sincronizada")
    print("=" * 100)
    print("Arquivo:", SCENE)
    print("CSV DAS:", das_csv)
    print("Pontos DAS selecionados:", len(das_seg))
    print("Frames:", len(frames))
    print("Par lat/lon escolhido:", report["selected_lat_col"], "/", report["selected_lon_col"])
    print("Grupo escolhido:", report["selected_group_col"], "=", report["selected_group_value"])
    print("Distância mediana DAS x AIS [km]:", report["median_distance_to_ais_km"])
    print("Distância média DAS x AIS [km]:", report["mean_distance_to_ais_km"])


if __name__ == "__main__":
    main()
