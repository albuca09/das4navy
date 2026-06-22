from pathlib import Path
import re

jsx_path = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
css_path = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.css")

s = jsx_path.read_text(encoding="utf-8")
backup = jsx_path.with_suffix(".jsx.bak_english_info_layers")
backup.write_text(s, encoding="utf-8")

# -----------------------------------------------------------------------------
# 1) Remove probability information from the spectrogram box
# -----------------------------------------------------------------------------
lines = []
for line in s.splitlines():
    if "Prob.:" in line or "Probability:" in line:
        continue
    lines.append(line)
s = "\n".join(lines)

s = re.sub(
    r'\s*<span[^>]*>\s*Prob\.\s*:[\s\S]*?</span>',
    '',
    s,
    flags=re.IGNORECASE
)

s = re.sub(
    r'\s*<div[^>]*>\s*Prob\.\s*:[\s\S]*?</div>',
    '',
    s,
    flags=re.IGNORECASE
)

# -----------------------------------------------------------------------------
# 2) Translate common visible labels to English
# -----------------------------------------------------------------------------
replacements = {
    "Espectrograma DAS/XAI": "DAS/XAI Spectrogram",
    "Espectrograma": "Spectrogram",
    "Mapa": "Map",
    "Trajetória AIS": "AIS track",
    "Trajetória estimada pelo DAS": "DAS-estimated trajectory",
    "Trajetória estimada pelo DAS — somente trecho válido": "DAS-estimated trajectory — valid segment only",
    "Estimativa DAS": "DAS estimate",
    "Trecho AIS usado na animação DAS/XAI": "AIS segment used in the DAS/XAI animation",
    "Tempo": "Time",
    "Canal": "Channel",
    "Cabo": "Cable",
    "Eventos XAI": "XAI events",
    "Fluxo XAI": "XAI flow",
    "Reproduzir": "Play",
    "Pausar": "Pause",
    "Velocidade": "Speed",
    "Mostrar eventos": "Show events",
    "Ocultar eventos": "Hide events",
    "Frame": "Frame",
    "Navio": "Ship",
    "Dia": "Day",
    "Janela": "Window",
    "Canais": "Channels",
    "Legenda": "Legend",
    "AIS completo": "Full AIS track",
    "AIS": "AIS",
    "DAS": "DAS",
    "south": "south",
    "north": "north",
    "CartoDB claro": "CartoDB Light",
    "CartoDB escuro": "CartoDB Dark",
}

for a, b in replacements.items():
    s = s.replace(a, b)

# -----------------------------------------------------------------------------
# 3) Add Leaflet base layer control: OpenStreetMap / CartoDB Light / CartoDB Dark
# -----------------------------------------------------------------------------
layer_helper = r'''
function installDasBaseLayerControl(map) {
  if (!map || map._dasBaseLayerControlInstalled) {
    return;
  }

  map._dasBaseLayerControlInstalled = true;

  // Remove previous base tile layers to avoid double maps.
  map.eachLayer((layer) => {
    if (layer instanceof L.TileLayer) {
      map.removeLayer(layer);
    }
  });

  const openStreetMap = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors",
    }
  );

  const cartoLight = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    {
      maxZoom: 20,
      attribution: "© OpenStreetMap contributors © CARTO",
    }
  );

  const cartoDark = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    {
      maxZoom: 20,
      attribution: "© OpenStreetMap contributors © CARTO",
    }
  );

  cartoDark.addTo(map);

  L.control.layers(
    {
      "OpenStreetMap": openStreetMap,
      "CartoDB Light": cartoLight,
      "CartoDB Dark": cartoDark,
    },
    {},
    {
      collapsed: false,
      position: "topright",
    }
  ).addTo(map);
}
'''

if "function installDasBaseLayerControl(map)" not in s:
    import_block = re.search(r'import\s+["\']\.\/Das4NavySyncedViewer\.css["\'];?', s)
    if import_block:
        pos = import_block.end()
        s = s[:pos] + "\n\n" + layer_helper + s[pos:]
    else:
        s = layer_helper + "\n\n" + s

# Insert helper call after map creation.
if "installDasBaseLayerControl(" not in s.replace("function installDasBaseLayerControl(map)", ""):
    # Case 1: mapRef.current = L.map(...)
    pattern = r'((\w+)\.current\s*=\s*L\.map\([\s\S]*?\);)'
    m = re.search(pattern, s)
    if m:
        full = m.group(1)
        ref = m.group(2)
        s = s.replace(full, full + f"\n      installDasBaseLayerControl({ref}.current);", 1)
    else:
        # Case 2: const map = L.map(...)
        pattern = r'(const\s+(\w+)\s*=\s*L\.map\([\s\S]*?\);)'
        m = re.search(pattern, s)
        if m:
            full = m.group(1)
            ref = m.group(2)
            s = s.replace(full, full + f"\n      installDasBaseLayerControl({ref});", 1)
        else:
            print("WARNING: could not find L.map(...) to insert the layer control call.")

