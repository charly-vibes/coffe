#!/usr/bin/env python3
"""
test_fpa_f4.py — tests de viz-fpa.py F4 (ticket coffe-lat.5)

Alcance: motor de alertas con severity + regla + evidencia (FPA-080),
reglas verify-plan (FPA-081), reconciliación (FPA-082), budget (FPA-083),
unit-cost (FPA-084), mix premium (FPA-085), concentración (FPA-086),
staleness (FPA-087), umbrales configurables (FPA-088); economía de
suscripción: utilización (FPA-130), break-even/headroom (FPA-131),
comparación 4 casos (FPA-132), disclaimer de usage limits (FPA-133).
Golden de utilización/break-even/comparación (FPA-105): REGEN_GOLDEN=1.
Reutiliza el fixture de meses parciales de test_fpa_f2 (FPA-102).
"""

import importlib.util
import json
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "golden" / "fpa-f4-snapshot.json"
REGEN_GOLDEN = os.environ.get("REGEN_GOLDEN") == "1"
TODAY = "2026-09-20"  # fecha fija para staleness determinista en tests/golden


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viz = _load("viz_fpa_f4", "scripts/viz-fpa.py")
f2 = _load("test_fpa_f2", "tests/test_fpa_f2.py")
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())


def _cfg(**th_over):
    cfg = json.loads(json.dumps(CONFIG))
    cfg["alert_thresholds"].update(th_over)
    return cfg


def _cfg_budget(**budget_over):
    cfg = json.loads(json.dumps(CONFIG))
    cfg["budgets"].update(budget_over)
    return cfg


def _fixture_with(**over):
    fx = f2.f2_fixture()
    for key, val in over.items():
        if val is None:
            fx.pop(key, None)
        else:
            fx[key] = val
    return fx


def _rules(alerts):
    return [a["rule"] for a in alerts]


def _by_rule(alerts, rule):
    return [a for a in alerts if a["rule"] == rule]


# ======================================================================
# Motor de alertas (FPA-080, 088)
# ======================================================================

class TestAlertEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = f2.f2_fixture()
        cls.alerts = viz.build_alerts(cls.fixture, CONFIG, today=TODAY)

    def test_alert_estructura(self):
        """FPA-080: cada alerta lleva severity, rule name y evidence."""
        for a in self.alerts:
            self.assertIn(a["severity"], ("high", "medium", "low"), a)
            self.assertTrue(a["rule"], a)
            self.assertIsInstance(a["evidence"], dict)
            self.assertTrue(a["message"], a)

    def test_umbrales_configurables(self):
        """FPA-088: los umbrales salen de config.alert_thresholds."""
        fx = self.fixture
        alerts = viz.build_alerts(fx, _cfg(concentration_top3_pct=101.0),
                                  today=TODAY)
        self.assertNotIn("concentration", _rules(alerts))
        alerts = viz.build_alerts(fx, _cfg(concentration_top3_pct=0.0),
                                  today=TODAY)
        self.assertIn("concentration", _rules(alerts))


# ======================================================================
# Reglas individuales
# ======================================================================

class TestVerifyPlan(unittest.TestCase):
    """FPA-081: Claude efectivo ÷ precio del plan > 25× → alerta."""

    def setUp(self):
        self.fx = f2.f2_fixture()

    def _with_claude_cost(self, cost):
        fx = self.fx
        fx["monthly"]["2026-05"]["tools"]["claude-cli"]["cost_effective"] = cost
        return fx

    def test_no_fira_bajo_umbral(self):
        alerts = viz.build_alerts(self._with_claude_cost(40.0), CONFIG, today=TODAY)
        self.assertNotIn("verify-plan", _rules(alerts))

    def test_fira_sobre_umbral(self):
        """3000 efectivo ÷ $100 (Max en mayo) = 30× > 25×."""
        alerts = viz.build_alerts(self._with_claude_cost(3000.0), CONFIG, today=TODAY)
        ev = _by_rule(alerts, "verify-plan")
        self.assertEqual(1, len(ev))
        self.assertEqual("2026-05", ev[0]["evidence"]["month"])
        self.assertEqual(30.0, ev[0]["evidence"]["multiple"])

    def test_umbral_configurable(self):
        fx = self._with_claude_cost(3000.0)
        alerts = viz.build_alerts(fx, _cfg(plan_usage_multiple=100.0), today=TODAY)
        self.assertNotIn("verify-plan", _rules(alerts))


