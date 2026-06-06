import { useEffect, useRef, useState } from "react";
import "./App.css";

const FREQS = [0.6, 10, 20, 40, 80, 160, 320];

const CABLE_PATH_NORM = [
  [0.26, 0.18],
  [0.46, 0.16],
  [0.52, 0.31],
  [0.84, 0.36],
  [0.82, 0.72],
  [0.62, 0.78],
  [0.35, 0.68],
  [0.38, 0.35],
  [0.26, 0.18],
];

function clamp(v, a, b) {
  return Math.max(a, Math.min(b, v));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function dist(a, b) {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  return Math.sqrt(dx * dx + dy * dy);
}

function buildPathPoints(w, h) {
  const pts = CABLE_PATH_NORM.map(([x, y]) => [x * w, y * h]);
  const dense = [];

  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    const d = dist(a, b);
    const steps = Math.max(8, Math.floor(d / 8));

    for (let j = 0; j < steps; j++) {
      const t = j / steps;
      dense.push([lerp(a[0], b[0], t), lerp(a[1], b[1], t)]);
    }
  }

  return dense;
}

function movingPulseEnergy(s, time, activeFreq) {
  const freqFactor = Math.log2(activeFreq + 1);
  const speed1 = 0.035 + freqFactor * 0.002;
  const speed2 = 0.021 + freqFactor * 0.0015;
  const speed3 = 0.014 + freqFactor * 0.001;

  const p1 = (time * speed1) % 1;
  const p2 = (0.35 + time * speed2) % 1;
  const p3 = (0.72 - time * speed3 + 1) % 1;

  const pulse = (p, width, amp) => {
    const d = Math.min(Math.abs(s - p), 1 - Math.abs(s - p));
    return amp * Math.exp(-(d * d) / (2 * width * width));
  };

  const standing =
    0.18 * Math.sin(34 * s + time * 0.06) +
    0.12 * Math.sin(77 * s - time * 0.035) +
    0.08 * Math.cos(121 * s + activeFreq * 0.04);

  const e =
    pulse(p1, 0.025, 1.1) +
    pulse(p2, 0.038, 0.9) +
    pulse(p3, 0.018, 0.8) +
    standing;

  return clamp(e, 0, 1.35);
}

function drawSpectrogram(ctx, w, h, time, activeFreq) {
  const image = ctx.createImageData(w, h);
  const data = image.data;

  const scroll = time * 2.2;
  const freqFactor = Math.log2(activeFreq + 1);

  for (let y = 0; y < h; y++) {
    const yy = y + scroll;

    for (let x = 0; x < w; x++) {
      const nx = x / w;
      const ny = yy / h;

      let v = 0;

      v += 0.22 * Math.sin(nx * 95 + ny * 42 + time * 0.02);
      v += 0.18 * Math.cos(nx * 39 - ny * 88 + activeFreq * 0.015);
      v += 0.15 * Math.sin((nx + ny) * 170 + time * 0.04);

      const lowHorizontal = Math.abs(y - h * 0.69) < 4 ? 1.2 : 0;
      const magentaColumn = Math.abs(x - w * 0.50) < 2 ? 1.1 : 0;

      const diagonal1 =
        Math.abs(x - ((yy * 0.68 + 60 * Math.sin(yy * 0.015)) % w)) < 3
          ? 1.1
          : 0;

      const diagonal2 =
        Math.abs(x - ((w - yy * 0.48 + 80 * Math.cos(yy * 0.011)) % w)) < 3
          ? 0.9
          : 0;

      const comb =
        Math.abs(Math.sin((x * 0.032 + yy * 0.011 + freqFactor) * Math.PI)) > 0.985
          ? 0.55
          : 0;

      const burstZone =
        Math.sin(yy * 0.026 + time * 0.04) > 0.72 &&
        Math.sin(x * 0.035 + yy * 0.012) > 0.55
          ? 0.8
          : 0;

      v += diagonal1 + diagonal2 + comb + burstZone + lowHorizontal + magentaColumn;
      v += 0.18 * Math.random();

      v = clamp(v, 0, 1);

      const i = (y * w + x) * 4;

      const blue = 80 + 140 * (1 - v);
      const green = 35 + 230 * Math.pow(v, 1.4);
      const red = 8 + 245 * Math.pow(v, 2.3);

      data[i] = red;
      data[i + 1] = green;
      data[i + 2] = blue;
      data[i + 3] = 255;
    }
  }

  ctx.putImageData(image, 0, 0);

  const cursorY = h * 0.69;

  ctx.strokeStyle = "rgba(255, 0, 0, 0.96)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(0, cursorY);
  ctx.lineTo(w, cursorY);
  ctx.stroke();

  ctx.strokeStyle = "rgba(255, 58, 220, 0.9)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(w * 0.5, 0);
  ctx.lineTo(w * 0.5, h);
  ctx.stroke();

  ctx.fillStyle = "rgba(0,0,0,0.72)";
  ctx.beginPath();
  ctx.roundRect(w - 172, cursorY - 18, 148, 36, 18);
  ctx.fill();

  ctx.strokeStyle = "rgba(255, 0, 0, 0.95)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(w - 172, cursorY - 18, 148, 36, 18);
  ctx.stroke();

  ctx.fillStyle = "#ff3030";
  ctx.font = "bold 18px monospace";
  ctx.fillText("18:07:54", w - 153, cursorY + 6);
}

