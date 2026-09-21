#!/usr/bin/env python3
"""
test_fpa_f2.py — tests de viz-fpa.py F2 (ticket coffe-lat.3)

Alcance: árboles expandibles Time/Tool/Portfolio con roll-up (FPA-020…027,
101), KPI strip con sparkline y delta (FPA-030…045), secciones Data
(FPA-140/141/142/120) y vistas pre-calculadas por periodo (FPA-026).
Golden con fixture de meses parciales (FPA-102): REGEN_GOLDEN=1.
"""

import importlib.util
import json
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "golden" / "fpa-f2-snapshot.json"
REGEN_GOLDEN = os.environ.get("REGEN_GOLDEN") == "1"


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viz = _load("viz_fpa_f2", "scripts/viz-fpa.py")
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())


def _month(ym, interactions=100, cost_eff=50.0, cost_cash=20.0, **extra):
    return {
        "interactions": interactions, "input_tokens": 1000 * interactions,
        "output_tokens": 500 * interactions, "cache_read_tokens": 400 * interactions,
        "cache_write_tokens": 100 * interactions,
        "cost_effective": cost_eff, "cost_real": cost_cash,
        "tools": extra.pop("tools", {}),
        "models": extra.pop("models", {}),
        "subscription_fees": cost_cash, **extra,
    }


def flat_models(tools):
    """Union de los modelos de todas las tools de un mes (shape plano)."""
    out = {}
    for st in tools.values():
        for model, ms in st["models"].items():
            acc = out.setdefault(model, {"interactions": 0, "cost_effective": 0.0})
            acc["interactions"] += ms["interactions"]
            acc["cost_effective"] += ms["cost_effective"]
    return out


