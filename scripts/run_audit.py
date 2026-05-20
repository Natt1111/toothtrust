"""End-to-end pipeline runner for ToothTrust mock cases.

Usage:
    python -m scripts.run_audit data/mock_cases/case_01_crown_vs_composite
    python -m scripts.run_audit data/mock_cases/case_02_endo_vs_extraction
    python -m scripts.run_audit data/mock_cases/case_03_perio_voice
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# ── ANSI colour helpers ────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def green(s):  return f"{GREEN}{s}{RESET}"
def red(s):    return f"{RED}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"


# ── Serialisation helper ───────────────────────────────────────────────────────

def _serialise(obj):
    """Convert AuditResult dataclasses (or any object) to plain dicts/lists."""
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialise(v) for v in obj]
    try:
        return asdict(obj)
    except TypeError:
        return str(obj)


# ── Case loader ────────────────────────────────────────────────────────────────

def load_case(case_dir: Path) -> dict:
    case = json.loads((case_dir / "case.json").read_text())

    xray_path = case_dir / "xray_description.md"
    case["xray_description"] = xray_path.read_text() if xray_path.exists() else ""

    tp_path = case_dir / "treatment_plan.json"
    case["treatment_plan"] = json.loads(tp_path.read_text()) if tp_path.exists() else []

    vt_path = case_dir / "voice_transcript.txt"
    case["voice_transcript"] = vt_path.read_text() if vt_path.exists() else ""

    exp_audit = case_dir / "expected_audit.json"
    exp_chart = case_dir / "expected_chart.json"
    if exp_audit.exists():
        case["expected"] = json.loads(exp_audit.read_text())
        case["expected_file"] = "expected_audit.json"
    elif exp_chart.exists():
        case["expected"] = json.loads(exp_chart.read_text())
        case["expected_file"] = "expected_chart.json"
    else:
        case["expected"] = {}
        case["expected_file"] = None

    return case


# ── Runners ────────────────────────────────────────────────────────────────────

def run_audit_case(case: dict) -> dict:
    from src.agents.audit_agent import AuditAgent

    patient = case.get("patient", {})
    patient_context = (
        f"Age: {patient.get('age', 'unknown')}. "
        f"Chief complaint: {patient.get('chief_complaint', '')}. "
        f"Medical history: {patient.get('medical_history', '')}."
    )
    if case.get("xray_description"):
        patient_context += f"\n\nX-ray findings:\n{case['xray_description']}"

    agent = AuditAgent()
    result = agent.run(
        utterance=f"Audit this treatment plan: {json.dumps(case['treatment_plan'])}",
        treatment_plan=case["treatment_plan"],
        patient_context=patient_context,
    )

    # Flatten audit_result dataclass into the output dict
    audit_result = result.pop("audit_result", None)
    if audit_result is not None:
        result["audit_result"] = _serialise(audit_result)

    return result


def run_tc_case(case: dict, audit_result_obj) -> dict:
    from src.agents.treatment_coordinator_agent import TreatmentCoordinatorAgent

    agent = TreatmentCoordinatorAgent()
    patient = case.get("patient", {})
    return agent.run(
        audit_result=_serialise(audit_result_obj),
        patient_name=f"Patient (age {patient.get('age', '?')})",
        patient_context=patient.get("chief_complaint", ""),
    )


def run_perio_case(case: dict) -> dict:
    from src.agents.perio_chart_agent import PerioChartAgent

    agent = PerioChartAgent()
    return agent.run(
        transcript=case["voice_transcript"],
        corpus_citations=case.get("corpus_sources", []),
    )


# ── Comparison engine ──────────────────────────────────────────────────────────

def _check(label: str, actual_val, expected_val, mode: str = "eq") -> bool:
    """Print a comparison line and return True if it passes."""
    if actual_val is None:
        print(f"  {yellow('MISSING')}  {label}")
        print(f"           expected: {expected_val}")
        return False

    if mode == "eq":
        ok = str(actual_val).lower() == str(expected_val).lower()
    elif mode == "contains":
        ok = str(expected_val).lower() in str(actual_val).lower()
    elif mode == "overlap":
        # Both are lists; check non-empty intersection (case-insensitive filenames)
        a_set = {s.lower() for s in (actual_val or [])}
        e_set = {s.lower() for s in (expected_val or [])}
        ok = bool(a_set & e_set)
    else:
        ok = actual_val == expected_val

    status = green("PASS") if ok else red("FAIL")
    print(f"  {status}  {label}")
    if not ok:
        print(f"           actual:   {actual_val}")
        print(f"           expected: {expected_val}")
    return ok


def compare_audit(actual: dict, expected: dict) -> tuple[int, int]:
    """Compare audit output against expected. Returns (passes, total)."""
    print(bold("\n── Comparison: audit result ──────────────────────────────"))
    passes = 0
    total = 0

    # Map expected 'verdict' → actual 'overall' / audit_result.overall_assessment
    exp_verdict = expected.get("verdict", "").lower()
    act_overall = (actual.get("overall") or "").lower()
    # Also tolerate partial matches: "likely overtreatment" → "unsupported"
    verdict_map = {
        "likely overtreatment": ["unsupported", "partially_supported"],
        "questionable — missing option": ["partially_supported", "unsupported", "insufficient_evidence"],
        "supported": ["supported"],
    }
    ok = act_overall in verdict_map.get(exp_verdict, [exp_verdict]) or exp_verdict in act_overall
    total += 1
    status = green("PASS") if ok else red("FAIL")
    print(f"  {status}  verdict / overall_assessment")
    if not ok:
        print(f"           actual:   {act_overall}")
        print(f"           expected: {exp_verdict}")
    passes += int(ok)

    # Confidence
    exp_conf = expected.get("confidence", "")
    act_conf = actual.get("confidence", "")
    if exp_conf:
        total += 1
        passes += int(_check("confidence", act_conf, exp_conf, mode="eq"))

    # Citations — check overlap between expected corpus_sources and actual procedure citations
    exp_cites = expected.get("citations", [])
    act_cites = []
    for proc in (actual.get("audit_result", {}) or {}).get("procedures", []):
        act_cites.extend(proc.get("citations", []))
    if exp_cites:
        total += 1
        passes += int(_check("citations overlap", act_cites, exp_cites, mode="overlap"))

    # Patient summary present
    act_summary = (actual.get("audit_result", {}) or {}).get("patient_summary", "")
    total += 1
    ok = bool(act_summary and len(act_summary) > 20)
    status = green("PASS") if ok else red("FAIL")
    print(f"  {status}  patient_summary present ({len(act_summary)} chars)")
    passes += int(ok)

    # Recommended alternative CDT code mentioned somewhere in response
    alt = expected.get("recommended_alternative", {})
    if alt.get("cdt_code"):
        total += 1
        full_response = actual.get("response", "") + json.dumps(actual.get("audit_result", {}))
        passes += int(_check(
            f"recommended alternative {alt['cdt_code']} mentioned",
            full_response, alt["cdt_code"], mode="contains"
        ))

    return passes, total


def compare_perio(actual: dict, expected: dict) -> tuple[int, int]:
    """Compare PerioChartAgent output against expected chart."""
    print(bold("\n── Comparison: perio chart ───────────────────────────────"))
    passes = 0
    total = 0

    summary = (actual.get("chart") or {}).get("summary", {})
    exp_summary = expected.get("summary", {})

    # Teeth charted
    total += 1
    passes += int(_check("teeth_charted", summary.get("teeth_charted"), exp_summary.get("teeth_charted"), mode="eq"))

    # Worst CAL
    total += 1
    passes += int(_check("worst_cal", summary.get("worst_cal"), exp_summary.get("worst_cal"), mode="eq"))

    # AAP stage
    total += 1
    passes += int(_check("aap_stage", summary.get("aap_stage"), exp_summary.get("aap_stage"), mode="contains"))

    # AAP grade
    total += 1
    passes += int(_check("aap_grade", summary.get("aap_grade"), exp_summary.get("aap_grade"), mode="eq"))

    # BOP sites count
    total += 1
    passes += int(_check("bleeding_on_probing_sites", summary.get("bleeding_on_probing_sites"), exp_summary.get("bleeding_on_probing_sites"), mode="eq"))

    # Recommendations present
    recs = summary.get("recommended_next_steps", "")
    total += 1
    ok = bool(recs and len(recs) > 20)
    status = green("PASS") if ok else red("FAIL")
    print(f"  {status}  recommended_next_steps present ({len(str(recs))} chars)")
    passes += int(ok)

    return passes, total


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.run_audit <case_dir>")
        sys.exit(1)

    case_dir = Path(sys.argv[1])
    if not case_dir.exists():
        print(red(f"Case directory not found: {case_dir}"))
        sys.exit(1)

    print(bold(cyan(f"\n{'='*60}")))
    print(bold(cyan(f"  ToothTrust Pipeline Run — {case_dir.name}")))
    print(bold(cyan(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")))
    print(bold(cyan(f"{'='*60}\n")))

    case = load_case(case_dir)
    agent_spec = case.get("agent", "")
    is_perio = "PerioChartAgent" in agent_spec or bool(case.get("voice_transcript"))
    includes_tc = "TreatmentCoordinatorAgent" in agent_spec

    actual_output: dict = {}
    tc_output: dict = {}

    try:
        if is_perio:
            print(bold("▶ Running PerioChartAgent..."))
            actual_output = run_perio_case(case)
        else:
            print(bold("▶ Running AuditAgent..."))
            actual_output = run_audit_case(case)

            if includes_tc and actual_output.get("audit_result"):
                print(bold("\n▶ Running TreatmentCoordinatorAgent..."))
                # Reconstruct a lightweight audit object for TC
                from src.audit import AuditResult
                ar = actual_output["audit_result"]
                tc_output = run_tc_case(case, ar)

    except Exception as exc:
        print(red(f"\n✗ Pipeline error: {exc}"))
        import traceback
        traceback.print_exc()
        actual_output = {"error": str(exc)}

    # ── Print agent output ─────────────────────────────────────────────────────
    print(bold("\n── Agent Output ──────────────────────────────────────────"))

    if is_perio:
        print(f"  Response:  {actual_output.get('response', '')}")
        chart_summary = (actual_output.get("chart") or {}).get("summary", {})
        print(f"  AAP Stage: {chart_summary.get('aap_stage', '?')}, Grade: {chart_summary.get('aap_grade', '?')}")
        print(f"  Worst CAL: {chart_summary.get('worst_cal', '?')}mm")
        print(f"  BOP:       {chart_summary.get('bop_percent', '?')}%")
        print(f"\n  Recommendations:\n  {chart_summary.get('recommended_next_steps', '')}")
    else:
        print(f"  Overall:   {actual_output.get('overall', '')}")
        print(f"  Confidence:{actual_output.get('confidence', '')}")
        print(f"\n  Response text:\n{actual_output.get('response', '')}")

        ar = actual_output.get("audit_result", {}) or {}
        procs = ar.get("procedures", [])
        if procs:
            print(bold("\n  Per-procedure verdicts:"))
            for p in procs:
                verdict = p.get("verdict", "?")
                colour = green if verdict == "supported" else (red if verdict in ("unsupported",) else yellow)
                print(f"    {colour(verdict.upper())}  {p.get('description','?')}  [{p.get('cdt_code','')}]")
                for flag in p.get("flags", []):
                    print(f"      ⚑  {flag}")
                for cite in p.get("citations", []):
                    print(f"      📄 {cite}")

        if tc_output:
            print(bold("\n── TreatmentCoordinator Script ───────────────────────────"))
            script = tc_output.get("script") or {}
            print(f"  Opening: {script.get('opening', '')}")
            for opt in script.get("options", []):
                print(f"\n  {bold(opt.get('label','Option'))}")
                print(f"    Plain: {opt.get('plain_language','')}")
                print(f"    Outcome: {opt.get('typical_outcome','')}")
                print(f"    Worst case: {opt.get('worst_case','')}")
                print(f"    Timeline: {opt.get('timeline','')}")
                print(f"    Cost: ${opt.get('estimated_cost','?')}")
            print(f"\n  Recommendation framing:\n  {script.get('recommendation_framing','')}")

    # ── Comparison ────────────────────────────────────────────────────────────
    expected = case.get("expected", {})
    if expected:
        if is_perio:
            passes, total = compare_perio(actual_output, expected)
        else:
            passes, total = compare_audit(actual_output, expected)

        pct = round(passes / total * 100) if total else 0
        colour = green if pct >= 80 else (yellow if pct >= 50 else red)
        print(bold(f"\n── Score: {colour(f'{passes}/{total} ({pct}%)')} ─────────────────────────────────\n"))
    else:
        print(yellow("\nNo expected output file found — skipping comparison.\n"))
        passes, total = 0, 0

    # ── Save actual output ────────────────────────────────────────────────────
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    out_path = outputs_dir / f"{case_dir.name}_actual.json"

    save_payload = {
        "case_id": case.get("case_id"),
        "run_at": datetime.now(timezone.utc).isoformat(),
        "agent_output": _serialise(actual_output),
    }
    if tc_output:
        save_payload["tc_output"] = _serialise(tc_output)

    out_path.write_text(json.dumps(save_payload, indent=2))
    print(f"  Saved → {out_path}")

    sys.exit(0 if (total == 0 or passes == total) else 1)


if __name__ == "__main__":
    main()
