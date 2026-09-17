#!/usr/bin/env python3
"""
viz-gantt.py — Genera visualización tipo Gantt de actividad por proyecto/día.

Lee data/usage_report_v3.json (sección project_daily) y produce un HTML
autocontenido (sin dependencias externas) en data/gantt-multitasking.html:

  - Fila superior: concurrencia diaria (proyectos distintos activos por día)
  - Matriz proyecto × día: intensidad = interacciones (escala log), con
    toggle a modo presencia (activo/inactivo)
  - Fines de semana sombreados, tooltips con detalle por celda
"""

import json
from pathlib import Path

REPORT = Path("data/usage_report_v3.json")
OUT = Path("data/gantt-multitasking.html")

TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Multitasking — actividad por proyecto/día</title>
<style>
  :root {
    --bg: #16161d; --fg: #d8d8e0; --muted: #7a7a8a;
    --accent: #ff9f43; --grid: #23232e;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px; background: var(--bg); color: var(--fg);
    font: 13px/1.5 ui-monospace, "JetBrains Mono", Menlo, monospace;
  }
  h1 { font-size: 18px; margin: 0 0 4px; }
  .sub { color: var(--muted); margin-bottom: 16px; }
  .controls { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; }
  .controls button {
    background: transparent; color: var(--muted); border: 1px solid var(--grid);
    padding: 4px 12px; cursor: pointer; font: inherit; border-radius: 3px;
  }
  .controls button.on { color: var(--bg); background: var(--accent); border-color: var(--accent); }
  #legend { margin-left: auto; color: var(--muted); display: flex; gap: 4px; align-items: center; }
  #legend .sw { width: 22px; height: 12px; display: inline-block; border-radius: 2px; }
  .wrap { overflow-x: auto; }
  .grid { display: grid; position: relative; }
  .cell { width: 14px; height: 18px; border-radius: 2px; }
  .label {
    position: sticky; left: 0; z-index: 2; background: var(--bg);
    padding-right: 8px; white-space: nowrap; text-align: right;
    font-size: 12px; overflow: hidden; text-overflow: ellipsis; max-width: 190px;
  }
  .rowhead { height: 22px; }
  .weekend { background: rgba(255,255,255,0.035); }
  .monthtick { font-size: 10px; color: var(--muted); white-space: nowrap; overflow: visible; }
  #tip {
    position: fixed; display: none; pointer-events: none; z-index: 10;
    background: #26262f; border: 1px solid #3a3a48; padding: 8px 10px;
    border-radius: 4px; font-size: 12px; max-width: 340px; box-shadow: 0 4px 14px rgba(0,0,0,.5);
  }
  #tip b { color: var(--accent); }
  #tip .o { color: var(--muted); }
</style>
</head>
<body>
<h1>Multitasking — trabajo concurrente por proyecto</h1>
<div class="sub">__SUB__</div>
<div class="controls">
  <button id="b-int" class="on">interacciones</button>
  <button id="b-bin">activo/inactivo</button>
  <div id="legend"></div>
</div>
<div class="wrap"><div id="grid" class="grid"></div><div id="empty" style="display:none;color:var(--muted)">Sin datos: ejecuta primero <code>python scripts/usage-tracker.py</code></div></div>
<div id="tip"></div>
<script>
const DATA = __DATA__;
const days = DATA.days, projects = Object.keys(DATA.matrix), M = DATA.matrix;
const grid = document.getElementById('grid');
const tip = document.getElementById('tip');
let mode = 'int';

const NCOL = days.length, NROW = projects.length;
const LABEL_W = 190, CW = 14, CH = 18;
if (!NCOL) { document.getElementById('empty').style.display = 'block'; throw new Error('sin datos'); }

// fecha -> índice; weekend set (parsear como UTC: getUTCDay sobre hora local
// desplaza un día en zonas UTC+, ver CORR-001 del review)
const isWeekend = days.map(d => { const dt = new Date(d + 'T00:00:00Z'); const w = dt.getUTCDay(); return w === 0 || w === 6; });

function dayTotals(i) {
  let tot = 0, nproj = 0;
  for (const p of projects) { const v = M[p][i]; if (v > 0) { tot += v; nproj++; } }
  return { tot, nproj };
}
const dayInfo = days.map((_, i) => dayTotals(i));
const maxCount = Math.max(...projects.flatMap(p => M[p]), 1);
const logMax = Math.log(1 + maxCount);

function colorInt(v) {
  if (!v) return 'transparent';
  const t = Math.log(1 + v) / logMax;
  return `rgba(255,159,67,${0.15 + 0.85 * Math.pow(t, 0.7)})`;
}
function colorBin(v) { return v ? 'rgba(255,159,67,0.85)' : 'transparent'; }
const color = v => mode === 'int' ? colorInt(v) : colorBin(v);
const legendHTML = m => m === 'int'
  ? 'menos ' + [0.2, 0.45, 0.7, 0.95].map(a => `<span class="sw" style="background:rgba(255,159,67,${a})"></span>`).join('') + ' más'
  : '<span class="sw" style="background:rgba(255,159,67,0.85)"></span> activo';

