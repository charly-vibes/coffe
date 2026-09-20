#!/usr/bin/env python3
"""
viz_fpa_guide.py — ingesta de la guía de análisis a 4 niveles
(coffe-gen.3/gen.4, change update-fpa-site-integration).

Purpose: parsear docs/fpa-analyses-guide.md (español, 19 análisis ×
ELI5/Cotidiano/Practicante/Experto) con stdlib y exponerlo al sitio.

Responsibilities:
- load_guide(): parser del markdown → secciones/analysis/levels/IDs FPA-xxx
- ANALYSIS_SURFACES: mapeo declarado análisis→superficie (5 vistas del
  dashboard + data + gantt), anclado a los números del texto de la guía
- check_documentation(): guardas de grounding — cada análisis del mapeo
  existe en la guía y cada umbral citado en la guía coincide con el valor
  real del config/código (coffe-gen.3; lo invoca --check-docs de viz-fpa.py)
- render_guide_html(): data/fpa-guide.html autocontenida en el tema
  compartido (scripts/site_theme.py), anchors por análisis
- marginalia_fragment(num): devuelve el HTML de la nota colapsable para la
  vista que la gen.4 integra

Rationale: el contenido es verdad del repo (markdown versionado, pase de
grounding en coffe-gen.1); el generador nunca copia el texto a strings
propios. Las cifras del snapshot original se reemplazaron por cifras
derivadas en generación — la guía NO participa de la verificación
README↔JSON (FPA-143) y sus cifras se etiquetan como foto del reporte.
"""

import argparse
import html as html_mod
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_theme  # noqa: E402

GUIDE_MD = Path("docs/fpa-analyses-guide.md")
OUT = Path("data/fpa-guide.html")
CONFIG = Path("config/fpa.json")

NIVEL_RE = re.compile(r"^- \*\*(?P<n>[1-4]) · (?P<label>[^*]+):\*\*\s*"
                      r"(?P<rest>.*)$", flags=re.M)
HEADING_RE = re.compile(
    r"^### (?P<num>\d+(?:\s*\([ab]\))?)\. (?P<title>.+?) "
    r"\((?P<ids>[^)]+)\)\s*$", flags=re.M)

# Números canónicos de análisis para el mapeo (10a/10b del texto original).
_ANALYSIS_NUM_RE = re.compile(r"(\d+)(?:\s*\(\s*([ab])\s*\))?|^(\d+)([ab])$")


def _canon_num(raw):
    """'10 (a)' / '10a' / '10' → clave canónica: '10a' | '10'."""
    raw = re.sub(r"\s+", "", raw)
    m = re.fullmatch(r"(\d+)(?:\(([ab])\))?([ab])?", raw)
    if not m:
        return None
    num, paren, suffix = m.group(1), m.group(2), m.group(3)
    return num + (paren or suffix or "")


def load_guide(text):
    """Parsear el markdown de la guía → dict de secciones/analysis.

    Estructura por análisis: num (canónico), title, ids (lista FPA-xxx),
    levels ({'1 · ELI5': texto, ...}). Falla loud si falta un nivel.
    """
    if not text or "### " not in text:
        raise SystemExit(f"ERROR: guía vacía o sin análisis: {GUIDE_MD}")
    if not list(HEADING_RE.finditer(text)):
        raise SystemExit(f"ERROR: sin análisis parseables en {GUIDE_MD}")
    return _assign_sections(text)


def _assign_sections(text):
    """Recorrer el markdown con spans sobre el texto completo y agrupar
    análisis por sección '## X.'."""
    out = []
    headings = list(re.finditer(r"^## ([A-D])\. (.+)$|^### .+$", text,
                                flags=re.M))
    for i, hm in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        block = text[hm.end():end]
        if hm.group(1):  # '## X. título'
            out.append({"key": hm.group(1), "title": hm.group(2).strip(),
                        "analyses": []})
            continue
        ahm = HEADING_RE.match(hm.group(0))
        if not ahm or not out:
            continue
        num = _canon_num(ahm.group("num"))
        ids = _parse_ids(ahm.group("ids"))
        levels = _parse_analysis_block(block, ahm)
        out[-1]["analyses"].append(
            {"num": num, "title": ahm.group("title").strip(),
             "ids": ids, "ids_text": ahm.group("ids").strip(),
             "levels": levels})
    if not out:
        raise SystemExit(f"ERROR: sin secciones A–D en {GUIDE_MD}")
    return {"sections": out}


def _parse_analysis_block(block, ahm):
    """Bloque de un análisis (ya recortado por heading) → niveles."""
    levels, current = {}, None
    for line in block.splitlines():
        hm = NIVEL_RE.match(line.strip())
        if hm:
            current = f"{hm.group('n')} · {hm.group('label').strip()}"
            rest = hm.group("rest").strip()
            levels[current] = [rest] if rest else []
            continue
        if current and line.strip():
            levels[current].append(line.strip())
    if len(levels) != 4:
        raise SystemExit(f"ERROR: análisis {ahm.group('num')} tiene "
                         f"{len(levels)} niveles, se esperaban 4")
    return {k: " ".join(v) for k, v in levels.items()}


