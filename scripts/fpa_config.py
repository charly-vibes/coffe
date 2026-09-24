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
- energy_for(): coeficientes de energía (kWh) versionados por fecha — igual
  contrato que rates_for pero SIN fallback silencioso: None si el `when` es
  anterior a toda versión (el tracker aborta loud, coffe-7mj.1).
- validate_config() exige el bloque energy_coefficients (coffe-7mj.1): tiers de
  J/token entregado, default_tier, cache_read_energy_factor y versions
  consistentes.

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
    "energy_coefficients",
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

    site_name = cfg.get("site_name")
    if not isinstance(site_name, str) or not site_name.strip():
        errors.append("site_name ausente o vacío (nombre llano del "
                      "dashboard, change update-fpa-site-integration)")

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

    repos = cfg.get("repos")
    if repos is not None:  # coffe-vp8: bloque opcional pero con forma estricta
        if not isinstance(repos, dict):
            errors.append("repos debe ser un objeto")
        else:
            owners = repos.get("owners") or {}
            if not isinstance(owners, dict) or not owners:
                errors.append("repos.owners ausente o vacío (label-prefix → org GH)")
            for key in ("private", "no_remote"):
                for entry in repos.get(key) or []:
                    if not isinstance(entry, str) or "/" not in entry:
                        errors.append(f"repos.{key}: entrada sin 'org/repo': {entry!r}")
                    elif entry.split("/", 1)[0] not in owners:
                        errors.append(f"repos.{key}: org desconocida {entry!r} "
                                      f"(owners: {sorted(owners)})")
            for label, url in (repos.get("url_overrides") or {}).items():
                if not isinstance(url, str) or not url.startswith("https://"):
                    errors.append(f"repos.url_overrides[{label!r}]: URL no https: {url!r}")

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

    # coffe-7mj.1: energía estimada (kWh) — bloque requerido, fail-loud
    energy = cfg.get("energy_coefficients")
    if not isinstance(energy, dict):
        errors.append("energy_coefficients debe ser un objeto (ausente en "
                      "configs previos a add-energy-estimates)")
    else:
        factor = energy.get("cache_read_energy_factor")
        if not isinstance(factor, (int, float)) or isinstance(factor, bool) \
                or not 0 <= factor <= 1:
            errors.append(f"energy_coefficients.cache_read_energy_factor "
                          f"inválido: {factor!r} (número en [0, 1])")
        tiers = energy.get("tiers")
        if not isinstance(tiers, dict) or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                and v > 0 for v in tiers.values()) \
                or not {"flash", "mid", "frontier"}.issubset(tiers):
            errors.append("energy_coefficients.tiers debe ser objeto con "
                          "J/token > 0 por tier (mínimo flash/mid/frontier)")
        default_tier = energy.get("default_tier")
        if not isinstance(default_tier, str) or not isinstance(tiers, dict) \
                or default_tier not in tiers:
            errors.append(f"energy_coefficients.default_tier inválido: "
                          f"{default_tier!r} (debe ser un tier declarado)")
        versions = energy.get("versions")
        if not isinstance(versions, list) or not versions:
            errors.append("energy_coefficients.versions ausente o vacía")
        for i, version in enumerate(versions or []):
            if not isinstance(version, dict) or not _DATE_RE.match(str(version.get("effective", ""))):
                errors.append(f"energy_coefficients.versions[{i}].effective inválida")
                continue
            vtiers = version.get("tiers")
            if not isinstance(vtiers, dict):
                errors.append(f"energy_coefficients.versions[{i}].tiers "
                              "debe ser objeto")
            elif isinstance(tiers, dict) and any(
                    k not in tiers for k in vtiers):
                errors.append(f"energy_coefficients.versions[{i}].tiers usa "
                              "tiers no declarados en el bloque raíz")
            mapping = version.get("model_tiers")
            if not isinstance(mapping, dict):
                errors.append(f"energy_coefficients.versions[{i}].model_tiers "
                              "debe ser objeto (modelo → tier declarado)")
            elif isinstance(vtiers, dict):
                for model, tier in mapping.items():
                    if tier not in vtiers:
                        errors.append(f"energy_coefficients.versions[{i}]"
                                      f".model_tiers[{model!r}]: tier "
                                      f"desconocido {tier!r}")

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

    # Umbrales opcionales de F5 (FPA-118/119): se validan solo si la clave
    # existe (las fases tempranas del change no la tenían).
    for section, key in (("timeline", "gap_days"), ("sessions", "long_turns")):
        if section in cfg:
            val = cfg[section].get(key) if isinstance(cfg[section], dict) else None
            if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
                errors.append(f"{section}.{key} inválido: {val}")

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
            # FPA-167/168: acciones de alertas también salen del config, con
            # target obligatorio (nunca vacío).
            actions = ctas.get("alert_actions", {})
            if not isinstance(actions, dict):
                errors.append("ctas.alert_actions debe ser un objeto")
            else:
                for rule, act in actions.items():
                    if not isinstance(act, dict) or not act.get("target"):
                        errors.append(f"cta con target vacío: {rule}")
                    elif not act.get("label"):
                        errors.append(f"cta sin label: {rule}")

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


def energy_for(cfg, when):
    """coffe-7mj.1: versión de energy_coefficients vigente para `when` (date).

    Igual contrato que rates_for PERO sin fallback silencioso: devuelve None
    si `when` es anterior a toda versión — el tracker aborta loud nombrando
    el mes (el agregado mensual de tokens no puede partirse entre versiones,
    así que la selección es por primer día del bucket).
    """
    energy = cfg["energy_coefficients"]
    applicable = [
        v for v in energy.get("versions", [])
        if date.fromisoformat(v["effective"]) <= when
    ]
    if not applicable:
        return None
    return max(applicable, key=lambda v: v["effective"])


if __name__ == "__main__":
    config = load_fpa_config()
    problems = validate_config(config)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        raise SystemExit(1)
    print("config/fpa.json OK")