function fmt(n) { return n.toLocaleString('es'); }
function dateEs(d) { return new Date(d + 'T00:00').toLocaleDateString('es', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }); }

let html = [];
// fila de ticks de mes
html.push(`<div class="label rowhead"></div>`);
for (let i = 0; i < NCOL; i++) {
  const d = days[i];
  const tick = d.endsWith('-01') ? d.slice(0, 7) : (i % 14 === 0 ? d.slice(8) : '');
  html.push(`<div class="monthtick${isWeekend[i] ? ' weekend' : ''}" style="width:${CW}px">${tick}</div>`);
}
// fila de concurrencia diaria
html.push(`<div class="label" title="concurrencia diaria: proyectos distintos activos por día (la intensidad satura en 12)">→ proyectos/día</div>`);
for (let i = 0; i < NCOL; i++) {
  const { nproj } = dayInfo[i];
  const t = nproj ? 0.15 + 0.85 * Math.min(1, nproj / 12) : 0;
  html.push(`<div class="cell${isWeekend[i] ? ' weekend' : ''}" data-day="${i}" data-conc="1" style="background:${nproj ? `rgba(120,180,255,${t})` : 'transparent'}"></div>`);
}
// filas por proyecto
for (const p of projects) {
  html.push(`<div class="label" title="${p}">${p}</div>`);
  for (let i = 0; i < NCOL; i++) {
    const v = M[p][i];
    html.push(`<div class="cell${isWeekend[i] ? ' weekend' : ''}" data-p="${p}" data-i="${i}" style="background:${color(v)}"></div>`);
  }
}
grid.style.gridTemplateColumns = `${LABEL_W}px repeat(${NCOL}, ${CW}px)`;
grid.style.gridAutoRows = 'minmax(18px, auto)';
grid.style.gap = '2px 1px';
grid.innerHTML = html.join('');

// leyenda
const lg = document.getElementById('legend');
lg.innerHTML = legendHTML(mode);

// tooltip
document.addEventListener('mousemove', e => {
  const el = e.target.closest('.cell');
  if (!el) { tip.style.display = 'none'; return; }
  let body;
  if (el.dataset.conc) {
    const i = +el.dataset.day, { tot, nproj } = dayInfo[i];
    const act = projects.filter(p => M[p][i] > 0);
    body = `<b>${dateEs(days[i])}</b><br>${nproj} proyectos simultáneos · ${fmt(tot)} interacciones<br><span class="o">${act.join(', ') || 'sin actividad'}</span>`;
  } else {
    const i = +el.dataset.i, v = M[el.dataset.p][i];
    const { nproj } = dayInfo[i];
    body = `<b>${el.dataset.p}</b> — ${dateEs(days[i])}<br>${v ? fmt(v) + ' interacciones' : 'sin actividad'} · <span class="o">${nproj} proyectos ese día</span>`;
  }
  tip.innerHTML = body;
  tip.style.display = 'block';
  const x = Math.max(0, Math.min(e.clientX + 14, innerWidth - 360));
  tip.style.left = x + 'px';
  tip.style.top = (e.clientY + 14) + 'px';
});

// toggle de modo
const bi = document.getElementById('b-int'), bb = document.getElementById('b-bin');
function setMode(m) {
  mode = m;
  bi.classList.toggle('on', m === 'int'); bb.classList.toggle('on', m === 'bin');
  grid.querySelectorAll('.cell[data-p]').forEach(el => {
    el.style.background = color(M[el.dataset.p][+el.dataset.i]);
  });
  if (m === 'int') lg.innerHTML = legendHTML('int');
  else lg.innerHTML = legendHTML('bin');
}
bi.onclick = () => setMode('int');
bb.onclick = () => setMode('bin');
</script>
</body>
</html>
"""

def main():
    report = json.loads(REPORT.read_text())
    pd = report["project_daily"]
    meta = report["metadata"]
    mt = report["multitasking"]

    sub = (f"{meta['total_interactions']:,} interacciones · "
           f"{meta['total_projects']} proyectos · {meta['date_range']['start']} → {meta['date_range']['end']} · "
           f"{mt['hourly']['pct_hours_multitasking']}% de horas con ≥2 proyectos en paralelo")

    html = TEMPLATE.replace("__DATA__", json.dumps(pd, ensure_ascii=False)).replace("__SUB__", sub)
    OUT.write_text(html)
    print(f"OK → {OUT} ({OUT.stat().st_size // 1024} KB, {len(pd['days'])} días × {len(pd['matrix'])} proyectos)")

if __name__ == "__main__":
    main()