def f2_fixture():
    """FPA-102: fixture con mes parcial (julio 10/31) y meses completos.

    Dos tools, 3 modelos (opus = premium), 3 proyectos (2 charly + 1
    unclassified). Julio con codex sin tokens (FPA-045)."""
    tools_may = {
        "claude-cli": {"interactions": 60, "cost_effective": 40.0, "cost_real": 0.0,
                       "models": {"claude-sonnet-4-6": {"interactions": 40, "cost_effective": 30.0},
                                  "claude-opus-4.7": {"interactions": 20, "cost_effective": 10.0}}},
        "codex": {"interactions": 40, "cost_effective": 10.0, "cost_real": 10.0,
                  "models": {"gpt-5.4": {"interactions": 40, "cost_effective": 10.0}}},
    }
    tools_jun = {
        "claude-cli": {"interactions": 80, "cost_effective": 60.0, "cost_real": 0.0,
                       "models": {"claude-opus-4.7": {"interactions": 80, "cost_effective": 60.0}}},
        "codex": {"interactions": 20, "cost_effective": 5.0, "cost_real": 5.0,
                  "models": {"gpt-5.4": {"interactions": 20, "cost_effective": 5.0}}},
    }
    tools_jul = {
        "claude-cli": {"interactions": 30, "cost_effective": 30.0, "cost_real": 0.0,
                       "models": {"claude-sonnet-4-6": {"interactions": 30, "cost_effective": 30.0}}},
        "codex": {"interactions": 70, "cost_effective": 0.0, "cost_real": 0.0,
                  "models": {"gpt-5.4": {"interactions": 70, "cost_effective": 0.0}}},
    }
    months = {
        "2026-05": _month("2026-05", 100, 50.0, 20.0, tools=tools_may,
                          models=flat_models(tools_may)),
        "2026-06": _month("2026-06", 100, 65.0, 25.0, tools=tools_jun,
                          models=flat_models(tools_jun)),
        "2026-07": _month("2026-07", 100, 30.0, 0.0, tools=tools_jul,
                          models=flat_models(tools_jul)),
    }
    # tokens_by_model por mes (cache-hit rate FPA-043, ratio out/in FPA-044)
    months["2026-05"]["tokens_by_model"] = {
        "claude-sonnet-4-6": {"in": 40000, "out": 20000, "cache_read": 32000, "cache_write": 8000},
        "claude-opus-4.7": {"in": 20000, "out": 10000, "cache_read": 8000, "cache_write": 4000},
    }
    months["2026-06"]["tokens_by_model"] = {
        "claude-opus-4.7": {"in": 80000, "out": 40000, "cache_read": 32000, "cache_write": 8000},
    }
    months["2026-07"]["tokens_by_model"] = {
        "claude-sonnet-4-6": {"in": 30000, "out": 15000, "cache_read": 24000, "cache_write": 6000},
    }
    months["2026-05"]["interaction_kinds"] = {"user_prompt": 20, "assistant_turn": 60, "tool_call": 20}
    months["2026-06"]["interaction_kinds"] = {"user_prompt": 30, "assistant_turn": 60, "tool_call": 10}
    months["2026-07"]["interaction_kinds"] = {"user_prompt": 25, "assistant_turn": 55, "tool_call": 20}
    return {
        "metadata": {
            "date_range": {"start": "2026-05-01", "end": "2026-07-10"},
            "filter": "in-scope", "total_interactions": 300,
            "total_days": 71, "total_hours": 4, "total_projects": 3,
            "cost_total_effective": 145.0, "cost_total_real": 45.0,
            "subscription_fees": 45.0,
            "timezone": "America/Argentina/Buenos_Aires",
            "total_input_tokens": 0, "total_output_tokens": 0,
            "total_cache_read_tokens": 0, "total_cache_write_tokens": 0,
        },
        "hourly": {
            "2026-05-10 14:00": {"interactions": 60, "projects_active": 2,
                                 "tools": {"claude-cli": {"req": 60, "in": 60000, "out": 30000,
                                                          "cache_read": 40000, "cache_write": 8000,
                                                          "cost_eff": 40.0, "cost_real": 0.0}}},
            "2026-05-11 09:00": {"interactions": 40, "projects_active": 1,
                                 "tools": {"codex": {"req": 40, "in": 0, "out": 0,
                                                     "cache_read": 0, "cache_write": 0,
                                                     "cost_eff": 10.0, "cost_real": 10.0}}},
            "2026-07-02 10:00": {"interactions": 70, "projects_active": 1,
                                 "tools": {"codex": {"req": 70, "in": 0, "out": 0,
                                                     "cache_read": 0, "cache_write": 0,
                                                     "cost_eff": 0.0, "cost_real": 0.0}}},
        },
        "daily": {}, "monthly": dict(sorted(months.items())),
        "projects": {}, "skills": {}, "commands": {},
        "sessions": {"total_sessions": 8},
        "multitasking": {}, "project_daily": {},
        "project_monthly": {
            "charly-coffee": {"2026-05": {"interactions": 55, "cost_effective": 30.0},
                             "2026-06": {"interactions": 60, "cost_effective": 40.0},
                             "2026-07": {"interactions": 30, "cost_effective": 15.0}},
            "charly-atril": {"2026-05": {"interactions": 35, "cost_effective": 15.0},
                             "2026-06": {"interactions": 40, "cost_effective": 25.0},
                             "2026-07": {"interactions": 70, "cost_effective": 15.0}},
            "proyecto-externo": {"2026-05": {"interactions": 10, "cost_effective": 5.0}},
        },
        # consistente con project_monthly (roll-up del drill, FPA-021)
        "project_models": {
            "charly-coffee": {"claude-sonnet-4-6": {"interactions": 70, "cost_effective": 60.0},
                             "claude-opus-4.7": {"interactions": 75, "cost_effective": 25.0}},
            "charly-atril": {"gpt-5.4": {"interactions": 145, "cost_effective": 55.0}},
            "proyecto-externo": {"gpt-5.4": {"interactions": 10, "cost_effective": 5.0}},
        },
        "concurrency": {
            "distinct_projects_per_hour": {"measure": "parallel-agent", "peak": 2, "avg": 1.5},
            "peak_simultaneous_sessions": {"measure": "parallel-agent", "peak": 2, "reason": None},
            "project_switches_per_active_hour": {"measure": "human-context-switching", "value": 1.0},
        },
        "filtered_out": {"interactions": 30, "cost_effective": 5.0,
                         "by_tool": {"codex": 30}, "share": 0.0909},
        "sessions_monthly": {"2026-05": {"total": 4, "with_agent": 1},
                             "2026-06": {"total": 4, "with_agent": 2}},
        "subscription_config": {}, "subscription_fees_by_month": {},
    }


