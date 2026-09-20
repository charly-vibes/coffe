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
    """Modelo completo del dashboard (va embebido como JSON en el HTML).
    F2 añade vistas pre-calculadas por periodo, árboles con roll-up
    verificado y la sección Data (FPA-140/141/142/120)."""
    months = build_months(report)
    return {
        "period": report["metadata"]["date_range"],
        "months": months,
        "headlines": build_headlines(report),
        "claims": build_claims(report, cfg),
        "views": build_views(report, cfg),
        "data_notes": build_data_notes(report),
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
# F2 (coffe-lat.3): árboles expandibles + KPI strip
# (FPA-020…045, 140–142) — maths puras; el HTML lleva los valores ya
# pre-calculados por periodo y JS solo re-escala (design.md)
# ======================================================================

def _node(key, label):
    """Nodo de árbol: valores por mes (para recompute de periodo) + hijos."""
    return {"key": key, "label": label, "by_month": {}, "children": []}


def _node_add(node, ym, cost=0.0, interactions=0, budget=None):
    b = node["by_month"].setdefault(ym, {"cost": 0.0, "interactions": 0})
    b["cost"] += cost
    b["interactions"] += interactions
    if budget is not None:
        b["budget"] = b.get("budget", 0.0) + budget


def _cost_of(node, months=None):
    if months is None:
        months = node["by_month"].keys()
    return sum(node["by_month"][m]["cost"] for m in months if m in node["by_month"])


def _inter_of(node, months=None):
    if months is None:
        months = node["by_month"].keys()
    return sum(node["by_month"][m]["interactions"]
               for m in months if m in node["by_month"])


def _bucket(v):
    """Compat: modelos/tools del reporte viejo son Counters (int); los nuevos
    llevan dicts. Devuelve (interactions, cost) según el shape."""
    if isinstance(v, dict):
        return v.get("interactions", 0), v.get("cost_effective", 0.0) or 0.0
    return v, 0.0


def build_tool_tree(report):
    """FPA-020: árbol Tool → Model con valores por mes; el selector de periodo
    (FPA-026) recompute sumando meses pre-calculados, sin lógica de negocio."""
    root = _node("tool:__all__", "Todas las tools")
    tools = {}
    for ym, mo in sorted(report["monthly"].items()):
        if mo["interactions"] == 0:  # FPA-017: mes sin datos no aporta
            continue
        for tool, st in mo["tools"].items():
            n, cost = _bucket(st)
            tn = tools.setdefault(tool, _node(f"tool:{tool}", tool))
            _node_add(tn, ym, cost, n)
            _node_add(root, ym, cost, n)
            for model, ms in (st.get("models", {}) if isinstance(st, dict) else {}).items():
                model_node = next((c for c in tn["children"]
                                   if c["key"] == f"model:{tool}:{model}"), None)
                if model_node is None:
                    model_node = _node(f"model:{tool}:{model}", model)
                    tn["children"].append(model_node)
                n_model, c_model = _bucket(ms)
                _node_add(model_node, ym, c_model, n_model)
    for tn in tools.values():
        tn["children"].sort(key=lambda n: -_cost_of(n))
    root["children"] = sorted(tools.values(), key=lambda n: -_cost_of(n))
    return root


def build_time_tree(report, cfg):
    """FPA-020/024: Year → Quarter → Month con coste CASH (el comparable con
    el presupuesto cash; FPA-002: jamás se suma con el efectivo) y
    presupuesto mensual del config (assumed) en cada mes."""
    root = _node("time:__all__", "Todo el periodo")
    start = cfg.get("budgets", {}).get("start_month")
    cash_budget = cfg.get("budgets", {}).get("cash_monthly")
    years = {}
    for meta in build_months(report):
        ym = meta["ym"]
        y, q = ym[:4], f"Q{(int(ym[5:7]) - 1) // 3 + 1}"
        budget = cash_budget if (start and ym >= start and cash_budget) else None
        month_node = _node(f"time:{ym}", month_label(ym))
        _node_add(month_node, ym, meta["cost_cash"], meta["interactions"], budget)
        ynode = years.setdefault(y, _node(f"time:{y}", y))
        qnode = next((c for c in ynode["children"]
                      if c["key"] == f"time:{y}-{q}"), None)
        if qnode is None:
            qnode = _node(f"time:{y}-{q}", f"{q} {y[2:]}")
            ynode["children"].append(qnode)
        qnode["children"].append(month_node)
        _node_add(qnode, ym, meta["cost_cash"], meta["interactions"], budget)
        _node_add(ynode, ym, meta["cost_cash"], meta["interactions"], budget)
    root["children"] = [years[y] for y in sorted(years)]
    # roll-up por construcción: el root es la suma de sus años
    for ynode in root["children"]:
        for ym, b in ynode["by_month"].items():
            _node_add(root, ym, b["cost"], b["interactions"], b.get("budget"))
    return root


def build_portfolio_tree(report, cfg):
    """FPA-018/020/021: Category → Project con drill a Model (totales).
    Con project_monthly (FPA-012) el árbol tiene valores por mes; el drill
    Project→Model solo tiene datos del periodo completo — limitación visible."""
    root = _node("pf:__all__", "Portfolio")
    cats = {}
    for proj, months in report.get("project_monthly", {}).items():
        cat = fpa_config.classify_project(cfg, proj)
        cn = cats.setdefault(cat, _node(f"pf:{cat}", cat))
        proj_node = next((c for c in cn["children"]
                          if c["key"] == f"pf:{proj}"), None)
        if proj_node is None:
            proj_node = _node(f"pf:{proj}", proj)
            cn["children"].append(proj_node)
        for ym, v in months.items():
            _node_add(proj_node, ym, v["cost_effective"], v["interactions"])
            _node_add(cn, ym, v["cost_effective"], v["interactions"])
    for cat in cats.values():
        for p_node in cat["children"]:
            for model, ms in report.get("project_models", {}).get(p_node["label"], {}).items():
                m_node = _node(f"pfm:{p_node['label']}:{model}", model)
                m_node["totals_only"] = True
                m_node["by_month"]["__total__"] = {
                    "cost": ms["cost_effective"], "interactions": ms["interactions"]}
                p_node["children"].append(m_node)
        cat["children"].sort(key=lambda n: -_cost_of(n))
    root["children"] = sorted(cats.values(), key=lambda n: -_cost_of(n))
    for cn in root["children"]:
        for ym, b in cn["by_month"].items():
            _node_add(root, ym, b["cost"], b["interactions"])
    return root


def check_rollup(node):
    """FPA-025: todo padre = suma de sus hijos dentro de $0.01 y 1 interacción.
    Devuelve violaciones (lista vacía = OK). Verificación recursiva."""
    bad = []
    if node.get("children"):
        c_cost = sum(_cost_of(c) for c in node["children"])
        c_inter = sum(_inter_of(c) for c in node["children"])
        p_cost, p_inter = _cost_of(node), _inter_of(node)
        if abs(p_cost - c_cost) > 0.01:
            bad.append(f"{node['key']}: coste padre {p_cost:.4f} ≠ hijos {c_cost:.4f}")
        if abs(p_inter - c_inter) > 1:
            bad.append(f"{node['key']}: interacciones padre {p_inter} ≠ hijos {c_inter}")
        for c in node["children"]:
            bad.extend(check_rollup(c))
    return bad


def kpi_ingredients(report, cfg):
    """Ingredientes crudos por mes (solo meses con datos, FPA-017).

    Todo lo que un KPI necesita por mes: costes, días para daily rate,
    tokens, sesiones, concentración top-3, premium, multitasking, outcomes
    y presencia de tokens por tool (FPA-045). Las funciones de KPI solo
    combinan estos números."""
    sessions_m = report.get("sessions_monthly", {}) or {}
    premium = [p.lower() for p in cfg.get("premium_models", [])]
    ing = {}
    for meta in build_months(report):
        ym = meta["ym"]
        if not meta["has_data"]:
            continue
        mo = report["monthly"][ym]
        inp = out_t = cr = cw = 0
        for t in mo.get("tokens_by_model", {}).values():
            inp += t.get("in", 0)
            out_t += t.get("out", 0)
            cr += t.get("cache_read", 0)
            cw += t.get("cache_write", 0)
        else_cost = 0.0  # coste de modelos sin datos nuevos (reporte viejo)
        # FPA-045: tools sin datos de tokens ese mes → exclusión con share
        inter_by_tool, notokens_inter = {}, 0
        for h, hb in report.get("hourly", {}).items():
            if h[:7] != ym:
                continue
            for tool, ts_ in hb.get("tools", {}).items():
                inter_by_tool[tool] = inter_by_tool.get(tool, 0) + ts_.get("req", 0)
                if (ts_.get("in", 0) + ts_.get("out", 0)
                        + ts_.get("cache_read", 0) + ts_.get("cache_write", 0)) == 0:
                    notokens_inter += ts_.get("req", 0)
        mt_inter = sum(hb["interactions"]
                       for h, hb in report.get("hourly", {}).items()
                       if h[:7] == ym and hb.get("projects_active", 0) >= 2)
        proj_costs = sorted(
            (v[ym]["cost_effective"]
             for v in report.get("project_monthly", {}).values() if ym in v),
            reverse=True)
        outc = mo.get("outcomes_by_project") or {}
        premium_cost = sum(
            _bucket(st)[1] for model, st in mo.get("models", {}).items()
            if any(p in model.lower() for p in premium))
        sm = sessions_m.get(ym, {})
        ing[ym] = {
            "cost_effective": mo["cost_effective"],
            "cost_cash": mo["cost_real"],
            "interactions": mo["interactions"],
            "days": meta["elapsed"],  # FPA-041: días efectivos (parciales: elapsed)
            "partial": meta["partial"],
            "sessions": sm.get("total", 0),
            "sessions_agent": sm.get("with_agent", 0),
            "tokens": {"in": inp, "out": out_t, "cache_read": cr, "cache_write": cw},
            "excluded_interactions": notokens_inter,
            "interactions_by_tool": inter_by_tool,
            "mt_interactions": mt_inter,
            "top3_cost": sum(proj_costs[:3]),
            "proj_cost": sum(proj_costs),
            "premium_cost": premium_cost,
            "commits": sum(o.get("commits", 0) or 0 for o in outc.values()),
            "releases": sum(o.get("releases", 0) or 0 for o in outc.values()),
        }
    return ing


def _pct_change(cur, prev):
    """Delta porcentual; None si no hay base o valor (FPA-042: nunca infinito)."""
    if prev is None or prev == 0 or cur is None:
        return None
    return (cur - prev) / prev


def _sum_ing(ing, window, key):
    return sum(ing[ym].get(key, 0) for ym in window if ym in ing)


def _sum_tokens(ing, window, key):
    return sum(ing[ym]["tokens"].get(key, 0) for ym in window if ym in ing)


def _spark(ing, compute):
    """Serie mensual de un KPI (solo meses con datos) para el sparkline."""
    out = []
    for ym in sorted(ing):
        v = compute(ing[ym])
        if v is not None:
            out.append({"ym": ym, "value": round(v, 6)})
    return out


def _kpi(key, label, value, fmt, reason=None, provenance="reported",
         prev=None, cur_rate=None, prev_rate=None, spark=None,
         excluded_share=None):
    """Card de KPI normalizada. value None → n/a con razón (FPA-008/042).

    Delta: si viene cur_rate/prev_rate se compara la tasa diaria (FPA-041);
    si no, Δ% del valor del periodo vs el previo. Sin periodo previo en el
    reporte → delta n/a."""
    if cur_rate is not None:
        delta = _pct_change(cur_rate, prev_rate)
        kind = "daily-rate"
    else:
        delta = _pct_change(value, prev)
        kind = "periodo"
    k = {
        "key": key, "label": label, "value": value,
        "display": fmt(value) if value is not None else "n/a",
        "provenance": provenance, "reason": reason,
        "delta": None if delta is None else round(delta, 4),
        "delta_display": (f"{'+' if delta >= 0 else ''}{delta * 100:.1f}%"
                          if delta is not None else "n/a"),
        "delta_kind": kind,
        "spark": spark or [],
    }
    if excluded_share:
        k["excluded_share"] = round(excluded_share, 4)
        k["excluded_display"] = f"{excluded_share * 100:.1f}%"
    return k


def kpis_for_window(ing, window, prior):
    """KPIs FPA-030…045 para una ventana de meses, con delta vs la ventana
    previa (de igual longitud) y sparkline mensual. Denominador 0 → n/a con
    razón (FPA-042). FPA-041: con mes parcial las comparaciones de coste son
    tasas diarias."""
    if not window:
        return []
    eff = _sum_ing(ing, window, "cost_effective")
    cash = _sum_ing(ing, window, "cost_cash")
    inter = _sum_ing(ing, window, "interactions")
    days = _sum_ing(ing, window, "days")
    sessions = _sum_ing(ing, window, "sessions")
    sessions_agent = _sum_ing(ing, window, "sessions_agent")
    mt_inter = _sum_ing(ing, window, "mt_interactions")
    top3 = _sum_ing(ing, window, "top3_cost")
    proj_cost = _sum_ing(ing, window, "proj_cost")
    premium_cost = _sum_ing(ing, window, "premium_cost")
    commits = _sum_ing(ing, window, "commits")
    releases = _sum_ing(ing, window, "releases")
    tok = {k: _sum_tokens(ing, window, k)
           for k in ("in", "out", "cache_read", "cache_write")}
    excluded_inter = _sum_ing(ing, window, "excluded_interactions")

    partial = any(ym in ing and ing[ym]["partial"] for ym in window)
    if prior:
        partial = partial or any(ym in ing and ing[ym]["partial"] for ym in prior)

    # tasas diarias (FPA-041) — siempre calculadas; se usan para costes
    rate_eff = eff / days if days else None
    rate_cash = cash / days if days else None
    p_eff = _sum_ing(ing, prior, "cost_effective") if prior else 0
    p_cash = _sum_ing(ing, prior, "cost_cash") if prior else 0
    p_days = _sum_ing(ing, prior, "days") if prior else 0
    p_inter = _sum_ing(ing, prior, "interactions") if prior else 0
    p_sessions = _sum_ing(ing, prior, "sessions") if prior else 0
    p_tok = {k: _sum_tokens(ing, prior, k) if prior else 0
             for k in ("in", "out", "cache_read", "cache_write")}
    p_denom = p_tok["in"] + p_tok["cache_read"] + p_tok["cache_write"] if prior else 0

    excluded_share = (excluded_inter / inter) if inter else None

    kpis = []

    # FPA-030/031: costes con delta de tasa diaria (siempre tasa diaria: es
    # la comparación justa incluso entre meses completos de distinta longitud)
    kpis.append(_kpi(
        "cost_effective", "Coste efectivo", eff if eff else None, fmt_usd,
        reason="sin coste efectivo en el periodo" if not eff else None,
        cur_rate=eff / days if days else None,
        prev_rate=(p_eff / p_days) if p_days else None,
        spark=_spark(ing, lambda i: i["cost_effective"] / i["days"]
                     if i["days"] else None)))
    kpis.append(_kpi(
        "cost_cash", "Coste cash", cash if cash else None, fmt_usd,
        reason="sin coste cash en el periodo" if not cash else None,
        cur_rate=cash / days if days else None,
        prev_rate=(p_cash / p_days) if p_days else None,
        spark=_spark(ing, lambda i: i["cost_cash"] / i["days"]
                     if i["days"] else None)))
    p_cash_ = p_cash if prior else 0
    kpis.append(_kpi(
        "leverage", "Leverage", eff / cash if cash else None,
        lambda v: f"{v:.1f}×",
        reason="requiere coste cash > 0" if not cash else None,
        prev=(p_eff / p_cash) if p_cash else None,
        spark=_spark(ing, lambda i: i["cost_effective"] / i["cost_cash"]
                     if i["cost_cash"] else None)))
    kpis.append(_kpi(
        "cost_per_1k_eff", "Coste efectivo por 1k",
        eff / (inter / 1000) if inter else None, fmt_usd,
        reason="sin interacciones en el periodo" if not inter else None,
        prev=(p_eff / (p_inter / 1000)) if p_inter else None,
        spark=_spark(ing, lambda i: i["cost_effective"] / (i["interactions"] / 1000)
                     if i["interactions"] else None)))
    kpis.append(_kpi(
        "cost_per_1k_cash", "Coste cash por 1k",
        cash / (inter / 1000) if inter else None, fmt_usd,
        reason="sin interacciones en el periodo" if not inter else None,
        prev=(p_cash / (p_inter / 1000)) if p_inter else None,
        spark=_spark(ing, lambda i: i["cost_cash"] / (i["interactions"] / 1000)
                     if i["interactions"] else None)))
    kpis.append(_kpi(
        "cost_per_session", "Coste por sesión",
        eff / sessions if sessions else None, fmt_usd,
        reason="sin sesiones en el periodo" if not sessions else None,
        prev=(p_eff / _sum_ing(ing, prior, "sessions")) if p_sessions else None,
        spark=_spark(ing, lambda i: i["cost_effective"] / i["sessions"]
                     if i["sessions"] else None)))
    kpis.append(_kpi(
        "top3_concentration", "Concentración top-3",
        top3 / proj_cost if proj_cost else None, lambda v: f"{v * 100:.1f}%",
        reason="sin coste por proyecto en el periodo" if not proj_cost else None,
        prev=(_sum_ing(ing, prior, "top3_cost") / _sum_ing(ing, prior, "proj_cost"))
        if prior and _sum_ing(ing, prior, "proj_cost") else None,
        spark=_spark(ing, lambda i: i["top3_cost"] / i["proj_cost"]
                     if i["proj_cost"] else None)))
    # share premium: la lista de modelos premium viene del config → assumed
    kpis.append(_kpi(
        "premium_share", "Share premium",
        premium_cost / eff if eff else None, lambda v: f"{v * 100:.1f}%",
        provenance="assumed",
        reason="sin coste efectivo en el periodo" if not eff else None,
        prev=(_sum_ing(ing, prior, "premium_cost") / p_eff) if p_eff else None,
        spark=_spark(ing, lambda i: i["premium_cost"] / i["cost_effective"]
                     if i["cost_effective"] else None)))
    kpis.append(_kpi(
        "autonomous_share", "Autonomous share",
        sessions_agent / sessions if sessions else None, lambda v: f"{v * 100:.1f}%",
        reason="sin sesiones en el periodo" if not sessions else None,
        prev=(_sum_ing(ing, prior, "sessions_agent") / p_sessions) if p_sessions else None,
        spark=_spark(ing, lambda i: i["sessions_agent"] / i["sessions"]
                     if i["sessions"] else None)))
    kpis.append(_kpi(
        "multitasking_share", "Multitasking",
        mt_inter / inter if inter else None, lambda v: f"{v * 100:.1f}%",
        reason="sin interacciones en el periodo" if not inter else None,
        prev=(_sum_ing(ing, prior, "mt_interactions") / p_inter) if p_inter else None,
        spark=_spark(ing, lambda i: i["mt_interactions"] / i["interactions"]
                     if i["interactions"] else None)))
    # FPA-043/045: token KPIs con exclusión de tools sin tokens
    denom = tok["in"] + tok["cache_read"] + tok["cache_write"]
    kpis.append(_kpi(
        "cache_hit_rate", "Cache-hit rate",
        tok["cache_read"] / denom if denom else None, lambda v: f"{v * 100:.1f}%",
        reason="sin tokens registrados en el periodo" if not denom else None,
        prev=(p_tok["cache_read"] / p_denom) if p_denom else None,
        excluded_share=excluded_share,
        spark=_spark(ing, lambda i: (lambda d: i["tokens"]["cache_read"] / d
                                     if d else None)(
            i["tokens"]["in"] + i["tokens"]["cache_read"] + i["tokens"]["cache_write"]))))
    kpis.append(_kpi(
        "out_in_ratio", "Ratio out/in",
        tok["out"] / tok["in"] if tok["in"] else None, lambda v: f"{v:.2f}",
        reason="sin tokens de input en el periodo" if not tok["in"] else None,
        prev=(p_tok["out"] / p_tok["in"]) if p_tok["in"] else None,
        excluded_share=excluded_share,
        spark=_spark(ing, lambda i: i["tokens"]["out"] / i["tokens"]["in"]
                     if i["tokens"]["in"] else None)))
    # FPA-040: outcome KPIs solo donde haya datos
    if commits:
        kpis.append(_kpi(
            "cost_per_commit", "Coste por commit", eff / commits, fmt_usd,
            prev=(p_eff / _sum_ing(ing, prior, "commits"))
            if prior and _sum_ing(ing, prior, "commits") else None,
            spark=_spark(ing, lambda i: i["cost_effective"] / i["commits"]
                         if i["commits"] else None)))
    if releases:
        kpis.append(_kpi(
            "cost_per_release", "Coste por release", eff / releases, fmt_usd,
            prev=(p_eff / _sum_ing(ing, prior, "releases"))
            if prior and _sum_ing(ing, prior, "releases") else None,
            spark=_spark(ing, lambda i: i["cost_effective"] / i["releases"]
                         if i["releases"] else None)))
    return kpis



# ----------------------------------------------------------------------
# Vistas pre-calculadas por periodo (FPA-026): Python computa, JS re-escala
# ----------------------------------------------------------------------

def _windows(months):
    """Ventanas predefinidas: periodo completo, cada año, cada trimestre y
    cada mes con datos. El selector JS solo elige entre vistas ya calculadas."""
    out = [("all", "Todo el periodo", list(months), None)]
    years = sorted({ym[:4] for ym in months})
    for y in years:
        wy = [ym for ym in months if ym.startswith(y)]
        py = str(int(y) - 1)
        pwy = [ym for ym in months if ym.startswith(py)]
        out.append((f"year:{y}", y, wy,
                    pwy if len(pwy) == len(wy) else None))
        for q in range(1, 5):
            qms = [f"{y}-{m:02d}" for m in range(3 * q - 2, 3 * q + 1)
                   if f"{y}-{m:02d}" in months]
            if not qms:
                continue
            pq = (q - 1) or 4
            py = f"{int(y) - 1}" if q == 1 else y
            pms = [f"{py}-{m:02d}" for m in range(3 * pq - 2, 3 * pq + 1)
                   if f"{py}-{m:02d}" in months]
            out.append((f"q:{y}Q{q}", f"Q{q} {y[2:]}", qms,
                        pms if len(pms) == len(qms) else None))
    for ym in months:
        idx = months.index(ym)
        p = [months[idx - 1]] if idx else None
        out.append((f"month:{ym}", month_label(ym), [ym], p))
    return out


def _tree_rows(node, window, prior, total_cost, is_time=False, full=False):
    """Filas de árbol pre-formateadas para una ventana (columnas FPA-023/024).
    Cada celda sale lista para render; JS no formatea nada."""
    cost = _cost_of(node, window)
    inter = _inter_of(node, window)
    prior_cost = _cost_of(node, prior) if prior else None
    row = {
        "key": node["key"], "label": node["label"],
        "cost": round(cost, 2),
        "cost_display": fmt_usd(cost) if cost else "n/a",
        "pct_display": (f"{100 * cost / total_cost:.1f}%"
                        if total_cost and cost else "n/a"),
        "interactions": inter,
        "interactions_display": fmt_int(inter),
        "per_1k_display": (fmt_usd(cost / (inter / 1000)) if inter and cost
                           else "n/a"),  # FPA-042
        "delta_display": (_delta_display(_pct_change(cost, prior_cost))
                          if prior_cost is not None else "n/a"),
        "totals_only": bool(node.get("totals_only")),
        "children": [],
    }
    if is_time:
        budget = sum(node["by_month"][m].get("budget", 0.0) or 0.0
                     for m in window if m in node["by_month"])
        variance = cost - budget
        row["budget_display"] = fmt_usd(budget) + " *" if budget else "n/a"
        row["variance_display"] = (f"{'+' if variance >= 0 else '-'}"
                                   f"${abs(variance):,.2f}" if budget else "n/a")
        row["variance_pct_display"] = (f"{100 * variance / budget:+.1f}%"
                                       if budget else "n/a")
    row["children"] = [
        _tree_rows(c, window, prior, total_cost, is_time, full)
        for c in node["children"]
        if full or not c.get("totals_only")  # drill Model: solo periodo completo
    ]
    return row


def _delta_display(delta):
    if delta is None:
        return "n/a"
    return f"{'+' if delta >= 0 else ''}{delta * 100:.1f}%"


def build_views(report, cfg):
    """FPA-026: una vista pre-calculada por ventana (todo, año, trimestre, mes).
    Cada vista trae KPIs con delta vs ventana previa, las tres columnas de
    árboles y su limitación si aplica (FPA-027)."""
    months_all = [m["ym"] for m in build_months(report)]
    ing = kpi_ingredients(report, cfg)
    months = [m for m in months_all if m in ing]
    trees = {
        "time": build_time_tree(report, cfg),
        "tool": build_tool_tree(report),
        "portfolio": build_portfolio_tree(report, cfg),
    }
    # FPA-101: roll-up verificado por árbol (falla ruidosa si se rompe)
    for name, tree in trees.items():
        bad = check_rollup(tree)
        if bad:
            raise ValueError(f"roll-up inconsistente en árbol {name}: {bad}")
    views = {}
    for key, label, window, prior in _windows(months):
        full = key == "all"
        view = {
            "label": label,
            "months": window,
            "has_prior": prior is not None,
            "kpis": kpis_for_window(ing, window, prior),
        }
        view["trees"] = {
            "time": _tree_rows(trees["time"], window, prior,
                               _cost_of(trees["time"], window), is_time=True),
            "tool": _tree_rows(trees["tool"], window, prior,
                               _cost_of(trees["tool"], window)),
            "portfolio": _tree_rows(trees["portfolio"], window, prior,
                                    _cost_of(trees["portfolio"], window),
                                    full=full),
        }
        if not full:  # FPA-021/027: el drill Project→Model solo tiene totales
            view["limitation"] = ("el drill Project→Model solo está disponible "
                                  "para el periodo completo (no hay "
                                  "project-by-model por mes)")
        views[key] = view
    return views


def build_data_notes(report):
    """Sección Data: definición de interacción + kinds (FPA-140), share
    filtrado (FPA-141), timezone (FPA-142) y concurrencia (FPA-120)."""
    md = report["metadata"]
    kinds_total = {"user_prompt": 0, "assistant_turn": 0, "tool_call": 0}
    for mo in report["monthly"].values():
        if mo["interactions"] == 0:
            continue
        for k, n in (mo.get("interaction_kinds") or {}).items():
            kinds_total[k] = kinds_total.get(k, 0) + n
    total_kinds = sum(kinds_total.values())
    filtered = report.get("filtered_out") or {}
    total_all = md["total_interactions"] + filtered.get("interactions", 0)
    tz = md.get("timezone")
    conc = report.get("concurrency") or {}
    return {
        "interaction_definition": (
            "interacción = una llamada de API registrada en los logs "
            "(assistant turn facturable). Los eventos se cuentan además por "
            "kind — user prompts, assistant turns y tool calls — para que la "
            "inflación por actividad de agentes sea visible (FPA-140)."),
        "kinds": kinds_total,
        "tool_call_share": (round(kinds_total["tool_call"] / total_kinds, 4)
                            if total_kinds else None),
        "filtered_share": (round(filtered.get("interactions", 0) / total_all, 4)
                           if total_all else None),
        "filtered_interactions": filtered.get("interactions", 0),
        "timezone": tz if tz else None,
        "timezone_missing_reason": (None if tz else
                                    "el reporte no registra timezone (FPA-142); "
                                    "vistas hora/día sin verificar"),
        "unverified_time": tz is None,
        "concurrency": conc,
    }


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
.kpi .spark { display: block; margin-top: .3rem; color: var(--acc); }
#period-select { font: inherit; margin-left: .4rem; }
.ttree { width: 100%; border-collapse: collapse; font-size: .85rem;
  font-variant-numeric: tabular-nums; }
.ttree th { text-align: right; padding: .25rem .5rem; border-bottom: 1px solid var(--line);
  font-weight: 600; color: var(--muted); }
.ttree th:first-child { text-align: left; }
.ttree td { text-align: right; padding: .2rem .5rem; border-bottom: 1px solid var(--line); }
.ttree td:first-child { text-align: left; }
.ttree details > summary { cursor: pointer; list-style: none; }
.ttree details > summary::before { content: '▸ '; color: var(--muted); }
.ttree details[open] > summary::before { content: '▾ '; }
#data { margin-top: 1.5rem; }
#data table { border-collapse: collapse; }
#data th, #data td { padding: .2rem .7rem; border-bottom: 1px solid var(--line);
  text-align: left; }
