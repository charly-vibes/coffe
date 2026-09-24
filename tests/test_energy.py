#!/usr/bin/env python3
"""
test_energy.py — coffe-7mj.1: energía estimada (kWh) por modelo en el
reporte (openspec change add-energy-estimates).

Cubre:
- config: bloque energy_coefficients requerido y validado fail-loud
  (fpa_config.validate_config), con tiers/default_tier/cache_read_energy_factor
  y versions por fecha effective.
- fpa_config.energy_for(): selección de versión por fecha (mismo contrato que
  rates_for, pero sin fallback silencioso — None si no hay cobertura).
- emisión aditiva del tracker: monthly[].energy_kwh_by_model
  ({"kwh": <3 dec>, "tier": <str>} | {"kwh": null, "reason": ...}) y
  monthly[].energy_kwh (suma de modelos con datos), metadata.energy_*.
- pesos: cache_read ponderado por cache_read_energy_factor; cache_write a peso
  completo (prefill); energía jamás mezclada con costes USD (FPA-002).
- mes sin cobertura de versión → ValueError nombrando el mes (abort loud).
- fallback sin config → metadata energy_provenance "unavailable" con razón
  (FPA-008), sin campos mensuales.
- schema: el reporte con energía valida contra usage-report-v3 (aditivo).

Los coeficientes son estimaciones de laboratorio (Luccioni et al. / AI Energy
Score) — la energía es SIEMPRE provenance "assumed", jamás "reported".
"""

import importlib.util
import json
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRACKER_PATH = REPO / "scripts" / "usage-tracker.py"
SCHEMA_PATH = REPO / "specs" / "usage-report-v3.schema.json"
CONFIG_PATH = REPO / "config" / "fpa.json"


