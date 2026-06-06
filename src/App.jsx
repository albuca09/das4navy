import { useEffect, useRef, useState } from "react";
import "./App.css";

const FREQS = [0.6, 10, 20, 40, 80, 160, 320];

function randomEnergy(x, y, t, freq) {
  const a = Math.sin(x * 0.018 + t * 0.018 + freq * 0.04);
  const b = Math.cos(y * 0.026 - t * 0.012 + freq * 0.01);
  const c = Math.sin((x + y) * 0.012 + t * 0.02);
  return Math.max(0, (a + b + c + 1.2) / 4);
}

function drawSpectrogram(ctx, w, h, t, activeFreq) {
  const img = ctx.createImageData(w, h);
  const data = img.data;

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let v =
        0.28 * Math.sin(x * 0.035 + y * 0.018 + t * 0.03) +
        0.22 * Math.cos(x * 0.012 - y * 0.042 + t * 0.018) +
        0.18 * Math.sin((x + y) * 0.025 + activeFreq * 0.08);

      const event1 = Math.abs(x - ((y * 0.85 + t * 1.5) % w)) < 3 ? 1.4 : 0;
      const event2 = Math.abs(x - ((w - y * 0.65 + t * 1.1) % w)) < 2 ? 1.0 : 0;
      const vertical = Math.abs(x - w * 0.48) < 2 ? 1.2 : 0;
      const lowBand = y > h * 0.68 && y < h * 0.72 ? 1.5 : 0;

      v = Math.max(0, v + event1 + event2 + vertical + lowBand);
      v = Math.min(1, v);

      const i = (y * w + x) * 4;

      data[i] = 10 + v * 220;
      data[i + 1] = 35 + Math.pow(v, 1.7) * 220;
      data[i + 2] = 70 + (1 - v) * 120;
      data[i + 3] = 255;
    }
  }

  ctx.putImageData(img, 0, 0);

  ctx.strokeStyle = "rgba(255, 0, 0, 0.95)";
  ctx.lineWidth = 3;
  const lineY = h * 0.69;
  ctx.beginPath();
  ctx.moveTo(0, lineY);
  ctx.lineTo(w, lineY);
  ctx.stroke();

  ctx.strokeStyle = "rgba(255, 68, 220, 0.85)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(w * 0.48, 0);
  ctx.lineTo(w * 0.48, h);
  ctx.stroke();

  ctx.fillStyle = "rgba(0,0,0,0.55)";
  ctx.fillRect(w - 170, lineY - 18, 150, 36);
  ctx.strokeStyle = "red";
  ctx.strokeRect(w - 170, lineY - 18, 150, 36);
  ctx.fillStyle = "#ff3030";
  ctx.font = "bold 18px monospace";
  ctx.fillText("18:07:54", w - 153, lineY + 6);
}

