#!/usr/bin/env python3
"""
test_fpa_f5.py — tests de viz-fpa.py F5 (ticket coffe-lat.6)

Alcance: heatmap día×hora + timezone (FPA-110/142), after-hours/weekend
(FPA-111), WoW + varianza semanal (FPA-112), skills/commands con zero/once
(FPA-113…115), buckets de sesión + coste/mediana/p90 (FPA-116/117),
/clear por 100 sesiones (FPA-118), timeline con gaps (FPA-119),
concurrencia etiquetada paralelo vs context switching (FPA-120), share de
sesiones con Agent (FPA-121), lifecycle new/active/dormant con coste
dormante (FPA-122/123), overlay de creación de repos (FPA-098), Pareto con
cola agrupada (FPA-028) y concentración top-3 (FPA-036).
El drill Project→Model (FPA-021) ya está cubierto por test_fpa_f2
(árbol Portfolio, test_drill_model_solo_periodo_completo).
Golden: REGEN_GOLDEN=1.
"""

import importlib.util
import json
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "golden" / "fpa-f5-snapshot.json"
REGEN_GOLDEN = os.environ.get("REGEN_GOLDEN") == "1"


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viz = _load("viz_fpa_f5", "scripts/viz-fpa.py")
f2 = _load("test_fpa_f2", "tests/test_fpa_f2.py")
fpa_config = _load("fpa_config_f5", "scripts/fpa_config.py")
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())


def _hour(ts, interactions, projects_active=1, tools=None, models=None):
    return {
        "interactions": interactions, "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_write_tokens": 0,
        "cost_effective": 0.0, "cost_real": 0.0,
        "tools": tools or {}, "models": models or {},
        "projects_active": projects_active,
    }


def f5_fixture():
    """Fixture F5: extiende f2_fixture con hourly rica (heatmap, after-hours,
    concurrencia, timeline), daily (semanas), skills/commands, sesiones y
    projects con first/last seen (lifecycle + Pareto).

    Horario laboral config: Mon–Fri 09:00–18:00.
    Hourly: dom 2026-05-10 14:00 (60, weekend+after-hours), lun 2026-05-11
    09:00 (40, en horario), lun 2026-05-11 22:00 (10, after-hours),
    jue 2026-07-02 10:00 (70, en horario)."""
    fx = f2.f2_fixture()
    fx["hourly"] = {
        "2026-05-10 14:00": _hour(
            "2026-05-10 14:00", 60, 2,
            tools={"claude-cli": {"req": 60, "in": 0, "out": 0, "cache_read": 0,
                                  "cache_write": 0, "cost_eff": 0.0,
                                  "cost_real": 0.0}},
            models={"claude-sonnet-4-6": 40, "claude-opus-4.7": 20}),
        "2026-05-11 09:00": _hour(
            "2026-05-11 09:00", 40, 1,
            tools={"codex": {"req": 40, "in": 0, "out": 0, "cache_read": 0,
                             "cache_write": 0, "cost_eff": 0.0,
                             "cost_real": 0.0}},
            models={"gpt-5.4": 40}),
        "2026-05-11 22:00": _hour(
            "2026-05-11 22:00", 10, 1,
            tools={"claude-cli": {"req": 10, "in": 0, "out": 0, "cache_read": 0,
                                  "cache_write": 0, "cost_eff": 0.0,
                                  "cost_real": 0.0}},
            models={"claude-sonnet-4-6": 10}),
        "2026-07-02 10:00": _hour(
            "2026-07-02 10:00", 70, 1,
            tools={"codex": {"req": 70, "in": 0, "out": 0, "cache_read": 0,
                             "cache_write": 0, "cost_eff": 0.0,
                             "cost_real": 0.0}},
            models={"gpt-5.4": 70}),
    }
    fx["daily"] = {
        "2026-05-10": {"interactions": 60, "cost_effective": 40.0},
        "2026-05-11": {"interactions": 50, "cost_effective": 10.0},
        "2026-06-03": {"interactions": 100, "cost_effective": 60.0},
        "2026-07-02": {"interactions": 70, "cost_effective": 0.0},
        "2026-07-10": {"interactions": 80, "cost_effective": 30.0},
    }
    fx["skills"] = {"commit": 75, "tdd": 4, "ro5": 1, "wrap-up": 1}
    fx["commands"] = {"/clear": 5, "/model": 2}
    fx["sessions"] = {
        "total_sessions": 20, "with_agent": 5,
        "length_distribution": {"1-10": 8, "11-50": 7, "51-100": 3,
                                "101-300": 2},
        "top_longest_by_turns": [
            {"turns": 260, "msgs": 180, "date": "2026-05-12",
             "project": "charly-coffe"},
            {"turns": 120, "msgs": 80, "date": "2026-06-03",
             "project": "charly-atril"},
        ],
    }
    fx["sessions_monthly"] = {"2026-05": {"total": 10, "with_agent": 2},
                              "2026-06": {"total": 10, "with_agent": 3}}
    fx["projects"] = {
        "charly-coffe": {"cost_effective": 90.0, "first_seen": "2026-07-01",
                         "last_seen": "2026-07-10"},
        "charly-atril": {"cost_effective": 60.0, "first_seen": "2026-05-01",
                         "last_seen": "2026-06-01"},
        "charly-dont": {"cost_effective": 45.0, "first_seen": "2026-06-01",
                        "last_seen": "2026-07-08"},
        "proyecto-externo": {"cost_effective": 5.0, "first_seen": "2026-05-05",
                             "last_seen": "2026-07-05"},
    }
    fx["multitasking"] = {
        "context_switches": {"total": 30},
        "hourly": {"total_active_hours": 6},
    }
    fx.pop("concurrency", None)  # F5 computa desde hourly/multitasking
    return fx


