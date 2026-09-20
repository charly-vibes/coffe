#!/usr/bin/env python3
"""
test_fpa_charges.py — tests de viz-fpa.py con el ledger de cargos reales
(ticket coffe-a31.3, CRG-F2; epic coffe-a31 FPA-013/082)

Alcance:
- cash cost = cargos reales del ledger `data/charges.json` (*reported*)
  en KPIs, árboles y presupuestos (FPA-031 cambia de semántica); el
  efectivo queda API-equivalente estimado; jamás se suman (FPA-002).
- sección de reconciliación por tool: real pagado vs fee implícito del
  calendario vs efectivo estimado (FPA-082), con alerta.
- FPA-081 (25×) sobre el calendario corregido: sin plan activo que cubra
  un mes con uso de Claude → alerta (jun-sep con el calendario real).
- economía de planes (FPA-130…133) sobre el cash del ledger.
- proveedor sin facturas en el periodo → n/a con razón (FPA-008).
- check-docs: cifra "Cash real (ledger)" acoplada al reporte (FPA-143).

Golden: tests/golden/fpa-charges-snapshot.json (REGEN_GOLDEN=1).
"""

import importlib.util
import json
import os

import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "golden" / "fpa-charges-snapshot.json"
REGEN_GOLDEN = os.environ.get("REGEN_GOLDEN") == "1"
TODAY = "2026-07-20"


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viz = _load("viz_fpa_charges", "scripts/viz-fpa.py")
f2 = _load("test_fpa_f2", "tests/test_fpa_f2.py")
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())


def _charged_fixture():
    """Fixture f2 + emisiones del ledger (shape del tracker coffe-a31.2).

    Ledger del fixture: claude-cli may $100 (Max) + jun $20 (créditos
    p2p); codex may $20 (Plus); `otro-tool` solo tiene factura fuera del
    periodo (dic-2025) → n/a con razón en el periodo (FPA-008).
    """
    fx = f2.f2_fixture()
    fx["metadata"]["charges_provenance"] = "reported"
    fx["metadata"]["charges_source"] = "data/charges.json"
    fx["metadata"]["charges_total_real"] = 170.0
    fx["charges_real_by_month"] = {
        "claude-cli": {"2026-05": 100.0, "2026-06": 20.0},
        "codex": {"2026-05": 20.0},
        "otro-tool": {"2025-12": 30.0},  # fuera del periodo del reporte
    }
    # calendario corregido: may = claude Max $100 + codex Plus $20
    fx["subscription_fees_by_month"] = {"2026-05": 120.0}
    # p2p del ledger para jun (créditos claude $20) → *reported* (FPA-013)
    fx["monthly"]["2026-06"]["pay_per_token_charges"] = 20.0
    fx["monthly"]["2026-06"]["pay_per_token_provenance"] = "reported"
    return fx


def _kpi_value(kpis, key):
    return next(k for k in kpis if k["key"] == key)


class TestCashLedger(unittest.TestCase):
    """FPA-031 con cargos reales: cash mensual = ledger (*reported*)."""

    def test_cash_mensual_del_ledger(self):
        """may $120 (claude 100 + codex 20), jun $20 (créditos), jul $0."""
        months = {m["ym"]: m for m in viz.build_months(_charged_fixture())}
        self.assertAlmostEqual(120.0, months["2026-05"]["cost_cash"])
        self.assertAlmostEqual(20.0, months["2026-06"]["cost_cash"])
        self.assertAlmostEqual(0.0, months["2026-07"]["cost_cash"])
        for ym in months:
            self.assertEqual("reported", months[ym]["cash_provenance"])

    def test_charges_por_proveedor_en_el_mes(self):
        months = {m["ym"]: m for m in viz.build_months(_charged_fixture())}
        self.assertEqual({"claude-cli": 100.0, "codex": 20.0},
                         months["2026-05"]["charges_by_provider"])
        self.assertEqual({"claude-cli": 20.0},
                         months["2026-06"]["charges_by_provider"])
        self.assertEqual({}, months["2026-07"]["charges_by_provider"])

    def test_refund_descuenta(self):
        """FPA-003 escenario: el refund negativo descuenta el cash del mes."""
        fx = _charged_fixture()
        fx["charges_real_by_month"]["claude-cli"]["2026-06"] = -28.22
        months = {m["ym"]: m for m in viz.build_months(fx)}
        self.assertAlmostEqual(-28.22, months["2026-06"]["cost_cash"])

    def test_fallback_sin_ledger_es_assumed(self):
        """Reporte previo a coffe-a31.2 (sin ledger): cash = suma del
        tracker con provenance *assumed* y razón (FPA-008)."""
        fx = f2.f2_fixture()
        months = {m["ym"]: m for m in viz.build_months(fx)}
        self.assertAlmostEqual(20.0, months["2026-05"]["cost_cash"])
        self.assertEqual("assumed", months["2026-05"]["cash_provenance"])
        self.assertTrue(months["2026-05"]["cash_reason"])
        self.assertIsNone(months["2026-05"]["charges_by_provider"])

    def test_cash_y_efectivo_no_se_suman(self):
        """FPA-002: headlines separados, sin cifra que mezcle ambos."""
        heads = viz.build_headlines(_charged_fixture())
        keys = {h["key"] for h in heads}
        self.assertIn("cost_cash", keys)
        self.assertIn("cost_effective", keys)
        self.assertNotIn("cost_total", keys)


