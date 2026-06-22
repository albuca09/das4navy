from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_manifest")
backup.write_text(s, encoding="utf-8")

# 1) Garante fetch sem cache do JSON leve da cena
s = s.replace(
    'fetch("/data/das4navy_scene_web.json")',
    'fetch("/data/das4navy_scene_web_lite.json?cache=" + Date.now())'
)
s = s.replace(
    'fetch("/data/das4navy_scene_web_lite.json")',
    'fetch("/data/das4navy_scene_web_lite.json?cache=" + Date.now())'
)

# 2) Adiciona estado do manifesto dos espectrogramas
target_state = 'const [showEvents, setShowEvents] = useState(true);'
if "const [manifestSpecs, setManifestSpecs]" not in s:
    if target_state not in s:
        raise RuntimeError("Não encontrei o estado showEvents para inserir manifestSpecs.")
    s = s.replace(
        target_state,
        target_state + '\n  const [manifestSpecs, setManifestSpecs] = useState([]);'
    )

# 3) Adiciona fetch independente do spectrogram_manifest.json
marker_frames = '  const frames = scene?.frames || [];'

manifest_fetch = r'''
  useEffect(() => {
    fetch("/data/spectrogram_manifest.json?cache=" + Date.now())
      .then((r) => {
        if (!r.ok) throw new Error("spectrogram_manifest.json não encontrado");
        return r.json();
      })
      .then((j) => {
        const rows = Array.isArray(j?.spectrograms)
          ? j.spectrograms.filter((x) => x && x.image_url)
          : [];
        console.log("spectrogram_manifest rows:", rows.length);
        setManifestSpecs(rows);
      })
      .catch((e) => {
        console.error("Erro carregando spectrogram_manifest:", e);
      });
  }, []);
'''

if "spectrogram_manifest rows:" not in s:
    if marker_frames not in s:
        raise RuntimeError("Não encontrei const frames = scene?.frames || [];")
    s = s.replace(marker_frames, manifest_fetch + "\n" + marker_frames)

# 4) Troca a origem dos espectrogramas:
# usa scene.spectrogram_timeline quando existir; senão usa manifestSpecs.
replacement = r'''
  const sceneSpectrograms = Array.isArray(scene?.spectrogram_timeline)
    ? scene.spectrogram_timeline.filter((x) => x && x.image_url)
    : [];

  const spectrograms = sceneSpectrograms.length > 0
    ? sceneSpectrograms
    : manifestSpecs;
'''

patterns = [
    r'\n\s*const spectrograms = scene\?\.spectrogram_timeline \|\| \[\];',
    r'\n\s*const spectrograms = Array\.isArray\(scene\?\.spectrogram_timeline\)\s*\?\s*scene\.spectrogram_timeline\.filter\(\(s\) => s && s\.image_url\)\s*:\s*\[\];',
]

changed = False
for pat in patterns:
    s2, n = re.subn(pat, "\n" + replacement, s, count=1)
    if n:
        s = s2
        changed = True
        break

if not changed and "const sceneSpectrograms" not in s:
    marker_time = '  const currentTimeMs = currentFrame ? ms(currentFrame.time_utc) : NaN;'
    if marker_time not in s:
        raise RuntimeError("Não encontrei currentTimeMs para inserir spectrograms.")
    s = s.replace(marker_time, marker_time + "\n" + replacement)

p.write_text(s, encoding="utf-8")

print("OK — componente atualizado.")
print("Backup:", backup)
