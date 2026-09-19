#!/usr/bin/env python3
"""
viz-fpa.py — Dashboard FP&A de uso de IA (epic coffe-lat).

Fase 1 (coffe-lat.2): esqueleto stdlib-only con resumen ejecutivo.

Lee data/usage_report_v3.json + config/fpa.json y produce
data/fpa-dashboard.html: un único HTML autocontenido (FPA-001) con SVG inline,
tema claro/oscuro según sistema (FPA-093), formatos USD con separadores y
cifras tabulares (FPA-095), header con fecha de generación y versión del
tracker (FPA-005), marca de mes parcial con días transcurridos/total
(FPA-004), provenance tag reported/assumed en toda cifra (FPA-003),
separación estricta efectivo/cash jamás sumados (FPA-002), resumen ejecutivo
de 3–5 headlines con interpretación de una línea y fallback "n/a" con razón
(FPA-007/008), claims narrativos solo con métrica + threshold visibles
(FPA-009) y validación de schema con exit non-zero listando los campos
fallidos (FPA-006).

Las matemáticas se computan en Python (design.md): el modelo va embebido
como JSON (`id="fpa-model"`) para que las fases siguientes (F2+) re-escale
en JS sin recalcular.

Uso: python3 scripts/viz-fpa.py [--report PATH] [--config PATH] [--out PATH]
"""

import argparse
import calendar
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fpa_config  # noqa: E402

REPORT = Path("data/usage_report_v3.json")
CONFIG = Path("config/fpa.json")
OUT = Path("data/fpa-dashboard.html")
SCHEMA = Path("specs/usage-report-v3.schema.json")

MONTH_SHORT = {"01": "ene", "02": "feb", "03": "mar", "04": "abr",
               "05": "may", "06": "jun", "07": "jul", "08": "ago", "09": "sep",
               "10": "oct", "11": "nov", "12": "dic"}


# ======================================================================
# Formatos (FPA-095): USD con separadores, enteros con separadores
# ======================================================================

def fmt_usd(x):
    """Formato USD: $1,234.50 — separador de miles, 2 decimales."""
    if x is None:
        return "n/a"
    return "${:,.2f}".format(x)


def fmt_int(x):
    """Formato de miles: 1,397,354."""
    if x is None:
        return "n/a"
    return "{:,}".format(x)


def month_label(ym):
    y, m = ym.split("-")
    return f"{MONTH_SHORT.get(m, m)} {y[2:]}"


# ======================================================================
# Matemáticas puras (sin IO)
# ======================================================================

def month_total_days(ym):
    """Días del mes 'YYYY-MM' (28/29/30/31)."""
    y, m = int(ym[:4]), int(ym[5:7])
    return calendar.monthrange(y, m)[1]


def fme(value, elapsed, total):
    """Full-month equivalent: valor parcial × días_del_mes / días_transcurridos.

    None si elapsed es 0 (no hay base para anualizar).
    """
    if elapsed == 0:
        return None
    return value * total / elapsed


def build_months(report):
    """Meta por mes: interacciones, costes separados (FPA-002), parcial (FPA-004).

    has_data=False marca meses sin datos (FPA-017): se excluyen de trends y
    unit-cost; el generador los muestra con marker n/a.
    """
    end = report["metadata"]["date_range"]["end"]
    months = []
    for ym in sorted(report["monthly"].keys()):
        mo = report["monthly"][ym]
        total_days = month_total_days(ym)
        last = date.fromisoformat(end) if end else None
        partial = last is not None and end[:7] == ym and last.day < total_days
        months.append({
            "ym": ym,
            "label": month_label(ym),
            "interactions": mo["interactions"],
            "cost_effective": mo["cost_effective"],
            "cost_cash": mo["cost_real"],
            "subscription_fees": mo.get("subscription_fees", 0.0),
            "total_days": total_days,
            "elapsed": last.day if partial else total_days,
            "partial": partial,
            "has_data": mo["interactions"] > 0,
        })
    return months