class F5Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = f5_fixture()
        cls.usage = viz.build_usage_patterns(cls.fixture, CONFIG)

    def _by_name(self, items, name):
        return next(x for x in items if x["name"] == name)


# ======================================================================
# Heatmap día×hora (FPA-110) + timezone (FPA-142)
# ======================================================================

class TestHeatmap(F5Base):

    def test_grid_7x24(self):
        grid = self.usage["heatmap"]["grid"]
        self.assertEqual(7, len(grid))
        for row in grid:
            self.assertEqual(24, len(row))

    def test_celdas(self):
        """dom 14h=60, lun 9h=40, lun 22h=10, jue 10h=70."""
        grid = self.usage["heatmap"]["grid"]
        self.assertEqual(60, grid[6][14])   # domingo (isoweekday 7)
        self.assertEqual(40, grid[0][9])    # lunes
        self.assertEqual(10, grid[0][22])
        self.assertEqual(70, grid[3][10])   # jueves
        self.assertEqual(180, self.usage["heatmap"]["total"])

    def test_timezone_verificada(self):
        """FPA-110/142: timezone del tracker etiquetada."""
        hm = self.usage["heatmap"]
        self.assertTrue(hm["verified"])
        self.assertEqual("America/Argentina/Buenos_Aires", hm["timezone"])

    def test_timezone_ausente_unverified(self):
        """FPA-142: sin timezone, la vista hora/día va marcada unverified."""
        fx = f5_fixture()
        del fx["metadata"]["timezone"]
        usage = viz.build_usage_patterns(fx, CONFIG)
        self.assertFalse(usage["heatmap"]["verified"])
        self.assertTrue(usage["heatmap"]["unverified_reason"])
        self.assertFalse(usage["timeline"]["verified"])

    def test_render_unverified(self):
        """FPA-142: el HTML muestra la marca unverified, no la tz."""
        fx = f5_fixture()
        del fx["metadata"]["timezone"]
        html = viz.render_html(fx, CONFIG, generated="T")
        self.assertIn("unverified", html)
        self.assertNotIn("America/Argentina", html)


# ======================================================================
# After-hours / weekend (FPA-111)
# ======================================================================

class TestRhythm(F5Base):

    def test_after_hours_share(self):
        """FPA-111: fuera de Mon–Fri 09:00–18:00 = dom 14h (60) + lun 22h
        (10) = 70 de 180 → 38.9%."""
        self.assertAlmostEqual(70 / 180,
                               self.usage["rhythm"]["after_hours_share"],
                               places=4)

    def test_weekend_share(self):
        """FPA-111: domingo 60 de 180 → 33.3%."""
        self.assertAlmostEqual(60 / 180,
                               self.usage["rhythm"]["weekend_share"], places=4)

    def test_horario_configurable(self):
        """FPA-111: working_hours del config; con horario ampliado el
        share baja."""
        cfg = json.loads(json.dumps(CONFIG))
        cfg["working_hours"] = {"days": [1, 2, 3, 4, 5, 6, 7],
                                "start": "00:00", "end": "22:00"}
        usage = viz.build_usage_patterns(f5_fixture(), cfg)
        # todo cae "en horario" salvo la hora 22–23 (end excluyente)
        self.assertAlmostEqual(10 / 180, usage["rhythm"]["after_hours_share"],
                               places=4)


