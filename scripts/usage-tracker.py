#!/usr/bin/env python3
"""
usage-tracker.py v3 — Extractor completo de uso de IA.
Filtra solo proyectos charly, incluye Amp, sesiones y patrones.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PI_DIR = Path.home() / ".pi" / "agent"
AMP_DIR = Path.home() / ".amp"
GEMINI_DIR = Path.home() / ".gemini"
OUTPUT_DIR = Path("data")
LOCAL_TZ = datetime.now().astimezone().tzinfo

# Solo proyectos charly
CHARLY_FILTER = True

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


def parse_ts(ts):
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
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


def extract_claude():
    rows = []
    for pd in (CLAUDE_DIR / "projects").iterdir():
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
                            rows.append({
                                "source": "claude", "tool": "claude-cli",
                                "model_raw": model, "model_family": fam,
                                "model_version": ver, "project": proj,
                                "timestamp": ts.isoformat(), "hour": hour_key(ts),
                                "input_tokens": usage.get("input_tokens", 0) or 0,
                                "output_tokens": usage.get("output_tokens", 0) or 0,
                                "cost_effective": None,
                            })
            except: pass

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
                fam, ver = model_details(model)
                rows.append({
                    "source": "claude_cache", "tool": "claude-cli",
                    "model_raw": model, "model_family": fam, "model_version": ver,
                    "project": proj, "timestamp": ts.isoformat(), "hour": hour_key(ts),
                    "input_tokens": turn.get("input_tokens", 0) or 0,
                    "output_tokens": turn.get("output_tokens", 0) or 0,
                    "cost_effective": turn.get("cost", 0) or 0,
                })
    return rows


def extract_pi():
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
                        cost_info = usage.get("cost", {})
                        cost = cost_info.get("total") if isinstance(cost_info, dict) else (usage.get("cost") or 0)
                        model = msg.get("model", "unknown")
                        provider = entry.get("provider", msg.get("provider", ""))
                        ts = parse_ts(entry.get("timestamp"))
                        if not ts: continue
                        fam, ver = model_details(model)
                        tool_map = {"openai-codex":"codex","claude-cli":"claude-cli","google-gemini-cli":"gemini-cli","gemini-cli":"gemini-cli","openrouter":"openrouter","github-copilot":"copilot","anthropic":"claude-cli"}
                        tool = tool_map.get(provider, provider)
                        rows.append({
                            "source": "pi", "tool": tool,
                            "model_raw": model, "model_family": fam, "model_version": ver,
                            "project": proj, "timestamp": ts.isoformat(), "hour": hour_key(ts),
                            "input_tokens": usage.get("input_tokens") or usage.get("input", 0) or 0,
                            "output_tokens": usage.get("output_tokens") or usage.get("output", 0) or 0,
                            "cost_effective": cost,
                        })
            except: pass
    return rows


def extract_amp():
    """Extrae de Amp (@ampcode/cli, agente autónomo).
    Solo guarda URIs de archivos modificados. No hay costo ni modelo.
    Amp fue la herramienta principal ene-feb (fabbro, nayra), reemplazado por Claude CLI."""
    rows = []
    amp_dir = AMP_DIR / "file-changes"
    if not amp_dir.exists(): return rows
    for td in amp_dir.iterdir():
        if not td.is_dir(): continue
        # Check if this task touched charly files
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
            except: pass
        if task_proj and task_dates:
            for ts in task_dates:
                rows.append({
                    "source": "amp", "tool": "amp",
                    "model_raw": "amp", "model_family": "amp", "model_version": "v1",
                    "project": "charly/amp-auto", "timestamp": ts.isoformat(),
                    "hour": hour_key(ts),
                    "input_tokens": 0, "output_tokens": 0, "cost_effective": 0,
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
            "avg_input_per_turn": 0,
            "avg_output_per_turn": 0,
        })
    return sessions


def get_sub_cost(tool, ts_str, eff_cost):
    """tool, timestamp_str, effective_cost -> (real_cost, effective_cost, sub_label)"""
    if tool not in ["claude-cli", "codex"]:
        return eff_cost, eff_cost, "pay-per-token"
    date = (ts_str or "")[:10]
    for period in SUBSCRIPTIONS[tool]:
        if period["start"] <= date and (period["end"] is None or date < period["end"]):
            if period["monthly_fee"] > 0:
                label = period["label"]
                return 0.0, eff_cost, label
            else:
                return eff_cost, eff_cost, period["label"]
    return eff_cost, eff_cost, "unknown"


def aggregate(interactions, sessions):
    hourly = {}
    daily = {}
    monthly = {}
    by_project = {}
    by_tool_model = Counter()
    by_skill_total = Counter()
    
    def new_hourly():
        return {"interactions":0,"input_tokens":0,"output_tokens":0,"cost_real":0.0,"cost_effective":0.0,"tools":defaultdict(lambda:{"req":0,"in":0,"out":0,"cost_eff":0.0,"cost_real":0.0}),"models":defaultdict(int)}
    
    def new_simple():
        return {"interactions":0,"input_tokens":0,"output_tokens":0,"cost_real":0.0,"cost_effective":0.0,"tools":Counter(),"models":Counter()}
    
    def new_proj():
        return {"interactions":0,"input_tokens":0,"output_tokens":0,"cost_effective":0.0,"cost_real":0.0,"first_seen":None,"last_seen":None,"tools":Counter(),"models":Counter(),"skills":Counter()}
    
    for r in interactions:
        h = r["hour"]; d = h[:10]; m = d[:7]
        tool = r["tool"]; model = r["model_raw"]
        inp = r.get("input_tokens",0) or 0
        out = r.get("output_tokens",0) or 0
        eff = r.get("cost_effective",0) or 0
        real, _, _ = get_sub_cost(tool, r.get("timestamp",""), eff)
        
        if h not in hourly: hourly[h] = new_hourly()
        hr = hourly[h]
        hr["interactions"] += 1; hr["input_tokens"] += inp; hr["output_tokens"] += out
        hr["cost_effective"] += eff; hr["cost_real"] += real
        hr["tools"][tool]["req"] += 1; hr["tools"][tool]["in"] += inp
        hr["tools"][tool]["out"] += out; hr["tools"][tool]["cost_real"] += real
        hr["tools"][tool]["cost_eff"] += eff; hr["models"][model] += 1
        
        for agg, key in [(daily, d), (monthly, m)]:
            if key not in agg: agg[key] = new_simple()
            a = agg[key]
            a["interactions"] += 1; a["input_tokens"] += inp; a["output_tokens"] += out
            a["cost_effective"] += eff; a["cost_real"] += real
            a["tools"][tool] += 1; a["models"][model] += 1
        
        proj = r.get("project","unknown").replace("-var-home-sasha-para-areas-dev-gh-","").replace("--","/")
        if proj not in by_project: by_project[proj] = new_proj()
        pp = by_project[proj]
        pp["interactions"] += 1; pp["input_tokens"] += inp; pp["output_tokens"] += out
        pp["cost_effective"] += eff; pp["cost_real"] += real
        pp["tools"][tool] += 1; pp["models"][model] += 1
        if pp["first_seen"] is None or r["timestamp"] < pp["first_seen"]: pp["first_seen"] = r["timestamp"]
        if pp["last_seen"] is None or r["timestamp"] > pp["last_seen"]: pp["last_seen"] = r["timestamp"]
    
    # Skills from session cache
    cache_file = CLAUDE_DIR / "dashboard-cache.json"
    if cache_file.exists():
        cache = json.loads(cache_file.read_text())
        for key, summary in cache.get("entries", {}).items():
            if summary.get("source") != "claude": continue
            proj = summary.get("project","")
            if not is_charly(proj): continue
            proj_clean = proj.replace("-var-home-sasha-para-areas-dev-gh-","").replace("--","/")
            for skill, count in summary.get("skill_uses",{}).items():
                by_skill_total[skill] += count
                if proj_clean in by_project:
                    by_project[proj_clean]["skills"][skill] += count
    
    # Commands from history
    commands = Counter()
    hist_file = CLAUDE_DIR / "history.jsonl"
    if hist_file.exists():
        with open(hist_file) as f:
            for line in f:
                try: entry = json.loads(line)
                except: continue
                display = entry.get("display","")
                proj = entry.get("project","")
                if not is_charly(proj): continue
                stripped = display.strip()
                if stripped.startswith("/") and len(stripped)>2:
                    cmd = stripped.split()[0]
                    if 2 <= len(cmd) <= 30:
                        commands[cmd] += 1
    
    def clean(o):
        if isinstance(o, defaultdict): return {k: clean(v) for k,v in o.items()}
        if isinstance(o, Counter): return dict(o.most_common())
        return o
    
    # Session analytics
    session_stats = {
        "total_sessions": len(sessions),
        "length_distribution": Counter(),
        "with_agent": 0,
        "total_api_errors": 0,
        "total_compactions": 0,
        "avg_turns": 0,
        "avg_tools": 0,
        "avg_skills": 0,
    }
    longest_by_turns = []
    longest_by_duration = []
    for s in sessions:
        n = s["n_turns"]
        if n <= 10: session_stats["length_distribution"]["1-10"] += 1
        elif n <= 50: session_stats["length_distribution"]["11-50"] += 1
        elif n <= 100: session_stats["length_distribution"]["51-100"] += 1
        elif n <= 300: session_stats["length_distribution"]["101-300"] += 1
        elif n <= 500: session_stats["length_distribution"]["301-500"] += 1
        else: session_stats["length_distribution"]["500+"] += 1
        if s["has_agent"]: session_stats["with_agent"] += 1
        session_stats["total_api_errors"] += s["n_errors"]
        session_stats["total_compactions"] += s["n_compactions"]
        session_stats["avg_turns"] += n
        session_stats["avg_tools"] += s["n_tools"]
        session_stats["avg_skills"] += s["n_skills"]
        longest_by_turns.append((n, s["duration_msgs"], s["first_ts"], s["project"]))
    
    if sessions:
        n = len(sessions)
        session_stats["avg_turns"] /= n
        session_stats["avg_tools"] /= n
        session_stats["avg_skills"] /= n
    
    longest_by_turns.sort(key=lambda x: -x[0])
    session_stats["top_longest_by_turns"] = [{"turns":t,"msgs":m,"date":d,"project":p.replace("-var-home-sasha-para-areas-dev-gh-","").replace("--","/")} for t,m,d,p in longest_by_turns[:10]]
    
    return clean({
        "metadata": {
            "date_range": {
                "start": min(r["timestamp"] for r in interactions)[:10] if interactions else None,
                "end": max(r["timestamp"] for r in interactions)[:10] if interactions else None,
            },
            "filter": "charly-only" if CHARLY_FILTER else "all",
            "total_interactions": sum(h["interactions"] for h in hourly.values()),
            "total_input_tokens": sum(h["input_tokens"] for h in hourly.values()),
            "total_output_tokens": sum(h["output_tokens"] for h in hourly.values()),
            "cost_total_effective": round(sum(h["cost_effective"] for h in hourly.values()), 2),
            "cost_total_real": round(sum(h["cost_real"] for h in hourly.values()), 2),
            "total_hours": len(hourly),
            "total_days": len(daily),
            "total_months": len(monthly),
            "total_projects": len(by_project),
        },
        "hourly": hourly,
        "daily": daily,
        "monthly": clean({m: {
            "interactions": v["interactions"], "input_tokens": v["input_tokens"],
            "output_tokens": v["output_tokens"], "cost_effective": round(v["cost_effective"],2),
            "cost_real": round(v["cost_real"],2),
            "tools": dict(v["tools"].most_common()),
            "models": dict(v["models"].most_common()),
        } for m, v in sorted(monthly.items())}),
        "projects": clean({p: {
            "interactions": v["interactions"], "input_tokens": v["input_tokens"],
            "output_tokens": v["output_tokens"], "cost_effective": round(v["cost_effective"],2),
            "cost_real": round(v["cost_real"],2),
            "first_seen": (v["first_seen"] or "")[:10],
            "last_seen": (v["last_seen"] or "")[:10],
            "tools": dict(v["tools"].most_common()),
            "models": dict(v["models"].most_common()),
            "skills": dict(v["skills"].most_common()),
        } for p, v in sorted(by_project.items(), key=lambda x: -x[1]["cost_effective"])}),
        "skills": dict(by_skill_total.most_common(50)),
        "commands": dict(commands.most_common(30)),
        "sessions": session_stats,
        "subscription_config": SUBSCRIPTIONS,
        "tools_summary": {},
    })


def main():
    print("=== IA Usage Tracker v3 (Charly only) ===", flush=True)
    
    interactions = []
    
    all_sources = [
        ("Claude", extract_claude()),
        ("Pi", extract_pi()),
        ("Amp", extract_amp()),
    ]
    
    for name, rows in all_sources:
        print(f"  {name}: {len(rows)} rows", flush=True)
        interactions.extend(rows)
    
    # Dedup
    seen = set()
    unique = []
    for r in sorted(interactions, key=lambda x: x["timestamp"]):
        key = (r["timestamp"], r["tool"], r["model_raw"], r.get("source",""))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    print(f"  Total: {len(interactions)} → {len(unique)} unique", flush=True)
    
    print("Session stats...", flush=True)
    sessions = extract_session_stats()
    print(f"  {len(sessions)} charly sessions", flush=True)
    
    print("Aggregating...", flush=True)
    report = aggregate(unique, sessions)
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "usage_report_v3.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    # Pretty print
    m = report["metadata"]
    print(f"\n=== REPORT ===")
    print(f"Period: {m['date_range']['start']} → {m['date_range']['end']} ({m['filter']})")
    print(f"Interactions: {m['total_interactions']:,}")
    print(f"Cost effective: ${m['cost_total_effective']:,.2f}")
    print(f"Cost real: ${m['cost_total_real']:,.2f}")
    print(f"Hours: {m['total_hours']}, Days: {m['total_days']}, Projects: {m['total_projects']}")
    
    print(f"\n--- Monthly ---")
    for m_name, mo in report["monthly"].items():
        tools_s = ", ".join(f"{t}:{c}" for t,c in list(mo["tools"].items())[:4])
        models_s = ", ".join(f"{mv}:{c}" for mv,c in list(mo["models"].items())[:4])
        print(f"  {m_name}: {mo['interactions']:>6} reqs  ${mo['cost_effective']:>7.2f} eff  ${mo['cost_real']:>6.2f} real  {mo['input_tokens']//1000:>5}K in  {mo['output_tokens']//1000:>5}K out")
        print(f"       Tools: {tools_s}")
        print(f"       Models: {models_s}")
    
    print(f"\n--- Sessions ---")
    ss = report["sessions"]
    print(f"  Total: {ss['total_sessions']}")
    print(f"  Length distribution: {dict(ss['length_distribution'])}")
    print(f"  With Agent (autonomous): {ss['with_agent']}/{ss['total_sessions']} ({100*ss['with_agent']/max(1,ss['total_sessions']):.0f}%)")
    print(f"  Avg turns: {ss['avg_turns']:.0f}, Avg tools: {ss['avg_tools']:.1f}")
    print(f"  API errors: {ss['total_api_errors']}, Compactions: {ss['total_compactions']}")
    print(f"  Longest sessions:")
    for s in ss['top_longest_by_turns'][:5]:
        print(f"    {s['turns']:>4} turns | {s['msgs']:>3} msgs | {s['date']} | {s['project'][:45]}")
    
    print(f"\n--- Skills ---")
    for skill, count in list(report['skills'].items())[:10]:
        print(f"  {skill}: {count}")
    
    print(f"\n--- Commands ---")
    for cmd, count in list(report['commands'].items())[:10]:
        print(f"  {cmd}: {count}")
    
    print(f"\nDone. data/usage_report_v3.json")


if __name__ == "__main__":
    main()