def build_headlines(report):
    """FPA-007: 3–5 cifras headline con interpretación de una línea.

    FPA-002: efectivo y cash son medidas separadas y nunca se suman.
    FPA-008: valor no computable → value=None + reason; display "n/a".
    """
    months = [m for m in build_months(report) if m["has_data"]]  # FPA-017
    interactions = sum(m["interactions"] for m in months)
    eff = sum(m["cost_effective"] for m in months)
    cash = sum(m["cost_cash"] for m in months)
    n = len(months)

    heads = []

    def head(key, label, value, provenance, interp, reason=None, fmt=fmt_usd):
        heads.append({
            "key": key, "label": label, "value": value,
            "display": fmt(value) if value is not None else "n/a",
            "provenance": provenance, "interp": interp,
            "reason": reason,
        })

    if eff > 0:
        head("cost_effective", "Coste efectivo", eff, "reported",
             f"estimación API-equivalente en {n} {'mes' if n == 1 else 'meses'} de datos "
             f"(≈ {fmt_usd(eff / n)}/mes)")
    else:
        head("cost_effective", "Coste efectivo", None, "reported", "",
             reason="sin meses con datos en el reporte")

    head("cost_cash", "Coste cash", cash, "reported",
         f"cuotas de suscripción + cargas reales (≈ {fmt_usd(cash / n)}/mes)"
         if cash > 0 else "",
         reason="sin meses con datos en el reporte" if n == 0
         else "sin cargas cash registradas" if cash == 0 else None)

    if eff > 0 and cash > 0:
        lev = eff / cash
        head("leverage", "Leverage", lev, "reported",
             f"el coste efectivo equivale a {lev:.1f}× el cash cost",
             fmt=lambda v: f"{v:.1f}×")
    else:
        head("leverage", "Leverage", None, "reported", "",
             reason="requiere coste efectivo y cash mayores que 0")

    if interactions > 0 and eff > 0:
        per_1k = eff / (interactions / 1000)
        head("cost_per_1k", "Coste por 1k interacciones", per_1k, "reported",
             f"por cada {fmt_int(1000)} interacciones "
             f"({fmt_int(interactions)} en el periodo)",
             fmt=fmt_usd)
    else:
        head("cost_per_1k", "Coste por 1k interacciones", None, "reported", "",
             reason="sin interacciones en el periodo" if interactions == 0
             else "sin coste efectivo")

    # Outcome metric: coste efectivo por commit, donde haya datos (FPA-007)
    commits = sum(
        (o.get("commits", 0) or 0)
        for m in report["monthly"].values() if m["interactions"] > 0
        for o in (m.get("outcomes_by_project") or {}).values()
    )
    if commits > 0 and eff > 0:
        head("outcome", "Coste efectivo por commit", eff / commits, "reported",
             f"{fmt_int(commits)} commits en el periodo")
    else:
        head("outcome", "Coste efectivo por commit", None, "reported", "",
             reason="el reporte no registra commits/releases"
             if commits == 0 else "sin coste efectivo")

    return heads


def build_claims(report, cfg):
    """FPA-009: claims narrativos solo con métrica nombrada + threshold.

    Un claim se emite solo si la métrica es computable; el threshold viene de
    config y es *assumed*. Sin métrica → el claim no se renderiza.
    """
    months = [m for m in build_months(report) if m["has_data"]]
    interactions = sum(m["interactions"] for m in months)
    eff = sum(m["cost_effective"] for m in months)
    claims = []
    target = cfg["budgets"]["target_per_1k"]  # assumed (config)
    if interactions > 0 and eff > 0:
        per_1k = eff / (interactions / 1000)
        inside = per_1k <= target
        claims.append({
            "text": ("Coste por 1k dentro del objetivo" if inside
                     else "Coste por 1k por encima del objetivo"),
            "metric_name": "coste por 1k interacciones",
            "metric_value": per_1k,
            "threshold": target,
            "threshold_provenance": "assumed",
            "verdict": "✔" if inside else "✘",
        })
    return claims