# ======================================================================
# Weekly WoW y varianza (FPA-112)
# ======================================================================

class TestWeekly(F5Base):

    def test_series_semanal_excluye_bordes_parciales(self):
        """FPA-112: semanas ISO con datos; la primera (W19, solo dom) y la
        última (W28, solo vie) van marcadas partial y no entran a la
        varianza. Semanas sin datos se omiten (convención FPA-017)."""
        weeks = self.usage["rhythm"]["weeks"]
        self.assertEqual(["2026-05-04", "2026-05-11", "2026-06-01",
                          "2026-06-29", "2026-07-06"],
                         [w["start"] for w in weeks])
        self.assertTrue(weeks[0]["partial"])
        self.assertTrue(weeks[-1]["partial"])
        self.assertFalse(weeks[1]["partial"])

    def test_valores_semanales(self):
        weeks = self.usage["rhythm"]["weeks"]
        w20 = weeks[1]
        self.assertEqual(50, w20["interactions"])
        self.assertAlmostEqual(10.0, w20["cost_effective"], places=6)

    def test_wow(self):
        """FPA-112: WoW de W23 vs W20 = +100% int; W27 = -30% int y
        -100% coste. Primera semana sin prior → None."""
        weeks = self.usage["rhythm"]["weeks"]
        self.assertIsNone(weeks[0]["wow_interactions"])
        self.assertAlmostEqual(1.0, weeks[2]["wow_interactions"], places=6)
        self.assertAlmostEqual(-0.30, weeks[3]["wow_interactions"], places=6)
        self.assertAlmostEqual(-1.0, weeks[3]["wow_cost"], places=6)

    def test_varianza_semanal(self):
        """FPA-112: varianza poblacional sobre semanas completas.
        int [50,100,70] → 422.22; coste [10,60,0] → 688.89."""
        var = self.usage["rhythm"]["variance"]
        self.assertAlmostEqual(422.222, var["interactions"], places=2)
        self.assertAlmostEqual(688.889, var["cost_effective"], places=2)
        self.assertEqual(3, var["weeks_count"])

    def test_varianza_sin_semanas_suficientes(self):
        """FPA-008: con <3 semanas completas → n/a con razón."""
        fx = f5_fixture()
        fx["daily"] = {"2026-05-11": {"interactions": 50,
                                      "cost_effective": 10.0}}
        usage = viz.build_usage_patterns(fx, CONFIG)
        self.assertIsNone(usage["rhythm"]["variance"]["interactions"])
        self.assertTrue(usage["rhythm"]["variance"]["reason"])


# ======================================================================
# Skills y commands (FPA-113…115)
# ======================================================================

class TestSkillsCommands(F5Base):

    def test_top_skills(self):
        """FPA-113: ordenadas por usos desc."""
        top = self.usage["skills"]["top"]
        self.assertEqual(["commit", "tdd", "ro5", "wrap-up"],
                         [s["name"] for s in top])
        self.assertEqual([75, 4, 1, 1], [s["uses"] for s in top])

    def test_skills_once(self):
        """FPA-114: skills usadas exactamente una vez."""
        self.assertEqual(["ro5", "wrap-up"], self.usage["skills"]["once"])

    def test_skills_zero_na_con_razon(self):
        """FPA-008/114: el tracker no emite instaladas → n/a con razón."""
        self.assertIsNone(self.usage["skills"]["zero"])
        self.assertTrue(self.usage["skills"]["zero_reason"])

    def test_skills_instaladas_emitidas(self):
        """FPA-114: si el tracker emite instaladas, zero-uso sale de la
        diferencia."""
        fx = f5_fixture()
        fx["skills_installed"] = ["commit", "tdd", "ro5", "wrap-up",
                                  "sin-uso", "otro-sin-uso"]
        usage = viz.build_usage_patterns(fx, CONFIG)
        self.assertEqual(["otro-sin-uso", "sin-uso"], usage["skills"]["zero"])

    def test_trend_na_con_razon(self):
        """FPA-114/115: el tracker no emite uso por mes → n/a con razón."""
        self.assertIsNone(self.usage["skills"]["trend"])
        self.assertTrue(self.usage["skills"]["trend_reason"])
        self.assertIsNone(self.usage["commands"]["trend"])
        self.assertTrue(self.usage["commands"]["trend_reason"])

    def test_top_commands(self):
        self.assertEqual(["/clear", "/model"],
                         [c["name"] for c in self.usage["commands"]["top"]])


