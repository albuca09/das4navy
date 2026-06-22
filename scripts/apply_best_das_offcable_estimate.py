# -*- coding: utf-8 -*-
"""
Aplica no DAS4NAVY a melhor estimativa off-cable encontrada no relatório:

  _debug_das_candidate_tracks.csv

Usa somente candidatos com:
  est_ship_lat / est_ship_lon
  canais sobrepondo 13619--14819
  menor distância mediana em relação ao AIS somente para diagnóstico

Depois atualiza:
  public/data/das4navy_scene_web_lite.json
"""

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd


APP = Path(r"C:\Users\Luis\Desktop\das4navy")

REPORT = APP / "_debug_das_candidate_tracks.csv"
SCENE = APP / "public" / "data" / "das4navy_scene_web_lite.json"

EVENT_START = pd.to_datetime("2021-11-01T17:48:15Z", utc=True)
EVENT_END   = pd.to_datetime("2021-11-01T18:16:04Z", utc=True)

CHANNEL_MIN = 13619
CHANNEL_MAX = 14819


def clean(x):
    if x is None:
        return None
    if isinstance(x, (float, np.floating)):
        if math.isnan(x) or math.isinf(x):
            return None
        return float(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if pd.isna(x):
        return None
    return x


def records(df):
    return json.loads(df.replace({np.nan: None}).to_json(orient="records"))


def find_col(df, names):
    low = {c.lower(): c for c in df.columns}
    for name in names:
        if name.lower() in low:
            return low[name.lower()]
    for c in df.columns:
        cl = c.lower()
        for name in names:
            if name.lower() in cl:
                return c
    return None


def parse_time(x):
    return pd.to_datetime(x, utc=True, errors="coerce")


def haversine_km(lat1, lon1, lat2, lon2):
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lon1 = np.radians(np.asarray(lon1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    lon2 = np.radians(np.asarray(lon2, dtype=float))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 6371.0088 * 2.0 * np.arcsin(np.sqrt(a))


def interpolate_ais_from_scene(scene, frame_times):
    ais = pd.DataFrame(scene.get("ais", []))

    if ais.empty:
        return pd.DataFrame({
            "time_utc": frame_times,
            "lat": np.nan,
            "lon": np.nan,
            "sog": np.nan,
            "cog": np.nan,
            "heading": np.nan,
        })

    ais["time_utc"] = parse_time(ais["time_utc"])
    ais["lat"] = pd.to_numeric(ais["lat"], errors="coerce")
    ais["lon"] = pd.to_numeric(ais["lon"], errors="coerce")

    ais = ais[
        ais["time_utc"].notna()
        & ais["lat"].between(-90, 90)
        & ais["lon"].between(-180, 180)
    ].copy()

    ais = ais.sort_values("time_utc").drop_duplicates("time_utc")

    if len(ais) < 2:
        return pd.DataFrame({
            "time_utc": frame_times,
            "lat": np.nan,
            "lon": np.nan,
            "sog": np.nan,
            "cog": np.nan,
            "heading": np.nan,
        })

    src_t = ais["time_utc"].astype("int64").to_numpy(dtype=float)
    dst_t = frame_times.astype("int64").to_numpy(dtype=float)

    out = pd.DataFrame()
    out["time_utc"] = frame_times
    out["lat"] = np.interp(dst_t, src_t, ais["lat"].to_numpy(dtype=float))
    out["lon"] = np.interp(dst_t, src_t, ais["lon"].to_numpy(dtype=float))

    for col in ["sog", "cog", "heading"]:
        if col in ais.columns:
            vals = pd.to_numeric(ais[col], errors="coerce").to_numpy(dtype=float)
            ok = np.isfinite(vals)
            if ok.sum() >= 2:
                out[col] = np.interp(dst_t, src_t[ok], vals[ok])
            else:
                out[col] = np.nan
        else:
            out[col] = np.nan

    return out


def choose_best_candidate():
    rep = pd.read_csv(REPORT, low_memory=False)

    for col in ["median_km", "mean_km", "p90_km", "channel_min", "channel_max"]:
        rep[col] = pd.to_numeric(rep[col], errors="coerce")

    cand = rep[
        (rep["lat_col"].astype(str) == "est_ship_lat")
        & (rep["lon_col"].astype(str) == "est_ship_lon")
        & (rep["channel_max"] >= CHANNEL_MIN)
        & (rep["channel_min"] <= CHANNEL_MAX)
        & (~rep["path"].astype(str).str.contains("groundtruth_ais_projected", case=False, na=False))
        & (~rep["path"].astype(str).str.contains("ais_groundtruth_raw", case=False, na=False))
    ].copy()

    if cand.empty:
        raise RuntimeError("Não encontrei candidato est_ship_lat/est_ship_lon na faixa de canais do evento.")

    cand = cand.sort_values(["median_km", "mean_km", "p90_km"]).reset_index(drop=True)

    return cand.iloc[0].to_dict()


def main():
    if not REPORT.exists():
        raise FileNotFoundError(REPORT)

    if not SCENE.exists():
        raise FileNotFoundError(SCENE)

    best = choose_best_candidate()

    csv_path = Path(str(best["path"]))
    lat_col = str(best["lat_col"])
    lon_col = str(best["lon_col"])
    time_col = str(best["time_col"]) if "time_col" in best and pd.notna(best["time_col"]) else "time_utc"

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    print("=" * 100)
    print("MELHOR ESTIMATIVA DAS OFF-CABLE SELECIONADA")
    print("=" * 100)
    print("CSV:", csv_path)
    print("time_col:", time_col)
    print("lat_col :", lat_col)
    print("lon_col :", lon_col)
    print("median_km:", best["median_km"])
    print("mean_km  :", best["mean_km"])
    print("channels :", best["channel_min"], "→", best["channel_max"])

    scene = json.loads(SCENE.read_text(encoding="utf-8"))

    df = pd.read_csv(csv_path, low_memory=False)

    if time_col not in df.columns:
        time_col = find_col(df, ["time_utc", "timestamp", "datetime", "utc", "estimated_time_utc", "closest_time_utc"])

    if time_col is None:
        raise RuntimeError("Não encontrei coluna de tempo no CSV selecionado.")

    channel_col = find_col(df, [
        "est_channel",
        "channel",
        "nearest_cable_channel",
        "das_channel",
        "est_channel_argmax",
    ])

    score_col = find_col(df, [
        "est_score",
        "score",
        "confidence",
        "probability",
        "z_score",
        "est_score_argmax",
    ])

    cable_col = find_col(df, [
        "est_cable",
        "cable",
        "cable_id",
        "side",
    ])

    cable_lat_col = find_col(df, [
        "est_cable_lat",
        "nearest_cable_lat",
        "cable_lat",
        "das_lat",
    ])

    cable_lon_col = find_col(df, [
        "est_cable_lon",
        "nearest_cable_lon",
        "cable_lon",
        "das_lon",
    ])

    cable_dist_col = find_col(df, [
        "est_cable_dist_km",
        "nearest_cable_dist_km",
        "cable_dist_km",
    ])

    ais_lat_col = find_col(df, ["ais_lat", "gt_lat", "groundtruth_lat"])
    ais_lon_col = find_col(df, ["ais_lon", "gt_lon", "groundtruth_lon"])

    df["_time"] = parse_time(df[time_col])
    df["_lat"] = pd.to_numeric(df[lat_col], errors="coerce")
    df["_lon"] = pd.to_numeric(df[lon_col], errors="coerce")

    df = df[
        df["_time"].notna()
        & df["_lat"].between(-90, 90)
        & df["_lon"].between(-180, 180)
    ].copy()

    df = df[(df["_time"] >= EVENT_START) & (df["_time"] <= EVENT_END)].copy()

    if channel_col is not None:
        df["_channel"] = pd.to_numeric(df[channel_col], errors="coerce")
        df = df[
            df["_channel"].isna()
            | ((df["_channel"] >= CHANNEL_MIN) & (df["_channel"] <= CHANNEL_MAX))
        ].copy()
    else:
        df["_channel"] = np.nan

    df = df.sort_values("_time").drop_duplicates("_time").reset_index(drop=True)

    if df.empty:
        raise RuntimeError("O CSV selecionado não tem pontos válidos dentro da janela/canais do evento.")

    segment = pd.DataFrame()
    segment["time_utc"] = df["_time"]
    segment["lat"] = df["_lat"]
    segment["lon"] = df["_lon"]
    segment["channel"] = df["_channel"]
    segment["score"] = pd.to_numeric(df[score_col], errors="coerce") if score_col else np.nan
    segment["cable"] = df[cable_col].astype(str) if cable_col else "south"

    segment["cable_lat"] = pd.to_numeric(df[cable_lat_col], errors="coerce") if cable_lat_col else np.nan
    segment["cable_lon"] = pd.to_numeric(df[cable_lon_col], errors="coerce") if cable_lon_col else np.nan
    segment["cable_dist_km"] = pd.to_numeric(df[cable_dist_col], errors="coerce") if cable_dist_col else np.nan

    segment["source_csv"] = str(csv_path)
    segment["lat_col_used"] = lat_col
    segment["lon_col_used"] = lon_col
    segment["marker_type"] = "das_offcable_ship_estimate"

    frame_times = pd.to_datetime(segment["time_utc"], utc=True)

    # AIS do mesmo CSV, se existir; caso contrário, interpola da cena.
    if ais_lat_col and ais_lon_col:
        ais_event = pd.DataFrame()
        ais_event["time_utc"] = frame_times
        ais_event["lat"] = pd.to_numeric(df[ais_lat_col], errors="coerce")
        ais_event["lon"] = pd.to_numeric(df[ais_lon_col], errors="coerce")
        ais_event["sog"] = np.nan
        ais_event["cog"] = np.nan
        ais_event["heading"] = np.nan
    else:
        ais_event = interpolate_ais_from_scene(scene, frame_times)

    # Diagnóstico DAS x AIS.
    if "lat" in ais_event.columns and "lon" in ais_event.columns:
        ok = (
            pd.to_numeric(ais_event["lat"], errors="coerce").between(-90, 90)
            & pd.to_numeric(ais_event["lon"], errors="coerce").between(-180, 180)
        )

        dist = np.full(len(segment), np.nan)

        if ok.any():
            dist[ok.to_numpy()] = haversine_km(
                segment.loc[ok.to_numpy(), "lat"].to_numpy(),
                segment.loc[ok.to_numpy(), "lon"].to_numpy(),
                ais_event.loc[ok.to_numpy(), "lat"].to_numpy(),
                ais_event.loc[ok.to_numpy(), "lon"].to_numpy(),
            )

        segment["distance_to_ais_km"] = dist
    else:
        segment["distance_to_ais_km"] = np.nan

    frames = []

    for i in range(len(segment)):
        ar = ais_event.iloc[i]
        dr = segment.iloc[i]

        frames.append({
            "time_utc": pd.to_datetime(dr["time_utc"], utc=True).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ais": {
                "lat": clean(ar.get("lat", None)),
                "lon": clean(ar.get("lon", None)),
                "sog": clean(ar.get("sog", None)),
                "cog": clean(ar.get("cog", None)),
                "heading": clean(ar.get("heading", None)),
            },
            "das": {
                "lat": clean(dr["lat"]),
                "lon": clean(dr["lon"]),
                "channel": clean(dr["channel"]),
                "score": clean(dr["score"]),
                "cable": clean(dr["cable"]),
                "cable_lat": clean(dr["cable_lat"]),
                "cable_lon": clean(dr["cable_lon"]),
                "cable_dist_km": clean(dr["cable_dist_km"]),
                "distance_to_ais_km": clean(dr["distance_to_ais_km"]),
                "marker_type": "das_offcable_ship_estimate",
            }
        })

    # Formata tempos para JSON.
    segment_json = segment.copy()
    segment_json["time_utc"] = pd.to_datetime(segment_json["time_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    ais_json = ais_event.copy()
    ais_json["time_utc"] = pd.to_datetime(ais_json["time_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    scene["das_estimate_segment"] = records(segment_json)
    scene["das_estimate"] = records(segment_json)
    scene["ais_event_segment"] = records(ais_json)
    scene["frames"] = frames

    if "metadata" not in scene:
        scene["metadata"] = {}

    scene["metadata"]["das_marker_semantics"] = "DAS marker is off-cable ship position estimated by DAS"
    scene["metadata"]["das_estimate_source_csv"] = str(csv_path)
    scene["metadata"]["das_estimate_lat_col"] = lat_col
    scene["metadata"]["das_estimate_lon_col"] = lon_col
    scene["metadata"]["das_estimate_channel_col"] = channel_col
    scene["metadata"]["n_das_estimate_segment_points"] = int(len(segment))
    scene["metadata"]["das_channel_min"] = float(np.nanmin(segment["channel"]))
    scene["metadata"]["das_channel_max"] = float(np.nanmax(segment["channel"]))
    scene["metadata"]["das_vs_ais_median_km"] = float(np.nanmedian(segment["distance_to_ais_km"]))
    scene["metadata"]["das_vs_ais_mean_km"] = float(np.nanmean(segment["distance_to_ais_km"]))
    scene["metadata"]["das_vs_ais_p90_km"] = float(np.nanpercentile(segment["distance_to_ais_km"], 90))

    SCENE.write_text(
        json.dumps(scene, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8"
    )

    print("\n" + "=" * 100)
    print("OK — CENA ATUALIZADA COM ESTIMATIVA DAS OFF-CABLE CORRETA")
    print("=" * 100)
    print("Pontos DAS:", len(segment))
    print("Tempo:", segment_json["time_utc"].iloc[0], "→", segment_json["time_utc"].iloc[-1])
    print("Canais:", scene["metadata"]["das_channel_min"], "→", scene["metadata"]["das_channel_max"])
    print("Mediana DAS x AIS [km]:", scene["metadata"]["das_vs_ais_median_km"])
    print("Média DAS x AIS [km]:", scene["metadata"]["das_vs_ais_mean_km"])
    print("P90 DAS x AIS [km]:", scene["metadata"]["das_vs_ais_p90_km"])
    print("Arquivo atualizado:", SCENE)


if __name__ == "__main__":
    main()
