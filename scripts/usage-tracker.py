#!/usr/bin/env python3
"""
usage-tracker.py v4.1 — Extractor completo de uso de IA.
Filtra solo proyectos charly, incluye Amp, sesiones y patrones.
Corrige cálculo de costos: estima desde tokens × pricing para Claude JSONL,
fusiona cache de dashboard para costos precisos, suma cuotas de suscripción.
v4.1: cuenta tokens de cache (cacheRead/cacheWrite) de Pi y Claude
(validado contra toolpath/path-cli).
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PI_DIR = Path.home() / ".pi" / "agent"  # Gemini llega vía logs de Pi (google-gemini-cli), no hay extractor propio
AMP_DIR = Path.home() / ".amp"
OUTPUT_DIR = Path("data")
LOCAL_TZ = datetime.now().astimezone().tzinfo  # OJO: los buckets hourly/daily usan la TZ local de la máquina que extrae

CHARLY_FILTER = True

# Umbral anti-clobber: si los extractores encuentran menos interacciones que esto
# (p.ej. máquina sin ~/.claude / ~/.pi/agent / ~/.amp), NO se escribe el reporte
# sin --force, para no destruir el dataset versionado en data/.
MIN_INTERACTIONS = 1000

SUBSCRIPTIONS = {
    "claude-cli": [
        {"start": "2026-03-19", "end": "2026-04-19", "label": "Pro $20/mes", "monthly_fee": 20},
        {"start": "2026-04-19", "end": "2026-06-19", "label": "Max $100/mes", "monthly_fee": 100},
        {"start": "2026-06-19", "end": None, "label": "Pro $20/mes", "monthly_fee": 20},
    ],
    "codex": [
        {"start": "2026-04-01", "end": "2026-05-15", "label": "Subscripción", "monthly_fee": 10},
        {"start": "2026-05-15", "end": None, "label": "Pay-per-token", "monthly_fee": 0},
    ],
}

# Model pricing per million tokens (pay-per-token rates)
MODEL_PRICING = {
    "claude": {
        "opus-4.7":   {"input": 0.000015, "output": 0.000075, "cache_read": 0.0000015},
        "opus-4.6":   {"input": 0.000015, "output": 0.000075, "cache_read": 0.0000015},
        "opus-4.5":   {"input": 0.000015, "output": 0.000075, "cache_read": 0.0000015},
        "sonnet-4.6": {"input": 0.000003, "output": 0.000015, "cache_read": 0.0000003},
        "haiku":      {"input": 0.00000025, "output": 0.00000125, "cache_read": 0.000000025},
        "synthetic":  {"input": 0.000003, "output": 0.000015, "cache_read": 0.0000003},
    },
    "codex": {
        "gpt-5.5": {"input": 0.000010, "output": 0.000040, "cache_read": 0.0000010},
        "gpt-5.4": {"input": 0.000010, "output": 0.000040, "cache_read": 0.0000010},
        "gpt-5.3": {"input": 0.000010, "output": 0.000040, "cache_read": 0.0000010},
    },
    "gemini": {
        "gemini-3.1":    {"input": 0.00000125, "output": 0.000005, "cache_read": 0.0000000625},
        "gemini-3-pro":  {"input": 0.00000125, "output": 0.000005, "cache_read": 0.0000000625},
        "gemini-2.5":    {"input": 0.000000625, "output": 0.0000025, "cache_read": 0.00000003125},
    },
    "deepseek": {
        "v4-flash": {"input": 0.0000003, "output": 0.0000012, "cache_read": 0.00000003},
    },
    "kimi": {
        "k2": {"input": 0.000002, "output": 0.000008, "cache_read": 0.0000002},
    },
}

DEFAULT_RATES = {"input": 0.000003, "output": 0.000015, "cache_read": 0.0000003}


def estimate_cost(family, version, input_tokens, output_tokens, cache_read=0, cache_write=0):
    """Estimate cost from token counts at pay-per-token rates."""
    rates = MODEL_PRICING.get(family, {}).get(version, DEFAULT_RATES)
    # Anthropic cobra cache writes a 1.25x del input rate
    input_cost = (input_tokens + cache_write * 1.25) * rates["input"]
    cache_read_cost = cache_read * rates.get("cache_read", rates["input"] * 0.1)
    output_cost = output_tokens * rates["output"]
    return round(input_cost + cache_read_cost + output_cost, 8)


def parse_ts(ts):
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return None

def hour_key(dt):
    return dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:00")

def is_charly(proj):
    if not CHARLY_FILTER:
        return True
    p = (proj or "").lower()
    return "charly" in p or "sk-" in p

def model_details(model_id):
    m = model_id.lower()
    if "claude-opus-4-7" in m: return ("claude", "opus-4.7")
    if "claude-opus-4-6" in m: return ("claude", "opus-4.6")
    if "claude-opus-4-5" in m: return ("claude", "opus-4.5")
    if "claude-sonnet-4-6" in m: return ("claude", "sonnet-4.6")
    if "claude-haiku" in m: return ("claude", "haiku")
    if "gpt-5.5" in m: return ("codex", "gpt-5.5")
    if "gpt-5.4" in m: return ("codex", "gpt-5.4")
    if "gpt-5.3" in m: return ("codex", "gpt-5.3")
    if "gemini-3.1" in m: return ("gemini", "gemini-3.1")
    if "gemini-3-" in m: return ("gemini", "gemini-3-pro")
    if "gemini-2.5" in m: return ("gemini", "gemini-2.5")
    if "deepseek" in m: return ("deepseek", "v4-flash")
    if "kimi" in m: return ("kimi", "k2")
    if "synthetic" in m: return ("claude", "synthetic")
    return ("other", model_id[:20])


def clean_proj_name(raw):
    """Normaliza nombres de proyecto a forma canónica entre fuentes.

    Claude usa paths con '/' reemplazado por '-' (p.ej. el repo en
    <home>/para/areas/dev/gh/charly/coffe aparece como
    '-var-home-sasha-para-areas-dev-gh-charly-coffe'). El prefijo se deriva
    de Path.home() en runtime para ser independiente de la máquina.
    Pi usa nombres de directorio distintos ('-charly-atril/',
    '-sk-REPLy.jl/' → 'sk-REPLy-jl').
    """
    home_prefix = str(Path.home()).replace("/", "-") + "-para-areas-dev-gh-"
    p = raw.replace(home_prefix, "")
    p = p.strip("-/")
    p = p.replace(".jl", "-jl")  # repos Julia: REPLy.jl → REPLy-jl
    return {"charly-mibilioteca": "charly-miblioteca",  # typo en sesiones Pi
            "sk-sxAct": "sk-XAct-jl"}.get(p, p)  # sxAct no existe; repo real XAct.jl


def extract_claude(skipped=None):
    """
    Read Claude JSONL files + dashboard cache.
    Uses cache cost where available (more accurate), falls back to token-based estimate.
    Returns deduplicated rows (no double counting between JSONL and cache).

    `skipped`: dict opcional; se incrementa con las líneas/archivos descartados
    por error de parseo (visible en metadata.skipped_lines del reporte).
    """
    # Step 1: Read JSONL files
    jsonl_rows = []
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return []  # máquina sin logs de Claude (el guard de main() se encarga del resto)
    for pd in projects_dir.iterdir():
        if not pd.is_dir(): continue
        proj = pd.name
        if not is_charly(proj): continue
        for f in pd.glob("*.jsonl"):
            try:
                with open(f) as fh:
                    for line in fh:
                        entry = json.loads(line)
                        ts = parse_ts(entry.get("timestamp"))
                        if not ts: continue
                        if entry.get("type") == "assistant":
                            msg = entry.get("message", {})
                            if isinstance(msg, str): msg = json.loads(msg)
                            usage = msg.get("usage", {}) or {}
                            model = msg.get("model", "unknown")
                            fam, ver = model_details(model)
                            inp = usage.get("input_tokens", 0) or 0
                            out = usage.get("output_tokens", 0) or 0
                            cache_r = usage.get("cache_read_input_tokens", 0) or 0
                            cache_c = usage.get("cache_creation_input_tokens", 0) or 0
                            cost = estimate_cost(fam, ver, inp, out, cache_r, cache_c)
                            jsonl_rows.append({
                                "source": "claude_jsonl",
                                "tool": "claude-cli",
                                "model_raw": model,
                                "model_family": fam,
                                "model_version": ver,
                                "project": proj,
                                "timestamp": ts.isoformat(),
                                "hour": hour_key(ts),
                                "input_tokens": inp,
                                "output_tokens": out,
                                "cache_read_tokens": cache_r,
                                "cache_write_tokens": cache_c,
                                "cost_effective": cost,
                            })
            except (json.JSONDecodeError, OSError, ValueError, TypeError, KeyError) as e:
                if skipped is not None:
                    k = f"claude:{f.name}"
                    skipped[k] = skipped.get(k, 0) + 1
                elif os.environ.get("TRACKER_DEBUG"):
                    print(f"  [skipped] {f.name}: {e}", file=sys.stderr)

    # Step 2: Read dashboard cache for cost overrides
    cache_cost_lookup = {}
    cache_file = CLAUDE_DIR / "dashboard-cache.json"
    if cache_file.exists():
        cache = json.loads(cache_file.read_text())
        for key, summary in cache.get("entries", {}).items():
            if summary.get("source") != "claude": continue
            proj = summary.get("project", "")
            if not is_charly(proj): continue
            for turn in summary.get("turns", []):
                ts = parse_ts(turn.get("ts"))
                if not ts: continue
                model = turn.get("model", "unknown")
                cost = turn.get("cost", 0) or 0
                # Build lookup key: (timestamp_iso, model, project)
                lk = (ts.isoformat(), model, proj)
                # Keep the first (earliest) entry if multiple matches
                if lk not in cache_cost_lookup:
                    cache_cost_lookup[lk] = cost

    # Step 3: Merge cache costs into JSONL rows
    merged = []
    for row in jsonl_rows:
        lk = (row["timestamp"], row["model_raw"], row["project"])
        if lk in cache_cost_lookup:
            row["cost_effective"] = cache_cost_lookup[lk]
            row["source"] = "claude_cache_merged"
        merged.append(row)

    # Step 4: Add any cache entries that weren't in JSONL (shouldn't happen, but safety)
    cache_keys = {(r["timestamp"], r["model_raw"], r["project"]) for r in merged}
    for (ts, model, proj), cost in cache_cost_lookup.items():
        if (ts, model, proj) not in cache_keys:
            fam, ver = model_details(model)
            merged.append({
                "source": "claude_cache_only",
                "tool": "claude-cli",
                "model_raw": model,
                "model_family": fam,
                "model_version": ver,
                "project": proj,
                "timestamp": ts,
                "hour": hour_key(parse_ts(ts)),
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "cost_effective": cost,
            })

    return merged


def extract_pi(skipped=None):
    rows = []
    sessions_dir = PI_DIR / "sessions"
    if not sessions_dir.exists(): return rows
    for sd in sessions_dir.iterdir():
        if not sd.is_dir(): continue
        proj = sd.name
        if not is_charly(proj): continue
        for f in sd.glob("*.jsonl"):
            try:
                with open(f) as fh:
                    for line in fh:
                        entry = json.loads(line)
                        if entry.get("type") != "message": continue
                        msg = entry.get("message", {}) or {}
                        if msg.get("role") != "assistant": continue
                        usage = msg.get("usage", {}) or {}
                        # Cost can be a dict {input, output, cacheRead, cacheWrite, total} or a number
                        cost_info = usage.get("cost", {})
                        if isinstance(cost_info, dict):
                            cost = cost_info.get("total", 0) or 0
                        else:
                            cost = cost_info or 0
                        model = msg.get("model", "unknown")
                        provider = entry.get("provider", msg.get("provider", ""))
                        ts = parse_ts(entry.get("timestamp"))
                        if not ts: continue
                        fam, ver = model_details(model)
                        tool_map = {"openai-codex": "codex", "claude-cli": "claude-cli",
                                    "google-gemini-cli": "gemini-cli", "gemini-cli": "gemini-cli",
                                    "openrouter": "openrouter", "github-copilot": "copilot",
                                    "anthropic": "claude-cli"}
                        tool = tool_map.get(provider, provider)
                        inp = usage.get("input_tokens") or usage.get("input", 0) or 0
                        out = usage.get("output_tokens") or usage.get("output", 0) or 0
                        cache_r = usage.get("cacheRead") or usage.get("cache_read") or 0
                        cache_w = usage.get("cacheWrite") or usage.get("cache_write") or 0
                        rows.append({
                            "source": "pi",
                            "tool": tool,
                            "model_raw": model,
                            "model_family": fam,
                            "model_version": ver,
                            "project": proj,
                            "timestamp": ts.isoformat(),
                            "hour": hour_key(ts),
                            "input_tokens": inp,
                            "output_tokens": out,
                            "cache_read_tokens": cache_r or 0,
                            "cache_write_tokens": cache_w or 0,
                            "cost_effective": cost,
                        })
            except (json.JSONDecodeError, OSError, ValueError, TypeError, KeyError) as e:
                if skipped is not None:
                    k = f"pi:{f.name}"
                    skipped[k] = skipped.get(k, 0) + 1
                elif os.environ.get("TRACKER_DEBUG"):
                    print(f"  [skipped] {f.name}: {e}", file=sys.stderr)
    return rows


def extract_amp():
    """Extrae de Amp (@ampcode/cli, agente autónomo). Sin costo."""
    rows = []
    amp_dir = AMP_DIR / "file-changes"
    if not amp_dir.exists(): return rows
    for td in amp_dir.iterdir():
        if not td.is_dir(): continue
        task_proj = None
        task_dates = []
        for f in td.iterdir():
            try:
                entry = json.loads(f.read_text())
                uri = entry.get("uri", "")
                if "charly" in uri.lower() or "sk-" in uri.lower():
                    ts = parse_ts(entry.get("timestamp"))
                    if ts:
                        task_dates.append(ts)
                        if not task_proj:
                            task_proj = "charly"
            except (json.JSONDecodeError, OSError, ValueError, TypeError, KeyError) as e:
                if os.environ.get("TRACKER_DEBUG"):
                    print(f"  [skipped] amp: {e}", file=sys.stderr)
        if task_proj and task_dates:
            for ts in task_dates:
                rows.append({
                    "source": "amp", "tool": "amp",
                    "model_raw": "amp", "model_family": "amp", "model_version": "v1",
                    "project": "charly/amp-auto",
                    "timestamp": ts.isoformat(), "hour": hour_key(ts),
                    "input_tokens": 0, "output_tokens": 0,
                    "cache_read_tokens": 0, "cache_write_tokens": 0,
                    "cost_effective": 0,
                })
    return rows


def extract_session_stats():
    """Extrae estadísticas de sesión desde el cache de Claude."""
    sessions = []
    cache_file = CLAUDE_DIR / "dashboard-cache.json"
    if not cache_file.exists(): return sessions
    cache = json.loads(cache_file.read_text())
    for key, summary in cache.get("entries", {}).items():
        if summary.get("source") != "claude": continue
        proj = summary.get("project", "")
        if not is_charly(proj): continue
        n_turns = len(summary.get("turns", []))
        tools = summary.get("tool_counts", {})
        skills = summary.get("skill_uses", {})
        n_skills = sum(skills.values())
        n_errors = len(summary.get("api_errors", []))
        n_compactions = summary.get("compactions", 0)
        has_agent = "Agent" in tools
        fs = summary.get("first_ts")
        ls = summary.get("last_ts")
        msgs = summary.get("user_messages", 0)
        sessions.append({
            "project": proj,
            "first_ts": (fs or " ")[:10],
            "duration_msgs": msgs,
            "n_turns": n_turns,
            "n_tools": len(tools),
            "has_agent": has_agent,
            "n_skills": n_skills,
            "n_errors": n_errors,
            "n_compactions": n_compactions,
        })
    return sessions


def get_sub_cost(tool, ts_str, eff_cost):
    """
    tool, timestamp_str, effective_cost -> (real_cost, effective_cost, sub_label)
    For subscription periods: real_cost = 0 (covered by subscription).
    For pay-per-token: real_cost = effective_cost.
    """
    if tool not in ["claude-cli", "codex"]:
        return eff_cost, eff_cost, "pay-per-token"
    date = (ts_str or "")[:10]
    for period in SUBSCRIPTIONS[tool]:
        if period["start"] <= date and (period["end"] is None or date < period["end"]):
            if period["monthly_fee"] > 0:
                return 0.0, eff_cost, period["label"]
            else:
                return eff_cost, eff_cost, period["label"]
    return eff_cost, eff_cost, "unknown"


def calc_subscription_fees(monthly_data):
    """
    Calculate monthly subscription fees for each month.
    Returns dict: {month_key: total_sub_fee}
    """
    sub_fees = {}
    for m_key, m_data in monthly_data.items():
        # Find which months had which subscriptions active
        total = 0.0
        # Check if the month has any claude-cli activity
        tools = m_data.get("tools", {})
        if "claude-cli" in tools:
            for period in SUBSCRIPTIONS["claude-cli"]:
                if period["monthly_fee"] > 0:
                    p_start = period["start"]
                    p_end = period["end"] or "9999-12"
                    # Does this month overlap with the subscription period?
                    if m_key >= p_start[:7] and m_key < p_end[:7]:
                        total += period["monthly_fee"]
        if "codex" in tools:
            for period in SUBSCRIPTIONS["codex"]:
                if period["monthly_fee"] > 0:
                    p_start = period["start"]
                    p_end = period["end"] or "9999-12"
                    if m_key >= p_start[:7] and m_key < p_end[:7]:
                        total += period["monthly_fee"]
        if total > 0:
            sub_fees[m_key] = total
    return sub_fees


class Bucket:
    """Acumulador de métricas para un bucket de agregación (día, mes, proyecto).

    Una sola implementación del bloque de acumulación que antes estaba
    copiado 4 veces en aggregate() — el cambio de contabilidad de tokens
    se hace en UN lugar.
    """

    def __init__(self):
        self.interactions = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_write_tokens = 0
        self.cost_effective = 0.0
        self.cost_real = 0.0
        self.tools = Counter()
        self.models = Counter()
        self.first_seen = None
        self.last_seen = None
        self.skills = Counter()

    def add(self, r, real_cost):
        self.interactions += 1
        self.input_tokens += r.get("input_tokens", 0) or 0
        self.output_tokens += r.get("output_tokens", 0) or 0
        self.cache_read_tokens += r.get("cache_read_tokens", 0) or 0
        self.cache_write_tokens += r.get("cache_write_tokens", 0) or 0
        self.cost_effective += r.get("cost_effective", 0) or 0
        self.cost_real += real_cost
        self.tools[r["tool"]] += 1
        self.models[r["model_raw"]] += 1

    def to_dict(self, detail=False):
        d = {
            "interactions": self.interactions,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "cost_effective": round(self.cost_effective, 2),
            "cost_real": round(self.cost_real, 2),
            "tools": dict(self.tools.most_common()),
            "models": dict(self.models.most_common()),
        }
        if detail:
            d["subscription_fees"] = 0.0
        return d


class HourlyBucket(Bucket):
    """Bucket horario: además lleva stats detalladas por herramienta."""

    def __init__(self):
        super().__init__()
        self.tool_stats = defaultdict(Bucket)

    def add(self, r, real_cost):
        super().add(r, real_cost)
        ts = self.tool_stats[r["tool"]]
        ts.interactions += 1
        ts.input_tokens += r.get("input_tokens", 0) or 0
        ts.output_tokens += r.get("output_tokens", 0) or 0
        ts.cache_read_tokens += r.get("cache_read_tokens", 0) or 0
        ts.cache_write_tokens += r.get("cache_write_tokens", 0) or 0
        ts.cost_effective += r.get("cost_effective", 0) or 0
        ts.cost_real += real_cost

    def to_dict(self):
        d = super().to_dict()
        d["tools"] = {t: {
            "req": b.interactions, "in": b.input_tokens, "out": b.output_tokens,
            "cache_read": b.cache_read_tokens, "cache_write": b.cache_write_tokens,
            "cost_eff": round(b.cost_effective, 8), "cost_real": round(b.cost_real, 8),
        } for t, b in self.tool_stats.items()}
        return d


def _context_switches(interactions):
    """Cambios de proyecto entre requests consecutivos (por día)."""
    switches_by_day = Counter()
    prev = None
    for r in sorted(interactions, key=lambda x: x["timestamp"]):
        d = r["timestamp"][:10]
        p = clean_proj_name(r.get("project", "unknown"))
        if prev and prev[1] != p:
            switches_by_day[d] += 1
        prev = (d, p)
    return switches_by_day


def _project_daily(by_project, day_projects, proj_day):
    """Matriz densa proyecto × día para el Gantt."""
    from datetime import date as _date, timedelta as _td
    all_days = []
    if day_projects:
        d0 = _date.fromisoformat(min(day_projects))
        d1 = _date.fromisoformat(max(day_projects))
        cur = d0
        while cur <= d1:
            all_days.append(cur.isoformat())
            cur += _td(days=1)
    return {
        "days": all_days,
        "matrix": {
            p: [proj_day[p].get(d, 0) for d in all_days]
            for p in sorted(by_project, key=lambda x: -sum(proj_day[x].values()))
        },
    }


def _multitasking_block(hour_projects, day_projects, daily, switches_by_day):
    mt_hour_counts = {h: len(ps) for h, ps in hour_projects.items()}
    mt_dist = Counter()
    for n in mt_hour_counts.values():
        if n == 1: mt_dist["1"] += 1
        elif n == 2: mt_dist["2"] += 1
        elif n == 3: mt_dist["3"] += 1
        else: mt_dist["4+"] += 1

    total_active_hours = len(hour_projects)
    mt_hours_n = sum(1 for n in mt_hour_counts.values() if n >= 2)
    top_mt_hours = sorted(mt_hour_counts.items(), key=lambda x: -x[1])[:10]
    max_n = max(mt_hour_counts.values()) if mt_hour_counts else 0
    max_hours = [h for h, n in mt_hour_counts.items() if n == max_n] if mt_hour_counts else []

    active_days = len(day_projects)
    mt_days = {d: len(ps) for d, ps in day_projects.items()}
    mt_days_n = sum(1 for n in mt_days.values() if n >= 2)
    top_mt_days = sorted(mt_days.items(), key=lambda x: -x[1])[:10]
    total_switches = sum(switches_by_day.values())
    top_switch_days = sorted(switches_by_day.items(), key=lambda x: -x[1])[:10]

    return {
        "description": (
            "Proyectos distintos con actividad en la misma ventana. "
            "'context_switches' cuenta cambios de proyecto entre requests "
            "consecutivos (puede inflarse por agentes paralelos en el mismo minuto)."
        ),
        "hourly": {
            "total_active_hours": total_active_hours,
            "hours_with_multiple_projects": mt_hours_n,
            "pct_hours_multitasking": round(100 * mt_hours_n / total_active_hours, 1) if total_active_hours else 0,
            "avg_projects_per_active_hour": round(sum(mt_hour_counts.values()) / total_active_hours, 2) if total_active_hours else 0,
            "distribution": dict(mt_dist.most_common()),
            "max_projects_in_one_hour": {
                "count": max_n,
                "hours": max_hours[:5],
                "projects": sorted(hour_projects[max_hours[0]]) if max_hours else [],
            },
            "top_10_hours": [
                {"hour": h, "projects": n, "list": sorted(hour_projects[h])}
                for h, n in top_mt_hours
            ],
        },
        "daily": {
            "total_active_days": active_days,
            "days_with_multiple_projects": mt_days_n,
            "pct_days_multitasking": round(100 * mt_days_n / active_days, 1) if active_days else 0,
            "avg_projects_per_active_day": round(sum(mt_days.values()) / active_days, 2) if active_days else 0,
            "top_10_days": [
                {"date": d, "projects": n, "list": sorted(day_projects[d]),
                 "interactions": daily[d]["interactions"] if d in daily else 0}
                for d, n in top_mt_days
            ],
        },
        "context_switches": {
            "total": total_switches,
            "avg_per_active_day": round(total_switches / active_days, 1) if active_days else 0,
            "max_in_one_day": top_switch_days[0][1] if top_switch_days else 0,
            "top_10_days": dict(top_switch_days),
        },
    }


def _session_stats(sessions):
    """Estadísticas de sesiones (largos, autonomía, promedios, top)."""
    stats = {
        "total_sessions": len(sessions),
        "length_distribution": Counter(),
        "with_agent": 0,
        "total_api_errors": 0,
        "total_compactions": 0,
        "avg_turns": 0,
        "avg_tools": 0,
        "avg_skills": 0,
    }
    longest = []
    for s in sessions:
        n = s["n_turns"]
        if n <= 10: stats["length_distribution"]["1-10"] += 1
        elif n <= 50: stats["length_distribution"]["11-50"] += 1
        elif n <= 100: stats["length_distribution"]["51-100"] += 1
        elif n <= 300: stats["length_distribution"]["101-300"] += 1
        elif n <= 500: stats["length_distribution"]["301-500"] += 1
        else: stats["length_distribution"]["500+"] += 1
        if s["has_agent"]:
            stats["with_agent"] += 1
        stats["total_api_errors"] += s["n_errors"]
        stats["total_compactions"] += s["n_compactions"]
        stats["avg_turns"] += n
        stats["avg_tools"] += s["n_tools"]
        stats["avg_skills"] += s["n_skills"]
        longest.append((n, s["duration_msgs"], s["first_ts"], s["project"]))

    if sessions:
        n = len(sessions)
        stats["avg_turns"] /= n
        stats["avg_tools"] /= n
        stats["avg_skills"] /= n

    longest.sort(key=lambda x: -x[0])
    stats["top_longest_by_turns"] = [
        {"turns": t, "msgs": m, "date": d, "project": clean_proj_name(p)}
        for t, m, d, p in longest[:10]
    ]
    return stats


def collect_skills_and_commands():
    """Extrae skills (cache de Claude) y comandos slash (history.jsonl).

    Vive FUERA de aggregate() para que la agregación sea pura y testeable:
    los resultados se inyectan como parámetros.
    """
    by_skill_total = Counter()
    skills_by_project = defaultdict(Counter)  # proyecto limpio -> skill -> count
    cache_file = CLAUDE_DIR / "dashboard-cache.json"
    if cache_file.exists():
        cache = json.loads(cache_file.read_text())
        for key, summary in cache.get("entries", {}).items():
            if summary.get("source") != "claude": continue
            proj = summary.get("project", "")
            if not is_charly(proj): continue
            proj_clean = clean_proj_name(proj)
            for skill, count in summary.get("skill_uses", {}).items():
                by_skill_total[skill] += count
                skills_by_project[proj_clean][skill] += count

    commands = Counter()
    hist_file = CLAUDE_DIR / "history.jsonl"
    if hist_file.exists():
        with open(hist_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                display = entry.get("display", "")
                proj = entry.get("project", "")
                if not is_charly(proj): continue
                stripped = display.strip()
                if stripped.startswith("/") and len(stripped) > 2:
                    cmd = stripped.split()[0]
                    if 2 <= len(cmd) <= 30:
                        commands[cmd] += 1

    return by_skill_total, skills_by_project, commands


def aggregate(interactions, sessions, skills_total=None, skills_by_project=None,
              commands=None):
    """Agrega rows → reporte completo. Pura: los datos de skills/comandos
    se inyectan (ver collect_skills_and_commands())."""
    hourly = {}
    daily = {}
    monthly = {}
    by_project = {}
    hour_projects = defaultdict(set)  # hora -> proyectos distintos activos
    day_projects = defaultdict(set)   # día -> proyectos distintos activos
    proj_day = defaultdict(Counter)   # proyecto -> {día: interacciones}

    for r in interactions:
        h = r["hour"]
        d = h[:10]
        m = d[:7]
        real, _, _ = get_sub_cost(r["tool"], r.get("timestamp", ""), r.get("cost_effective", 0) or 0)

        if h not in hourly: hourly[h] = HourlyBucket()
        if d not in daily: daily[d] = Bucket()
        if m not in monthly: monthly[m] = Bucket()
        hourly[h].add(r, real)
        daily[d].add(r, real)
        monthly[m].add(r, real)

        proj = clean_proj_name(r.get("project", "unknown"))
        hour_projects[h].add(proj)
        day_projects[d].add(proj)
        proj_day[proj][d] += 1
        if proj not in by_project: by_project[proj] = Bucket()
        by_project[proj].add(r, real)
        # first/last seen
        ts = r["timestamp"]
        pp = by_project[proj]
        if pp.first_seen is None or ts < pp.first_seen:
            pp.first_seen = ts
        if pp.last_seen is None or ts > pp.last_seen:
            pp.last_seen = ts

    # --- Multitasking + context switches ---
    switches_by_day = _context_switches(interactions)
    multitasking = _multitasking_block(hour_projects, day_projects,
                                       {d: b.to_dict() for d, b in daily.items()},
                                       switches_by_day)

    # Conteo de proyectos activos por hora
    for h, ps in hour_projects.items():
        if h in hourly:
            hourly[h].projects_active = len(ps)

    # --- Subscription fees ---
    monthly_dicts = {m: b.to_dict(detail=True) for m, b in monthly.items()}
    sub_fees = calc_subscription_fees(monthly_dicts)
    for m_key, fee in sub_fees.items():
        if m_key in monthly:
            monthly[m_key].cost_real += fee
            monthly_dicts[m_key]["cost_real"] = round(monthly[m_key].cost_real, 2)
            monthly_dicts[m_key]["subscription_fees"] = fee
        for d_key, d_data in daily.items():
            if d_key[:7] == m_key:
                d_data.cost_real += fee / 30.0  # prorated roughly

    # --- Skills (inyectados; default: colección en vivo) ---
    if skills_total is None or skills_by_project is None or commands is None:
        skills_total, skills_by_project, commands = collect_skills_and_commands()
    skills_total = Counter(skills_total)
    commands = Counter(commands)
    for proj_clean, sk in skills_by_project.items():
        if proj_clean in by_project:
            by_project[proj_clean].skills = Counter(sk)

    # --- Sessions ---
    session_stats = _session_stats(sessions)

    # --- project_daily ---
    project_daily = _project_daily(by_project, day_projects, proj_day)

    def clean(o):
        if isinstance(o, defaultdict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, Counter):
            return dict(o.most_common())
        return o

    return clean({
        "metadata": {
            "date_range": {
                "start": min(r["timestamp"] for r in interactions)[:10] if interactions else None,
                "end": max(r["timestamp"] for r in interactions)[:10] if interactions else None,
            },
            "filter": "charly-only" if CHARLY_FILTER else "all",
            "total_interactions": sum(b.interactions for b in hourly.values()),
            "total_input_tokens": sum(b.input_tokens for b in hourly.values()),
            "total_output_tokens": sum(b.output_tokens for b in hourly.values()),
            "total_cache_read_tokens": sum(b.cache_read_tokens for b in hourly.values()),
            "total_cache_write_tokens": sum(b.cache_write_tokens for b in hourly.values()),
            "cost_total_effective": round(sum(b.cost_effective for b in hourly.values()), 2),
            "cost_total_real": round(sum(b.cost_real for b in hourly.values()), 2),
            "subscription_fees": round(sum(sub_fees.values()), 2),
            "token_accounting": (
                "cache_read/cache_write se reportan aparte de input/output. "
                "cache_read no se factura a input rate (10x mas barato); "
                "total tokens = input + output + cache_read + cache_write"
            ),
            "total_hours": len(hourly),
            "total_days": len(daily),
            "total_months": len(monthly),
            "total_projects": len(by_project),
        },
        "hourly": {h: b.to_dict() | {"projects_active": getattr(b, "projects_active", 0)}
                   for h, b in hourly.items()},
        "daily": {d: b.to_dict() for d, b in daily.items()},
        "monthly": dict(sorted(monthly_dicts.items())),
        "projects": {p: (b.to_dict() | {
            "first_seen": (b.first_seen or "")[:10],
            "last_seen": (b.last_seen or "")[:10],
            "skills": dict(getattr(b, "skills", {}).most_common()),
        }) for p, b in sorted(by_project.items(), key=lambda x: -x[1].cost_effective)},
        "skills": dict(skills_total.most_common(50)),
        "commands": dict(commands.most_common(30)),
        "sessions": session_stats,
        "multitasking": multitasking,
        "project_daily": project_daily,
        "subscription_config": SUBSCRIPTIONS,
        "subscription_fees_by_month": sub_fees,
    })

def main():
    ap = argparse.ArgumentParser(description="Extractor de uso de IA (charly only)")
    ap.add_argument("--output", default=None,
                    help="Ruta del JSON de salida (default: data/usage_report_v3.json)")
    ap.add_argument("--force", action="store_true",
                    help="Escribir aunque los datos extraídos sean casi vacíos")
    args = ap.parse_args()
    out_path = Path(args.output) if args.output else OUTPUT_DIR / "usage_report_v3.json"

    print("=== IA Usage Tracker v4.1 (Charly only) ===", flush=True)

    interactions = []
    skipped = {}

    all_sources = [
        ("Claude", extract_claude(skipped)),
        ("Pi", extract_pi(skipped)),
        ("Amp", extract_amp()),
    ]

    for name, rows in all_sources:
        print(f"  {name}: {len(rows)} rows", flush=True)
        interactions.extend(rows)

    # Dedup across sources
    seen = set()
    unique = []
    for r in sorted(interactions, key=lambda x: x["timestamp"]):
        key = (r["timestamp"], r["tool"], r["model_raw"], r.get("source", ""), r.get("project", ""))
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"  Total: {len(interactions)} → {len(unique)} unique", flush=True)

    if len(unique) < MIN_INTERACTIONS and not args.force:
        print(
            f"\nABORTADO: solo {len(unique)} interacciones encontradas (< {MIN_INTERACTIONS}).",
            "\nLos extractores leen ~/.claude, ~/.pi/agent y ~/.amp — ¿estás en la máquina con los logs?",
            "\nUsa --force para escribir de todas formas.",
            flush=True,
        )
        sys.exit(1)

    print("Session stats...", flush=True)
    sessions = extract_session_stats()
    print(f"  {len(sessions)} charly sessions", flush=True)

    print("Aggregating...", flush=True)
    report = aggregate(unique, sessions, *collect_skills_and_commands())
    if skipped:
        report["metadata"]["skipped"] = dict(skipped)
        report["metadata"]["skipped_lines"] = sum(skipped.values())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Pretty print
    m = report["metadata"]
    print(f"\n=== REPORT v4.1 ===")
    print(f"Period: {m['date_range']['start']} → {m['date_range']['end']} ({m['filter']})")
    print(f"Interactions: {m['total_interactions']:,}")
    print(f"Cost effective: ${m['cost_total_effective']:,.2f}")
    print(f"Cost real: ${m['cost_total_real']:,.2f}")
    print(f"  Subscription fees: ${m['subscription_fees']:,.2f}")
    print(f"  Pay-per-token: ${m['cost_total_real'] - m['subscription_fees']:,.2f}")
    print(f"Hours: {m['total_hours']}, Days: {m['total_days']}, Projects: {m['total_projects']}")

    print(f"\n--- Monthly ---")
    for m_name, mo in report["monthly"].items():
        tools_s = ", ".join(f"{t}:{c}" for t, c in list(mo["tools"].items())[:3])
        models_s = ", ".join(f"{mv}:{c}" for mv, c in list(mo["models"].items())[:3])
        sub = mo.get("subscription_fees", 0)
        print(f"  {m_name}: {mo['interactions']:>6} reqs  "
              f"${mo['cost_effective']:>7.2f} eff  "
              f"${mo['cost_real']:>6.2f} real"
              f"{f' (sub ${sub:.0f})' if sub else ''}  "
              f"{mo['input_tokens']//1000:>5}K in  {mo['output_tokens']//1000:>5}K out")
        print(f"       Tools: {tools_s}")
        print(f"       Models: {models_s}")

    print(f"\n--- Sessions ---")
    ss = report["sessions"]
    print(f"  Total: {ss['total_sessions']}")
    print(f"  Length distribution: {dict(ss['length_distribution'])}")
    if ss['total_sessions'] > 0:
        print(f"  With Agent (autonomous): {ss['with_agent']}/{ss['total_sessions']} "
              f"({100 * ss['with_agent'] / ss['total_sessions']:.0f}%)")
    print(f"  Avg turns: {ss['avg_turns']:.0f}, Avg tools: {ss['avg_tools']:.1f}")
    print(f"  API errors: {ss['total_api_errors']}, Compactions: {ss['total_compactions']}")
    print(f"  Longest sessions:")
    for s in ss['top_longest_by_turns'][:5]:
        print(f"    {s['turns']:>4} turns | {s['msgs']:>3} msgs | {s['date']} | {s['project'][:45]}")

    print(f"\n--- Multitasking ---")
    mt = report["multitasking"]
    mh, md, mc = mt["hourly"], mt["daily"], mt["context_switches"]
    print(f"  Horas con ≥2 proyectos: {mh['hours_with_multiple_projects']}/{mh['total_active_hours']} "
          f"({mh['pct_hours_multitasking']}%)")
    print(f"  Avg proyectos/hora activa: {mh['avg_projects_per_active_hour']}")
    print(f"  Distribución por hora: {mh['distribution']}")
    mx = mh["max_projects_in_one_hour"]
    print(f"  Máx simultáneo: {mx['count']} proyectos en {mx['hours']}")
    print(f"  Días con ≥2 proyectos: {md['days_with_multiple_projects']}/{md['total_active_days']} "
          f"({md['pct_days_multitasking']}%)")
    print(f"  Context switches: {mc['total']} total, {mc['avg_per_active_day']}/día activo")
    print(f"  Top días multitasking:")
    for t in md["top_10_days"][:5]:
        print(f"    {t['date']}: {t['projects']} proyectos, {t['interactions']} reqs")

    print(f"\n--- Skills ---")
    for skill, count in list(report['skills'].items())[:10]:
        print(f"  {skill}: {count}")

    print(f"\n--- Commands ---")
    for cmd, count in list(report['commands'].items())[:10]:
        print(f"  {cmd}: {count}")

    print(f"\nDone. {out_path}")


if __name__ == "__main__":
    main()