class TestHeadlineCash(unittest.TestCase):

    def test_headline_cash_reported(self):
        heads = {h["key"]: h for h in viz.build_headlines(_charged_fixture())}
        cash = heads["cost_cash"]
        self.assertAlmostEqual(140.0, cash["value"])  # 120 + 20 + 0
        self.assertEqual("reported", cash["provenance"])
        self.assertIn("data/charges.json", cash["interp"])

    def test_headline_cash_sin_facturas_en_el_periodo(self):
        """Ledger ok pero cero facturas dentro del periodo → n/a con razón."""
        fx = _charged_fixture()
        fx["charges_real_by_month"] = {"otro-tool": {"2025-12": 30.0}}
        heads = {h["key"]: h for h in viz.build_headlines(fx)}
        cash = heads["cost_cash"]
        self.assertIsNone(cash["value"])
        self.assertEqual("reported", cash["provenance"])
        self.assertTrue(cash["reason"])


class TestKpisCashLedger(unittest.TestCase):
    """KPIs FPA-030/031 con cash del ledger."""

    def test_kpi_cost_cash_del_ledger(self):
        ing = viz.kpi_ingredients(_charged_fixture(), CONFIG)
        kpis = viz.kpis_for_window(ing, ["2026-05", "2026-06", "2026-07"], None)
        kpi = _kpi_value(kpis, "cost_cash")
        self.assertAlmostEqual(140.0, kpi["value"])
        self.assertEqual("reported", kpi["provenance"])

    def test_kpi_cost_cash_fallback_assumed(self):
        ing = viz.kpi_ingredients(f2.f2_fixture(), CONFIG)
        kpis = viz.kpis_for_window(ing, ["2026-05", "2026-06", "2026-07"], None)
        kpi = _kpi_value(kpis, "cost_cash")
        self.assertAlmostEqual(45.0, kpi["value"])  # 20 + 25 + 0
        self.assertEqual("assumed", kpi["provenance"])


class TestBudgetCashLedger(unittest.TestCase):
    """FPA-050…055: el actual de la tabla de varianza es el cash del ledger."""

    def test_actual_cash_del_ledger(self):
        budget = viz.build_budget(_charged_fixture(), CONFIG)
        rows = {r["ym"]: r for r in budget["rows"]}
        self.assertAlmostEqual(120.0, rows["2026-05"]["actual_cash"])
        self.assertAlmostEqual(20.0, rows["2026-06"]["actual_cash"])
        self.assertAlmostEqual(0.0, rows["2026-07"]["actual_cash"])

    def test_ytd_cash_del_ledger(self):
        budget = viz.build_budget(_charged_fixture(), CONFIG)
        self.assertAlmostEqual(140.0, budget["ytd_cash"]["actual"])