# ======================================================================
# Sesiones (FPA-116…118)
# ======================================================================

class TestSessions(F5Base):

    def test_buckets_fpa116(self):
        """FPA-116: buckets 1–10, 11–50, 51–100, 100+ (101-300 y mayores
        se agregan en 100+)."""
        buckets = self.usage["sessions"]["buckets"]
        self.assertEqual(["1–10", "11–50", "51–100", "100+"],
                         [b["label"] for b in buckets])
        self.assertEqual([8, 7, 3, 2], [b["count"] for b in buckets])

    def test_longest_con_coste_na(self):
        """FPA-116: sesiones largas con turns/date/project; el coste por
        sesión no lo emite el tracker → None con razón (FPA-008)."""
        longest = self.usage["sessions"]["longest"]
        self.assertEqual(260, longest[0]["turns"])
        self.assertEqual("charly-coffe", longest[0]["project"])
        self.assertIsNone(longest[0]["cost"])
        self.assertTrue(longest[0]["cost_reason"])

    def test_coste_por_bucket_na(self):
        """FPA-117: sin coste por sesión → n/a con razón; igual mediana/p90."""
        s = self.usage["sessions"]
        self.assertIsNone(s["cost_by_bucket"])
        self.assertTrue(s["cost_by_bucket_reason"])
        self.assertIsNone(s["median_p90"])
        self.assertTrue(s["median_p90_reason"])

    def test_clear_por_100_sesiones(self):
        """FPA-118: /clear (5) / sesiones (20) × 100 = 25.0."""
        self.assertAlmostEqual(25.0, self.usage["sessions"]["clear_per_100"],
                               places=6)

    def test_clear_mensual_na_con_razon(self):
        """FPA-118: sin /clear por mes → n/a con razón."""
        s = self.usage["sessions"]
        self.assertIsNone(s["clear_monthly"])
        self.assertTrue(s["clear_monthly_reason"])

    def test_largas_sin_clear_na_con_razon(self):
        """FPA-118: el tracker no marca /clear por sesión → n/a con razón."""
        s = self.usage["sessions"]
        self.assertIsNone(s["long_no_clear"])
        self.assertTrue(s["long_no_clear_reason"])

    def test_umbral_largas_configurable(self):
        """FPA-118: el umbral de sesión larga viene del config (default 100)."""
        cfg = json.loads(json.dumps(CONFIG))
        cfg["sessions"] = {"long_turns": 200}
        usage = viz.build_usage_patterns(f5_fixture(), cfg)
        self.assertEqual(200, usage["sessions"]["long_turns"])


# ======================================================================
# Timeline con gaps (FPA-119)
# ======================================================================

class TestTimeline(F5Base):

    def test_first_last_por_tool(self):
        tl = {t["name"]: t for t in self.usage["timeline"]["tools"]}
        self.assertEqual("2026-05-10", tl["claude-cli"]["first"])
        self.assertEqual("2026-05-11", tl["claude-cli"]["last"])
        self.assertEqual("2026-05-11", tl["codex"]["first"])
        self.assertEqual("2026-07-02", tl["codex"]["last"])

    def test_gap_flag(self):
        """FPA-119: gap codex 05-11→07-02 = 52 días > 7 → flagged;
        claude-cli gap 1 día → no."""
        tl = {t["name"]: t for t in self.usage["timeline"]["tools"]}
        self.assertFalse(tl["claude-cli"]["flagged"])
        self.assertTrue(tl["codex"]["flagged"])
        self.assertEqual(52, tl["codex"]["max_gap_days"])

    def test_models(self):
        tl = {m["name"]: m for m in self.usage["timeline"]["models"]}
        self.assertIn("gpt-5.4", tl)
        self.assertTrue(tl["gpt-5.4"]["flagged"])
        self.assertFalse(tl["claude-sonnet-4-6"]["flagged"])
        # opus: un solo día → sin gaps
        self.assertFalse(tl["claude-opus-4.7"]["flagged"])

    def test_gap_days_configurable(self):
        """FPA-119: umbral de gap del config; 60 días → 52 ya no flag."""
        cfg = json.loads(json.dumps(CONFIG))
        cfg["timeline"] = {"gap_days": 60}
        usage = viz.build_usage_patterns(f5_fixture(), cfg)
        tl = {t["name"]: t for t in usage["timeline"]["tools"]}
        self.assertFalse(tl["codex"]["flagged"])