# -----------------------------------------------------------------------------
# 4) Add lower information panel under the spectrogram
# -----------------------------------------------------------------------------
info_panel = r'''
          <section className="das-info-panel">
            <div className="info-title">DAS-guided ship trajectory</div>
            <p className="info-text">
              Full AIS × DAS correlation map, cable projection, and off-cable ship trajectory
              estimated from DAS. Use the layer control in the upper-right corner to switch base
              maps and inspect cables, AIS, DAS projection, trajectory estimates, errors, and markers.
            </p>

            <div className="info-grid">
              <div className="info-card">
                <div className="info-card-title">Processed event</div>
                <div className="kv"><span>Ship</span><b>JEANOAH</b></div>
                <div className="kv"><span>MMSI</span><b>366959080</b></div>
                <div className="kv"><span>Day</span><b>2021-11-01</b></div>
                <div className="kv"><span>Cable</span><b>south</b></div>
                <div className="kv"><span>GT window</span><b>2021-11-01 17:52:15+00:00 → 18:12:04+00:00</b></div>
                <div className="kv"><span>GT channels</span><b>13.985 → 14.219</b></div>
                <div className="kv"><span>Min./median distance</span><b>0.2064 km / 0.3643 km</b></div>
              </div>

              <div className="info-card">
                <div className="info-card-title">AIS × cable correlation</div>
                <table className="mini-table">
                  <thead>
                    <tr><th>Cable</th><th>Min. dist. km</th><th>Channel</th><th>Time</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>south</td><td>0.206</td><td>14.219</td><td>2021-11-01 18:12:04+00:00</td></tr>
                    <tr><td>north</td><td>0.429</td><td>16.530</td><td>2021-11-01 21:40:06+00:00</td></tr>
                  </tbody>
                </table>
              </div>

              <div className="info-card">
                <div className="info-card-title">TDMS files used</div>
                <div className="kv"><span>Number of files</span><b>112</b></div>
                <div className="kv"><span>Start</span><b>2021-11-01 17:48:09.839000+00:00</b></div>
                <div className="kv"><span>End</span><b>2021-11-01 18:16:09.839000+00:00</b></div>
                <div className="kv"><span>First</span><b>OOIPacCity_UTC_20211101_174809.839.tdms</b></div>
                <div className="kv"><span>Last</span><b>OOIPacCity_UTC_20211101_181554.839.tdms</b></div>
              </div>

              <div className="info-card">
                <div className="info-card-title">Estimation metrics</div>
                <div className="kv"><span>Matched frames</span><b>7,844</b></div>
                <div className="kv"><span>Channel MAE</span><b>114.10</b></div>
                <div className="kv"><span>Channel RMSE</span><b>123.76</b></div>
                <div className="kv"><span>Cable-distance MAE</span><b>0.2321 km</b></div>
                <div className="kv"><span>Cable-position MAE</span><b>0.2320 km</b></div>
                <div className="kv"><span>AIS → estimated ship MAE</span><b>0.2284 km</b></div>
                <div className="kv"><span>AIS → estimated ship RMSE</span><b>0.2475 km</b></div>
                <div className="kv"><span>Cross-track offset MAE</span><b>0.0030 km</b></div>
              </div>

              <div className="info-card">
                <div className="info-card-title">Correlation side options</div>
                <div className="kv"><span>Search by</span><b>vessel_name / imo / callsign / mmsi</b></div>
                <div className="kv"><span>AIS–cable radius</span><b>2.00 km</b></div>
                <div className="kv"><span>DAS temporal padding</span><b>5.0 min</b></div>
                <div className="kv"><span>Event gap</span><b>30.0 min</b></div>
                <div className="kv"><span>AIS interpolation</span><b>60 s</b></div>
                <div className="kv"><span>Cable-region filter</span><b>True</b></div>
                <div className="kv"><span>Server</span><b>http://127.0.0.1:8050</b></div>
              </div>

              <div className="info-card">
                <div className="info-card-title">Generated files</div>
                <p className="file-list">
                  groundtruth_ais_projected_to_das.csv · groundtruth_event_focused_for_das.csv ·
                  selected_tdms_files.csv · estimated_ship_track_projected_on_cable_v12.csv ·
                  estimated_ship_track_offcable_v12.csv · estimate_vs_groundtruth_joined.csv ·
                  metrics_estimation_vs_groundtruth.csv · activated_channels_by_frame.csv ·
                  activated_channels_summary.csv · cable_3d_view.html
                </p>
              </div>

              <div className="info-card wide">
                <div className="info-card-title">Figures and diagnostics</div>
                <p className="file-list">
                  Channel-time view: ground truth vs DAS · DAS energy heatmap · temporal errors ·
                  interactive 3D cable view · top activated channels.
                </p>
              </div>
            </div>
          </section>
'''