function drawMap(ctx, w, h, t, activeFreq) {
  ctx.clearRect(0, 0, w, h);

  const grad = ctx.createRadialGradient(w * 0.45, h * 0.45, 30, w * 0.45, h * 0.45, w);
  grad.addColorStop(0, "#222");
  grad.addColorStop(1, "#050505");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  ctx.save();
  ctx.translate(w * 0.05, h * 0.02);
  ctx.rotate(-0.12);

  ctx.strokeStyle = "rgba(120,120,120,0.32)";
  ctx.lineWidth = 2;

  for (let i = -2; i < 12; i++) {
    ctx.beginPath();
    ctx.moveTo(i * 120, -50);
    ctx.lineTo(i * 120 + 120, h + 80);
    ctx.stroke();
  }

  for (let j = 0; j < 10; j++) {
    ctx.beginPath();
    ctx.moveTo(-80, j * 85);
    ctx.lineTo(w + 120, j * 85 - 40);
    ctx.stroke();
  }

  ctx.fillStyle = "rgba(120,120,120,0.38)";
  for (let i = 0; i < 32; i++) {
    const x = 80 + (i % 8) * 150 + Math.sin(i) * 25;
    const y = 70 + Math.floor(i / 8) * 130 + Math.cos(i) * 20;
    ctx.fillRect(x, y, 70 + (i % 3) * 30, 40 + (i % 4) * 18);
  }

  ctx.restore();

  const path = [
    [w * 0.26, h * 0.18],
    [w * 0.46, h * 0.16],
    [w * 0.52, h * 0.31],
    [w * 0.84, h * 0.36],
    [w * 0.82, h * 0.72],
    [w * 0.62, h * 0.78],
    [w * 0.35, h * 0.68],
    [w * 0.38, h * 0.35],
    [w * 0.26, h * 0.18],
  ];

  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  ctx.strokeStyle = "rgba(70,150,255,0.35)";
  ctx.lineWidth = 22;
  ctx.beginPath();
  path.forEach(([x, y], idx) => {
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.strokeStyle = "rgba(120,200,255,0.95)";
  ctx.lineWidth = 4;
  ctx.beginPath();
  path.forEach(([x, y], idx) => {
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  for (let i = 0; i < path.length - 1; i++) {
    const [x1, y1] = path[i];
    const [x2, y2] = path[i + 1];

    for (let s = 0; s <= 1; s += 0.04) {
      const x = x1 + (x2 - x1) * s;
      const y = y1 + (y2 - y1) * s;
      const e = randomEnergy(x, y, t, activeFreq);

      if (e > 0.42) {
        const r = 4 + e * 20;
        const height = 10 + e * 55;

        const g = ctx.createRadialGradient(x, y - height, 2, x, y, r);
        g.addColorStop(0, `rgba(220,255,30,${0.9 * e})`);
        g.addColorStop(0.45, `rgba(90,220,255,${0.45 * e})`);
        g.addColorStop(1, "rgba(50,120,255,0)");

        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.ellipse(x, y - height * 0.25, r, r * 0.65, 0, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = `rgba(170,230,255,${0.3 * e})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, y - height);
        ctx.stroke();
      }
    }
  }

  const selected = path[3];
  ctx.fillStyle = "#ff4fb3";
  ctx.beginPath();
  ctx.arc(selected[0], selected[1], 11, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "white";
  ctx.font = "bold 42px Arial";
  ctx.fillText("DAS4Navy", 36, 64);

  ctx.fillStyle = "rgba(255,255,255,0.72)";
  ctx.font = "15px Arial";
  ctx.fillText("Distributed Acoustic Sensing Visualizer", 40, 92);
}

export default function App() {
  const specRef = useRef(null);
  const mapRef = useRef(null);
  const [activeFreq, setActiveFreq] = useState(0.6);
  const [running, setRunning] = useState(true);

  useEffect(() => {
    let raf;
    let t = 0;

    function resizeCanvas(canvas) {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      return [ctx, rect.width, rect.height];
    }

    function loop() {
      if (running) t += 1;

      const spec = specRef.current;
      const map = mapRef.current;

      if (spec && map) {
        const [sctx, sw, sh] = resizeCanvas(spec);
        const [mctx, mw, mh] = resizeCanvas(map);
        drawSpectrogram(sctx, Math.floor(sw), Math.floor(sh), t, activeFreq);
        drawMap(mctx, mw, mh, t, activeFreq);
      }

      raf = requestAnimationFrame(loop);
    }

    loop();

    window.addEventListener("resize", loop);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", loop);
    };
  }, [activeFreq, running]);

  return (
    <main className="app">
      <section className="spectrogram-panel">
        <canvas ref={specRef} />
      </section>

      <section className="map-panel">
        <canvas ref={mapRef} />

        <div className="frequency-menu">
          {FREQS.map((f) => (
            <button
              key={f}
              className={activeFreq === f ? "active" : ""}
              onClick={() => setActiveFreq(f)}
            >
              {f} Hz
            </button>
          ))}
        </div>

        <button className="reset" onClick={() => setRunning((v) => !v)}>
          {running ? "Pause" : "Play"}
        </button>

        <div className="info-box">
          <strong>Selected band:</strong> {activeFreq} Hz<br />
          Synthetic demonstration inspired by distributed acoustic sensing.
        </div>
      </section>
    </main>
  );
}
