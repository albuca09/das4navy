# -*- coding: utf-8 -*-
"""
Força o DAS4NAVY a usar a saída correta do estimador DAS-only:

  time_utc
  est_ship_lat
  est_ship_lon
  est_channel
  est_score
  est_cable
  est_cable_lat/lon apenas como ponto no cabo, não como navio.

Gera/atualiza:
  public/data/das4navy_scene_web_lite.json
"""

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd


APP = Path(r"C:\Users\Luis\Desktop\das4navy")

SCENE = APP / "public" / "data" / "das4navy_scene_web_lite.json"

DAS_CSV = Path(
    r"D:\DAS\_ship_position_estimation_from_das_noais"
    r"\run_20260613_222353"
    r"\tables"
    r"\estimated_ship_track_offcable_das_only.csv"
)

EVENT_START = pd.to_datetime("2021-11-01T17:48:15Z", utc=True)
EVENT_END   = pd.to_datetime("2021-11-01T18:16:04Z", utc=True)


def clean_value(x):
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


def parse_time(x):
    return pd.to_datetime(x, utc=True, errors="coerce")


def valid_latlon(df, lat_col, lon_col):
    return (
        pd.to_numeric(df[lat_col], errors="coerce").between(-90, 90)
        & pd.to_numeric(df[lon_col], errors="coerce").between(-180, 180)
    )


def interpolate_ais_at_times(ais_df, frame_times):
    ais = ais_df.copy()

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
        raise RuntimeError("AIS insuficiente para interpolar o navio.")

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


