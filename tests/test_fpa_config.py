#!/usr/bin/env python3
"""
test_fpa_config.py — tests de scripts/fpa_config.py (F0: config/fpa.json)

Estrategia (std-lib only, como el repo):
- validate_config(): errores de forma (secciones requeridas, FPA-168 targets
  vacíos, fechas, horarios, presupuesto).
- classify_project(): FPA-018 — override gana, luego primera regla que matchea,
  fallback "Unclassified".
- rates_for(): FPA-016 — pricing versionado por fecha efectiva.
- Schema extendido (specs/usage-report-v3.schema.json): el reporte actual sigue
  válido y los campos nuevos aceptan muestras válidas (jsonschema si está
  instalado, skip si no).
"""

import importlib.util
import json
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "fpa_config", REPO / "scripts" / "fpa_config.py"
)
fpa_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fpa_config)


def _cfg(**over):
    """Fixture mínimo válido derivado del config real."""
    cfg = json.loads((REPO / "config" / "fpa.json").read_text())
    for k, v in over.items():
        if v is None:
            cfg.pop(k, None)
        else:
            cfg[k] = v
    return cfg


class TestConfigRealValido(unittest.TestCase):
    """El config del repo debe validar sin errores."""

    def test_config_real_valida(self):
        errors = fpa_config.validate_config(fpa_config.load_fpa_config())
        self.assertEqual([], errors)

    def test_idioma_es(self):
        cfg = fpa_config.load_fpa_config()
        self.assertEqual("es", cfg["language"])

    def test_retro_default_on(self):
        cfg = fpa_config.load_fpa_config()
        self.assertTrue(cfg["retro"]["enabled"])

    def test_horarios_default_spec(self):
        cfg = fpa_config.load_fpa_config()
        self.assertEqual([1, 2, 3, 4, 5], cfg["working_hours"]["days"])
        self.assertEqual("09:00", cfg["working_hours"]["start"])
        self.assertEqual("18:00", cfg["working_hours"]["end"])

    def test_suscripciones_default_spec(self):
        """FPA-015: Pro Mar-19, Max Abr-19, Pro Jun-19."""
        subs = fpa_config.load_fpa_config()["subscriptions"]["claude-cli"]
        self.assertEqual("2026-03-19", subs[0]["start"])
        self.assertEqual(20, subs[0]["monthly_fee"])
        self.assertEqual("2026-04-19", subs[1]["start"])
        self.assertEqual(100, subs[1]["monthly_fee"])
        self.assertEqual("2026-06-19", subs[2]["start"])
        self.assertEqual(20, subs[2]["monthly_fee"])
        self.assertIsNone(subs[2]["end"])

    def test_presupuesto_mes_inicio_default(self):
        """FPA-051: budgets aplican solo desde el mes de inicio (default Abril)."""
        cfg = fpa_config.load_fpa_config()
        self.assertEqual("2026-04", cfg["budgets"]["start_month"])
        for key in ("cash_monthly", "effective_monthly", "target_per_1k"):
            self.assertIsInstance(cfg["budgets"][key], (int, float))

    def test_umbrales_alerta_defaults_spec(self):
        """FPA-088 con defaults de la spec (FPA-081/084/085/086/087)."""
        th = fpa_config.load_fpa_config()["alert_thresholds"]
        self.assertEqual(25, th["plan_usage_multiple"])
        self.assertEqual(15, th["unit_cost_rise_pct"])
        self.assertEqual(5, th["premium_share_rise_pts"])
        self.assertEqual(50, th["concentration_top3_pct"])
        self.assertEqual(14, th["staleness_days"])

    def test_modelos_premium_default_opus(self):
        """FPA-037: lista configurable, default Opus."""
        self.assertIn("opus", fpa_config.load_fpa_config()["premium_models"])

    def test_lifecycle_dormancia(self):
        """FPA-122: nuevo = primera actividad dentro de N días (default 30)."""
        self.assertEqual(30, fpa_config.load_fpa_config()["lifecycle"]["new_days"])

    def test_ctas_ningun_target_vacio(self):
        """FPA-168: el generador falla si un CTA configurado tiene target vacío."""
        ctas = fpa_config.load_fpa_config()["ctas"]
        self.assertEqual("Leer la serie", ctas["primary"]["label"])
        self.assertLessEqual(len(ctas["secondary"]), 3)
        for cta in [ctas["primary"], *ctas["secondary"]]:
            self.assertTrue(cta.get("target"), f"target vacío: {cta}")