def _raw_tree(fixture, cfg, name):
    if name == "time":
        return viz.build_time_tree(fixture, cfg)
    if name == "tool":
        return viz.build_tool_tree(fixture)
    return viz.build_portfolio_tree(fixture, cfg)


class F2Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = f2_fixture()
        cls.model = viz.build_model(cls.fixture, CONFIG)


class TestToolTree(F2Base):
    """FPA-020/022/023: árbol Tool→Model con columnas completas."""

    def test_estructura_tool_model(self):
        tree = self.model["views"]["all"]["trees"]["tool"]
        labels = {c["label"] for c in tree["children"]}
        self.assertEqual({"claude-cli", "codex"}, labels)
        claude = next(c for c in tree["children"] if c["label"] == "claude-cli")
        self.assertEqual({"claude-opus-4.7", "claude-sonnet-4-6"},
                         {c["label"] for c in claude["children"]})

    def test_hijos_con_las_mismas_columnas(self):
        """FPA-022: hijos con las mismas columnas que el padre."""
        rows = self.model["views"]["all"]["trees"]["tool"]
        for child in rows["children"]:
            for field in ("cost_display", "pct_display", "interactions_display",
                          "per_1k_display", "delta_display"):
                self.assertIn(field, child)

    def test_rollup_tool_model(self):
        """FPA-025: tool = suma de sus modelos, root = suma de tools."""
        self.assertEqual([], viz.check_rollup(viz.build_tool_tree(self.fixture)))


class TestTimeTree(F2Base):
    """FPA-020/024: Time Year→Quarter→Month con presupuesto y varianza."""

    def test_estructura_anio_trimestre_mes(self):
        tree = self.model["views"]["all"]["trees"]["time"]
        self.assertEqual(1, len(tree["children"]))
        quarters = {c["label"] for c in tree["children"][0]["children"]}
        self.assertEqual({"Q2 26", "Q3 26"}, quarters)

    def test_budget_del_config_en_todos_los_meses(self):
        """FPA-024/050: presupuesto cash desde budgets.start_month (2026-04)."""
        tree = self.model["views"]["all"]["trees"]["time"]
        month_nodes = {c["key"]: c for y in tree["children"]
                       for q in y["children"] for c in q["children"]}
        self.assertIn("$100.00", month_nodes["time:2026-05"]["budget_display"])
        self.assertIn("$100.00", month_nodes["time:2026-06"]["budget_display"])

    def test_budget_pro_rata_mes_parcial(self):
        """coffe-9p4/FPA-052: julio parcial (10/31) recibe presupuesto
        pro-rateado $32.26, no $100 — misma fuente que build_budget."""
        tree = self.model["views"]["all"]["trees"]["time"]
        jul = [c for y in tree["children"] for q in y["children"]
               for c in q["children"] if c["key"] == "time:2026-07"][0]
        self.assertIn("$32.26", jul["budget_display"])
        # YTD del árbol = 100 + 100 + 32.26 (no $300)
        self.assertIn("$232.26", tree["budget_display"])

    def test_varianza_ventana_mixta_tramo_in_budget(self):
        """coffe-9p4: ventana que mezcla meses fuera del periodo presupuestado
        — la varianza compara solo el tramo in-budget (may cash $20 queda fuera)."""
        cfg = json.loads(json.dumps(CONFIG))
        cfg["budgets"]["start_month"] = "2026-06"
        model = viz.build_model(self.fixture, cfg)
        root = model["views"]["all"]["trees"]["time"]
        # budget = 100 (jun) + 32.26 (jul pro-rata); coste in-budget = 25 + 0
        self.assertIn("$132.26", root["budget_display"])
        self.assertEqual("-$107.26", root["variance_display"])
        self.assertEqual("-81.1%", root["variance_pct_display"])

    def test_varianza_cash_vs_presupuesto(self):
        """jun: cash 25.0 vs presupuesto 100 → varianza -75 (-75%)."""
        view = self.model["views"]["month:2026-06"]
        jun = [c for y in view["trees"]["time"]["children"]
               for q in y["children"] for c in q["children"]
               if c["key"] == "time:2026-06"][0]
        self.assertEqual("-$75.00", jun["variance_display"])
        self.assertEqual("-75.0%", jun["variance_pct_display"])

    def test_rollup_time(self):
        self.assertEqual([], viz.check_rollup(viz.build_time_tree(self.fixture, CONFIG)))


