from pathlib import Path
import re

p = Path(r"C:\Users\Luis\Desktop\das4navy\src\components\Das4NavySyncedViewer.jsx")
s = p.read_text(encoding="utf-8")

backup = p.with_suffix(".jsx.bak_spec_video")
backup.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------
# 1) Adiciona refs do canvas dentro do componente
# ---------------------------------------------------------------------
needle = 'const [manifestSpecs, setManifestSpecs] = useState([]);'

insert = '''const [manifestSpecs, setManifestSpecs] = useState([]);

  // Painel esquerdo: vídeo contínuo de espectrogramas/XAI via canvas.
  const specCanvasRef = useRef(null);
  const specImageCacheRef = useRef(new Map());'''

if needle in s and "specCanvasRef" not in s:
    s = s.replace(needle, insert)

# ---------------------------------------------------------------------
# 2) Adiciona efeito que desenha o frame atual no canvas
# ---------------------------------------------------------------------
effect = r'''
  // Renderiza o espectrograma como vídeo contínuo sincronizado com frameIndex/currentSpec.
  useEffect(() => {
    const canvas = specCanvasRef.current;

    if (!canvas || !currentSpec || !currentSpec.image_url) {
      return;
    }

    let cancelled = false;

    const url = assetUrl(currentSpec.image_url);
    const cache = specImageCacheRef.current;

    function fitCanvas() {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;

      const w = Math.max(2, Math.floor(rect.width * dpr));
      const h = Math.max(2, Math.floor(rect.height * dpr));

      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      return { w, h };
    }

    function drawImage(img) {
      if (cancelled || !img) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const { w, h } = fitCanvas();

      ctx.clearRect(0, 0, w, h);

      // Recorte para remover título/eixos do Matplotlib e deixar só a região útil.
      const sx = img.width * 0.08;
      const sy = img.height * 0.10;
      const sw = img.width * 0.84;
      const sh = img.height * 0.78;

      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, w, h);

      // Vinheta leve para dar aspecto de vídeo/tela.
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, "rgba(0,0,0,0.20)");
      grad.addColorStop(0.50, "rgba(0,0,0,0.00)");
      grad.addColorStop(1, "rgba(0,0,0,0.24)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
    }

    const cached = cache.get(url);

    if (cached && cached.complete) {
      drawImage(cached);
    } else {
      const img = new Image();
      img.onload = () => {
        cache.set(url, img);
        drawImage(img);
      };
      img.onerror = () => {
        console.warn("Falha ao carregar frame do espectrograma:", url);
      };
      img.src = url;
    }

    // Pré-carrega alguns frames próximos para a troca ficar mais fluida.
    if (Array.isArray(spectrograms) && spectrograms.length > 1) {
      const idx = spectrograms.findIndex((x) => x && x.image_url === currentSpec.image_url);
      for (let k = 1; k <= 4; k += 1) {
        const next = spectrograms[idx + k];
        if (next && next.image_url) {
          const nextUrl = assetUrl(next.image_url);
          if (!cache.has(nextUrl)) {
            const pre = new Image();
            pre.onload = () => cache.set(nextUrl, pre);
            pre.src = nextUrl;
          }
        }
      }
    }

    return () => {
      cancelled = true;
    };
  }, [currentSpec, frameIndex, spectrograms]);
'''

if "Renderiza o espectrograma como vídeo contínuo" not in s:
    marker = "\n  return ("
    if marker not in s:
        raise RuntimeError("Não encontrei o início do return do componente.")
    s = s.replace(marker, "\n" + effect + marker, 1)

# ---------------------------------------------------------------------
# 3) Substitui a imagem <img className='spec-img'> por canvas
# ---------------------------------------------------------------------
pattern = r'<img\s+[^>]*className=["\']spec-img["\'][\s\S]*?/>'

replacement = '<canvas ref={specCanvasRef} className="spec-video-canvas" />'

s2, n = re.subn(pattern, replacement, s, count=1)

if n == 0:
    print("AVISO: não encontrei <img className='spec-img'>. Tentando substituição alternativa.")
    pattern2 = r'<img\s+[^>]*spec-img[^>]*>'
    s2, n = re.subn(pattern2, replacement, s, count=1)

if n == 0:
    print("AVISO: nenhum <img> de espectrograma foi substituído. Verifique manualmente.")
else:
    s = s2

p.write_text(s, encoding="utf-8")

print("OK — painel esquerdo convertido para vídeo contínuo via canvas.")
print("Backup:", backup)
