from pathlib import Path

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_das_segment")
backup.write_text(s, encoding="utf-8")

# 1) No bloco da trajetória DAS, usa o segmento selecionado.
s = s.replace(
    'const dasCoords = (scene.das_estimate || [])',
    'const dasSource = (scene.das_estimate_segment && scene.das_estimate_segment.length) ? scene.das_estimate_segment : (scene.das_estimate || []);\n    const dasCoords = dasSource'
)

# 2) Depois da trajetória AIS completa, adiciona trecho AIS da janela DAS/XAI.
marker = '''
    // Trajetória estimada pelo DAS
'''

insert = '''
    // Trecho AIS usado na animação DAS/XAI
    const aisEventCoords = (scene.ais_event_segment || [])
      .filter((p) => validLatLon(p.lat, p.lon))
      .map((p) => [Number(p.lat), Number(p.lon)]);

    if (aisEventCoords.length > 1) {
      L.polyline(aisEventCoords, {
        color: "#fde047",
        weight: 5,
        opacity: 0.98,
      })
        .bindPopup("<b>Trecho AIS usado na animação DAS/XAI</b>")
        .addTo(staticLayer.current);

      aisEventCoords.forEach((c) => bounds.extend(c));
    }

'''

if "Trecho AIS usado na animação DAS/XAI" not in s:
    if marker not in s:
        raise RuntimeError("Não encontrei marcador da trajetória DAS.")
    s = s.replace(marker, insert + marker)

# 3) Ajusta popup/legenda textual da estimativa.
s = s.replace(
    ".bindPopup(\"<b>Trajetória estimada pelo DAS</b>\")",
    ".bindPopup(\"<b>Trajetória estimada pelo DAS — somente trecho válido</b>\")"
)

p.write_text(s, encoding="utf-8")

print("OK — React atualizado.")
print("Backup:", backup)