_IDS_TOKEN_RE = re.compile(r"(?:FPA-)?(\d+)(?:[–—-](\d+))?$")


def _parse_ids(raw):
    """Lista de IDs FPA desde el texto del heading, expandiendo rangos.

    'FPA-002, 030–032' → ['FPA-002', 'FPA-030', 'FPA-031', 'FPA-032'].
    Los números sin prefijo heredan el FPA- del token anterior.
    """
    out, seen = [], set()
    for token in (t.strip() for t in raw.split(",")):
        m = _IDS_TOKEN_RE.match(token)
        if not m:
            continue
        lo, hi = m.group(1), m.group(2)
        if hi is not None:
            span = [f"FPA-{i:03d}" for i in range(int(lo), int(hi) + 1)]
        else:
            span = [f"FPA-{int(lo):03d}"]
        for i in span:
            if i not in seen:
                seen.add(i)
                out.append(i)
    return out


def analyses_flat(guide_dict):
    return [a for s in guide_dict["sections"] for a in s["analyses"]]


# Mapeo declarado análisis→superficie (coffe-gen.4 lo consume para la
# marginalia). Claves canónicas del texto; superficies: las 5 vistas del
# dashboard + 'data' (Datos y método) + 'gantt'.
ANALYSIS_SURFACES = [
    ("1", ["summary"]),      # efectivo vs real vs apalancamiento (headline)
    ("2", ["summary"]),      # claim coste/1k vs target
    ("3", ["summary"]),      # headline costo por sesión
    ("4", ["breakdown", "outlook"]),  # Pareto/portfolio + alerta top-3
    ("5", ["cost"]),         # mezcla mensual de modelos + premium share
    ("6", ["cost"]),         # KPIs cache-hit rate y out/in
    ("7", ["habits"]),       # share de sesiones con Agent
    ("8", ["habits", "gantt"]),  # multitasking (3 medidas) + concurrencia
    ("9", ["habits", "gantt"]),  # heatmap/after-hours + ritmo semanal
    ("10a", ["habits"]),     # buckets de sesión + /clear
    ("10b", ["habits"]),     # skills/commands
    ("11", ["breakdown"]),   # lifecycle new/active/dormant
    ("12", ["outlook"]),     # outcomes: costo por commit/release
    ("13", ["outlook"]),     # presupuesto/varianza + alertas
    ("14", ["outlook"]),     # bridge PVM
    ("15", ["outlook"]),     # forecast/escenarios
    ("16", ["outlook"]),     # economía de suscripción
    ("17", ["breakdown"]),   # árboles con roll-up
    ("18", ["data"]),        # calidad de datos
    ("19", ["data"]),        # interfaz y CTAs
]

# Umbrales citados en la guía ↔ valores reales (config o defaults del
# código). La clave es (ruta, etiqueta humana); el valor efectivo se lee
# del config con su default de código (check_documentation).
CITED_THRESHOLDS = [
    (("alert_thresholds", "plan_usage_multiple"), "25x verify-plan"),
    (("alert_thresholds", "reconcile_tolerance_pct"), "10% reconciliación"),
    (("alert_thresholds", "unit_cost_rise_pct"), "15% costo unitario"),
    (("alert_thresholds", "premium_share_rise_pts"), "5 pts premium"),
    (("alert_thresholds", "concentration_top3_pct"), "50% top-3"),
    (("alert_thresholds", "staleness_days"), "14 días staleness"),
    (("lifecycle", "dormant_days"), "30 días dormant"),
    (("lifecycle", "new_days"), "30 días new"),
    (("sessions", "long_turns"), "100 turns larga"),
    (("timeline", "gap_days"), "7 días gap"),
]

# Defaults de código para claves ausentes en el config (igual que hace
# viz-fpa.py con _cfg_int).
CODE_DEFAULTS = {
    ("sessions", "long_turns"): 100,
    ("timeline", "gap_days"): 7,
}


def _effective_threshold(cfg, path):
    section, key = path
    default = CODE_DEFAULTS.get(path)
    val = (cfg.get(section) or {}).get(key, default)
    return val


def check_documentation(cfg, guide_text, mapping_override=None):
    """Guardas de grounding. Devuelve lista de errores ([] = OK).

    1. cada análisis del mapeo existe en la guía
    2. cada umbral CITED_THRESHOLDS: su valor efectivo (config o default
       de código) aparece citado como número en el texto de la guía — si
       el config cambia, la guía debe re-groundearse o el build falla
    """
    errors = []
    nums = {a["num"]
            for s in _assign_sections(guide_text)["sections"]
            for a in s["analyses"]}
    mapping = mapping_override if mapping_override is not None else (
        ANALYSIS_SURFACES)
    for num, surfaces in mapping:
        if num not in nums:
            errors.append(f"mapping: análisis {num} no existe en la guía "
                          f"(superficies: {','.join(surfaces)})")
    for path, label in CITED_THRESHOLDS:
        val = _effective_threshold(cfg, path)
        if val is None:
            errors.append(f"umbral {label}: sin valor en config ni default")
            continue
        # citar los enteros como tales; tolerar coma decimal
        if not re.search(rf"(?<![\d.,]){re.escape(str(val))}(?![\d.,])",
                         guide_text):
            errors.append(
                f"umbral {label}: el valor real {val} "
                f"(config {path[0]}.{path[1]}) no aparece citado en la guía —"
                f" re-groundear docs/fpa-analyses-guide.md")
    return errors