class TestVerifyPlanSinPlan(unittest.TestCase):
    """FPA-081 sobre el calendario corregido: sin plan que cubra el mes
    con uso de Claude → alerta (el caso jun-sep del calendario real)."""

    def _alerts(self, fx):
        return viz.build_alerts(fx, CONFIG, today=TODAY)

    def test_sin_plan_activo_fira(self):
        """claude jun: efectivo $60 y el calendario no cubre el mes."""
        alerts = self._alerts(_charged_fixture())
        ev = [a for a in alerts if a["rule"] == "verify-plan"
              and a["evidence"]["month"] == "2026-06"]
        self.assertEqual(1, len(ev))
        self.assertEqual("high", ev[0]["severity"])
        self.assertEqual(0.0, ev[0]["evidence"]["plan_fee"])
        self.assertIsNone(ev[0]["evidence"]["multiple"])
        self.assertAlmostEqual(60.0, ev[0]["evidence"]["claude_eff"])

    def test_sin_plan_y_sin_uso_no_fira(self):
        """Sin uso de Claude en el mes no hay nada que verificar."""
        fx = _charged_fixture()
        fx["monthly"]["2026-06"]["tools"]["claude-cli"]["cost_effective"] = 0.0
        fx["monthly"]["2026-06"]["models"] = {}
        alerts = self._alerts(fx)
        ev = [a for a in alerts if a["rule"] == "verify-plan"
              and a["evidence"]["month"] == "2026-06"]
        self.assertEqual(0, len(ev))

    def test_calendario_sin_claude_no_fira(self):
        """Sin entradas de claude-cli en el config no hay calendario que
        verificar (el alerta no fabrica señal)."""
        cfg = json.loads(json.dumps(CONFIG))
        cfg["subscriptions"].pop("claude-cli")
        alerts = viz.build_alerts(_charged_fixture(), cfg, today=TODAY)
        self.assertNotIn("verify-plan", {a["rule"] for a in alerts})

    def test_mes_cubierto_usa_el_multiple(self):
        """may: cubierto por el calendario corregido ($20 de Pro tras el
        19-05) → el multiple > umbral sigue disparando como antes."""
        fx = _charged_fixture()
        fx["monthly"]["2026-05"]["tools"]["claude-cli"]["cost_effective"] = 3000.0
        alerts = viz.build_alerts(fx, CONFIG, today=TODAY)
        ev = [a for a in alerts if a["rule"] == "verify-plan"
              and a["evidence"]["month"] == "2026-05"]
        self.assertEqual(1, len(ev))
        self.assertEqual(20.0, ev[0]["evidence"]["plan_fee"])
        self.assertEqual(150.0, ev[0]["evidence"]["multiple"])


class TestReconciliationAlertaLedger(unittest.TestCase):
    """FPA-082: cash real (ledger) vs cargas implícitas del calendario."""

    def test_caso_resuelto_no_fira(self):
        """Calendario corregido: real = implícito + p2p reportado → sin
        alerta (el caso motivador jun $0 vs implícito $0 queda resuelto)."""
        fx = _charged_fixture()
        alerts = viz.build_alerts(fx, CONFIG, today=TODAY)
        self.assertNotIn("reconciliation", {a["rule"] for a in alerts})

    def test_calendario_desalineado_fira(self):
        """Calendario que cobra $50 en may vs facturas reales $120 → alerta
        con ambos montos (real *reported* vs implícito *assumed*)."""
        fx = _charged_fixture()
        fx["subscription_fees_by_month"] = {"2026-05": 50.0}
        alerts = viz.build_alerts(fx, CONFIG, today=TODAY)
        ev = [a for a in alerts if a["rule"] == "reconciliation"]
        self.assertEqual(1, len(ev))
        self.assertEqual("high", ev[0]["severity"])
        self.assertAlmostEqual(140.0, ev[0]["evidence"]["reported"])
        self.assertAlmostEqual(70.0, ev[0]["evidence"]["implied"])  # 50 + 20 p2p
        self.assertEqual("data/charges.json",
                         ev[0]["evidence"]["source"])

    def test_tolerancia_configurable(self):
        fx = _charged_fixture()
        fx["subscription_fees_by_month"] = {"2026-05": 130.0}
        # 10/150 ≈ 6.7%: dentro de la tolerancia default (10%), fuera de 5%
        cfg10 = json.loads(json.dumps(CONFIG))
        alerts = viz.build_alerts(fx, cfg10, today=TODAY)
        self.assertNotIn("reconciliation", {a["rule"] for a in alerts})
        cfg5 = json.loads(json.dumps(CONFIG))
        cfg5["alert_thresholds"]["reconcile_tolerance_pct"] = 5.0
        alerts = viz.build_alerts(fx, cfg5, today=TODAY)
        self.assertIn("reconciliation", {a["rule"] for a in alerts})

    def test_fallback_sin_ledger_conserva_comportamiento(self):
        """Reporte sin ledger: el chequeo previo (cash tracker vs implícito)
        sigue disponible — no se rompen reportes viejos."""
        fx = f2.f2_fixture()
        fx["subscription_fees_by_month"] = {"2026-05": 110.0, "2026-06": 110.0}
        fx["monthly"]["2026-05"]["cost_real"] = 55.58
        fx["monthly"]["2026-06"]["cost_real"] = 10.0
        alerts = viz.build_alerts(fx, CONFIG, today=TODAY)
        ev = [a for a in alerts if a["rule"] == "reconciliation"]
        self.assertEqual(1, len(ev))
        self.assertAlmostEqual(65.58, ev[0]["evidence"]["reported"])