class TestReconciliation(unittest.TestCase):
    """FPA-082: coste real reportado vs cargas implícitas del calendario."""

    def test_caso_readme_65_vs_220(self):
        """Caso motivador: reporte con $65.58 reales vs ~$220 implícitos."""
        fx = f2.f2_fixture()
        fx["subscription_fees_by_month"] = {"2026-05": 110.0, "2026-06": 110.0}
        fx["monthly"]["2026-05"]["cost_real"] = 55.58
        fx["monthly"]["2026-06"]["cost_real"] = 10.0
        alerts = viz.build_alerts(fx, CONFIG, today=TODAY)
        ev = _by_rule(alerts, "reconciliation")
        self.assertEqual(1, len(ev))
        self.assertAlmostEqual(65.58, ev[0]["evidence"]["reported"])
        self.assertAlmostEqual(220.0, ev[0]["evidence"]["implied"])
        self.assertIn("high", ev[0]["severity"])

    def test_no_fira_si_coinciden(self):
        """Tracker actual: fees plegados en cost_real → reportado = implícito."""
        fx = f2.f2_fixture()
        fx["subscription_fees_by_month"] = {"2026-05": 110.0, "2026-06": 110.0}
        fx["monthly"]["2026-05"]["cost_real"] = 120.0   # 110 fee + 10 p2p
        fx["monthly"]["2026-06"]["cost_real"] = 110.0   # 110 fee + 0 p2p
        alerts = viz.build_alerts(fx, CONFIG, today=TODAY)
        self.assertNotIn("reconciliation", _rules(alerts))

    def test_tolerancia_configurable(self):
        fx = f2.f2_fixture()
        fx["subscription_fees_by_month"] = {"2026-05": 100.0}
        fx["monthly"]["2026-05"]["cost_real"] = 85.0  # 15% off, tolerancia 10%
        alerts = viz.build_alerts(fx, _cfg(reconcile_tolerance_pct=20.0), today=TODAY)
        self.assertNotIn("reconciliation", _rules(alerts))

    def test_efectivo_y_cash_no_se_suman(self):
        """FPA-002: la evidencia jamás mezcla efectivo con cash."""
        fx = f2.f2_fixture()
        fx["subscription_fees_by_month"] = {"2026-05": 110.0}
        alerts = viz.build_alerts(fx, CONFIG, today=TODAY)
        ev = _by_rule(alerts, "reconciliation")
        if ev:
            for key in ev[0]["evidence"]:
                self.assertNotIn("effective", key.lower().replace("_", ""))


class TestBudgetAlert(unittest.TestCase):
    """FPA-083: mes sobre presupuesto → alerta con monto de overage."""

    def test_fira_con_cash_over(self):
        alerts = viz.build_alerts(f2.f2_fixture(), _cfg_budget(cash_monthly=15.0),
                                  today=TODAY)
        ev = _by_rule(alerts, "budget")
        months = {a["evidence"]["month"]: a for a in ev}
        self.assertIn("2026-05", months)
        self.assertAlmostEqual(5.0, months["2026-05"]["evidence"]["overage_cash"])

    def test_fira_con_efectivo_over(self):
        alerts = viz.build_alerts(f2.f2_fixture(), _cfg_budget(effective_monthly=40.0),
                                  today=TODAY)
        ev = _by_rule(alerts, "budget")
        months = {a["evidence"]["month"]: a for a in ev}
        self.assertIn("2026-05", months)
        self.assertAlmostEqual(10.0, months["2026-05"]["evidence"]["overage_eff"])

    def test_no_fira_en_presupuesto(self):
        alerts = viz.build_alerts(f2.f2_fixture(), CONFIG, today=TODAY)
        self.assertNotIn("budget", _rules(alerts))


class TestUnitCost(unittest.TestCase):
    """FPA-084: coste por 1k interacciones +15% MoM → alerta."""

    def setUp(self):
        self.fx = f2.f2_fixture()
        # unit cost may=500, jun=650 (+30%), jul=300 (−54%)

    def test_fira_en_may_to_jun(self):
        alerts = viz.build_alerts(self.fx, CONFIG, today=TODAY)
        ev = _by_rule(alerts, "unit-cost")
        self.assertEqual(1, len(ev))
        self.assertEqual("2026-06", ev[0]["evidence"]["month"])
        self.assertAlmostEqual(500.0, ev[0]["evidence"]["prev_per_1k"])
        self.assertAlmostEqual(650.0, ev[0]["evidence"]["cur_per_1k"])

    def test_umbral_configurable(self):
        alerts = viz.build_alerts(self.fx, _cfg(unit_cost_rise_pct=50.0), today=TODAY)
        self.assertNotIn("unit-cost", _rules(alerts))

    def test_mes_sin_datos_excluido(self):
        """FPA-017: un mes sin datos no genera comparación MoM."""
        fx = self.fx
        fx["monthly"]["2026-06"]["interactions"] = 0
        alerts = viz.build_alerts(fx, CONFIG, today=TODAY)
        self.assertNotIn("unit-cost", _rules(alerts))