class TestPortfolioTree(F2Base):
    """FPA-018/020/021/027: taxonomía, drill y limitación."""

    def test_categorias_y_unclassified(self):
        tree = self.model["views"]["all"]["trees"]["portfolio"]
        labels = {c["label"] for c in tree["children"]}
        self.assertIn("charly", labels)
        self.assertIn("Unclassified", labels)

    def test_drill_model_solo_periodo_completo(self):
        """FPA-021/027: drill Project→Model solo en la vista 'all'."""
        full = self.model["views"]["all"]["trees"]["portfolio"]
        charly = next(c for c in full["children"] if c["label"] == "charly")
        coffee = next(c for c in charly["children"] if c["label"] == "charly-coffee")
        self.assertEqual({"claude-sonnet-4-6", "claude-opus-4.7"},
                         {c["label"] for c in coffee["children"]})
        for c in coffee["children"]:
            self.assertTrue(c["totals_only"])

    def test_drill_cifras_de_project_models(self):
        """coffe-0d5/coffe-itp: las filas pfm del drill leen el total
        (__total__) — muestran las cifras de project_models, no n/a/0."""
        full = self.model["views"]["all"]["trees"]["portfolio"]
        charly = next(c for c in full["children"] if c["label"] == "charly")
        coffee = next(c for c in charly["children"] if c["label"] == "charly-coffee")
        for c in coffee["children"]:
            pm = self.fixture["project_models"]["charly-coffee"][c["label"]]
            self.assertEqual(pm["cost_effective"], c["cost"])
            self.assertEqual(pm["interactions"], c["interactions"])
            self.assertNotEqual("n/a", c["cost_display"])
            self.assertNotEqual("n/a", c["interactions_display"])
            self.assertEqual("n/a", c["delta_display"])  # totals_only: sin delta vs prior
        month_view = self.model["views"]["month:2026-06"]
        charly_m = next(c for c in month_view["trees"]["portfolio"]["children"]
                        if c["label"] == "charly")
        for proj in charly_m["children"]:
            self.assertEqual([], proj["children"])

    def test_limitation_en_vistas_no_full(self):
        """FPA-027: limitación visible en vistas que no son el periodo completo."""
        for key, view in self.model["views"].items():
            if key == "all":
                self.assertNotIn("limitation", view)
            else:
                self.assertIn("Project→Model", view["limitation"])

    def test_rollup_portfolio(self):
        """FPA-025: categoría = suma de proyectos (los totals_only se excluyen)."""
        self.assertEqual([], viz.check_rollup(viz.build_portfolio_tree(self.fixture, CONFIG)))


