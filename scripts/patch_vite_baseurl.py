from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_baseurl")
backup.write_text(s, encoding="utf-8")

# 1) Adiciona helper para respeitar o base do Vite: /das4navy/
helper = r'''
const APP_BASE = import.meta.env.BASE_URL || "/";

function assetUrl(path) {
  if (!path) return "";
  const p = String(path);
  if (p.startsWith("http://") || p.startsWith("https://")) return p;
  const base = APP_BASE.endsWith("/") ? APP_BASE : APP_BASE + "/";
  return base + p.replace(/^\/+/, "");
}
'''

if "function assetUrl(path)" not in s:
    marker = 'const cablePulseIcon = makePulseIcon("cable");'
    if marker not in s:
        raise RuntimeError("Não encontrei marker cablePulseIcon.")
    s = s.replace(marker, marker + "\n" + helper)

# 2) Corrige fetch da cena
s = re.sub(
    r'fetch\("/data/das4navy_scene_web_lite\.json\?cache="\s*\+\s*Date\.now\(\)\)',
    'fetch(assetUrl("data/das4navy_scene_web_lite.json") + "?cache=" + Date.now())',
    s
)

s = re.sub(
    r'fetch\("/data/das4navy_scene_web_lite\.json"\)',
    'fetch(assetUrl("data/das4navy_scene_web_lite.json") + "?cache=" + Date.now())',
    s
)

s = re.sub(
    r'fetch\("/data/das4navy_scene_web\.json"\)',
    'fetch(assetUrl("data/das4navy_scene_web_lite.json") + "?cache=" + Date.now())',
    s
)

# 3) Corrige fetch do manifesto
s = re.sub(
    r'fetch\("/data/spectrogram_manifest\.json\?cache="\s*\+\s*Date\.now\(\)\)',
    'fetch(assetUrl("data/spectrogram_manifest.json") + "?cache=" + Date.now())',
    s
)

s = re.sub(
    r'fetch\("/data/spectrogram_manifest\.json"\)',
    'fetch(assetUrl("data/spectrogram_manifest.json") + "?cache=" + Date.now())',
    s
)

# 4) Corrige src da imagem do espectrograma
s = s.replace(
    'src={currentSpec.image_url}',
    'src={assetUrl(currentSpec.image_url)}'
)

p.write_text(s, encoding="utf-8")

print("OK — BASE_URL corrigido.")
print("Backup:", backup)
