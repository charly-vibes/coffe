#!/usr/bin/env python3
"""
viz-dashboard.py — Dashboard de insights de uso de IA.

Lee data/usage_report_v3.json y produce data/dashboard.html autocontenido
(sin dependencias externas, charts en SVG puro):

  - Tarjetas resumen: interacciones, costos, días, proyectos, multitasking
  - Tendencia mensual: interacciones (barras) + costo real (línea)
  - Costo efectivo mensual apilado por herramienta
  - Top proyectos por interacciones (con costo y rango de fechas)
  - Heatmap día-de-semana × hora
  - Top skills y comandos
  - Distribución de sesiones + autonomía
  - Timeline de herramientas (primera/última vez, derivado de monthly)

Uso: python3 scripts/viz-dashboard.py [reporte.json] [salida.html]
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPORT = Path("data/usage_report_v3.json")
OUT = Path("data/dashboard.html")

DOW = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MONTH_SHORT = {"01": "ene", "02": "feb", "03": "mar", "04": "abr",
               "05": "may", "06": "jun", "07": "jul", "08": "ago", "09": "sep",
               "10": "oct", "11": "nov", "12": "dic"}


def fmt_k(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def month_label(ym):
    y, m = ym.split("-")
    return f"{MONTH_SHORT.get(m, m)} {y[2:]}"


def prepare(report):
    meta = report["metadata"]
    monthly = report["monthly"]
    months = sorted(monthly.keys())

    # --- series mensuales ---
    months_data = []
    for ym in months:
        mo = monthly[ym]
        months_data.append({
            "label": month_label(ym),
            "interactions": mo["interactions"],
            "cost_effective": round(mo["cost_effective"], 2),
            "cost_real": round(mo["cost_real"], 2),
            "input_tokens": mo["input_tokens"],
            "output_tokens": mo["output_tokens"],
            "tools": mo["tools"],
            "models": mo["models"],
            "sub_fees": mo.get("subscription_fees", 0),
        })

    # --- proyectos: top por interacciones ---
    projects = report["projects"] if isinstance(report["projects"], list) \
        else [dict(name=k, **v) for k, v in report["projects"].items()]
    top_projects = sorted(projects, key=lambda p: p["interactions"], reverse=True)[:20]

    # --- heatmap dow × hour ---
    heat = [[0] * 24 for _ in range(7)]
    for key, hv in report["hourly"].items():
        dt = datetime.strptime(key, "%Y-%m-%d %H:%M")
        heat[dt.weekday()][dt.hour] += hv["interactions"]

    # --- herramientas: timeline derivado de monthly (primera/última vez) ---
    tool_first, tool_last, tool_total = {}, {}, defaultdict(int)
    for ym in months:
        for tool, cnt in monthly[ym]["tools"].items():
            tool_first.setdefault(tool, ym)
            tool_last[tool] = ym
            tool_total[tool] += cnt
    tools_timeline = sorted(
        ({"tool": t, "first": tool_first[t], "last": tool_last[t],
          "total": tool_total[t]} for t in tool_total),
        key=lambda x: x["first"],
    )

    # --- sesiones ---
    ss = report["sessions"]
    sessions = {
        "total": ss["total_sessions"],
        "with_agent": ss["with_agent"],
        "pct_agent": round(100 * ss["with_agent"] / ss["total_sessions"], 1) if ss["total_sessions"] else 0,
        "avg_turns": ss["avg_turns"],
        "length_distribution": dict(sorted(ss["length_distribution"].items())),
        "top_longest": ss["top_longest_by_turns"][:8],
    }

    mt = report["multitasking"]

    return {
        "meta": {
            "start": meta["date_range"]["start"],
            "end": meta["date_range"]["end"],
            "total": meta["total_interactions"],
            "cost_effective": meta["cost_total_effective"],
            "cost_real": meta["cost_total_real"],
            "days": meta["total_days"],
            "hours": meta["total_hours"],
            "projects": meta["total_projects"],
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "months": months_data,
        "projects": [
            {"name": p.get("name", p.get("project", "?")),
             "interactions": p["interactions"],
             "cost_effective": round(p.get("cost_effective", 0), 2),
             "cost_real": round(p.get("cost_real", 0), 2),
             "first": p.get("first_seen", ""),
             "last": p.get("last_seen", ""),
             "tools": p.get("tools", {})}
            for p in top_projects
        ],
        "skills": dict(sorted(report["skills"].items(), key=lambda kv: -kv[1])[:12]),
        "commands": dict(sorted(report["commands"].items(), key=lambda kv: -kv[1])[:12]),
        "heatmap": heat,
        "sessions": sessions,
        "tools_timeline": tools_timeline,
        "multitasking": {
            "pct_hours": mt["hourly"]["pct_hours_multitasking"],
            "avg_per_hour": mt["hourly"]["avg_projects_per_active_hour"],
            "pct_days": mt["daily"]["pct_days_multitasking"],
            "max": mt["hourly"]["max_projects_in_one_hour"],
        },
    }


TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Uso de IA — dashboard</title>
<style>
  :root {
    --bg: #16161d; --panel: #1c1c25; --fg: #d8d8e0; --muted: #7a7a8a;
    --accent: #ff9f43; --accent2: #4fc3f7; --grid: #23232e; --good: #66bb6a;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px; background: var(--bg); color: var(--fg);
    font: 13px/1.5 ui-monospace, "JetBrains Mono", Menlo, monospace;
  }
  h1 { font-size: 18px; margin: 0 0 2px; }
  h2 { font-size: 13px; color: var(--muted); margin: 28px 0 10px;
       text-transform: uppercase; letter-spacing: .08em; border-bottom: 1px solid var(--grid); padding-bottom: 6px; }
  .sub { color: var(--muted); margin-bottom: 20px; font-size: 12px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
  .card { background: var(--panel); border: 1px solid var(--grid); border-radius: 6px; padding: 12px 14px; }
  .card .v { font-size: 20px; color: var(--accent); }
  .card .l { color: var(--muted); font-size: 11px; margin-top: 2px; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 900px) { .row { grid-template-columns: 1fr; } }
  .panel { background: var(--panel); border: 1px solid var(--grid); border-radius: 6px; padding: 14px; }
  svg { display: block; width: 100%; height: auto; }
  svg text { fill: var(--muted); font: 10px ui-monospace, monospace; }
  .bar:hover { opacity: .8; }
  .tooltip { position: fixed; background: #26262f; border: 1px solid var(--grid); color: var(--fg);
             padding: 8px 10px; border-radius: 4px; font-size: 12px; pointer-events: none;
             display: none; z-index: 10; max-width: 340px; white-space: pre; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { color: var(--muted); text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--grid); }
  td { padding: 4px 8px; border-bottom: 1px solid var(--grid); }
  td.num, th.num { text-align: right; }
  tr:hover td { background: #22222d; }
  .legend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; font-size: 11px; color: var(--muted); }
  .legend span::before { content: "■ "; }
  footer { color: var(--muted); font-size: 11px; margin-top: 24px; }
</style>
</head>
<body>
<h1>Uso de IA — dashboard</h1>
<div class="sub" id="subtitle"></div>
<div class="tooltip" id="tip"></div>

<h2>Resumen</h2>
<div class="cards" id="cards"></div>

<h2>Tendencia mensual — interacciones y costo real</h2>
<div class="panel"><div id="chart-monthly"></div><div class="legend"><span style="color:var(--accent)">interacciones</span><span style="color:var(--accent2)">costo real $</span></div></div>

<h2>Costo efectivo por mes y herramienta</h2>
<div class="panel"><div id="chart-tools-cost"></div><div class="legend" id="legend-tools"></div></div>

<h2>Top 20 proyectos</h2>
<div class="panel"><div id="chart-projects"></div></div>

<h2>Cuándo se usa: día de la semana × hora</h2>
<div class="panel"><div id="chart-heatmap"></div></div>

<div class="row">
  <div>
    <h2>Top skills</h2>
    <div class="panel"><div id="chart-skills"></div></div>
  </div>
  <div>
    <h2>Top comandos slash</h2>
    <div class="panel"><div id="chart-commands"></div></div>
  </div>
</div>

<div class="row">
  <div>
    <h2>Sesiones</h2>
    <div class="panel"><div id="chart-sessions"></div>
    <div id="sessions-summary" class="sub" style="margin-top:8px"></div>
    <table id="sessions-table" style="margin-top:10px"></table>
    </div>
  </div>
  <div>
    <h2>Timeline de herramientas</h2>
    <div class="panel"><table id="tools-table"></table></div>
  </div>
</div>

<footer id="footer" style="margin-top:24px"></footer>
<script>
const D = __DATA__;

// ---------- helpers ----------
const tip = document.getElementById('tip');
function showTip(e, txt) {
  tip.textContent = txt; tip.style.display = 'block';
  tip.style.left = Math.min(e.clientX + 14, innerWidth - 360) + 'px';
  tip.style.top = (e.clientY + 14) + 'px';
}
function hideTip() { tip.style.display = 'none'; }
document.addEventListener('mousemove', e => { if (tip.style.display === 'block') {
  tip.style.left = Math.min(e.clientX + 14, innerWidth - 360) + 'px';
  tip.style.top = (e.clientY + 14) + 'px';
}});

function svgEl(w, h) {
  const NS = 'http://www.w3.org/2000/svg';
  const s = document.createElementNS(NS, 'svg');
  s.setAttribute('viewBox', `0 0 ${w} ${h}`);
  return s;
}
function line(svg, x1, y1, x2, y2, color, dash) {
  const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  l.setAttribute('x1', x1); l.setAttribute('y1', y1);
  l.setAttribute('x2', x2); l.setAttribute('y2', y2);
  l.setAttribute('stroke', color || '#23232e');
  if (dash) l.setAttribute('stroke-dasharray', dash);
  svg.appendChild(l);
  return l;
}
function text(svg, x, y, str, size, anchor, fill) {
  const t = document.createElementNS('text');
  t.setAttribute('x', x); t.setAttribute('y', y);
  t.setAttribute('font-size', size || 9);
  if (anchor) t.setAttribute('text-anchor', anchor);
  if (fill) t.setAttribute('fill', fill);
  t.textContent = str;
  svg.appendChild(t);
  return t;
}
function rect(svg, x, y, w, h, fill, cls) {
  const r = document.createElementNS('rect');
  r.setAttribute('x', x); r.setAttribute('y', y);
  r.setAttribute('width', Math.max(0, w)); r.setAttribute('height', Math.max(0, h));
  r.setAttribute('fill', fill); r.setAttribute('rx', 1);
  if (cls) r.setAttribute('class', cls);
  svg.appendChild(r);
  return r;
}
const fmtInt = n => n.toLocaleString('en-US');
const fmtMoney = n => '$' + n.toLocaleString('en-US', {maximumFractionDigits: n < 100 ? 2 : 0});
const fmtK = n => n >= 1e6 ? (n/1e6).toFixed(1) + 'M' : n >= 1000 ? Math.round(n/1000) + 'K' : String(Math.round(n));

// ---------- resumen (cards) ----------
{
  const m = D.meta;
  document.getElementById('subtitle').textContent =
    `${m.start} → ${m.end} · generado ${m.generated} · fuente: usage_report_v3.json`;
  const cards = [
    [fmtInt(m.total), 'interacciones'],
    [fmtMoney(m.cost_effective), 'costo efectivo'],
    [fmtMoney(m.cost_real), 'costo real'],
    [m.days, 'días activos'],
    [m.hours, 'horas con actividad'],
    [m.projects, 'proyectos'],
    [D.multitasking.pct_hours + '%', 'horas con ≥2 proyectos'],
    [D.sessions.total, 'sesiones'],
  ];
  document.querySelector('.cards').innerHTML =
    cards.map(c => `<div class="card"><div class="v">${c[0]}</div><div class="l">${c[1]}</div></div>`).join('');
}

// ---------- chart 1: mensual interacciones + costo real ----------
{
  const W = 800, H = 240, padL = 60, padR = 60, padT = 20, padB = 34;
  const svg = svgEl(W, H);
  const data = D.months, n = data.length;
  const maxI = Math.max(...data.map(d => d.interactions));
  const maxC = Math.max(...data.map(d => d.cost_real), 1);
  const iw = (W - padL - padR) / n;
  const yI = v => padT + (H - padT - padB) * (1 - v / maxI);
  const yC = v => padT + (H - padT - padB) * (1 - v / maxC);
  // grid
  for (let g = 0; g <= 4; g++) {
    const y = padT + (H - padT - padB) * g / 4;
    line(svg, padL, y, W - padR, y);
    text(svg, padL - 6, y + 3, fmtK(maxI * (4 - g) / 4), 9, 'end');
  }
  data.forEach((d, i) => {
    const x = padL + iw * i;
    const bw = Math.min(38, iw * 0.55);
    const bx = x + (iw - bw) / 2;
    const by = yI(d.interactions);
    const b = rect(svg, bx, by, bw, H - padB - by, 'var(--accent)', 'bar');
    b.addEventListener('mousemove', e => showTip(e,
      `${d.label}\ninteracciones: ${fmtInt(d.interactions)}\ncosto efectivo: ${fmtMoney(d.cost_effective)}\ncosto real: ${fmtMoney(d.cost_real)}`));
    b.addEventListener('mouseleave', hideTip);
    text(svg, x + iw / 2, H - padB + 14, d.label, 9, 'middle');
  });
  // línea de costo real
  let path = '';
  data.forEach((d, i) => {
    const x = padL + iw * i + iw / 2, y = yC(d.cost_real);
    path += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
  });
  const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  p.setAttribute('d', path); p.setAttribute('fill', 'none');
  p.setAttribute('stroke', 'var(--accent2)'); p.setAttribute('stroke-width', '1.5');
  svg.appendChild(p);
  data.forEach((d, i) => {
    const x = padL + iw * i + iw / 2, y = yC(d.cost_real);
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', x); c.setAttribute('cy', y); c.setAttribute('r', 2.5);
    c.setAttribute('fill', 'var(--accent2)');
    c.addEventListener('mousemove', e => showTip(e, `${d.label}\ncosto real: ${fmtMoney(d.cost_real)}`));
    c.addEventListener('mouseleave', hideTip);
    svg.appendChild(c);
  });
  text(svg, padL - 42, padT - 6, 'interacciones', 8);
  text(svg, W - padR + 4, padT - 6, 'costo real', 8, 'start', 'var(--accent2)');
  document.getElementById('chart-monthly').appendChild(svg);
}

// ---------- chart 2: costo efectivo apilado por herramienta ----------
{
  const tools = [...new Set(D.months.flatMap(d => Object.keys(d.tools)))];
  const COLORS = ['#ff9f43', '#4fc3f7', '#66bb6a', '#ab47bc', '#ef5350', '#ffa726', '#26a69a', '#ec407a'];
  const W = 800, H = 240, padL = 60, padR = 20, padT = 20, padB = 34;
  const svg = svgEl(W, H);
  const data = D.months, n = data.length;
  const totals = data.map(d => Object.values(d.tools).reduce((a, b) => a + b, 0));
  const maxT = Math.max(...totals);
  const iw = (W - padL - padR) / n;
  const y = v => padT + (H - padT - padB) * (1 - v / maxT);
  for (let g = 0; g <= 4; g++) {
    const gy = padT + (H - padT - padB) * g / 4;
    line(svg, padL, gy, W - padR, gy);
    text(svg, padL - 8, gy + 3, fmtInt(Math.round(maxT * (4 - g) / 4)), 9, 'end');
  }
  data.forEach((d, i) => {
    const x = padL + iw * i;
    const bw = Math.min(38, iw * 0.7);
    let acc = 0;
    tools.forEach((t, ti) => {
      const v = d.tools[t] || 0;
      if (!v) return;
      const y0 = y(acc), y1 = y(acc + v);
      const r = rect(svg, x + (iw - bw) / 2, y1, bw, y0 - y1, COLORS[ti % COLORS.length]);
      r.addEventListener('mousemove', e => showTip(e,
        `${d.label}\n${t}: ${fmtInt(v)} de ${fmtInt(totals[i])} (${Math.round(100 * v / totals[i])}%)`));
      r.addEventListener('mouseleave', hideTip);
      acc += v;
    });
    text(svg, x + iw / 2, H - padB + 14, d.label, 9, 'middle');
  });
  document.getElementById('legend-tools').innerHTML =
    tools.map((t, i) => `<span style="color:${COLORS[i % COLORS.length]}">${t}</span>`).join('');
  document.getElementById('chart-tools-cost').appendChild(svg);
}

// ---------- chart 3: top proyectos ----------
{
  const W = 800, rowH = 26, padL = 170, padR = 90, padT = 8;
  const H = padT + D.projects.length * rowH + 8;
  const svg = svgEl(W, H);
  const maxP = D.projects[0].interactions;
  const bw = W - padL - padR;
  D.projects.forEach((p, i) => {
    const y = padT + i * rowH;
    text(svg, padL - 8, y + 15, p.name.replace(/^charly-/, ''), 10, 'end');
    const w = bw * p.interactions / maxP;
    const r = rect(svg, padL, y + 5, w, rowH - 10, 'var(--accent)');
    r.addEventListener('mousemove', e => showTip(e,
      `${p.name}\n${fmtInt(p.interactions)} interacciones\ncosto efectivo: ${fmtMoney(p.cost_effective)}\ncosto real: ${fmtMoney(p.cost_real)}\n${p.first || '?'} → ${p.last || '?'}`));
    r.addEventListener('mouseleave', hideTip);
    text(svg, padL + w + 6, y + 15, fmtInt(p.interactions), 9);
  });
  document.getElementById('chart-projects').appendChild(svg);
}

// ---------- heatmap ----------
{
  const W = 800, cell = 28, padL = 40, padT = 20;
  const H = padT + 7 * cell + 30;
  const svg = svgEl(W, H);
  const max = Math.max(...D.heatmap.flat());
  const maxV = max || 1;
  const hours = [...Array(24).keys()];
  hours.forEach(hh => {
    if (hh % 3 === 0) text(svg, padL + cell * hh + cell / 2, padT - 6, hh + 'h', 9, 'middle');
  });
  const dowNames = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];
  D.heatmap.forEach((row, di) => {
    text(svg, padL - 8, padT + di * cell + cell / 2 + 4, dowNames[di], 10, 'end');
    row.forEach((v, hi) => {
      const x = padL + hi * cell, y = padT + di * cell;
      const inten = v / maxV;
      const r = rect(svg, x + 1, y + 1, cell - 2, cell - 2,
        inten === 0 ? 'var(--grid)' : `rgba(255,159,67,${0.12 + 0.88 * Math.pow(inten, 0.5)})`);
      r.addEventListener('mousemove', e => showTip(e,
        `${dowNames[di]} ${String(hi).padStart(2, '0')}:00\n${fmtInt(v)} interacciones`));
      r.addEventListener('mouseleave', hideTip);
      if (v > 0 && inten > 0.25) text(svg, x + cell / 2, y + cell / 2 + 3,
        v >= 1000 ? Math.round(v / 1000) + 'k' : v, 8, 'middle', '#16161d');
    });
  });
  text(svg, padL, H - 6, 'día de la semana (lun→dom) × hora local', 9);
  document.getElementById('chart-heatmap').appendChild(svg);
}

// ---------- barras horizontales genéricas (skills, comandos) ----------
function hbars(elId, obj, color) {
  const entries = Object.entries(obj);
  if (!entries.length) return;
  const W = 380, rowH = 22, padL = 180, padR = 60;
  const H = 10 + entries.length * rowH;
  const svg = svgEl(W, H);
  const max = Math.max(...entries.map(e => e[1]));
  entries.forEach(([k, v], i) => {
    const y = 10 + i * rowH;
    text(svg, padL - 8, y + 13, k, 10, 'end');
    const w = (W - padL - padR) * v / max;
    const r = rect(svg, padL, y + 4, w, rowH - 8, color);
    r.addEventListener('mousemove', e => showTip(e, `${k}\n${fmtInt(v)} usos`));
    r.addEventListener('mouseleave', hideTip);
    text(svg, padL + w + 6, y + 13, fmtInt(v), 9);
  });
  document.getElementById(elId).appendChild(svg);
}

// ---------- skills / comandos ----------
hbars('chart-skills', D.skills, 'var(--good)');
hbars('chart-commands', D.commands, 'var(--accent)');

// ---------- sesiones ----------
{
  const dist = D.sessions.length_distribution;
  const order = ['1-10', '11-50', '51-100', '101-300', '301-500', '500+'];
  const entries = Object.keys(dist).sort((a, b) =>
    order.indexOf(a) - order.indexOf(b)).map(k => [k, dist[k]]);
  // barras simples
  const W = 380, rowH = 26, padL = 90, padR = 60;
  const H = 10 + entries.length * rowH;
  const svg = svgEl(W, H);
  const max = Math.max(...entries.map(e => e[1]));
  entries.forEach(([k, v], i) => {
    const y = 10 + i * rowH;
    text(svg, padL - 8, y + 13, k + ' turns', 10, 'end');
    const w = (W - padL - padR) * v / max;
    rect(svg, padL, y + 4, w, rowH - 10, 'var(--accent2)');
    text(svg, padL + w + 6, y + 13, fmtInt(v), 9);
  });
  document.getElementById('chart-sessions').appendChild(svg);
  document.getElementById('sessions-summary').textContent =
    `${fmtInt(D.sessions.total)} sesiones · ${D.sessions.pct_agent}% autónomas (con Agent) · promedio ${Math.round(D.sessions.avg_turns)} turnos`;
  // tabla top sesiones
  const rows = D.sessions.top_longest.map(s =>
    `<tr><td class="num">${s.turns}</td><td>${s.date}</td><td>${s.project.replace(/^charly-/, '')}</td></tr>`).join('');
  document.getElementById('sessions-table').innerHTML =
    '<tr><th>turns</th><th>fecha</th><th>proyecto</th></tr>' + rows;
}

// ---------- tools timeline ----------
{
  document.getElementById('tools-table').innerHTML =
    '<tr><th>herramienta</th><th class="num">primera</th><th class="num">última</th><th class="num">total</th></tr>' +
    D.tools_timeline.map(t =>
      `<tr><td>${t.tool}</td><td class="num">${t.first}</td><td class="num">${t.last}</td><td class="num">${fmtInt(t.total)}</td></tr>`
    ).join('');
}

document.getElementById('footer').textContent =
  `generado ${D.meta.generated} · scripts/viz-dashboard.py · datos solo-charly`;
</script>
</body>
</html>
"""


def main():
    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPORT
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT

    report = json.loads(report_path.read_text())
    data = prepare(report)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    out_path.write_text(html)
    print(f"OK → {out_path} ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