class TestKpis(F2Base):
    """FPA-030…045: valores, n/a con denominador cero, daily rates, exclusión."""

    def test_12_kpis_base(self):
        keys = {k["key"] for k in self.model["views"]["all"]["kpis"]}
        for expected in ("cost_effective", "cost_cash", "leverage", "cost_per_1k_eff",
                         "cost_per_1k_cash", "cost_per_session", "top3_concentration",
                         "premium_share", "autonomous_share", "multitasking_share",
                         "cache_hit_rate", "out_in_ratio"):
            self.assertIn(expected, keys)

    def test_valores_contra_fixture(self):
        """Full period: efectivo 50+65+30 = 145; cash 20+25+0 = 45."""
        kpis = {k["key"]: k for k in self.model["views"]["all"]["kpis"]}
        self.assertAlmostEqual(145.0, kpis["cost_effective"]["value"])
        self.assertAlmostEqual(45.0, kpis["cost_cash"]["value"])
        self.assertAlmostEqual(145.0 / 45.0, kpis["leverage"]["value"], places=4)
        # 3 proyectos con coste → top-3 = 100%
        self.assertAlmostEqual(1.0, kpis["top3_concentration"]["value"])
        # premium = opus: 10 (may) + 60 (jun) + 0 (jul) = 70 / 145
        self.assertAlmostEqual(70.0 / 145.0, kpis["premium_share"]["value"], places=4)
        # autonomous: (1+2)/8 sesiones
        self.assertAlmostEqual(3 / 8, kpis["autonomous_share"]["value"], places=4)

    def test_top3_concentracion_del_periodo_no_suma_mensuales(self):
        """coffe-hn7: el KPI top-3 de una ventana es el top-3 del agregado
        del periodo (matchea Pareto y alerta), no la suma de top-3
        mensuales (que sobreestima cuando el ranking cambia por mes)."""
        fx = f2_fixture()
        # 4to proyecto: su coste vive en jun, donde los demás ya son top
        fx["project_monthly"]["charly-zzz"] = {
            "2026-05": {"interactions": 0, "cost_effective": 0.0},
            "2026-06": {"interactions": 60, "cost_effective": 60.0},
            "2026-07": {"interactions": 0, "cost_effective": 0.0}}
        kpis = {k["key"]: k for k in
                viz.build_model(fx, CONFIG)["views"]["all"]["kpis"]}
        # agregado del periodo: top-3 = coffee 85 + zzz 60 + atril 55 = 200
        # (total 205) → 97.6%; la suma de top-3 mensuales daría 100%.
        self.assertAlmostEqual(200.0 / 205.0,
                               kpis["top3_concentration"]["value"], places=4)

    def test_delta_vs_prior_ventana_previa(self):
        """jun vs may por tasa diaria: 65/30 vs 50/31 → +34.3%.
        'all' no tiene periodo previo en el reporte → delta n/a."""
        kpis = {k["key"]: k for k in self.model["views"]["month:2026-06"]["kpis"]}
        self.assertAlmostEqual((65.0 / 30) / (50.0 / 31) - 1,
                               kpis["cost_effective"]["delta"], places=3)
        self.assertIsNone(self.model["views"]["all"]["kpis"][0]["delta"])

    def test_daily_rate_en_mes_parcial(self):
        """FPA-041: julio parcial (10/31) compara por tasa diaria."""
        eff = next(k for k in self.model["views"]["month:2026-07"]["kpis"]
                   if k["key"] == "cost_effective")
        self.assertEqual("daily-rate", eff["delta_kind"])
        # julio: 30/10 = 3.0/día; junio: 65/30 ≈ 2.1667/día → +38.46%
        self.assertAlmostEqual((30.0 / 10) / (65.0 / 30) - 1, eff["delta"], places=4)

    def test_denominador_cero_na_con_razon(self):
        """FPA-042: julio sin sesiones → coste por sesión n/a, no cero."""
        k = next(k for k in self.model["views"]["month:2026-07"]["kpis"]
                 if k["key"] == "cost_per_session")
        self.assertIsNone(k["value"])
        self.assertEqual("n/a", k["display"])
        self.assertTrue(k["reason"])

    def test_outcome_kpis_solo_con_datos(self):
        """FPA-040: sin commits/releases en el fixture → sin cards outcome."""
        keys = {k["key"] for k in self.model["views"]["all"]["kpis"]}
        self.assertNotIn("cost_per_commit", keys)

    def test_token_kpis_con_excluded_share(self):
        """FPA-045: julio con codex sin tokens → exclusión con share visible."""
        cache_hit = next(k for k in self.model["views"]["month:2026-07"]["kpis"]
                         if k["key"] == "cache_hit_rate")
        self.assertAlmostEqual(0.7, cache_hit["excluded_share"])  # 70/100 codex
        self.assertIsNotNone(cache_hit["value"])

    def test_cache_hit_rate_formula(self):
        """FPA-043: cache_read / (in + cache_read + cache_write). may."""
        ch = next(k for k in self.model["views"]["month:2026-05"]["kpis"]
                  if k["key"] == "cache_hit_rate")
        # in 60000, cr 40000, cw 12000 → 40000/112000
        self.assertAlmostEqual(40000 / 112000, ch["value"], places=6)

    def test_out_in_ratio(self):
        """FPA-044: out/in del periodo = 85000/170000 = 0.5."""
        kpis = {k["key"]: k for k in self.model["views"]["all"]["kpis"]}
        self.assertAlmostEqual(0.5, kpis["out_in_ratio"]["value"], places=6)

    def test_premium_share_es_assumed(self):
        """FPA-003/037: deriva de la lista premium del config → assumed."""
        kpis = {k["key"]: k for k in self.model["views"]["all"]["kpis"]}
        self.assertEqual("assumed", kpis["premium_share"]["provenance"])

    def test_multitasking_weighted_by_interactions(self):
        """FPA-039: share de interacciones en horas con ≥2 proyectos."""
        mt = next(k for k in self.model["views"]["month:2026-05"]["kpis"]
                  if k["key"] == "multitasking_share")
        self.assertAlmostEqual(60 / 100, mt["value"], places=6)

    def test_mes_sin_datos_excluido(self):
        """FPA-017: ningún KPI tiene series de meses sin datos."""
        for k in self.model["views"]["all"]["kpis"]:
            for p in k["spark"]:
                self.assertNotEqual("2026-08", p["ym"])