class TestPremiumMix(unittest.TestCase):
    """FPA-085: share premium +5pts en 3 meses → alerta."""

    def _four_month_fixture(self, jul_opus_cost):
        """Fixture de 4 meses (abr–jul) para tener ventana de 3 meses."""
        fx = _fixture_with()
        abr = {
            "interactions": 100, "input_tokens": 100000, "output_tokens": 50000,
            "cache_read_tokens": 40000, "cache_write_tokens": 10000,
            "cost_effective": 40.0, "cost_real": 20.0,
            "tools": {"claude-cli": {"interactions": 100, "cost_effective": 40.0,
                                     "models": {}}},
            "models": {"claude-sonnet-4-6": {"interactions": 100,
                                             "cost_effective": 40.0}},
            "subscription_fees": 20.0,
        }
        fx["monthly"]["2026-04"] = abr
        if jul_opus_cost is not None:
            fx["monthly"]["2026-07"]["models"]["claude-opus-4.7"] = {
                "interactions": 10, "cost_effective": jul_opus_cost}
        return fx

    def test_no_fira_con_pocos_meses(self):
        """Ventana de 3 meses requiere ≥4 meses con datos."""
        alerts = viz.build_alerts(f2.f2_fixture(), CONFIG, today=TODAY)
        self.assertNotIn("mix", _rules(alerts))

    def test_fira_con_salto_premium(self):
        # abr 0% premium; jul 12/42 = 28.6% → +28.6pts > 5pts
        alerts = viz.build_alerts(self._four_month_fixture(12.0), CONFIG,
                                  today=TODAY)
        ev = _by_rule(alerts, "mix")
        self.assertEqual(1, len(ev))
        self.assertEqual("2026-07", ev[0]["evidence"]["month"])
        self.assertAlmostEqual(28.57, ev[0]["evidence"]["rise_pts"], places=1)

    def test_no_fira_si_plano(self):
        alerts = viz.build_alerts(self._four_month_fixture(0.5), CONFIG,
                                  today=TODAY)
        self.assertNotIn("mix", _rules(alerts))

    def test_umbral_configurable(self):
        alerts = viz.build_alerts(self._four_month_fixture(12.0),
                                  _cfg(premium_share_rise_pts=50.0), today=TODAY)
        self.assertNotIn("mix", _rules(alerts))


class TestConcentration(unittest.TestCase):
    """FPA-086: concentración top-3 de proyectos > 50% → alerta."""

    def test_fira_con_fixture(self):
        # top-3 = todos los proyectos con coste → 100% > 50%
        alerts = viz.build_alerts(f2.f2_fixture(), CONFIG, today=TODAY)
        ev = _by_rule(alerts, "concentration")
        self.assertEqual(1, len(ev))
        self.assertGreater(ev[0]["evidence"]["top3_share"], 0.5)

    def test_umbral_configurable(self):
        alerts = viz.build_alerts(f2.f2_fixture(), _cfg(concentration_top3_pct=101.0),
                                  today=TODAY)
        self.assertNotIn("concentration", _rules(alerts))


class TestStaleness(unittest.TestCase):
    """FPA-087: reporte con >14 días de antigüedad → alerta."""

    def test_fira_con_reporte_viejo(self):
        alerts = viz.build_alerts(f2.f2_fixture(), CONFIG, today="2026-08-01")
        ev = _by_rule(alerts, "staleness")
        self.assertEqual(1, len(ev))
        self.assertEqual(22, ev[0]["evidence"]["age_days"])

    def test_no_fira_fresco(self):
        alerts = viz.build_alerts(f2.f2_fixture(), CONFIG, today="2026-07-20")
        self.assertNotIn("staleness", _rules(alerts))

    def test_umbral_configurable(self):
        alerts = viz.build_alerts(f2.f2_fixture(), _cfg(staleness_days=5),
                                  today="2026-07-20")
        self.assertIn("staleness", _rules(alerts))


# ======================================================================
# Economía de suscripción (FPA-130…133)
# ======================================================================