class TestValidateConfig(unittest.TestCase):
    def test_falta_seccion_requerida(self):
        for section in (
            "taxonomy", "subscriptions", "model_pricing", "budgets",
            "alert_thresholds", "premium_models", "working_hours",
            "lifecycle", "ctas", "language", "retro",
        ):
            with self.subTest(section=section):
                errors = fpa_config.validate_config(_cfg(**{section: None}))
                self.assertTrue(
                    any(section in e for e in errors),
                    f"'{section}' ausente no reportado: {errors}",
                )

    def test_cta_target_vacio_falla(self):
        """FPA-168: target vacío → error (la clave ctas existe)."""
        cfg = _cfg()
        cfg["ctas"]["primary"]["target"] = ""
        errors = fpa_config.validate_config(cfg)
        self.assertTrue(any("target" in e.lower() for e in errors))

    def test_budget_start_month_formato(self):
        cfg = _cfg()
        cfg["budgets"]["start_month"] = "abril"
        errors = fpa_config.validate_config(cfg)
        self.assertTrue(any("start_month" in e for e in errors))

    def test_horario_dia_invalido(self):
        cfg = _cfg()
        cfg["working_hours"]["days"] = [0, 8]
        errors = fpa_config.validate_config(cfg)
        self.assertTrue(any("working_hours" in e for e in errors))

    def test_horario_hora_invalida(self):
        cfg = _cfg()
        cfg["working_hours"]["start"] = "9am"
        errors = fpa_config.validate_config(cfg)
        self.assertTrue(any("start" in e for e in errors))

    def test_forma_malformada_no_crash(self):
        """Config malformado devuelve errores, nunca excepción."""
        for section, bad in (
            ("subscriptions", ["no-dict"]),
            ("model_pricing", ["no-dict"]),
            ("ctas", "no-dict"),
            ("taxonomy", ["no-dict"]),
        ):
            with self.subTest(section=section):
                errors = fpa_config.validate_config(_cfg(**{section: bad}))
                self.assertTrue(any(section in e for e in errors))

    def test_regla_taxonomia_sin_shape(self):
        cfg = _cfg()
        cfg["taxonomy"]["rules"] = [{"category": "x"}, {"match": "^y"}]
        errors = fpa_config.validate_config(cfg)
        self.assertTrue(any("rules" in e for e in errors))


class TestClassifyProject(unittest.TestCase):
    """FPA-018: taxonomía por reglas de nombre + overrides, fallback Unclassified."""

    def test_regla_charly(self):
        cfg = _cfg()
        self.assertEqual("charly", fpa_config.classify_project(cfg, "charly-wai"))
        self.assertEqual("charly", fpa_config.classify_project(cfg, "charly/tv"))

    def test_regla_sk(self):
        cfg = _cfg()
        self.assertEqual("sk", fpa_config.classify_project(cfg, "sk-REPLy-jl"))

    def test_override_gana_sobre_regla(self):
        cfg = _cfg()
        cfg["taxonomy"]["overrides"]["charly-wai"] = "otro"
        self.assertEqual("otro", fpa_config.classify_project(cfg, "charly-wai"))

    def test_fallback_unclassified(self):
        cfg = _cfg()
        cfg["taxonomy"]["rules"] = []
        self.assertEqual(
            "Unclassified", fpa_config.classify_project(cfg, "proyecto-raro")
        )


