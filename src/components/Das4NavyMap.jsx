import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./Das4NavyMap.css";

function ok(lat, lon) {
  return (
    lat !== null &&
    lon !== null &&
    lat !== undefined &&
    lon !== undefined &&
    Number.isFinite(Number(lat)) &&
    Number.isFinite(Number(lon)) &&
    Number(lat) >= -90 &&
    Number(lat) <= 90 &&
    Number(lon) >= -180 &&
    Number(lon) <= 180
  );
}

function fmt(x, d = 3) {
  if (x === null || x === undefined || Number.isNaN(Number(x))) return "-";
  return Number(x).toFixed(d);
}

function makeIcon(label, cls) {
  return L.divIcon({
    className: "das-real-marker " + cls,
    html: `<div>${label}</div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  });
}

const aisIcon = makeIcon("AIS", "ais");
const dasIcon = makeIcon("DAS", "das");

export default function Das4NavyMap() {
  const mapDiv = useRef(null);
  const map = useRef(null);
  const staticLayer = useRef(null);
  const xaiLayer = useRef(null);
  const movingLayer = useRef(null);

  const aisMarker = useRef(null);
  const dasMarker = useRef(null);
  const aisTrail = useRef(null);
  const dasTrail = useRef(null);

  const [scene, setScene] = useState(null);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [showXai, setShowXai] = useState(false);

  useEffect(() => {
    fetch("/data/das4navy_scene.json")
      .then((r) => {
        if (!r.ok) throw new Error("JSON não encontrado");
        return r.json();
      })
      .then((j) => {
        setScene(j);
        setFrame(0);
      })
      .catch((e) => {
        console.error(e);
        alert("Não foi possível carregar /data/das4navy_scene.json. Rode o export_das4navy_scene.py.");
      });
  }, []);

  useEffect(() => {
    if (!mapDiv.current || map.current) return;

    map.current = L.map(mapDiv.current, {
      preferCanvas: true,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map.current);

    map.current.setView([45.2, -124.0], 9);

    staticLayer.current = L.layerGroup().addTo(map.current);
    xaiLayer.current = L.layerGroup().addTo(map.current);
    movingLayer.current = L.layerGroup().addTo(map.current);

    return () => {
      map.current.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!scene || !map.current || !staticLayer.current || !movingLayer.current) return;

    staticLayer.current.clearLayers();
    movingLayer.current.clearLayers();
    xaiLayer.current.clearLayers();

    const bounds = L.latLngBounds([]);

    // Cabos DAS reais
    for (const cable of scene.cables || []) {
      const coords = (cable.points || [])
        .filter((p) => ok(p.lat, p.lon))
        .map((p) => [Number(p.lat), Number(p.lon)]);

      if (coords.length < 2) continue;

      const color = String(cable.id).toLowerCase().includes("north")
        ? "#00a2ff"
        : "#00ff88";

      const line = L.polyline(coords, {
        color,
        weight: 4,
        opacity: 0.9,
      });

      line.bindPopup(`
        <b>Cabo DAS real: ${cable.id}</b><br/>
        Pontos: ${cable.n_points}<br/>
        Fonte: ${cable.source_file || "-"}
      `);

      line.addTo(staticLayer.current);
      coords.forEach((c) => bounds.extend(c));
    }

    // AIS JEANOAH
    const aisCoords = (scene.ais || [])
      .filter((p) => ok(p.lat, p.lon))
      .map((p) => [Number(p.lat), Number(p.lon)]);

    if (aisCoords.length > 1) {
      L.polyline(aisCoords, {
        color: "#ff9f1a",
        weight: 4,
        opacity: 0.9,
      })
        .bindPopup("<b>Trajetória AIS — JEANOAH</b>")
        .addTo(staticLayer.current);

      aisCoords.forEach((c) => bounds.extend(c));
    }

    // Trajetória estimada pelo DAS
    const dasCoords = (scene.das_estimate || [])
      .filter((p) => ok(p.lat, p.lon))
      .map((p) => [Number(p.lat), Number(p.lon)]);

    if (dasCoords.length > 1) {
      L.polyline(dasCoords, {
        color: "#ff3155",
        weight: 4,
        opacity: 0.95,
        dashArray: "8 8",
      })
        .bindPopup("<b>Trajetória estimada pelo DAS</b>")
        .addTo(staticLayer.current);

      dasCoords.forEach((c) => bounds.extend(c));
    }

    aisTrail.current = L.polyline([], {
      color: "#ff9f1a",
      weight: 6,
      opacity: 1,
    }).addTo(movingLayer.current);

    dasTrail.current = L.polyline([], {
      color: "#ff3155",
      weight: 6,
      opacity: 1,
      dashArray: "6 6",
    }).addTo(movingLayer.current);

    aisMarker.current = L.marker([0, 0], { icon: aisIcon, zIndexOffset: 2000 })
      .addTo(movingLayer.current);

    dasMarker.current = L.marker([0, 0], { icon: dasIcon, zIndexOffset: 2000 })
      .addTo(movingLayer.current);

    if (bounds.isValid()) {
      map.current.fitBounds(bounds.pad(0.12));
    }
  }, [scene]);

  useEffect(() => {
    if (!scene || !showXai || !xaiLayer.current) {
      if (xaiLayer.current) xaiLayer.current.clearLayers();
      return;
    }

    xaiLayer.current.clearLayers();

    // Limita para não travar o navegador.
    const events = (scene.xai_events || []).slice(0, 2500);

    for (const ev of events) {
      if (!ok(ev.lat, ev.lon)) continue;

      const score = Number(ev.score || 1);
      const radius = Math.max(3, Math.min(12, 3 + score));

      L.circleMarker([Number(ev.lat), Number(ev.lon)], {
        radius,
        color: "#d946ef",
        fillColor: "#d946ef",
        fillOpacity: 0.45,
        weight: 1,
      })
        .bindPopup(`
          <b>Evento DAS/XAI</b><br/>
          Tempo: ${ev.time_utc}<br/>
          Canal: ${ev.channel}<br/>
          Cabo: ${ev.mapped_cable || "-"}<br/>
          Score: ${fmt(ev.score)}
        `)
        .addTo(xaiLayer.current);
    }
  }, [scene, showXai]);

  useEffect(() => {
    if (!scene || !playing) return;

    const n = scene.frames?.length || 0;
    if (n < 2) return;

    const timer = setInterval(() => {
      setFrame((v) => (v + 1 >= n ? 0 : v + 1));
    }, 250);

    return () => clearInterval(timer);
  }, [scene, playing]);

  useEffect(() => {
    if (!scene || !aisMarker.current || !dasMarker.current) return;

    const frames = scene.frames || [];
    if (!frames.length) return;

    const f = frames[Math.min(frame, frames.length - 1)];

    const aisPath = [];
    const dasPath = [];

    for (let i = 0; i <= frame && i < frames.length; i++) {
      const ff = frames[i];

      if (ff.ais && ok(ff.ais.lat, ff.ais.lon)) {
        aisPath.push([Number(ff.ais.lat), Number(ff.ais.lon)]);
      }

      if (ff.das && ok(ff.das.lat, ff.das.lon)) {
        dasPath.push([Number(ff.das.lat), Number(ff.das.lon)]);
      }
    }

    if (aisTrail.current) aisTrail.current.setLatLngs(aisPath);
    if (dasTrail.current) dasTrail.current.setLatLngs(dasPath);

    if (f.ais && ok(f.ais.lat, f.ais.lon)) {
      aisMarker.current.setLatLng([Number(f.ais.lat), Number(f.ais.lon)]);
      aisMarker.current.bindPopup(`
        <b>JEANOAH — AIS</b><br/>
        Tempo: ${f.time_utc}<br/>
        SOG: ${fmt(f.ais.sog, 2)}<br/>
        COG: ${fmt(f.ais.cog, 2)}<br/>
        Heading: ${fmt(f.ais.heading, 2)}
      `);
    }

    if (f.das && ok(f.das.lat, f.das.lon)) {
      dasMarker.current.setLatLng([Number(f.das.lat), Number(f.das.lon)]);
      dasMarker.current.bindPopup(`
        <b>Estimativa DAS</b><br/>
        Tempo: ${f.time_utc}<br/>
        Canal: ${fmt(f.das.channel, 0)}<br/>
        Cabo: ${f.das.cable || "-"}<br/>
        Score: ${fmt(f.das.score)}<br/>
        Erro: ${fmt(f.das.error)}
      `);
    }
  }, [scene, frame]);

  const meta = scene?.metadata || {};
  const nFrames = scene?.frames?.length || 0;
  const currentTime = scene?.frames?.[frame]?.time_utc || "-";

  return (
    <div className="das-real-page">
      <aside className="das-real-panel">
        <h1>DAS4NAVY</h1>
        <h2>OOI DAS / JEANOAH</h2>

        <div className="das-real-card">
          <b>Tempo atual</b>
          <span>{currentTime}</span>
        </div>

        <div className="das-real-grid">
          <div className="das-real-card">
            <b>Cabos</b>
            <strong>{meta.n_cables || 0}</strong>
          </div>
          <div className="das-real-card">
            <b>AIS</b>
            <strong>{meta.n_ais_points || 0}</strong>
          </div>
          <div className="das-real-card">
            <b>DAS</b>
            <strong>{meta.n_das_estimate_points || 0}</strong>
          </div>
          <div className="das-real-card">
            <b>XAI</b>
            <strong>{meta.n_xai_events || 0}</strong>
          </div>
        </div>

        <div className="das-real-card">
          <b>Animação</b>

          <button onClick={() => setPlaying(!playing)}>
            {playing ? "Pausar" : "Reproduzir"}
          </button>

          <button onClick={() => setFrame(0)}>Reiniciar</button>

          <input
            type="range"
            min="0"
            max={Math.max(0, nFrames - 1)}
            value={frame}
            onChange={(e) => setFrame(Number(e.target.value))}
          />

          <small>
            Frame {nFrames ? frame + 1 : 0} / {nFrames}
          </small>
        </div>

        <label className="das-real-check">
          <input
            type="checkbox"
            checked={showXai}
            onChange={(e) => setShowXai(e.target.checked)}
          />
          Mostrar eventos DAS/XAI
        </label>

        <div className="das-real-legend">
          <p><span className="ln north"></span>Cabo north real</p>
          <p><span className="ln south"></span>Cabo south real</p>
          <p><span className="ln ais"></span>AIS JEANOAH</p>
          <p><span className="ln das"></span>Estimativa DAS</p>
          <p><span className="dot xai"></span>Eventos DAS/XAI</p>
        </div>
      </aside>

      <main className="das-real-map-wrap">
        <div ref={mapDiv} className="das-real-map" />
      </main>
    </div>
  );
}