def haversine_km(lat1, lon1, lat2, lon2):
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lon1 = np.radians(np.asarray(lon1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    lon2 = np.radians(np.asarray(lon2, dtype=float))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(a))


def main():
    if not SCENE.exists():
        raise FileNotFoundError(SCENE)

    if not DAS_CSV.exists():
        raise FileNotFoundError(DAS_CSV)

    print("=" * 100)
    print("CORRIGINDO TRAJETÓRIA DAS NO DAS4NAVY")
    print("=" * 100)
    print("Cena:", SCENE)
    print("CSV DAS:", DAS_CSV)

    scene = json.loads(SCENE.read_text(encoding="utf-8"))

    das = pd.read_csv(DAS_CSV, low_memory=False)

    required = [
        "time_utc",
        "est_ship_lat",
        "est_ship_lon",
        "est_channel",
        "est_score",
        "est_cable",
        "est_cable_lat",
        "est_cable_lon",
        "est_cable_dist_km",
        "est_ship_side_sign_selected_noais",
        "inference_uses_ais",
        "ais_used_only_for_evaluation",
    ]

    missing = [c for c in required if c not in das.columns]
    if missing:
        raise RuntimeError(f"Colunas ausentes no CSV DAS: {missing}")

    das["time_utc"] = parse_time(das["time_utc"])
    das["lat"] = pd.to_numeric(das["est_ship_lat"], errors="coerce")
    das["lon"] = pd.to_numeric(das["est_ship_lon"], errors="coerce")

    das = das[
        das["time_utc"].notna()
        & das["lat"].between(-90, 90)
        & das["lon"].between(-180, 180)
    ].copy()

    das = das[(das["time_utc"] >= EVENT_START) & (das["time_utc"] <= EVENT_END)].copy()
    das = das.sort_values("time_utc").drop_duplicates("time_utc").reset_index(drop=True)

    if das.empty:
        raise RuntimeError("Nenhum ponto DAS dentro da janela do evento.")

    out = pd.DataFrame()
    out["time_utc"] = das["time_utc"]
    out["lat"] = das["lat"]
    out["lon"] = das["lon"]

    out["channel"] = pd.to_numeric(das["est_channel"], errors="coerce")
    out["score"] = pd.to_numeric(das["est_score"], errors="coerce")
    out["cable"] = das["est_cable"].astype(str)

    # Ponto do cabo associado, para desenhar o vínculo cabo → estimativa.
    out["cable_lat"] = pd.to_numeric(das["est_cable_lat"], errors="coerce")
    out["cable_lon"] = pd.to_numeric(das["est_cable_lon"], errors="coerce")
    out["cable_dist_km"] = pd.to_numeric(das["est_cable_dist_km"], errors="coerce")

    out["cross_track_abs_km"] = pd.to_numeric(
        das["est_ship_cross_track_abs_km_noais"],
        errors="coerce"
    )

    out["side_sign"] = pd.to_numeric(
        das["est_ship_side_sign_selected_noais"],
        errors="coerce"
    )

    out["method"] = das["estimation_method"].astype(str)
    out["inference_uses_ais"] = das["inference_uses_ais"].astype(bool)
    out["ais_used_only_for_evaluation"] = das["ais_used_only_for_evaluation"].astype(bool)

    # Formata tempo para JSON.
    out["time_utc"] = pd.to_datetime(out["time_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # AIS completo permanece como linha completa.
    ais_full = pd.DataFrame(scene.get("ais", []))
    if ais_full.empty:
        raise RuntimeError("A cena não contém AIS completo.")

    frame_times = pd.to_datetime(out["time_utc"], utc=True)
    ais_interp = interpolate_ais_at_times(ais_full, frame_times)

    # Distância DAS x AIS apenas para diagnóstico visual.
    out["_ais_lat"] = ais_interp["lat"].to_numpy()
    out["_ais_lon"] = ais_interp["lon"].to_numpy()
    out["distance_to_ais_km"] = haversine_km(
        out["lat"].to_numpy(),
        out["lon"].to_numpy(),
        out["_ais_lat"].to_numpy(),
        out["_ais_lon"].to_numpy(),
    )

    ais_event = ais_interp.copy()
    ais_event["time_utc"] = pd.to_datetime(ais_event["time_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    frames = []
    for i in range(len(out)):
        ar = ais_event.iloc[i]
        dr = out.iloc[i]

        frames.append({
            "time_utc": dr["time_utc"],
            "ais": {
                "lat": clean_value(ar["lat"]),
                "lon": clean_value(ar["lon"]),
                "sog": clean_value(ar.get("sog", None)),
                "cog": clean_value(ar.get("cog", None)),
                "heading": clean_value(ar.get("heading", None)),
            },
            "das": {
                "lat": clean_value(dr["lat"]),
                "lon": clean_value(dr["lon"]),
                "channel": clean_value(dr["channel"]),
                "score": clean_value(dr["score"]),
                "cable": clean_value(dr["cable"]),
                "cable_lat": clean_value(dr["cable_lat"]),
                "cable_lon": clean_value(dr["cable_lon"]),
                "cable_dist_km": clean_value(dr["cable_dist_km"]),
                "cross_track_abs_km": clean_value(dr["cross_track_abs_km"]),
                "side_sign": clean_value(dr["side_sign"]),
                "distance_to_ais_km": clean_value(dr["distance_to_ais_km"]),
            }
        })

    # Remove colunas auxiliares antes de salvar segmento.
    segment = out.drop(columns=["_ais_lat", "_ais_lon"], errors="ignore").copy()

    scene["das_estimate_segment"] = records(segment)
    scene["das_estimate"] = records(segment)
    scene["ais_event_segment"] = records(ais_event)
    scene["frames"] = frames

    if "metadata" not in scene:
        scene["metadata"] = {}

    scene["metadata"]["das_estimate_source_csv"] = str(DAS_CSV)
    scene["metadata"]["das_estimate_lat_col"] = "est_ship_lat"
    scene["metadata"]["das_estimate_lon_col"] = "est_ship_lon"
    scene["metadata"]["das_estimate_uses_ais_for_inference"] = False
    scene["metadata"]["ais_used_only_for_evaluation"] = True
    scene["metadata"]["n_das_estimate_segment_points"] = int(len(segment))
    scene["metadata"]["n_ais_event_segment_points"] = int(len(ais_event))
    scene["metadata"]["das_vs_ais_median_km"] = float(np.nanmedian(segment["distance_to_ais_km"]))
    scene["metadata"]["das_vs_ais_mean_km"] = float(np.nanmean(segment["distance_to_ais_km"]))
    scene["metadata"]["das_vs_ais_p90_km"] = float(np.nanpercentile(segment["distance_to_ais_km"], 90))

    SCENE.write_text(
        json.dumps(scene, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8"
    )

    print("\nOK")
    print("Pontos DAS:", len(segment))
    print("Frames:", len(frames))
    print("Coluna lat usada: est_ship_lat")
    print("Coluna lon usada: est_ship_lon")
    print("Mediana DAS x AIS [km]:", scene["metadata"]["das_vs_ais_median_km"])
    print("Média DAS x AIS [km]:", scene["metadata"]["das_vs_ais_mean_km"])
    print("P90 DAS x AIS [km]:", scene["metadata"]["das_vs_ais_p90_km"])
    print("Primeiro ponto DAS:")
    print(segment.head(1).to_string(index=False))
    print("Último ponto DAS:")
    print(segment.tail(1).to_string(index=False))


if __name__ == "__main__":
    main()
