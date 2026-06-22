from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_video_img")
backup.write_text(s, encoding="utf-8")

# Remove o efeito de canvas do patch anterior, se existir.
s = re.sub(
    r'\n\s*// Renderiza o espectrograma como vídeo contínuo sincronizado com frameIndex/currentSpec\.[\s\S]*?\n\s*\}, \[currentSpec, frameIndex, spectrograms\]\);\n',
    '\n',
    s
)

# Adiciona videoSpec antes do return.
video_spec_block = r'''
  // Frame de vídeo contínuo do painel esquerdo.
  // Mapeia o índice da animação do mapa para a sequência de espectrogramas.
  const videoSpec = useMemo(() => {
    if (!Array.isArray(spectrograms) || spectrograms.length === 0) {
      return currentSpec || null;
    }

    if (!Array.isArray(frames) || frames.length <= 1) {
      return spectrograms[0];
    }

    const a = Math.max(0, Math.min(1, frameIndex / Math.max(1, frames.length - 1)));
    const idx = Math.max(
      0,
      Math.min(
        spectrograms.length - 1,
        Math.round(a * (spectrograms.length - 1))
      )
    );

    return spectrograms[idx] || currentSpec || spectrograms[0];
  }, [spectrograms, frames, frameIndex, currentSpec]);

'''

if "const videoSpec = useMemo" not in s:
    marker = "\n  return ("
    if marker not in s:
        raise RuntimeError("Não encontrei o return do componente.")
    s = s.replace(marker, "\n" + video_spec_block + marker, 1)

img_block = '''<img
                  key={videoSpec?.image_url || currentSpec?.image_url || "no-spec"}
                  className="spec-img spec-video-img"
                  src={assetUrl(videoSpec?.image_url || currentSpec?.image_url)}
                  alt="DAS XAI spectrogram video frame"
                />'''

# Substitui canvas, se o patch anterior tiver entrado.
s, n_canvas = re.subn(
    r'<canvas\s+ref=\{specCanvasRef\}\s+className="spec-video-canvas"\s*/>',
    img_block,
    s,
    count=1
)

# Se não havia canvas, substitui o img antigo do espectrograma.
if n_canvas == 0:
    s, n_img = re.subn(
        r'<img\s+[^>]*className=["\'][^"\']*spec-img[^"\']*["\'][\s\S]*?/>',
        img_block,
        s,
        count=1
    )
else:
    n_img = 0

p.write_text(s, encoding="utf-8")

print("OK — patch aplicado.")
print("Backup:", backup)
print("Canvas substituído:", n_canvas)
print("Imagem antiga substituída:", n_img)