if "DAS-guided ship trajectory" not in s:
    # Find first div whose className contains spec-panel and insert after its closing div.
    m = re.search(r'<div[^>]*className=["\'][^"\']*spec-panel[^"\']*["\'][^>]*>', s)
    if not m:
        print("WARNING: could not find spec-panel block. Info panel not inserted.")
    else:
        start = m.start()
        i = m.end()
        depth = 1
        token_re = re.compile(r'<div\b|</div>', re.IGNORECASE)
        for tm in token_re.finditer(s, i):
            tok = tm.group(0).lower()
            if tok.startswith("<div"):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    end = tm.end()
                    s = s[:end] + "\n" + info_panel + s[end:]
                    break

# -----------------------------------------------------------------------------
# 5) Normalize layer and legend labels in JSX
# -----------------------------------------------------------------------------
legend_replacements = {
    "Full AIS": "Full AIS track",
    "DAS est.": "DAS estimate",
    "DAS estimate": "DAS estimate",
    "Cable north": "North DAS cable",
    "Cable south": "South DAS cable",
    "XAI pulse": "XAI pulse",
}
for a, b in legend_replacements.items():
    s = s.replace(a, b)

jsx_path.write_text(s, encoding="utf-8")

# -----------------------------------------------------------------------------
# 6) CSS: make left panel half spectrogram / half information panel
# -----------------------------------------------------------------------------
css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

css_add = r'''

/* ------------------------------------------------------------------------- */
/* English DAS4NAVY layout: half spectrogram, half information panel          */
/* ------------------------------------------------------------------------- */

.spec-panel {
  flex: 0 0 50%;
  height: 50%;
  min-height: 280px;
  max-height: 50%;
}

.das-info-panel {
  flex: 1 1 50%;
  height: 50%;
  min-height: 280px;
  overflow: auto;
  margin-top: 12px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(2, 6, 23, 0.96));
  color: #e5e7eb;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.34);
}

.info-title {
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.02em;
  margin-bottom: 8px;
  color: #f8fafc;
}

.info-text {
  font-size: 12.5px;
  line-height: 1.45;
  color: #cbd5e1;
  margin: 0 0 12px 0;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.info-card {
  border: 1px solid rgba(100, 116, 139, 0.35);
  background: rgba(15, 23, 42, 0.72);
  border-radius: 14px;
  padding: 10px;
}

.info-card-title {
  font-size: 12px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #93c5fd;
  margin-bottom: 8px;
}

.kv {
  display: grid;
  grid-template-columns: 132px 1fr;
  gap: 8px;
  font-size: 11.5px;
  line-height: 1.35;
  padding: 3px 0;
  border-bottom: 1px solid rgba(51, 65, 85, 0.55);
}

.kv span {
  color: #94a3b8;
}

.kv b {
  color: #f8fafc;
  font-weight: 700;
  word-break: break-word;
}

.mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.mini-table th,
.mini-table td {
  border-bottom: 1px solid rgba(51, 65, 85, 0.70);
  padding: 5px 4px;
  text-align: left;
  vertical-align: top;
}

.mini-table th {
  color: #bfdbfe;
  font-weight: 800;
}

.file-list {
  font-size: 11.5px;
  line-height: 1.45;
  color: #dbeafe;
  margin: 0;
}

/* Keep the Leaflet layer selector visible and readable */
.leaflet-control-layers {
  border-radius: 12px !important;
  border: 1px solid rgba(15, 23, 42, 0.45) !important;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35) !important;
}

.leaflet-control-layers-expanded {
  padding: 10px 12px !important;
  background: rgba(255, 255, 255, 0.94) !important;
  color: #111827 !important;
  font-size: 13px !important;
  font-weight: 700 !important;
}

/* Remove any residual probability chip/line if an old component still renders it */
.prob-chip,
.probability-chip,
.spec-prob,
.spec-probability {
  display: none !important;
}

'''

if "English DAS4NAVY layout" not in css:
    css += css_add

css_path.write_text(css, encoding="utf-8")

print("OK — English UI, layer control, half spectrogram layout, and lower information panel applied.")
print("JSX backup:", backup)
print("CSS file:", css_path)