function drawBaseMap(ctx, w, h) {
  const grad = ctx.createRadialGradient(
    w * 0.47,
    h * 0.46,
    20,
    w * 0.48,
    h * 0.5,
    w * 0.95
  );

  grad.addColorStop(0, "#252525");
  grad.addColorStop(0.55, "#111");
  grad.addColorStop(1, "#020202");

  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  ctx.save();
  ctx.translate(w * 0.02, h * 0.0);
  ctx.rotate(-0.12);

  ctx.strokeStyle = "rgba(180,180,180,0.22)";
  ctx.lineWidth = 2;

  for (let i = -4; i < 14; i++) {
    ctx.beginPath();
    ctx.moveTo(i * 120, -80);
    ctx.lineTo(i * 120 + 130, h + 100);
    ctx.stroke();
  }

  for (let j = -1; j < 12; j++) {
    ctx.beginPath();
    ctx.moveTo(-120, j * 82);
    ctx.lineTo(w + 150, j * 82 - 45);
    ctx.stroke();
  }

  ctx.setLineDash([2, 7]);
  ctx.strokeStyle = "rgba(210,210,210,0.18)";

  for (let j = 0; j < 9; j++) {
    ctx.beginPath();
    ctx.moveTo(-50, j * 95 + 30);
    ctx.lineTo(w + 100, j * 95 + 5);
    ctx.stroke();
  }

  ctx.setLineDash([]);

  ctx.fillStyle = "rgba(130,130,130,0.35)";

  for (let i = 0; i < 38; i++) {
    const x = 70 + (i % 9) * 138 + Math.sin(i * 1.7) * 30;
    const y = 65 + Math.floor(i / 9) * 125 + Math.cos(i * 1.3) * 24;
    const bw = 55 + (i % 4) * 22;
    const bh = 38 + (i % 5) * 13;
    ctx.fillRect(x, y, bw, bh);
  }

  ctx.restore();
}

function drawCable(ctx, w, h, time, activeFreq) {
  const path = CABLE_PATH_NORM.map(([x, y]) => [x * w, y * h]);
  const dense = buildPathPoints(w, h);

  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  ctx.shadowColor = "rgba(80,160,255,0.8)";
  ctx.shadowBlur = 16;

  ctx.strokeStyle = "rgba(45,115,255,0.32)";
  ctx.lineWidth = 24;
  ctx.beginPath();

  path.forEach(([x, y], i) => {
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.stroke();

  ctx.shadowBlur = 0;
  ctx.strokeStyle = "rgba(125,205,255,0.9)";
  ctx.lineWidth = 4;
  ctx.beginPath();

  path.forEach(([x, y], i) => {
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.stroke();

  for (let i = 0; i < dense.length; i++) {
    const s = i / Math.max(1, dense.length - 1);
    const [x, y] = dense[i];
    const e = movingPulseEnergy(s, time, activeFreq);

    if (e < 0.18) continue;

    const wave = 0.5 + 0.5 * Math.sin(time * 0.11 + s * 95);
    const r = 5 + e * 20;
    const lift = 8 + e * 58 + wave * 16;

    const g = ctx.createRadialGradient(x, y - lift, 2, x, y, r * 1.8);
    g.addColorStop(0, `rgba(230,255,20,${0.85 * e})`);
    g.addColorStop(0.38, `rgba(125,235,255,${0.5 * e})`);
    g.addColorStop(0.72, `rgba(35,110,255,${0.28 * e})`);
    g.addColorStop(1, "rgba(20,60,200,0)");

    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.ellipse(x, y - lift * 0.32, r * 1.3, r * 0.72, 0, 0, Math.PI * 2);
    ctx.fill();

    if (e > 0.55) {
      ctx.strokeStyle = `rgba(190,240,255,${0.35 * e})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x, y - lift);
      ctx.stroke();
    }
  }

  const selectedIndex = Math.floor(((time * 0.018) % 1) * dense.length);
  const selected = dense[selectedIndex] || path[3];

  ctx.shadowColor = "rgba(255,70,180,0.9)";
  ctx.shadowBlur = 16;
  ctx.fillStyle = "#ff4fb3";
  ctx.beginPath();
  ctx.arc(selected[0], selected[1], 10, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
}

function drawLabels(ctx, w, h) {
  ctx.fillStyle = "white";
  ctx.font = "bold 46px Arial";
  ctx.fillText("DAS4Navy", 36, 64);

  ctx.fillStyle = "rgba(255,255,255,0.68)";
  ctx.font = "15px Arial";
  ctx.fillText("Distributed Acoustic Sensing Visualizer", 40, 92);
}

function drawMap(ctx, w, h, time, activeFreq) {
  ctx.clearRect(0, 0, w, h);
  drawBaseMap(ctx, w, h);
  drawCable(ctx, w, h, time, activeFreq);
  drawLabels(ctx, w, h);
}

export default function App() {
  const specRef = useRef(null);
  const mapRef = useRef(null);
  const animationRef = useRef(null);

  const [activeFreq, setActiveFreq] = useState(0.6);
  const [running, setRunning] = useState(true);

  useEffect(() => {
    let time = 0;

    function prepareCanvas(canvas) {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;

      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);

      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      return [ctx, width, height];
    }

    function loop() {
      if (running) time += 1;

      const specCanvas = specRef.current;
      const mapCanvas = mapRef.current;

      if (specCanvas && mapCanvas) {
        const [specCtx, sw, sh] = prepareCanvas(specCanvas);
        const [mapCtx, mw, mh] = prepareCanvas(mapCanvas);

        drawSpectrogram(specCtx, sw, sh, time, activeFreq);
        drawMap(mapCtx, mw, mh, time, activeFreq);
      }

      animationRef.current = requestAnimationFrame(loop);
    }

    loop();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
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
          Waterfall cursor + moving energy pulses along the sensing cable.
        </div>
      </section>
    </main>
  );
}