class TestSeccionReconciliacion(unittest.TestCase):
    """Sección FPA-082: por tool y mes, real pagado vs fee implícito vs
    efectivo estimado; cash por proveedor con n/a con razón (FPA-008)."""

    def setUp(self):
        fx = _charged_fixture()
        fx["charges_reconciliation_by_month"] = {
            "2026-05": {
                "claude-cli": {"charges_real": 100.0,
                               "charges_provenance": "reported",
                               "subscription_fee_implicit": 100.0,
                               "cost_effective": 40.0,
                               "fee_month_total": 120.0},
                "codex": {"charges_real": 20.0,
                          "charges_provenance": "reported",
                          "subscription_fee_implicit": 20.0,
                          "cost_effective": 10.0,
                          "fee_month_total": 120.0},
            },
            "2026-06": {
                "claude-cli": {"charges_real": 20.0,
                               "charges_provenance": "reported",
                               "subscription_fee_implicit": 0.0,
                               "cost_effective": 60.0,
                               "fee_month_total": 0.0},
            },
        }
        self.rec = viz.build_reconciliation(fx)
        self.fx = fx

    def test_provenance_y_fuente(self):
        self.assertEqual("reported", self.rec["provenance"])
        self.assertEqual("data/charges.json", self.rec["source"])
        self.assertIsNone(self.rec["reason"])

    def test_proveedor_sin_facturas_en_el_periodo(self):
        """otro-tool solo factura fuera del periodo → n/a con razón."""
        otro = next(p for p in self.rec["providers"]
                    if p["provider"] == "otro-tool")
        self.assertIsNone(otro["total_in_period"])
        self.assertEqual("sin facturas en el periodo", otro["n_a_reason"])

    def test_proveedor_con_facturas_total_del_periodo(self):
        claude = next(p for p in self.rec["providers"]
                      if p["provider"] == "claude-cli")
        self.assertAlmostEqual(120.0, claude["total_in_period"])
        self.assertIsNone(claude["n_a_reason"])
        # mes sin factura pero proveedor activo → $0 (ausencia = dato)
        self.assertAlmostEqual(0.0, claude["months"]["2026-07"])

    def test_filas_tool_mes(self):
        row = next(r for r in self.rec["rows"]
                   if r["ym"] == "2026-05" and r["tool"] == "claude-cli")
        self.assertAlmostEqual(100.0, row["charges_real"])
        self.assertEqual("reported", row["charges_provenance"])
        self.assertAlmostEqual(100.0, row["subscription_fee_implicit"])
        self.assertAlmostEqual(40.0, row["cost_effective"])
        self.assertAlmostEqual(120.0, row["fee_month_total"])

    def test_filas_ordenadas_y_completas(self):
        keys = [(r["ym"], r["tool"]) for r in self.rec["rows"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(3, len(keys))  # may×2 + jun×1

    def test_sin_ledger_n_a_con_razon(self):
        rec = viz.build_reconciliation(f2.f2_fixture())
        self.assertEqual("unavailable", rec["provenance"])
        self.assertTrue(rec["reason"])
        self.assertEqual([], rec["providers"])
        self.assertEqual([], rec["rows"])

    def test_html_muestra_provenance_y_na(self):
        html = viz.reconciliation_html(self.rec)
        self.assertIn("data/charges.json", html)
        self.assertIn("reported", html)
        self.assertIn("assumed", html)
        self.assertIn("sin facturas en el periodo", html)
        self.assertNotIn("><td></td>", html)  # FPA-008: celda nunca vacía

    def test_html_sin_ledger(self):
        html = viz.reconciliation_html(viz.build_reconciliation(f2.f2_fixture()))
        self.assertIn("n/a", html)


class TestPlanEconomyLedger(unittest.TestCase):
    """FPA-130…133 sobre el cash real del ledger."""

    def test_caso_actual_usa_cash_del_ledger(self):
        econ = viz.build_plan_economy(_charged_fixture(), CONFIG)
        self.assertAlmostEqual(140.0, econ["four_cases"]["actual"])

    def test_caso_actual_fallback_tracker(self):
        econ = viz.build_plan_economy(f2.f2_fixture(), CONFIG)
        self.assertAlmostEqual(45.0, econ["four_cases"]["actual"])

    def test_planes_reales_del_calendario(self):
        """El calendario corregido: Max mar/abr, Pro may, AI Pro dic-may,
        Plus abr-may → un panel por periodo (FPA-130)."""
        econ = viz.build_plan_economy(_charged_fixture(), CONFIG)
        labels = [(p["tool"], p["label"]) for p in econ["plans"]]
        self.assertIn(("claude-cli", "Max $100/mes"), labels)
        self.assertIn(("claude-cli", "Pro $20/mes"), labels)
        self.assertIn(("gemini-cli", "Google AI Pro $19.99/mes"), labels)
        self.assertIn(("codex", "ChatGPT Plus $20/mes"), labels)


class TestCheckDocsLedger(unittest.TestCase):
    """FPA-143: la cifra 'Cash real (ledger)' sale del reporte."""

    def test_con_ledger_reported(self):
        expected = viz.expected_doc_figures(_charged_fixture())
        self.assertEqual("$140.00", expected["Cash real (ledger)"])

    def test_sin_ledger_n_a(self):
        expected = viz.expected_doc_figures(f2.f2_fixture())
        self.assertEqual("n/a", expected["Cash real (ledger)"])

    def test_check_docs_roundtrip(self):
        expected = viz.expected_doc_figures(_charged_fixture())
        block = "\n".join(f"- {k}: {v}" for k, v in expected.items())
        readme_tpl = (f"hola\n<!-- CHECK-DOCS:BEGIN -->\nfigs\n{block}\n"
                      f"<!-- CHECK-DOCS:END -->\n")
        with tempfile.TemporaryDirectory() as tmp:
            ok = Path(tmp) / "ok.md"
            bad = Path(tmp) / "bad.md"
            ok.write_text(readme_tpl)
            bad.write_text(readme_tpl.replace("$140.00", "$999.00"))
            self.assertEqual([], viz.check_docs(_charged_fixture(), ok))
            errors = viz.check_docs(_charged_fixture(), bad)
        self.assertTrue(any("Cash real (ledger)" in e for e in errors))


class TestGolden(unittest.TestCase):
    """FPA-104: golden del modelo con ledger (REGEN_GOLDEN=1)."""

    def test_golden_charges(self):
        model = viz.build_model(_charged_fixture(), CONFIG)
        snapshot = {k: model[k] for k in
                    ("months", "headlines", "reconciliation")}
        if REGEN_GOLDEN:
            GOLDEN.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN.write_text(json.dumps(snapshot, indent=2,
                                         ensure_ascii=False,
                                         sort_keys=True) + "\n")
            self.skipTest("golden regenerado; revisar diff antes de aceptar")
        if not GOLDEN.exists():
            self.fail("Falta golden; corre "
                      "REGEN_GOLDEN=1 python3 tests/test_fpa_charges.py")
        expected = json.loads(GOLDEN.read_text())
        self.assertEqual(expected, snapshot)

    def test_determinismo_seccion(self):
        """FPA-104: build_reconciliation determinista."""
        a = viz.build_reconciliation(_charged_fixture())
        b = viz.build_reconciliation(_charged_fixture())
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