class TestViews(F2Base):
    """FPA-026: vistas pre-calculadas por periodo; JS solo re-escala."""

    def test_presets_disponibles(self):
        views = self.model["views"]
        for key in ("all", "year:2026", "q:2026Q2", "month:2026-06"):
            self.assertIn(key, views)

    def test_kpis_de_vista_mensual_igualan_ventana(self):
        eff = next(k for k in self.model["views"]["month:2026-06"]["kpis"]
                   if k["key"] == "cost_effective")
        self.assertAlmostEqual(65.0, eff["value"])

    def test_rollup_de_todas_las_vistas(self):
        """FPA-101 aplicado a cada árbol fuente (las vistas derivan de él)."""
        for name in ("time", "tool", "portfolio"):
            self.assertEqual([], viz.check_rollup(_raw_tree(self.fixture, CONFIG, name)),
                             name)


class TestDataNotes(F2Base):
    """FPA-140/141/142/120: definición, kinds, share filtrado, timezone."""

    def test_definicion_de_interaccion(self):
        notes = self.model["data_notes"]
        self.assertIn("interacción", notes["interaction_definition"])

    def test_tool_call_share(self):
        notes = self.model["data_notes"]
        # tool calls: 20+10+20 = 50 de 300 eventos
        self.assertAlmostEqual(50 / 300, notes["tool_call_share"], places=4)

    def test_filtered_share(self):
        """FPA-141: share de lo excluido por el filtro charly."""
        notes = self.model["data_notes"]
        self.assertAlmostEqual(30 / 330, notes["filtered_share"], places=4)

    def test_timezone_presente(self):
        """FPA-142: timezone del fixture → no unverified."""
        notes = self.model["data_notes"]
        self.assertFalse(notes["unverified_time"])
        self.assertIn("Buenos_Aires", notes["timezone"])

    def test_timezone_ausente_flag_unverified(self):
        fixture = f2_fixture()
        del fixture["metadata"]["timezone"]
        notes = viz.build_data_notes(fixture)
        self.assertTrue(notes["unverified_time"])
        self.assertTrue(notes["timezone_missing_reason"])

    def test_concurrency_labeled(self):
        """FPA-120: (a)(b) paralelo, (c) contexto humano."""
        conc = self.model["data_notes"]["concurrency"]
        self.assertEqual("parallel-agent", conc["distinct_projects_per_hour"]["measure"])
        self.assertEqual("parallel-agent", conc["peak_simultaneous_sessions"]["measure"])
        self.assertEqual("human-context-switching",
                         conc["project_switches_per_active_hour"]["measure"])