class TestPlanEconomy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = f2.f2_fixture()
        cls.econ = viz.build_plan_economy(cls.fixture, CONFIG)

    def test_panel_por_plan(self):
        """FPA-130: un panel por cada periodo del calendario de suscripciones."""
        keys = [(p["tool"], p["start"]) for p in self.econ["plans"]]
        self.assertIn(("claude-cli", "2026-03-19"), keys)
        self.assertIn(("claude-cli", "2026-04-19"), keys)
        self.assertIn(("claude-cli", "2026-06-19"), keys)
        self.assertIn(("codex", "2026-04-01"), keys)

    def test_utilizacion_formula(self):
        """FPA-130: utilización = coste efectivo del periodo ÷ precio del plan.

        Abr19–Jun19 (Max $100/mes): el hourly del fixture registra $40 de
        efectivo claude en el periodo, precio pro-rateado ~$200 (2 meses)."""
        p = next(p for p in self.econ["plans"]
                 if p["tool"] == "claude-cli" and p["start"] == "2026-04-19")
        self.assertAlmostEqual(40.0, p["eff_cost"])
        self.assertAlmostEqual(0.199, p["utilization"], places=2)
        self.assertEqual("assumed", p["provenance"])  # FPA-003

    def test_utilizacion_na_sin_datos_horarios(self):
        """FPA-008: sin hourly para el periodo → n/a con razón, nunca vacío."""
        p = next(p for p in self.econ["plans"]
                 if p["tool"] == "claude-cli" and p["start"] == "2026-03-19")
        self.assertIsNone(p["eff_cost"])
        self.assertIsNone(p["utilization"])
        self.assertTrue(p["utilization_reason"])

    def test_breakeven_y_headroom(self):
        """FPA-131: break-even = precio mensual del plan; headroom = fee − efectivo."""
        p = next(p for p in self.econ["plans"]
                 if p["tool"] == "claude-cli" and p["start"] == "2026-04-19")
        self.assertEqual(100.0, p["break_even"])
        self.assertAlmostEqual(60.0, p["headroom"], places=1)

    def test_cuatro_casos(self):
        """FPA-132: cash del periodo bajo 4 escenarios, jamás mezclados (FPA-002)."""
        cases = self.econ["four_cases"]
        self.assertEqual({"actual", "todo_pay_per_token", "todo_pro", "todo_max"},
                         set(cases))
        self.assertAlmostEqual(45.0, cases["actual"])          # Σ cost_real
        self.assertAlmostEqual(145.0, cases["todo_pay_per_token"])  # Σ efectivo
        # 3 meses con claude activo × $20 Pro + $15 cash no-claude
        self.assertAlmostEqual(75.0, cases["todo_pro"])
        # 3 meses × $100 Max + $15 cash no-claude
        self.assertAlmostEqual(315.0, cases["todo_max"])
        self.assertEqual("assumed", self.econ["four_cases_provenance"])

    def test_disclaimer_usage_limits(self):
        """FPA-133: el modelo y el HTML declaran que se ignoran usage limits."""
        self.assertTrue(self.econ["usage_limits_disclaimer"])
        html = viz.render_html(self.fixture, CONFIG, generated="2026-09-20 12:00")
        self.assertIn("usage limits", html)


# ======================================================================
# Render HTML
# ======================================================================

class TestRenderF4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = f2.f2_fixture()
        cls.html = viz.render_html(cls.fixture, CONFIG, generated="2026-09-20 12:00")

    def test_seccion_alertas(self):
        self.assertIn('id="alerts"', self.html)

    def test_seccion_economia(self):
        self.assertIn('id="plan-economy"', self.html)
        self.assertIn("todo_pro", self.html)

    def test_alertas_en_html(self):
        """FPA-086: la concentración del fixture debe verse en el HTML."""
        self.assertIn("concentration", self.html)

    def test_determinismo_salvo_timestamp(self):
        a = viz.render_html(self.fixture, CONFIG, generated="T",
                            today=TODAY)
        b = viz.render_html(self.fixture, CONFIG, generated="T",
                            today=TODAY)
        self.assertEqual(a, b)


# ======================================================================
# Golden (FPA-105)
# ======================================================================

class TestGolden(unittest.TestCase):
    """FPA-105: golden de alertas + utilización/break-even/comparación.
    Regenerar: REGEN_GOLDEN=1 python3 tests/test_fpa_f4.py"""

    def test_golden_f4(self):
        """FPA-105: golden de alertas + economía sobre el fixture con meses
        parciales (FPA-102). today fijo para staleness determinista."""
        fx = f2.f2_fixture()
        snapshot = {
            "alerts": viz.build_alerts(fx, CONFIG, today=TODAY),
            "plan_economy": viz.build_plan_economy(fx, CONFIG),
        }
        if REGEN_GOLDEN:
            GOLDEN.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False,
                                         sort_keys=True) + "\n")
            self.skipTest("golden regenerado; revisar diff antes de aceptar")
        if not GOLDEN.exists():
            self.fail("Falta golden; corre REGEN_GOLDEN=1 python3 tests/test_fpa_f4.py")
        expected = json.loads(GOLDEN.read_text())
        self.assertEqual(expected, snapshot)


if __name__ == "__main__":
    unittest.main()