def build_model(report, cfg):
    """Modelo completo del dashboard (va embebido como JSON en el HTML)."""
    months = build_months(report)
    return {
        "period": report["metadata"]["date_range"],
        "months": months,
        "headlines": build_headlines(report),
        "claims": build_claims(report, cfg),
    }


# ======================================================================
# Validación de schema stdlib-only (FPA-006)
# ======================================================================

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "null": type(None),
}


def _type_ok(doc, t):
    if t == "number":
        return isinstance(doc, (int, float)) and not isinstance(doc, bool)
    if t == "integer":
        return isinstance(doc, int) and not isinstance(doc, bool)
    if t in _TYPES:
        return isinstance(doc, _TYPES[t])
    return False


def _resolve_ref(ref, root):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def validate_against_schema(doc, schema, root=None, path="$", errors=None,
                            depth=0):
    """Subconjunto JSON-Schema (draft-07) usado por usage-report-v3.

    Soporta: type, required, properties, additionalProperties, items, enum,
    minimum/maximum, pattern, patternProperties, allOf, $ref, definitions.
    Devuelve la lista de errores ("$ruta.campo: mensaje") — vacía = válido.
    """
    if errors is None:
        errors = []
    if depth > 32:  # guardia anti-recursión
        return errors
    if root is None:
        root = schema
    if schema is True:
        return errors
    if schema is False:
        errors.append(f"{path}: esquema lo prohíbe")
        return errors

    if "$ref" in schema:
        validate_against_schema(doc, _resolve_ref(schema["$ref"], root), root,
                                path, errors, depth + 1)

    for sub in schema.get("allOf", []):
        validate_against_schema(doc, sub, root, path, errors, depth + 1)

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(doc, t) for t in types):
            errors.append(f"{path}: tipo {type(doc).__name__}, esperaba "
                          f"{'/'.join(types)}")
            return errors  # con tipo mal, no seguir bajando

    if "enum" in schema and doc not in schema["enum"]:
        errors.append(f"{path}: {doc!r} no está en {schema['enum']!r}")

    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if "minimum" in schema and doc < schema["minimum"]:
            errors.append(f"{path}: {doc} < mínimo {schema['minimum']}")
        if "maximum" in schema and doc > schema["maximum"]:
            errors.append(f"{path}: {doc} > máximo {schema['maximum']}")

    if isinstance(doc, str) and "pattern" in schema:
        if not re.search(schema["pattern"], doc):
            errors.append(f"{path}: {doc!r} no matchea {schema['pattern']!r}")

    if isinstance(doc, dict):
        for key in schema.get("required", []):
            if key not in doc:
                errors.append(f"{path}: campo requerido ausente: {key}")
        props = schema.get("properties", {})
        for key, val in doc.items():
            if key in props:
                validate_against_schema(val, props[key], root,
                                        f"{path}.{key}", errors, depth + 1)
            else:
                matched = False
                for pat, sub in schema.get("patternProperties", {}).items():
                    if re.search(pat, key):
                        matched = True
                        validate_against_schema(val, sub, root,
                                                f"{path}.{key}", errors,
                                                depth + 1)
                ap = schema.get("additionalProperties", True)
                if not matched and ap is False:
                    errors.append(f"{path}.{key}: campo no permitido")

    if isinstance(doc, list) and "items" in schema:
        for i, item in enumerate(doc):
            validate_against_schema(item, schema["items"], root,
                                    f"{path}[{i}]", errors, depth + 1)

    return errors


def validate_report(report):
    """FPA-006: valida el reporte contra el schema; lista de campos fallidos."""
    schema = json.loads(SCHEMA.read_text())
    return validate_against_schema(report, schema)


# ======================================================================
# Render (FPA-001: HTML autocontenido; FPA-003: provenance por envoltorio)
# ======================================================================

def fig(value_html, provenance, extra_cls=""):
    """Envoltorio de cifra con provenance tag (FPA-003)."""
    cls = f' class="fig{"" if not extra_cls else " " + extra_cls}"'
    return f'<span{cls} data-provenance="{provenance}">{value_html}</span>'