class TestRatesFor(unittest.TestCase):
    """FPA-016: pricing versionado por fecha efectiva."""

    def test_unica_version(self):
        cfg = _cfg()
        rates = fpa_config.rates_for(cfg, date(2026, 5, 1))
        self.assertEqual(
            cfg["model_pricing"]["versions"][0]["rates"], rates
        )

    def test_version_por_fecha(self):
        cfg = _cfg()
        cfg["model_pricing"]["versions"] = [
            {"effective": "2026-01-01", "rates": {"claude": {"a": 1}}},
            {"effective": "2026-06-01", "rates": {"claude": {"a": 2}}},
        ]
        before = fpa_config.rates_for(cfg, date(2026, 3, 1))
        after = fpa_config.rates_for(cfg, date(2026, 7, 1))
        self.assertEqual({"claude": {"a": 1}}, before)
        self.assertEqual({"claude": {"a": 2}}, after)

    def test_antes_de_primera_version_usa_default(self):
        cfg = _cfg()
        cfg["model_pricing"]["versions"] = [
            {"effective": "2026-06-01", "rates": {"claude": {"a": 2}}}
        ]
        self.assertEqual(
            cfg["model_pricing"]["default_rates"],
            fpa_config.rates_for(cfg, date(2026, 1, 1)),
        )


class TestSchemaExtendido(unittest.TestCase):
    """El schema extendido acepta los campos nuevos y sigue validando el reporte actual."""

    def setUp(self):
        self.schema = json.loads(
            (REPO / "specs" / "usage-report-v3.schema.json").read_text()
        )

    def _validate(self, doc):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema no instalado")
        jsonschema.validate(doc, self.schema)

    def test_reporte_actual_sigue_valido(self):
        report = json.loads((REPO / "data" / "usage_report_v3.json").read_text())
        self._validate(report)

    def test_emisiones_nuevas_aceptadas(self):
        report = json.loads((REPO / "data" / "usage_report_v3.json").read_text())
        report["metadata"]["timezone"] = "America/Argentina/Buenos_Aires"
        report["metadata"]["interaction_kinds"] = {
            "user_prompt": 10, "assistant_turn": 20, "tool_call": 30,
        }
        report["metadata"]["filtered"] = {"interactions": 5, "cost_effective": 0.5}
        mes = report["monthly"]["2026-06"]
        mes["tokens_by_model"] = {
            "claude-cli": {"opus-4.5": {
                "in": 1, "out": 2, "cache_read": 3, "cache_write": 4,
            }}
        }
        mes["pay_per_token_charges"] = 0.0
        mes["interaction_kinds"] = {"user_prompt": 1, "tool_call": 2}
        mes["outcomes_by_project"] = {"charly-wai": {"commits": 3, "releases": 1}}
        report["concurrency"] = {
            "peak_simultaneous_sessions": 2,
            "switches_per_active_hour": 1.5,
        }
        self._validate(report)

    def test_pay_per_token_admite_null(self):
        """FPA-013: cargas pay-per-token sin datos reales → null permitido."""
        report = json.loads((REPO / "data" / "usage_report_v3.json").read_text())
        report["monthly"]["2026-06"]["pay_per_token_charges"] = None
        self._validate(report)


class TestConsistenciaConTracker(unittest.TestCase):
    """Hasta que coffe-mbz parametrice el tracker, config y tracker no deben divergir.

    Hallazgo ro5u CORR-001: config/fpa.json duplica SUBSCRIPTIONS y MODEL_PRICING
    de scripts/usage-tracker.py; este test hace la divergencia sonora.
    """

    def _tracker_mod(self):
        spec = importlib.util.spec_from_file_location(
            "usage_tracker", REPO / "scripts" / "usage-tracker.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_suscripciones_iguales(self):
        tracker = self._tracker_mod()
        cfg_subs = fpa_config.load_fpa_config()["subscriptions"]
        self.assertEqual(tracker.SUBSCRIPTIONS, cfg_subs)

    def test_pricing_igual(self):
        tracker = self._tracker_mod()
        cfg = fpa_config.load_fpa_config()
        self.assertEqual(
            tracker.MODEL_PRICING, cfg["model_pricing"]["versions"][0]["rates"]
        )
        self.assertEqual(tracker.DEFAULT_RATES, cfg["model_pricing"]["default_rates"])


if __name__ == "__main__":
    unittest.main()