#view-limitation { color: var(--muted); }
"""

CSS_LEGACY = (  # retro confinado a header/footer, sin animación (FPA-178)
    ".retro::before { content: '▚▞ '; color: var(--acc); }"
)


def prov_tag(kind):
    """Tag visible de procedencia: reported / assumed."""
    label = "reported" if kind == "reported" else "assumed"
    return f'<span class="prov-tag" title="procedencia: {kind}">{label}</span>'


def kpi_card(k):
    """Card de KPI con sparkline SVG, delta y provenance (FPA-030…045)."""
    if k["value"] is None:  # FPA-042: n/a con razón, nunca cero/infinito
        value = fig('<span class="na">n/a</span>', k["provenance"])
        sub = f'<p class="reason">{k["reason"]}</p>'
    else:
        value = fig(f'<span class="val">{k["display"]}</span>', k["provenance"])
        d = k.get("delta_display")
        sub = (f'<p class="interp">Δ vs prior: {d or "n/a"}'
               + (f' <span class="small">(tasa diaria)</span>'
                  if k.get("delta_kind") == "daily-rate" and d else "")
               + (f' · excluido por tokens: {k["excluded_display"]} (FPA-045)'
                  if k.get("excluded_share") else "")
               + "</p>")
    return (f'<div class="headline kpi" data-key="{k["key"]}">'
            f'<h3>{k["label"]}</h3>{value}{sub}'
            f'{sparkline_svg(k.get("spark"))}</div>')


def sparkline_svg(series, w=120, h=28):
    """FPA-030: sparkline mensual como SVG inline determinista."""
    vals = [p["value"] for p in (series or [])]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    step = w / (len(vals) - 1)
    pts = " ".join(
        f"{i * step:.1f},{h - 2 - (v - lo) / span * (h - 4):.1f}"
        for i, v in enumerate(vals))
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="sparkline"><polyline fill="none" '
            f'stroke="currentColor" stroke-width="1.5" points="{pts}"/></svg>')


def tree_section(name, title, root, is_time=False):
    """Sección de árbol expandible (FPA-020/022) con columnas pre-formateadas."""
    cols = ("Nodo", "Coste", "% total", "Interacciones", "$/1k", "Δ vs prior")
    if is_time:
        cols += ("Presupuesto*", "Varianza", "Var %")
    head = "".join(f"<th>{c}</th>" for c in cols)
    rows = _tree_html(root, is_time)
    return (f'<details class="tree" data-tree="{name}" open>'
            f'<summary><h2>{title}</h2></summary>'
            f'<table class="ttree"><thead><tr>{head}</tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'{"<p class=\"small\">* presupuesto cash del config (assumed)." if is_time else ""}'
            f'</details>')


def _tree_html(row, is_time=False, depth=0):
    cells = (f'<td>{row["cost_display"]}</td><td>{row["pct_display"]}</td>'
             f'<td>{row["interactions_display"]}</td><td>{row["per_1k_display"]}</td>'
             f'<td>{row["delta_display"]}</td>')
    if is_time:
        cells += (f'<td>{row["budget_display"]}</td>'
                  f'<td>{row["variance_display"]}</td>'
                  f'<td>{row["variance_pct_display"]}</td>')
    kids = "".join(_tree_html(c, is_time, depth + 1) for c in row["children"])
    if kids:
        label = (f'<details open><summary class="tlabel">{row["label"]}</summary>'
                 f'</details>')
    else:
        label = (f'<span style="display:inline-block;margin-left:{depth * 14}px">'
                 f'{row["label"]}</span>')
    return f'<tr class="trow" data-key="{row["key"]}"><td>{label}</td>{cells}</tr>{kids}'


def data_notes_html(notes):
    """Sección Data: definición, kinds, share filtrado, timezone, concurrencia."""
    ks = notes["kinds"]
    total_kinds = sum(ks.values())
    kind_cells = "".join(
        f'<tr><td>{k}</td><td>{fmt_int(v)}</td>'
        f'<td>{(f"{100 * v / total_kinds:.1f}%" if total_kinds else "n/a")}</td></tr>'
        for k, v in sorted(ks.items(), key=lambda x: -x[1]))
    share_txt = (f"{100 * notes['tool_call_share']:.1f}%"
                 if notes["tool_call_share"] is not None else "n/a (sin kinds)")
    filt = (f"{100 * notes['filtered_share']:.1f}%"
            if notes["filtered_share"] is not None else "n/a")
    if notes["unverified_time"]:  # FPA-142
        tz_cell = ('<span class="na">n/a</span> — ' + notes["timezone_missing_reason"])
    else:
        tz = notes["timezone"]
        tz_cell = fig(tz, "reported")
    conc = notes["concurrency"] or {}
    dp = conc.get("distinct_projects_per_hour") or {}
    ps = conc.get("peak_simultaneous_sessions") or {}
    sw = conc.get("project_switches_per_active_hour") or {}
    ps_peak = (fmt_int(ps["peak"]) if ps.get("peak") is not None
               else 'n/a — ' + (ps.get("reason") or "sin datos"))
    return f'''<section id="data" aria-label="Datos y definiciones">
  <h2>Datos y definiciones</h2>
  <p>{notes["interaction_definition"]}</p>
  <table class="small"><caption>Interacciones por kind</caption>
    <thead><tr><th>kind</th><th>Eventos</th><th>Share</th></tr></thead>
    <tbody>{kind_cells}</tbody></table>
  <p>Share de tool calls: {share_fig(notes["tool_call_share"])} —
     share excluido por el filtro charly: {share_fig(notes["filtered_share"])}
     ({fmt_int(notes["filtered_interactions"])} interacciones).</p>
  <p>Timezone de bucketing hora/día: {tz_cell}</p>
  <p>Concurrencia — proyectos distintos/hora ({dp.get("measure", "n/a")}): pico {fmt_int(dp.get("peak", 0))},
     media {dp.get("avg", 0)}/h · pico de sesiones simultáneas ({ps.get("measure", "parallel-agent")}):
     {ps_peak} · switches de proyecto/hora activa ({sw.get("measure", "human-context-switching")}): {sw.get("value", "n/a")}</p>
</section>'''


def share_fig(v):
    return fig(f"{100 * v:.1f}%", "reported") if v is not None else \
        '<span class="na">n/a</span>'


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

    # F2: vistas pre-calculadas, KPI strip, árboles y sección Data
    views = model["views"]
    all_view = views["all"]
    kpis_html = "".join(kpi_card(k) for k in all_view["kpis"])
    trees_html = (
        tree_section("time", "Árbol Time (Año → Trimestre → Mes)",
                     all_view["trees"]["time"], is_time=True)
        + tree_section("tool", "Árbol Tool (Tool → Model)",
                       all_view["trees"]["tool"])
        + tree_section("portfolio", "Árbol Portfolio (Categoría → Proyecto)",
                       all_view["trees"]["portfolio"]))
    notes_html = data_notes_html(model["data_notes"])

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
  <section id="kpi-strip" aria-label="KPIs del periodo">
    <h2>KPIs <span class="small">del periodo:</span>
      <select id="period-select" aria-label="Seleccionar periodo">
        <option value="all" selected>Todo el periodo</option>
        {''.join(f'<option value="{k}">{v["label"]}</option>' for k, v in views.items() if k != 'all')}
      </select>
    </h2>
    <div class="cards" id="kpi-cards">{kpis_html}</div>
    <p class="small" id="view-limitation" hidden></p>
  </section>
  <section id="trees" aria-label="Árboles expandibles">
    <h2>Árboles</h2>
    <div id="tree-box">{trees_html}</div>
  </section>
  {notes_html}
</main>
<footer class="site">
  <p class="retro small">Dashboard FP&A · generado por viz-fpa.py (stdlib-only,
  SVG inline) · cifras con tag reported/assumed</p>
</footer>
<script type="application/json" id="fpa-model">{model_json}</script>
<script>
(function () {{
  "use strict";
  var MODEL = JSON.parse(document.getElementById("fpa-model").textContent);
  function esc(s) {{
    return String(s).replace(/[&<>"']/g, function (c) {{
      if (c === "&") return "&amp;";
      if (c === "<") return "&lt;";
      if (c === ">") return "&gt;";
      if (c === "'") return "&#39;";
      return "&quot;";
    }});
  }}
  function kpiCard(k) {{
    var value = k.value === null
      ? '<span class="fig" data-provenance="' + k.provenance + '"><span class="na">n/a</span></span><p class="reason">' + esc(k.reason || "") + '</p>'
      : '<span class="fig" data-provenance="' + k.provenance + '"><span class="val">' + esc(k.display) + '</span></span>'
        + '<p class="interp">Δ vs prior: ' + esc(k.delta_display || "n/a")
        + (k.delta_kind === "daily-rate" && k.delta_display ? ' <span class="small">(tasa diaria)</span>' : '')
        + (k.excluded_share ? ' · excluido por tokens: ' + esc(k.excluded_display) + ' (FPA-045)' : '')
        + '</p>';
    var spark = (k.spark && k.spark.length > 1)
      ? '<svg class="spark" width="120" height="28" viewBox="0 0 120 28" role="img" aria-label="sparkline">'
        + sparkPoints(k.spark) + '</svg>' : "";
    return '<div class="headline kpi" data-key="' + esc(k.key) + '"><h3>' + esc(k.label) + '</h3>'
      + value + spark + '</div>';
  }}
  function sparkPoints(series) {{
    var vals = series.map(function (p) {{ return p.value; }});
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    var span = (hi - lo) || 1, step = 120 / (vals.length - 1);
    var pts = vals.map(function (v, i) {{
      return (i * step).toFixed(1) + "," + (28 - 2 - (v - lo) / span * 24).toFixed(1);
    }}).join(" ");
    return '<polyline fill="none" stroke="currentColor" stroke-width="1.5" points="' + pts + '"/>';
  }}
  function treeRows(row, isTime, depth) {{
    var cells = '<td>' + esc(row.cost_display) + '</td><td>' + esc(row.pct_display)
      + '</td><td>' + esc(row.interactions_display) + '</td><td>' + esc(row.per_1k_display)
      + '</td><td>' + esc(row.delta_display) + '</td>';
    if (isTime) cells += '<td>' + esc(row.budget_display) + '</td><td>'
      + esc(row.variance_display) + '</td><td>' + esc(row.variance_pct_display) + '</td>';
    var label = row.children.length
      ? '<details open><summary class="tlabel">' + esc(row.label) + '</summary></details>'
      : '<span style="display:inline-block;margin-left:' + (depth * 14) + 'px">' + esc(row.label) + '</span>';
    return '<tr class="trow" data-key="' + esc(row.key) + '"><td>' + label + '</td>' + cells + '</tr>'
      + row.children.map(function (c) {{ return treeRows(c, isTime, depth + 1); }}).join("");
  }}
  function renderView(key) {{
    var v = MODEL.views[key];
    if (!v) return;
    document.getElementById("kpi-cards").innerHTML = v.kpis.map(kpiCard).join("");
    var lim = document.getElementById("view-limitation");
    if (v.limitation) {{ lim.textContent = "Limitación: " + v.limitation; lim.hidden = false; }}
    else lim.hidden = true;
    var box = document.getElementById("tree-box");
    box.innerHTML = treeBlock("time", "Árbol Time (Año → Trimestre → Mes)", v.trees.time, true)
      + treeBlock("tool", "Árbol Tool (Tool → Model)", v.trees.tool, false)
      + treeBlock("portfolio", "Árbol Portfolio (Categoría → Proyecto)", v.trees.portfolio, false);
  }}
  function treeBlock(name, title, root, isTime) {{
    var cols = ["Nodo", "Coste", "% total", "Interacciones", "$/1k", "Δ vs prior"];
    if (isTime) cols.push("Presupuesto*", "Varianza", "Var %");
    var head = cols.map(function (c) {{ return "<th>" + c + "</th>"; }}).join("");
    return '<details class="tree" data-tree="' + name + '" open><summary><h2>' + title
      + '</h2></summary><table class="ttree"><thead><tr>' + head
      + '</tr></thead><tbody>' + treeRows(root, isTime, 0) + '</tbody></table>'
      + (isTime ? '<p class="small">* presupuesto cash del config (assumed).</p>' : "")
      + '</details>';
  }}
  var sel = document.getElementById("period-select");
  if (sel) sel.addEventListener("change", function () {{ renderView(sel.value); }});
}})();
</script>
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