class TestRenderF2(unittest.TestCase):
    """Render del HTML F2: KPI cards, árboles, data, selector, sparklines."""

    @classmethod
    def setUpClass(cls):
        cls.html = viz.render_html(f2_fixture(), CONFIG, generated="2026-09-20 12:00")

    def test_kpi_cards_renderizadas(self):
        self.assertGreaterEqual(self.html.count('class="headline kpi"'), 12)

    def test_arboles_con_columnas(self):
        for col in ("% total", "$/1k", "Δ vs prior", "Presupuesto*", "Varianza"):
            self.assertIn(col, self.html)

    def test_selector_de_periodo(self):
        self.assertIn('id="period-select"', self.html)
        self.assertIn('<option value="all"', self.html)
        self.assertIn("month:2026-06", self.html)

    def test_sparklines_svg(self):
        self.assertIn('class="spark"', self.html)
        self.assertIn("<polyline", self.html)

    def test_provenance_en_kpis(self):
        self.assertIn('data-provenance="assumed"', self.html)

    def test_seccion_data(self):
        self.assertIn("Datos y definiciones", self.html)
        self.assertIn("tool calls", self.html)

    def test_js_solo_reescala(self):
        """design.md: sin fórmulas de negocio en JS — solo re-render."""
        js = self.html.split("<script>")[-1]
        for forbidden in ("cost_effective", "cache_read", "budgets", "fme("):
            self.assertNotIn(forbidden, js, f"lógica de negocio en JS: {forbidden}")

    def test_todos_los_kpis_llevan_valor_o_na(self):
        """FPA-108: ninguna card KPI vacía."""
        self.assertNotIn('<span class="val"></span>', self.html)


class TestGolden(unittest.TestCase):
    """FPA-101/102: golden de vistas+KPIs sobre el fixture con meses parciales."""

    def test_golden_f2(self):
        model = viz.build_model(f2_fixture(), CONFIG)
        model.pop("usage", None)  # F5 (coffe-lat.6): golden propio en test_fpa_f5
        if REGEN_GOLDEN:
            GOLDEN.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN.write_text(json.dumps(model, indent=2, ensure_ascii=False,
                                         sort_keys=True) + "\n")
            self.skipTest("golden regenerado; revisar diff antes de aceptar")
        if not GOLDEN.exists():
            self.fail("Falta golden; corre REGEN_GOLDEN=1 python3 tests/test_fpa_f2.py")
        expected = json.loads(GOLDEN.read_text())
        self.assertEqual(expected, model)


if __name__ == "__main__":
    unittest.main()