def headline_card(h):
    """Card de headline con valor, tag de provenance e interpretación o n/a."""
    if h["value"] is None:  # FPA-008: n/a con razón, nunca vacío
        value = fig('<span class="na">n/a</span>', h["provenance"])
        sub = f'<p class="reason">{h["reason"]}</p>'
    else:
        value = fig(f'<span class="val">{h["display"]}</span>', h["provenance"])
        sub = f'<p class="interp">{h["interp"]}</p>'
    return (f'<div class="headline" data-key="{h["key"]}">'
            f'<h3>{h["label"]}</h3>{value}{sub}</div>')


def claim_html(c):
    """FPA-009: claim con métrica y threshold visibles (con provenance)."""
    return (f'<p class="claim">{c["verdict"]} <strong>{c["text"]}</strong> '
            f'— métrica: <em>{c["metric_name"]}</em> '
            + fig(fmt_usd(c["metric_value"]), "reported") + prov_tag("reported")
            + ' · umbral: '
            + fig(fmt_usd(c["threshold"]), c["threshold_provenance"])
            + prov_tag(c["threshold_provenance"]) + '</p>')


CSS = """
:root { --bg:#f4f2ec; --fg:#23211c; --muted:#6b675e; --card:#fffdf7;
        --line:#d8d3c8; --acc:#8a2b1e; --ok:#1e6b3a; --bad:#8a2b1e; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#1c1b18; --fg:#e8e4da; --muted:#9a958a; --card:#26241f;
          --line:#3a372f; --acc:#e0a08e; --ok:#7ec99a; --bad:#e0a08e; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); line-height:1.5;
       font-family: system-ui, sans-serif; }
main { max-width: 960px; margin: 0 auto; padding: 0 1rem 2rem; }
header.site, footer.site { border-bottom: 1px solid var(--line);
  max-width: 960px; margin: 0 auto; padding: .8rem 1rem; }
footer.site { border:0; border-top: 1px solid var(--line); }
header.site h1 { margin: 0; font-size: 1.35rem; }
header.site .meta, .small { color: var(--muted); font-size: .82rem; }
.skip { position:absolute; left:-9999px; }
.skip:focus { left:.5rem; top:.5rem; background:var(--card); padding:.4rem;
  border:1px solid var(--line); }
.banner-partial { background: var(--card); border: 1px solid var(--line);
  padding: .5rem .8rem; border-radius: 6px; font-size: .85rem; }
#summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px,1fr));
  gap: .7rem; margin: 1rem 0; }
#summary h2 { grid-column: 1 / -1; margin: 0 0 .2rem; }
.headline { background: var(--card); border: 1px solid var(--line);
  border-radius: 8px; padding: .7rem .8rem; }
.headline h3 { margin: 0 0 .3rem; font-size: .8rem; font-weight: 600;
  color: var(--muted); }
.fig { font-variant-numeric: tabular-nums; font-size: 1.25rem;
  font-weight: 700; display: inline-block; }
.headline .interp, .headline .reason { margin: .3rem 0 0; font-size: .78rem;
  color: var(--muted); }
.na { color: var(--muted); font-weight: 400; }
.claims { margin: .6rem 0 1rem; }
.claim { background: var(--card); border: 1px solid var(--line);
  border-left: 4px solid var(--acc); padding: .5rem .7rem; font-size: .85rem; }
.prov-tag { font-size: .62rem; font-weight: 500; vertical-align: super;
  padding: 0 .25em; border-radius: 3px; background: var(--line);
  color: var(--fg); letter-spacing: .03em; }
.retro { font-size: .7rem; color: var(--muted); letter-spacing: .08em; }
"""

CSS_LEGACY = (  # retro confinado a header/footer, sin animación (FPA-178)
    ".retro::before { content: '▚▞ '; color: var(--acc); }"
)