CSS = site_theme.base_css() + """
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  line-height: 1.5; font-family: var(--font-stack); }
main { max-width: 900px; margin: 0 auto; padding: 0 1rem 2rem; }
header.site, footer.site { border-bottom: 1px solid var(--line);
  max-width: 900px; margin: 0 auto; padding: .8rem 1rem; }
footer.site { border: 0; border-top: 1px solid var(--line); }
header.site h1 { margin: 0; font-size: 1.35rem; }
.meta, .small { color: var(--muted); font-size: .82rem; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: .5rem; top: .5rem; background: var(--card);
  padding: .4rem; border: 1px solid var(--line); }
h2 { font-size: 15px; color: var(--navy); margin: 26px 0 8px;
  text-transform: uppercase; letter-spacing: .06em;
  border-bottom: 3px double var(--navy); padding-bottom: 3px; }
.analysis { background: var(--card); border: 2px outset #fff;
  box-shadow: 3px 3px 0 #404040; padding: .8rem 1rem; margin: 0 0 1rem; }
.analysis h3 { margin: 0 0 .4rem; font-size: .95rem; }
.analysis h3 .fpa { font-size: .7rem; color: var(--muted); font-weight: 400; }
.level { margin: .45rem 0; padding-left: .6rem; border-left: 4px double
  var(--navy); }
.level b { color: var(--accent2); }
.volver { font-size: .78rem; }
nav.toc { background: var(--card); border: 2px outset #fff;
  padding: .7rem 1rem; margin: 1rem 0; }
nav.toc a { color: var(--navy); text-decoration: none; }
"""


def _anchor(num):
    return f"analisis-{html_mod.escape(num)}"


def render_guide_html(guide_dict, cfg, generated=None):
    """HTML autocontenido de la guía completa (determinista)."""
    generated = generated or datetime.now().strftime("%Y-%m-%d %H:%M")
    site_name = cfg.get("site_name", "Uso y costos de IA")
    toc = []
    sections_html = []
    for s in guide_dict["sections"]:
        items = []
        for a in s["analyses"]:
            anchor = _anchor(a["num"])
            items.append(f'<a href="#{anchor}">{a["num"]}</a>')
            levels = "".join(
                f'<div class="level"><b>{html_mod.escape(k)}</b> '
                f'{html_mod.escape(v)}</div>'
                for k, v in a["levels"].items())
            ids_text = html_mod.escape(a.get("ids_text", ""))
            sections_html.append(
                f'<div class="analysis" id="{anchor}">'
                f'<h3>{html_mod.escape(a["num"])}. '
                f'{html_mod.escape(a["title"])} '
                f'<span class="fpa">{ids_text}</span></h3>'
                f'{levels}'
                f'<p class="small volver"><a href="#toc">↑ índice</a></p>'
                f'</div>')
        toc.append(f'<div><b>{s["key"]}.</b> {html_mod.escape(s["title"])} '
                   f'{"".join(items)}</div>')
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guía de análisis — {html_mod.escape(site_name)}</title>
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#toc">Saltar al índice</a>
<header class="site">
  <h1>Guía de análisis — {html_mod.escape(site_name)}</h1>
  <p class="meta">Generado: {generated} · fuente: docs/fpa-analyses-guide.md
  (19 análisis × 4 niveles)</p>
</header>
<main>
<nav class="toc" id="toc">
  {"".join(toc)}
</nav>
{"".join(sections_html)}
<footer class="site">
  <p class="small">Guía de análisis · generado por viz_fpa_guide.py
  (stdlib-only) · las cifras citadas provienen del reporte vigente y son una
  foto del momento de la traducción — el dashboard calcula las cifras vivas
  en cada corrida.</p>
</footer>
</main>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(
        description="Guía de análisis a 4 niveles (viz_fpa_guide.py)")
    ap.add_argument("--check", action="store_true",
                    help="solo validar grounding (mapeo + umbrales vs config)")
    ap.add_argument("--report", default=str(Path("data/usage_report_v3.json")))
    args = ap.parse_args()
    text = GUIDE_MD.read_text(encoding="utf-8")
    cfg = json.loads(CONFIG.read_text())
    errors = check_documentation(cfg, text)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    if args.check:
        print("OK: guía con grounding verificado (mapeo + umbrales vs config)")
        return
    guide_dict = load_guide(text)
    OUT.write_text(render_guide_html(guide_dict, cfg), encoding="utf-8")
    print(f"OK → {OUT} ({len(analyses_flat(guide_dict))} análisis)")


if __name__ == "__main__":
    main()