def load_tracker(name="usage_tracker_energy"):
    spec = importlib.util.spec_from_file_location(name, TRACKER_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ut = load_tracker()
fc = ut.fpa_config


def row(ts="2026-05-10T14:23:00+00:00", project="charly-coffee",
        tool="claude-cli", model_raw="claude-sonnet-4-6", **kw):
    """Row sintético con el shape exacto que producen los extractores."""
    base = {
        "source": "test", "tool": tool, "model_raw": model_raw,
        "model_family": "claude", "model_version": "sonnet-4.6",
        "project": project, "timestamp": ts,
        "hour": ut.hour_key(ut.parse_ts(ts)),
        "input_tokens": 1_000_000, "output_tokens": 500_000,
        "cache_read_tokens": 10_000_000, "cache_write_tokens": 0,
        "cost_effective": 0.01,
    }
    base.update(kw)
    return base


def aggregate_of(rows):
    """aggregate() con skills/sesiones inyectadas vacías (sin colección viva)."""
    return ut.aggregate(rows, sessions=[], skills_total={},
                        skills_by_project={}, commands={})


def mes(rep, m):
    return rep["monthly"][m]


# --- helpers de config para tests de validación/abort ---

CFG_VALIDA = fc.load_fpa_config(CONFIG_PATH)


def cfg_base():
    """Config mínimo con pricing/subs vacíos para probar solo energía."""
    return {
        "taxonomy": {"rules": [], "overrides": {}, "fallback": "Unclassified"},
        "subscriptions": {},
        "model_pricing": {"default_rates": {"input": 1e-6, "output": 1e-5,
                                            "cache_read": 1e-7}},
        "energy_coefficients": {
            "cache_read_energy_factor": 0.1,
            "default_tier": "mid",
            "versions": [{"effective": "2025-12-23",
                          "tiers": {"flash": 0.03, "mid": 0.1,
                                    "frontier": 0.2},
                          "model_tiers": {}}],
        },
    }


class TestConfigEnergia(unittest.TestCase):
    """Bloque energy_coefficients requerido y validado fail-loud."""

    def test_config_repo_valida(self):
        """El config del repo (con el bloque nuevo) valida limpio."""
        self.assertEqual(fc.validate_config(CFG_VALIDA), [])

    def test_config_sin_bloque_energia_aborta(self):
        cfg = fc.load_fpa_config(CONFIG_PATH)
        del cfg["energy_coefficients"]
        errors = fc.validate_config(cfg)
        self.assertTrue(any("energy_coefficients" in e for e in errors),
                        f"errors sin energy_coefficients: {errors}")

    def test_cache_factor_invalido(self):
        cfg = cfg_base()
        cfg["energy_coefficients"]["cache_read_energy_factor"] = -1
        errors = fc.validate_config(cfg)
        self.assertTrue(any("cache_read_energy_factor" in e for e in errors))

    def test_default_tier_desconocido(self):
        cfg = cfg_base()
        cfg["energy_coefficients"]["default_tier"] = "ultra"
        errors = fc.validate_config(cfg)
        self.assertTrue(any("default_tier" in e for e in errors))

    def test_version_con_tier_de_mapeo_desconocido(self):
        cfg = cfg_base()
        cfg["energy_coefficients"]["versions"][0]["model_tiers"] = {
            "foo-model": "ultra"}
        errors = fc.validate_config(cfg)
        self.assertTrue(any("model_tiers" in e for e in errors))

    def test_versiones_ausentes(self):
        cfg = cfg_base()
        del cfg["energy_coefficients"]["versions"]
        errors = fc.validate_config(cfg)
        self.assertTrue(any("versions" in e for e in errors))


class TestSeleccionVersion(unittest.TestCase):
    """energy_for(): versión por primer día del bucket mensual."""

    def setUp(self):
        self.cfg = cfg_base()
        self.cfg["energy_coefficients"]["versions"].append(
            {"effective": "2026-07-01",
             "tiers": {"flash": 0.01, "mid": 0.05, "frontier": 0.1},
             "model_tiers": {}})

    def test_version_vigente_antes_de_segunda(self):
        v = fc.energy_for(self.cfg, date(2026, 6, 1))
        self.assertEqual(v["tiers"]["mid"], 0.1)

    def test_version_vigente_desde_effective(self):
        v = fc.energy_for(self.cfg, date(2026, 7, 1))
        self.assertEqual(v["tiers"]["mid"], 0.05)

    def test_sin_cobertura_devuelve_none(self):
        self.assertIsNone(fc.energy_for(self.cfg, date(2025, 11, 1)))


class TestEmisionEnergia(unittest.TestCase):
    """monthly[].energy_kwh_by_model / energy_kwh + metadata energy_*."""

    @classmethod
    def setUpClass(cls):
        cls.rep = aggregate_of([
            row(model_raw="claude-sonnet-4-6"),
            row(model_raw="claude-sonnet-4-6",
                ts="2026-05-11T09:00:00+00:00"),
            row(model_raw="deepseek/deepseek-v4-flash"),
        ])

    def test_energy_kwh_by_model_presente(self):
        e = mes(self.rep, "2026-05")["energy_kwh_by_model"]
        self.assertIn("claude-sonnet-4-6", e)
        self.assertIn("deepseek/deepseek-v4-flash", e)

    def test_kwh_con_tier_y_3_decimales(self):
        e = mes(self.rep, "2026-05")["energy_kwh_by_model"]["claude-sonnet-4-6"]
        self.assertGreater(e["kwh"], 0)
        self.assertEqual(e["tier"], "mid")
        self.assertEqual(e["kwh"], round(e["kwh"], 3))

    def test_ponderacion_cache_read(self):
        """(in + out + cache_write + cache_read×0.10) × J/tier / 3.6e6."""
        rep = aggregate_of([row(model_raw="claude-sonnet-4-6")])
        e = mes(rep, "2026-05")["energy_kwh_by_model"]["claude-sonnet-4-6"]
        esperado = (1_000_000 + 500_000 + 0 + 10_000_000 * 0.1) * 0.1 / 3.6e6
        self.assertAlmostEqual(e["kwh"], round(esperado, 3), places=3)

    def test_dos_rows_mismo_modelo_agregan_antes_de_energia(self):
        e = mes(self.rep, "2026-05")["energy_kwh_by_model"]["claude-sonnet-4-6"]
        esperado = (2_000_000 + 1_000_000 + 20_000_000 * 0.1) * 0.1 / 3.6e6
        self.assertAlmostEqual(e["kwh"], round(esperado, 3), places=3)

    def test_tier_flash_para_deepseek(self):
        e = mes(self.rep, "2026-05")["energy_kwh_by_model"][
            "deepseek/deepseek-v4-flash"]
        self.assertEqual(e["tier"], "flash")
        self.assertGreater(e["kwh"], 0)

    def test_modelo_sin_mapping_usa_default_tier(self):
        rep = aggregate_of([row(model_raw="modelo-futuro-sin-mapping")])
        e = mes(rep, "2026-05")["energy_kwh_by_model"]["modelo-futuro-sin-mapping"]
        self.assertEqual(e["tier"], "mid")

    def test_modelo_sin_telemetria_null_con_razon(self):
        rep = aggregate_of([row(tool="amp", model_raw="amp",
                                input_tokens=0, output_tokens=0,
                                cache_read_tokens=0, cache_write_tokens=0)])
        e = mes(rep, "2026-05")["energy_kwh_by_model"]["amp"]
        self.assertIsNone(e["kwh"])
        self.assertEqual(e["reason"], "sin telemetría de tokens")

    def test_total_mensual_suma_solo_modelos_con_datos(self):
        m = mes(self.rep, "2026-05")
        e = m["energy_kwh_by_model"]
        suma = round(sum(v["kwh"] for v in e.values()
                         if isinstance(v, dict) and v["kwh"] is not None), 3)
        self.assertAlmostEqual(m["energy_kwh"], suma, places=3)

    def test_metadata_energy(self):
        md = self.rep["metadata"]
        self.assertEqual(md["energy_provenance"], "assumed")
        self.assertEqual(md["energy_cache_read_factor"], 0.1)
        self.assertTrue(md["energy_config_source"])
        self.assertIn("J/token", md["energy_method"])

    def test_energia_ya_no_vive_en_campos_de_coste(self):
        """Aditivo: las claves de coste existentes no cambian de semántica."""
        m = mes(self.rep, "2026-05")
        for clave in ("cost_effective", "cost_real", "cost_real_tracker",
                      "subscription_fees"):
            self.assertIn(clave, m)
        self.assertNotIn("kwh", m["cost_effective"] if isinstance(
            m["cost_effective"], dict) else {})

    def test_meses_multiples_usan_su_version(self):
        """Un mes posterior a una segunda effective usa el coeficiente nuevo."""
        cfg = cfg_base()
        cfg["energy_coefficients"]["versions"].append(
            {"effective": "2026-06-01",
             "tiers": {"flash": 0.01, "mid": 0.05, "frontier": 0.1},
             "model_tiers": {}})
        original = ut._FPA_CONFIG
        ut._FPA_CONFIG = cfg
        try:
            rep = aggregate_of([row(ts="2026-05-10T14:23:00+00:00"),
                                row(ts="2026-06-10T14:23:00+00:00")])
            j_v1 = 0.1   # tiers de cfg_base
            j_v2 = 0.05  # tiers de la segunda versión
            tokens = 1_000_000 + 500_000 + 10_000_000 * 0.1
            e_may = mes(rep, "2026-05")["energy_kwh_by_model"]["claude-sonnet-4-6"]
            e_jun = mes(rep, "2026-06")["energy_kwh_by_model"]["claude-sonnet-4-6"]
            self.assertAlmostEqual(e_may["kwh"], round(tokens * j_v1 / 3.6e6, 3))
            self.assertAlmostEqual(e_jun["kwh"], round(tokens * j_v2 / 3.6e6, 3))
        finally:
            ut._FPA_CONFIG = original


class TestAbortLoud(unittest.TestCase):
    """Mes sin cobertura de versión → ValueError nombrando el mes."""

    def test_mes_sin_cobertura(self):
        cfg = cfg_base()
        cfg["energy_coefficients"]["versions"][0]["effective"] = "2030-01-01"
        original = ut._FPA_CONFIG
        ut._FPA_CONFIG = cfg
        try:
            with self.assertRaises(ValueError) as ctx:
                aggregate_of([row()])
            self.assertIn("2026-05", str(ctx.exception))
        finally:
            ut._FPA_CONFIG = original


class TestFallbackSinConfig(unittest.TestCase):
    """Sin config (fallback): provenance unavailable + razón, sin campos mensuales."""

    def test_fallback_energy_unavailable(self):
        original = ut._FPA_CONFIG
        ut._FPA_CONFIG = None
        try:
            rep = aggregate_of([row()])
            self.assertEqual(rep["metadata"]["energy_provenance"],
                             "unavailable")
            self.assertTrue(rep["metadata"].get("energy_reason"))
            self.assertNotIn("energy_kwh_by_model", mes(rep, "2026-05"))
        finally:
            ut._FPA_CONFIG = original


class TestSchema(unittest.TestCase):
    """El schema extendido valida un reporte con energía (aditivo)."""

    def _validate(self, doc):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema no instalado")
        jsonschema.validate(doc, json.loads(SCHEMA_PATH.read_text()))

    def test_reporte_con_energia_valida(self):
        rep = aggregate_of([row(model_raw="claude-sonnet-4-6"),
                            row(tool="amp", model_raw="amp",
                                input_tokens=0, output_tokens=0,
                                cache_read_tokens=0, cache_write_tokens=0)])
        self._validate(rep)

    def test_schema_tiene_campos_energy(self):
        s = json.loads(SCHEMA_PATH.read_text())
        mb = s["definitions"]["monthlyBucket"]["properties"]
        self.assertIn("energy_kwh", mb)
        self.assertIn("energy_kwh_by_model", mb)
        md = s["properties"]["metadata"]["properties"]
        self.assertIn("energy_provenance", md)


if __name__ == "__main__":
    unittest.main()