class TestGapDaysConfig(unittest.TestCase):

    def test_validacion_gap_days(self):
        cfg = json.loads(json.dumps(CONFIG))
        cfg["timeline"] = {"gap_days": 0}
        errors = fpa_config.validate_config(cfg)
        self.assertTrue(any("timeline.gap_days" in e for e in errors))
        del cfg["timeline"]
        self.assertEqual([], fpa_config.validate_config(cfg))


# ======================================================================
# Concurrencia etiquetada (FPA-120)
# ======================================================================

class TestConcurrency(F5Base):

    def test_proyectos_por_hora_parallel_agent(self):
        """FPA-120a: proyectos distintos/hora etiquetado parallel-agent.
        Horas activas: 2,1,1,1 → pico 2, media 1.25."""
        c = self.usage["concurrency"]["projects_per_hour"]
        self.assertEqual("parallel-agent", c["measure"])
        self.assertEqual(2, c["peak"])
        self.assertAlmostEqual(1.25, c["avg"], places=6)

    def test_sesiones_simultaneas_na_con_razon(self):
        """FPA-120b: el tracker no lo emite → n/a con razón, etiqueta
        parallel-agent."""
        c = self.usage["concurrency"]["peak_simultaneous_sessions"]
        self.assertEqual("parallel-agent", c["measure"])
        self.assertIsNone(c["peak"])
        self.assertTrue(c["reason"])

    def test_concurrencia_emitida_por_tracker(self):
        """FPA-120: si el tracker emite `concurrency`, se usa tal cual."""
        fx = f5_fixture()
        fx["concurrency"] = {
            "distinct_projects_per_hour": {"measure": "parallel-agent",
                                           "peak": 5, "avg": 2.0},
            "peak_simultaneous_sessions": {"measure": "parallel-agent",
                                           "peak": 3, "reason": None},
            "project_switches_per_active_hour": {
                "measure": "human-context-switching", "value": 7.5},
        }
        usage = viz.build_usage_patterns(fx, CONFIG)
        c = usage["concurrency"]
        self.assertEqual(5, c["projects_per_hour"]["peak"])
        self.assertEqual(3, c["peak_simultaneous_sessions"]["peak"])
        self.assertAlmostEqual(7.5, c["switches_per_hour"]["value"], places=6)

    def test_switches_context_switching(self):
        """FPA-120c: switches/hora activa etiquetado human-context-switching.
        30 switches / 6 horas activas = 5.0."""
        c = self.usage["concurrency"]["switches_per_hour"]
        self.assertEqual("human-context-switching", c["measure"])
        self.assertAlmostEqual(5.0, c["value"], places=6)


# ======================================================================
# Share de sesiones con Agent (FPA-121)
# ======================================================================

class TestAgentShare(F5Base):

    def test_share_total(self):
        self.assertAlmostEqual(5 / 20, self.usage["agent_share"]["share"],
                               places=6)

    def test_trend_mensual(self):
        """FPA-121: con sessions_monthly, trend mensual de shares."""
        monthly = self.usage["agent_share"]["monthly"]
        self.assertEqual(["2026-05", "2026-06"], [m["ym"] for m in monthly])
        self.assertAlmostEqual(0.2, monthly[0]["share"], places=6)
        self.assertAlmostEqual(0.3, monthly[1]["share"], places=6)

    def test_trend_na_con_razon(self):
        """FPA-008/121: sin sessions_monthly → n/a con razón."""
        fx = f5_fixture()
        del fx["sessions_monthly"]
        usage = viz.build_usage_patterns(fx, CONFIG)
        self.assertIsNone(usage["agent_share"]["monthly"])
        self.assertTrue(usage["agent_share"]["monthly_reason"])


