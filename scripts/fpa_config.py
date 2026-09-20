#!/usr/bin/env python3
"""
fpa_config.py — carga y validación de config/fpa.json (F0 del epic coffe-lat)

Responsabilidades:
- Cargar el config único del dashboard FP&A (FPA-015/016/018/050/051/088/037/
  111/122/168/162/178) y validarlo antes de generar el dashboard.
- classify_project(): taxonomía FPA-018 — override gana, luego la primera regla
  cuyo patrón matchea el nombre del proyecto, si no el fallback ("Unclassified").
- rates_for(): pricing FPA-016 versionado por fecha efectiva — la última versión
  con effective <= fecha; si no hay ninguna, default_rates.

Rationale: los valores de coste son *assumed* (FPA-003); centralizarlos en un
JSON versionado evita precios hardcodeados (hallazgo FPA-015/016 de la spec).
Stdlib-only, igual que el resto del repo.
"""

import json
import re
from datetime import date
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config") / "fpa.json"

REQUIRED_SECTIONS = (
    "taxonomy",
    "subscriptions",
    "model_pricing",
    "budgets",
    "alert_thresholds",
    "premium_models",
    "working_hours",
    "lifecycle",
    "ctas",
    "language",
    "retro",
)

_MONTH_RE = re.compile(r"^[0-9]{4}-[0-9]{2}$")
_HHMM_RE = re.compile(r"^[0-9]{2}:[0-9]{2}$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def load_fpa_config(path=DEFAULT_CONFIG_PATH):
    """Cargar config/fpa.json. Lanza FileNotFoundError si no existe."""
    return json.loads(Path(path).read_text())


def validate_config(cfg):
    """Validar el config; devuelve lista de errores ([] = válido).

    Chequeos: secciones requeridas, formato de fechas/meses/horarios,
    entradas de suscripción, targets de CTAs no vacíos (FPA-168).
    """
    errors = []

    for section in REQUIRED_SECTIONS:
        if section not in cfg:
            errors.append(f"sección requerida ausente: {section}")

    taxonomy = cfg.get("taxonomy", {})
    if not isinstance(taxonomy, dict):
        errors.append("taxonomy debe ser un objeto")
    else:
        for key in ("rules", "overrides", "fallback"):
            if key not in taxonomy:
                errors.append(f"taxonomy.{key} ausente")
        for i, rule in enumerate(taxonomy.get("rules", [])):
            if not isinstance(rule, dict) or "match" not in rule or "category" not in rule:
                errors.append(f"taxonomy.rules[{i}] sin match/category")

    subscriptions = cfg.get("subscriptions", {})
    if not isinstance(subscriptions, dict):
        errors.append("subscriptions debe ser un objeto")
    else:
        for tool, entries in subscriptions.items():
            if not isinstance(entries, list) or not entries:
                errors.append(f"subscriptions.{tool}: lista vacía o no lista")
                continue
            for i, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    errors.append(f"subscriptions.{tool}[{i}] no es objeto")
                    continue
                if not _DATE_RE.match(str(entry.get("start", ""))):
                    errors.append(f"subscriptions.{tool}[{i}].start inválida")
                end = entry.get("end")
                if end is not None and not _DATE_RE.match(str(end)):
                    errors.append(f"subscriptions.{tool}[{i}].end inválida")
                if not isinstance(entry.get("monthly_fee"), (int, float)):
                    errors.append(f"subscriptions.{tool}[{i}].monthly_fee inválido")

    pricing = cfg.get("model_pricing", {})
    if not isinstance(pricing, dict):
        errors.append("model_pricing debe ser un objeto")
    else:
        if "default_rates" not in pricing:
            errors.append("model_pricing.default_rates ausente")
        for i, version in enumerate(pricing.get("versions", [])):
            if not isinstance(version, dict) or not _DATE_RE.match(str(version.get("effective", ""))):
                errors.append(f"model_pricing.versions[{i}].effective inválida")

    budgets = cfg.get("budgets", {})
    if "start_month" in budgets and not _MONTH_RE.match(str(budgets["start_month"])):
        errors.append(f"budgets.start_month inválido: {budgets['start_month']}")
    for key in ("cash_monthly", "effective_monthly", "target_per_1k"):
        val = budgets.get(key)
        if not isinstance(val, (int, float)) or val < 0:
            errors.append(f"budgets.{key} inválido: {val}")

    wh = cfg.get("working_hours", {})
    for day in wh.get("days", []):
        if not isinstance(day, int) or not 1 <= day <= 7:
            errors.append(f"working_hours.days inválido: {day}")
    for key in ("start", "end"):
        if key in wh and not _HHMM_RE.match(str(wh[key])):
            errors.append(f"working_hours.{key} inválido: {wh[key]}")

    # FPA-088: umbrales de alertas presentes y numéricos
    for key, val in cfg.get("alert_thresholds", {}).items():
        if not isinstance(val, (int, float)) or isinstance(val, bool) or val < 0:
            errors.append(f"alert_thresholds.{key} inválido: {val}")

    if "ctas" in cfg:
        ctas = cfg["ctas"]
        if not isinstance(ctas, dict):
            errors.append("ctas debe ser un objeto")
        else:
            secondary = ctas.get("secondary", [])
            if not isinstance(secondary, list):
                errors.append("ctas.secondary debe ser una lista")
                secondary = []
            for cta in [ctas.get("primary", {}), *secondary]:
                if not isinstance(cta, dict) or not cta.get("target"):
                    errors.append(f"cta con target vacío: {cta.get('label', '?') if isinstance(cta, dict) else cta}")

    return errors


def classify_project(cfg, project):
    """FPA-018: categoría del proyecto según taxonomía del config."""
    taxonomy = cfg["taxonomy"]
    overrides = taxonomy.get("overrides", {})
    if project in overrides:
        return overrides[project]
    for rule in taxonomy.get("rules", []):
        if re.search(rule["match"], project):
            return rule["category"]
    return taxonomy.get("fallback", "Unclassified")


def rates_for(cfg, when):
    """FPA-016: rates vigentes para `when` (date) según versiones por effective.

    La última versión con effective <= when gana; si no hay ninguna
    (when anterior a todas), se usa default_rates.
    """
    pricing = cfg["model_pricing"]
    applicable = [
        v for v in pricing.get("versions", [])
        if date.fromisoformat(v["effective"]) <= when
    ]
    if not applicable:
        return pricing["default_rates"]
    return max(applicable, key=lambda v: v["effective"])["rates"]


if __name__ == "__main__":
    config = load_fpa_config()
    problems = validate_config(config)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        raise SystemExit(1)
    print("config/fpa.json OK")
