from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_fix_videoSpec_position")
backup.write_text(s, encoding="utf-8")

# Remove qualquer bloco videoSpec inserido em local errado.
s = re.sub(
    r'\n?\s*// Frame de vídeo contínuo do painel esquerdo\.[\s\S]*?const videoSpec = useMemo\(\(\) => \{[\s\S]*?\}, \[spectrograms, frames, frameIndex, currentSpec\]\);\n?',
    '\n',
    s
)

video_block = r'''
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

# Insere antes do return JSX principal. Usamos o último "return (" do arquivo.
marker = "\n  return ("
pos = s.rfind(marker)

if pos < 0:
    raise RuntimeError("Não encontrei o return principal do componente.")

s = s[:pos] + "\n" + video_block + s[pos:]

p.write_text(s, encoding="utf-8")

print("OK — videoSpec movido para dentro do componente.")
print("Backup:", backup)