# ======================================================================
# Lifecycle (FPA-122/123) + overlay repos (FPA-098)
# ======================================================================

class TestLifecycle(F5Base):

    def test_clasificacion(self):
        """FPA-122: vs fecha fin del periodo (2026-07-10), new ≤30 días,
        dormant >30 días sin actividad."""
        status = {p["name"]: p["status"]
                  for p in self.usage["lifecycle"]["projects"]}
        self.assertEqual("new", status["charly-coffe"])       # 9 días
        self.assertEqual("dormant", status["charly-atril"])   # 39 días
        self.assertEqual("active", status["charly-dont"])
        self.assertEqual("active", status["proyecto-externo"])

    def test_coste_dormante(self):
        """FPA-123: coste efectivo de dormantes, total y por proyecto."""
        d = self.usage["lifecycle"]["dormant"]
        self.assertEqual(1, d["count"])
        self.assertAlmostEqual(60.0, d["cost_total"], places=6)
        self.assertAlmostEqual(60.0, d["cost_per_project"], places=6)

    def test_activos_por_mes(self):
        """FPA-123: con project_monthly, activos por mes (proyectos con
        actividad)."""
        by_month = {m["ym"]: m["count"]
                    for m in self.usage["lifecycle"]["active_by_month"]}
        self.assertEqual(3, by_month["2026-05"])
        self.assertEqual(2, by_month["2026-07"])

    def test_activos_por_mes_na(self):
        fx = f5_fixture()
        del fx["project_monthly"]
        usage = viz.build_usage_patterns(fx, CONFIG)
        self.assertIsNone(usage["lifecycle"]["active_by_month"])
        self.assertTrue(usage["lifecycle"]["active_by_month_reason"])

    def test_new_dormant_configurable(self):
        """FPA-122: umbrales del config.lifecycle (new_days/dormant_days)."""
        cfg = json.loads(json.dumps(CONFIG))
        cfg["lifecycle"] = {"new_days": 5, "dormant_days": 10}
        usage = viz.build_usage_patterns(f5_fixture(), cfg)
        status = {p["name"]: p["status"]
                  for p in usage["lifecycle"]["projects"]}
        # coffe: 9 días ya no es new (new_days=5); atril: 39 días dormant
        self.assertEqual("active", status["charly-coffe"])
        self.assertEqual("dormant", status["charly-atril"])

    def test_overlay_repos_na(self):
        """FPA-098: sin fechas de creación de repos → overlay omitido con
        razón (requisito condicional)."""
        ov = self.usage["repo_overlay"]
        self.assertFalse(ov["available"])
        self.assertTrue(ov["reason"])
        html = viz.render_html(f5_fixture(), CONFIG, generated="T")
        self.assertNotIn('id="repo-overlay"', html)
        self.assertIn("creación de repos", html)


# ======================================================================
# Pareto (FPA-028) + concentración top-3 (FPA-036)
# ======================================================================

class TestPareto(F5Base):

    def test_filas_con_share_acumulado(self):
        """FPA-028: proyectos ordenados por coste desc con share y
        cumulative share."""
        rows = self.usage["pareto"]["rows"]
        self.assertEqual(["charly-coffe", "charly-atril", "charly-dont",
                          "proyecto-externo"], [r["name"] for r in rows])
        self.assertAlmostEqual(0.45, rows[0]["share"], places=6)
        self.assertAlmostEqual(0.45, rows[0]["cumulative_share"], places=6)
        self.assertAlmostEqual(0.75, rows[1]["cumulative_share"], places=6)
        self.assertAlmostEqual(1.0, rows[-1]["cumulative_share"], places=6)
        self.assertAlmostEqual(200.0, self.usage["pareto"]["total"], places=6)

    def test_cola_agrupada(self):
        """FPA-028: >10 proyectos → la cola se agrupa en una fila."""
        projects = {f"p{i:02d}": {"cost_effective": float(i * 10),
                                  "first_seen": "2026-05-01",
                                  "last_seen": "2026-07-01"}
                    for i in range(1, 13)}
        fx = f5_fixture()
        fx["projects"] = projects
        usage = viz.build_usage_patterns(fx, CONFIG)
        pareto = usage["pareto"]
        self.assertEqual(10, len(pareto["rows"]))
        self.assertEqual(2, pareto["tail"]["count"])
        self.assertAlmostEqual(30.0, pareto["tail"]["cost"], places=6)
        self.assertAlmostEqual(1.0, pareto["tail"]["cumulative_share"],
                               places=6)

    def test_concentracion_top3(self):
        """FPA-036: top-3 = 195 de 200 → 97.5% del coste efectivo."""
        self.assertAlmostEqual(0.975, self.usage["pareto"]["top3_share"],
                               places=6)

    def test_render_pareto(self):
        html = viz.render_html(f5_fixture(), CONFIG, generated="T")
        self.assertIn('id="pareto"', html)
        self.assertIn("Cola agrupada", html)  # FPA-028 en la sección