def prov_tag(kind):
    """Tag visible de procedencia: reported / assumed."""
    label = "reported" if kind == "reported" else "assumed"
    return f'<span class="prov-tag" title="procedencia: {kind}">{label}</span>'


def render_html(report, cfg, generated=None):
    """Generar el HTML completo (determinista salvo `generated`, FPA-104)."""
    generated = generated or datetime.now().strftime("%Y-%m-%d %H:%M")
    model = build_model(report, cfg)
    lang = cfg.get("language", "es")
    retro = cfg.get("retro", {}).get("enabled", False)

    months_meta = model["months"]
    partials = [m for m in months_meta if m["partial"]]
    banner = ""
    if partials:
        bits = [f'{m["label"]} <strong>{m["elapsed"]}/{m["total_days"]}</strong>'
                for m in partials]
        banner = ('<p class="banner-partial">Mes parcial: '
                  + ", ".join(bits)
                  + ' — las comparaciones del mes parcial usan tasas diarias.</p>')

    tracker_version = report["metadata"].get("tracker_version")
    tracker_cell = (f"Tracker {tracker_version}" if tracker_version
                    else "Tracker n/a (versión no registrada en el reporte)")
    period = model["period"]
    period_cell = " → ".join(p or "n/a" for p in
                             (period["start"], period["end"]))

    claims = model["claims"]
    cards = "".join(headline_card(h) for h in model["headlines"])

    claims_html = "".join(claim_html(c) for c in claims)
    if claims_html:
        claims_html = f"<div class='claims'>{claims_html}</div>"

    model_json = json.dumps(model, ensure_ascii=False, sort_keys=True)

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard FP&A — uso de IA</title>
<style>{CSS}{CSS_LEGACY if retro else ""}</style>
</head>
<body>
<a class="skip" href="#summary">Saltar al contenido</a>
<header class="site">
  <h1>Dashboard FP&A — uso de IA</h1>
  <p class="meta">Generado: {generated} · {tracker_cell} · periodo
  {period_cell}</p>
  {'<p class="retro">FP&A desk · edición quarterly</p>' if retro else ""}
</header>
<main id="main">
  {banner}
  <section id="summary" aria-label="Resumen ejecutivo">
    <h2>Resumen ejecutivo</h2>
    <div class="cards">{cards}</div>
    {claims_html}
  </section>
</main>
<footer class="site">
  <p class="retro small">Dashboard FP&A · generado por viz-fpa.py (stdlib-only,
  SVG inline) · cifras con tag reported/assumed</p>
</footer>
<script type="application/json" id="fpa-model">{model_json}</script>
</body>
</html>"""


def check_placeholders(html):
    """FPA-108: problemas de placeholders — resumen vacío o ph sin valor."""
    problems = []
    if html.count('class="headline') < 3:
        problems.append("resumen ejecutivo vacío o incompleto (<3 headlines)")
    for m in re.finditer(r'<(\w+)[^>]*class="[^"]*\bph\b[^"]*"[^>]*>([^<]*)</\1>',
                         html):
        if not m.group(2).strip():
            problems.append(f"placeholder sin valor: <{m.group(1)} class='ph'>")
    return problems


# ======================================================================
# CLI
# ======================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Dashboard FP&A (viz-fpa.py)")
    ap.add_argument("--report", default=str(REPORT))
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    # FPA-006: schema validation con exit non-zero y campos fallidos listados
    try:
        report = json.loads(Path(args.report).read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: no se pudo leer el reporte: {e}", file=sys.stderr)
        return 1
    errors = validate_report(report)
    if errors:
        print(f"ERROR: schema validation falló ({len(errors)} campos):",
              file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    cfg = fpa_config.load_fpa_config(args.config)
    cfg_errors = fpa_config.validate_config(cfg)
    if cfg_errors:
        print("ERROR: config inválida:", file=sys.stderr)
        for e in cfg_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    html = render_html(report, cfg)
    problems = check_placeholders(html)
    if problems:  # FPA-108
        print("ERROR: placeholder-check:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"OK: {out} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