# ======================================================================
# Render + integración
# ======================================================================

class TestRender(F5Base):
    @classmethod
    def setUpClass(cls):
        cls.html = viz.render_html(f5_fixture(), CONFIG, generated="T")

    def test_seccion_usage_patterns(self):
        self.assertIn('id="usage-patterns"', self.html)
        self.assertIn('id="heatmap"', self.html)
        self.assertIn('id="skills"', self.html)
        self.assertIn('id="timeline"', self.html)
        self.assertIn('id="lifecycle"', self.html)
        self.assertIn('id="weekly"', self.html)
        self.assertIn('id="concurrency"', self.html)

    def test_razones_na_en_html(self):
        """FPA-008: las razones n/a llegan al HTML, nunca celdas vacías."""
        self.assertIn("no emite", self.html)

    def test_etiquetas_concurrencia(self):
        """FPA-120: measures visibles en el HTML."""
        self.assertIn("parallel-agent", self.html)
        self.assertIn("human-context-switching", self.html)

    def test_determinismo(self):
        a = viz.render_html(f5_fixture(), CONFIG, generated="T")
        b = viz.render_html(f5_fixture(), CONFIG, generated="T")
        self.assertEqual(a, b)

    def test_provenance_tags(self):
        """FPA-003: cifras del modelo con tag; umbrales de config assumed."""
        self.assertIn('data-provenance="reported"', self.html)
        self.assertIn('data-provenance="assumed"', self.html)


# ======================================================================
# Edge cases
# ======================================================================

class TestEdgeCases(unittest.TestCase):

    def test_reporte_minimo_no_explota(self):
        """Reporte casi vacío: sin hourly/daily/sessions/projects todo sale
        n/a con razón y el HTML renderiza sin placeholders."""
        fx = f2.f2_fixture()
        for key in ("hourly", "daily", "sessions", "projects", "skills",
                    "commands", "sessions_monthly", "project_monthly",
                    "multitasking"):
            fx.pop(key, None)
        usage = viz.build_usage_patterns(fx, CONFIG)
        self.assertEqual(0, usage["heatmap"]["total"])
        self.assertIsNone(usage["rhythm"]["after_hours_share"])
        self.assertIsNone(usage["rhythm"]["variance"]["interactions"])
        self.assertEqual([], usage["timeline"]["tools"])
        self.assertIsNone(usage["pareto"]["top3_share"])
        html = viz.render_html(fx, CONFIG, generated="T")
        self.assertEqual([], viz.check_placeholders(html))


# ======================================================================
# Golden (FPA-101/102)
# ======================================================================

class TestGolden(unittest.TestCase):
    """FPA-101: golden de build_usage_patterns sobre el fixture F5 (rico en
    hourly/daily/skills/sessions/projects). Regenerar:
    REGEN_GOLDEN=1 python3 tests/test_fpa_f5.py"""

    def test_golden_f5(self):
        model = viz.build_model(f5_fixture(), CONFIG)
        snapshot = {"usage": model["usage"]}
        if REGEN_GOLDEN:
            GOLDEN.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False,
                                         sort_keys=True) + "\n")
            self.skipTest("golden regenerado; revisar diff antes de aceptar")
        if not GOLDEN.exists():
            self.fail("Falta golden; corre REGEN_GOLDEN=1 python3 tests/test_fpa_f5.py")
        golden = json.loads(GOLDEN.read_text())
        self.assertEqual(golden, snapshot)


if __name__ == "__main__":
    unittest.main()
