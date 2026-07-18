"""ToothTrust — voice-first multi-agent dental AI platform."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

# Must be set before any chromadb/tokenizer imports.
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Ensure project root is importable when running via `streamlit run app/streamlit_app.py`.
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="ToothTrust",
    page_icon="🦷",
    initial_sidebar_state="expanded",
)


def _get_secret(key: str, default: str = "") -> str:
    val = os.environ.get(key)
    if val:
        return val
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return default


def _inject_css() -> None:
    st.markdown("""
<style>
.tt-hero-headline {
    font-size: 2.8rem;
    font-weight: 800;
    color: #1E293B;
    line-height: 1.2;
    margin: 0 0 0.5rem 0;
}
.tt-hero-sub {
    font-size: 1.2rem;
    color: #64748B;
    font-weight: 400;
    margin-bottom: 2rem;
}
.tt-stat-number {
    font-size: 2.8rem;
    font-weight: 800;
    color: #0D9488;
    line-height: 1;
    margin-bottom: 0.2rem;
}
.tt-stat-label {
    font-size: 0.72rem;
    color: #94A3B8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.tt-agent-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin: 1rem 0 1.5rem 0;
}
.tt-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.tt-card-icon {
    font-size: 1.6rem;
    display: block;
    margin-bottom: 0.6rem;
}
.tt-card-name {
    font-size: 1rem;
    font-weight: 700;
    color: #1E293B;
    margin-bottom: 0.2rem;
}
.tt-card-role {
    font-size: 0.72rem;
    color: #0D9488;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}
.tt-card-desc {
    font-size: 0.85rem;
    color: #64748B;
    line-height: 1.5;
}
.tt-divider {
    border: none;
    border-top: 1px solid #E2E8F0;
    margin: 2rem 0;
}
.tt-positioning {
    font-size: 0.95rem;
    color: #475569;
    padding: 1rem 1.5rem;
    border-left: 3px solid #0D9488;
    background: #F0FDFA;
    border-radius: 0 8px 8px 0;
    margin: 1.5rem 0;
}
</style>
""", unsafe_allow_html=True)


# ── Constants ──────────────────────────────────────────────────────────────────

GITHUB_URL = "https://github.com/Natt1111/toothtrust"

CASES: dict[str, dict] = {
    "case_01": {
        "id": "case_01",
        "title": "Crown vs. Composite",
        "subtitle": "Tooth #19 · Occlusal Caries",
        "savings_label": "$1,180 savings",
        "agent_label": "AuditAgent",
        "dir": ROOT / "data/mock_cases/case_01_crown_vs_composite",
        "kind": "audit",
        "has_tc": False,
        "savings": 1180,
        "icon": "🦷",
    },
    "case_02": {
        "id": "case_02",
        "title": "Endo vs. Extraction",
        "subtitle": "Tooth #8 · Anterior Pain",
        "savings_label": "$2,700 savings",
        "agent_label": "AuditAgent + TreatmentCoordinatorAgent",
        "dir": ROOT / "data/mock_cases/case_02_endo_vs_extraction",
        "kind": "audit",
        "has_tc": True,
        "savings": 2700,
        "icon": "🔬",
    },
    "case_03": {
        "id": "case_03",
        "title": "PerioVoice — Hands-Free Charting",
        "subtitle": "6-tooth exam · AAP 2017 Staging",
        "savings_label": "Stage III · Grade B",
        "agent_label": "PerioChartAgent",
        "dir": ROOT / "data/mock_cases/case_03_perio_voice",
        "kind": "perio",
        "has_tc": False,
        "icon": "🎙️",
    },
    "case_04": {
        "id": "case_04",
        "title": "Lab Case Risk Scanner",
        "subtitle": "Front Desk + Office Manager",
        "savings_label": "Prevents lost appointments",
        "agent_label": "LabCaseAgent",
        "dir": ROOT / "data/mock_cases/case_04_lab_case_risk",
        "kind": "lab_case",
        "has_tc": False,
        "icon": "🗓️",
    },
}

V1_AGENTS = [
    {
        "name": "ChartAgent",
        "user": "Dental Assistant",
        "job": "Converts voice utterances into structured Dentrix chart entries with CDT codes.",
        "example": '"Chart MOD composite on tooth 14"',
        "icon": "📋",
    },
    {
        "name": "AuditAgent",
        "user": "Dentist / Patient",
        "job": "Audits proposed treatment plans against ADA guidelines and clinical evidence.",
        "example": '"Is this crown justified for a 30% lesion?"',
        "icon": "🔍",
    },
    {
        "name": "ResearchAgent",
        "user": "Any clinical staff",
        "job": "Answers chairside clinical questions via RAG retrieval from the evidence corpus.",
        "example": '"Bisphosphonate contraindications before extraction?"',
        "icon": "📚",
    },
    {
        "name": "DocumentationAgent",
        "user": "Dentist",
        "job": "Drafts SOAP notes from voice input, queues for review and explicit voice sign-off.",
        "example": '"Draft the note" → review → "Sign it"',
        "icon": "📝",
    },
    {
        "name": "TreatmentCoordinatorAgent",
        "user": "Treatment Coordinator",
        "job": "Converts audit results into plain-language patient conversation scripts.",
        "example": '"Explain this plan to the patient"',
        "icon": "💬",
    },
    {
        "name": "PerioChartAgent",
        "user": "Hygienist",
        "job": "Transcribes voice probe calls into a structured chart with AAP 2017 staging.",
        "example": '"Tooth 3 distobuccal 4 buccal 3 mesiobuccal 5 bleeding"',
        "icon": "🩺",
    },
    {
        "name": "LabCaseAgent",
        "user": "Front Desk / Office Manager",
        "job": "Proactively scans tomorrow's lab cases, surfaces at-risk appointments, identifies handoff gaps. Complementary to Dentrix Lab Case Manager.",
        "example": '"Scan tomorrow\'s lab cases"',
        "icon": "🗓️",
    },
]

CORPUS_CATEGORIES = [
    ("Restorative & Caries", [
        "crown_indications_ada.md", "composite_vs_crown_decision_criteria.md",
        "caries_classification_icdas.md", "amalgam_to_composite_replacement.md",
        "caries_risk_assessment_cambra.md", "minimally_invasive_dentistry_principles.md",
        "pulp_capping_indirect_direct.md",
    ]),
    ("Endodontics", [
        "aae_retreatment_position_statement.md", "aae_glossary_endodontic_terms.md",
        "apical_periodontitis_diagnosis.md", "endo_vs_extraction_decision_framework.md",
        "endodontic_success_rates_literature.md", "root_canal_outcomes_meta_analysis.md",
        "post_and_core_indications.md",
    ]),
    ("Periodontics", [
        "aap_2017_classification_system.md", "gingivitis_vs_periodontitis_diagnosis.md",
        "bone_loss_radiographic_interpretation.md", "maintenance_therapy_protocols.md",
        "periodontal_charting_requirements.md", "srp_medical_necessity_criteria.md",
    ]),
    ("Imaging & Diagnosis", [
        "bitewing_radiograph_interpretation.md", "periapical_radiograph_interpretation.md",
        "common_radiographic_findings_pathology.md", "cbct_indications_guidelines.md",
    ]),
    ("Insurance & Billing", [
        "cdt_code_reference_common_procedures.md", "dental_insurance_medical_necessity_overview.md",
        "common_denial_reasons_appeals.md", "documentation_standards_clinical_notes.md",
        "pre_authorization_requirements.md",
    ]),
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _api_key_present() -> bool:
    key = _get_secret("ANTHROPIC_API_KEY")
    return bool(key and key != "dummy")


_MAX_LIVE_CALLS_PER_SESSION = 15


def _require_access_gate() -> bool:
    """Gate live (billed) API usage behind APP_ACCESS_CODE, if one is configured.

    No-op (always True) when APP_ACCESS_CODE is unset, so local dev is unaffected.
    Sample Data Mode never calls this — it stays open regardless of the gate.
    """
    code = _get_secret("APP_ACCESS_CODE")
    if not code:
        return True
    if st.session_state.get("access_granted"):
        return True
    st.info("🔒 This runs a live, billed AI pipeline. Enter the access code to continue.")
    entered = st.text_input("Access code", type="password", key="access_code_input")
    if st.button("Unlock", key="access_code_submit"):
        if entered == code:
            st.session_state["access_granted"] = True
            st.rerun()
        else:
            st.error("Incorrect access code.")
    return False


def _live_ready() -> bool:
    """True if the live pipeline may run right now (key present + access gate cleared)."""
    return _api_key_present() and _require_access_gate()


def _consume_live_call_budget() -> bool:
    """Per-session cap on live API calls, to protect against runaway cost. Call once per actual call."""
    count = st.session_state.get("live_call_count", 0)
    if count >= _MAX_LIVE_CALLS_PER_SESSION:
        st.error(
            f"Session limit reached ({_MAX_LIVE_CALLS_PER_SESSION} live calls). "
            "Refresh the page to start a new session."
        )
        return False
    st.session_state["live_call_count"] = count + 1
    return True


def _verdict_badge(verdict: str) -> str:
    styles: dict[str, tuple[str, str]] = {
        "unsupported":           ("#DC2626", "⚠ Not Supported"),
        "partially_supported":   ("#D97706", "⚡ Partially Supported"),
        "supported":             ("#059669", "✓ Supported"),
        "insufficient_evidence": ("#6B7280", "? Insufficient Evidence"),
        "error":                 ("#6B7280", "⚠ Parse Error"),
    }
    bg, label = styles.get(verdict, ("#6B7280", verdict.replace("_", " ").title()))
    return (
        f'<span style="background:{bg};color:white;padding:5px 16px;'
        f'border-radius:16px;font-size:0.9em;font-weight:600;">{label}</span>'
    )


def _pill(text: str, bg: str = "#2563EB") -> str:
    return (
        f'<span style="background:{bg};color:white;padding:3px 12px;'
        f'border-radius:12px;font-size:0.82em;font-weight:600;">{text}</span>'
    )


def _savings_pill(amount: int) -> str:
    return _pill(f"${amount:,} savings", "#059669")


def _load_case_files(cfg: dict) -> dict | None:
    d = cfg["dir"]
    if not d.exists():
        st.error(f"Case directory not found: {d}")
        return None
    files: dict = {}
    try:
        files["case"] = json.loads((d / "case.json").read_text())
    except Exception as exc:
        st.error(f"Could not read case.json: {exc}")
        return None
    for name, filename in [
        ("xray", "xray_description.md"),
        ("transcript", "voice_transcript.txt"),
    ]:
        p = d / filename
        if p.exists():
            files[name] = p.read_text()
    for name, filename in [
        ("plan", "treatment_plan.json"),
        ("expected_audit", "expected_audit.json"),
        ("expected_chart", "expected_chart.json"),
    ]:
        p = d / filename
        if p.exists():
            try:
                files[name] = json.loads(p.read_text())
            except Exception:
                pass
    return files


# ── Overview page ──────────────────────────────────────────────────────────────

def page_overview() -> None:
    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("&nbsp;")
    st.markdown(
        '<div class="tt-hero-headline">One voice. Every role. Better care.</div>'
        '<div class="tt-hero-sub">Voice-first multi-agent AI for the dental office.</div>',
        unsafe_allow_html=True,
    )

    # ── Stat blocks ───────────────────────────────────────────────────────────
    s1, s2, s3, s4 = st.columns(4)
    for col, (num, label) in zip(
        [s1, s2, s3, s4],
        [("7", "Specialized Agents"), ("115", "Tests Passing"),
         ("30", "Evidence Documents"), ("4", "Case Studies")],
    ):
        with col:
            st.markdown(
                f'<div class="tt-stat-number">{num}</div>'
                f'<div class="tt-stat-label">{label}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<hr class="tt-divider">', unsafe_allow_html=True)

    # ── Problem + links ───────────────────────────────────────────────────────
    col_problem, col_links = st.columns([3, 1])
    with col_problem:
        st.markdown(
            "**Every dental staff member is always busy with their hands.** "
            "Gloves, instruments, patient contact. Every time someone needs to look something up, "
            "chart a finding, explain a procedure, or document a visit — they have to stop. "
            "That friction compounds across 20+ patients a day per provider.\n\n"
            "ToothTrust removes it through a single voice layer with **seven specialized AI agents** — "
            "one for every role in the dental office. Each agent does one job well, hands-free, "
            "in real time, grounded in 30 peer-reviewed evidence documents."
        )
    with col_links:
        st.markdown("&nbsp;")
        st.link_button("View on GitHub", GITHUB_URL)

    # ── Positioning ───────────────────────────────────────────────────────────
    st.markdown(
        '<div class="tt-positioning">'
        "Complementary to diagnostic AI like Pearl, Overjet, and VideaHealth — "
        "ToothTrust handles the workflow layer: charting, auditing, documentation, "
        "patient scripts, and lab case operations."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("&nbsp;")
    st.markdown("#### Where ToothTrust fits vs. imaging AI")
    st.markdown(
        "| | **ToothTrust** | Pearl / Overjet / VideaHealth |\n"
        "|---|---|---|\n"
        "| **Problem solved** | Clinical workflow — charting, auditing, documentation, patient communication | Diagnostic imaging — pathology detection in X-rays |\n"
        "| **Primary input** | Voice, hands-free, chairside | Radiograph images |\n"
        "| **Primary output** | Structured chart entries, treatment audits, patient scripts, SOAP notes | Annotated findings, detected pathology |\n"
        "| **Workflow stage** | *After* the finding — what staff do with it | *At* the finding — surfacing what's in the image |\n"
        "| **Interaction model** | Real-time, hands-free voice | Screen review, asynchronous |\n"
    )
    st.caption("Not a replacement for imaging AI — the two integrate: a Pearl/Overjet/VideaHealth finding becomes a ToothTrust chart entry, audit, and patient script.")

    st.markdown('<hr class="tt-divider">', unsafe_allow_html=True)

    # ── Agent grid ────────────────────────────────────────────────────────────
    st.markdown("### The 7-Agent Platform")
    st.caption("All agents deployed, tested, and integrated with the voice orchestration layer.")
    st.markdown("&nbsp;")

    cards_html = '<div class="tt-agent-grid">'
    for agent in V1_AGENTS:
        cards_html += (
            f'<div class="tt-card">'
            f'<span class="tt-card-icon">{agent["icon"]}</span>'
            f'<div class="tt-card-name">{agent["name"]}</div>'
            f'<div class="tt-card-role">{agent["user"]}</div>'
            f'<div class="tt-card-desc">{agent["job"]}</div>'
            f'</div>'
        )
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown('<hr class="tt-divider">', unsafe_allow_html=True)
    st.caption(
        "Clinical decision support — final treatment decisions "
        "remain with the licensed provider."
    )


# ── Demo runner page ───────────────────────────────────────────────────────────

def page_demo() -> None:
    st.markdown("## 🦷 Case Studies")
    st.markdown(
        "Pre-loaded with real clinical data. "
        "Click a case card, then hit **Run** to call the live AI pipeline."
    )

    if not _api_key_present():
        st.warning(
            "**Sample Data Mode** — no Anthropic API key detected. "
            "Results shown are pre-validated outputs from `expected_audit.json`, `expected_chart.json`, "
            "and `expected_scan_output.json`. "
            "Add `ANTHROPIC_API_KEY` to `.env` to run the live pipeline."
        )

    st.markdown("---")

    # ── Case selector cards ────────────────────────────────────────────────────
    sel_cols = st.columns(4, gap="medium")
    for col, (case_id, cfg) in zip(sel_cols, CASES.items()):
        with col:
            is_selected = st.session_state.get("selected_case") == case_id
            border_style = "border: 2px solid #2563EB;" if is_selected else ""
            with st.container(border=True):
                st.markdown(f"### {cfg['icon']} {cfg['title']}")
                st.caption(cfg["subtitle"])
                pill_color = {"audit": "#059669", "perio": "#2563EB", "lab_case": "#7C3AED"}.get(cfg["kind"], "#2563EB")
                st.markdown(_pill(cfg["savings_label"], pill_color), unsafe_allow_html=True)
                st.markdown("&nbsp;")
                st.caption(f"Agents: *{cfg['agent_label']}*")
                if st.button(
                    "✓ Selected" if is_selected else "Load Case",
                    key=f"sel_{case_id}",
                    type="primary" if is_selected else "secondary",
                ):
                    if not is_selected:
                        st.session_state.selected_case = case_id
                        st.session_state.pop(f"result_{case_id}", None)
                        st.session_state.pop(f"tc_{case_id}", None)
                    st.rerun()

    # ── Case detail ────────────────────────────────────────────────────────────
    selected = st.session_state.get("selected_case")
    if not selected:
        st.markdown("---")
        st.info("👆 Select a case above to load its clinical data and run the pipeline.")
        return

    cfg = CASES[selected]
    files = _load_case_files(cfg)
    if files is None:
        return

    st.markdown("---")
    st.markdown(f"## {cfg['icon']} Case: {cfg['title']}")

    if cfg["kind"] == "audit":
        _run_audit_case(selected, cfg, files)
    elif cfg["kind"] == "lab_case":
        _run_lab_case_case(selected, cfg, files)
    else:
        _run_perio_case(selected, cfg, files)


def _run_audit_case(case_id: str, cfg: dict, files: dict) -> None:
    import pandas as pd

    case = files["case"]
    patient = case.get("patient", {})

    # Context + X-ray
    ctx_col, xray_col = st.columns(2, gap="medium")
    with ctx_col:
        with st.container(border=True):
            st.markdown("#### 📋 Patient Context")
            st.markdown(
                f"**Age:** {patient.get('age', '?')}  \n"
                f"**Chief complaint:** {patient.get('chief_complaint', '—')}  \n"
                f"**Medical history:** {patient.get('medical_history', 'None documented')}"
            )
    with xray_col:
        if files.get("xray"):
            with st.container(border=True):
                st.markdown("#### 🩻 X-Ray Findings")
                xray_text = "\n".join(
                    ln for ln in files["xray"].splitlines() if not ln.startswith("#")
                ).strip()
                st.markdown(xray_text)

    st.markdown("&nbsp;")

    # Treatment plan table
    plan = files.get("plan", [])
    if plan:
        with st.container(border=True):
            st.markdown("#### 💰 Proposed Treatment Plan")
            df = pd.DataFrame([{
                "CDT Code": p.get("cdt_code", "—"),
                "Description": p.get("description", "—"),
                "Tooth #": p.get("tooth", "—"),
                "Fee": f"${p.get('fee', 0):,}" if p.get("fee") else "—",
                "Notes": p.get("notes", ""),
            } for p in plan])
            st.dataframe(df, hide_index=True, use_container_width=True)
            total = sum(p.get("fee", 0) for p in plan if p.get("fee"))
            if total:
                st.markdown(f"**Proposed total: ${total:,}**")

    st.markdown("&nbsp;")

    # Run / clear buttons
    cache_key = f"result_{case_id}"
    cached = st.session_state.get(cache_key)

    if cached is None:
        if _api_key_present() and not _require_access_gate():
            pass  # gate prompt rendered above; wait for the user to unlock
        else:
            label = "▶ Run Audit" if _api_key_present() else "▶ Show Pre-Computed Result"
            if st.button(label, type="primary", key=f"run_{case_id}"):
                if _api_key_present():
                    _execute_audit(case_id, cfg, patient, files, cache_key)
                else:
                    st.session_state[cache_key] = {
                        "source": "offline",
                        "data": files.get("expected_audit", {}),
                    }
                    st.rerun()
    else:
        if st.button("↺ Clear & Re-run", key=f"clear_{case_id}"):
            st.session_state.pop(cache_key, None)
            st.session_state.pop(f"tc_{case_id}", None)
            st.rerun()
        _render_audit_result(case_id, cfg, cached)


def _execute_audit(case_id: str, cfg: dict, patient: dict, files: dict, cache_key: str) -> None:
    if not _consume_live_call_budget():
        return
    with st.spinner("AuditAgent — retrieving evidence + calling Claude…"):
        try:
            from src.agents.audit_agent import AuditAgent
            agent = AuditAgent()
            ctx = (
                f"Age: {patient.get('age', '?')}. "
                f"Chief complaint: {patient.get('chief_complaint', '')}. "
                f"Medical history: {patient.get('medical_history', '')}."
            )
            if files.get("xray"):
                ctx += f"\n\nX-ray findings:\n{files['xray']}"
            res = agent.run(
                utterance="Audit this treatment plan",
                treatment_plan=files.get("plan", []),
                patient_context=ctx,
            )
            # Flatten AuditResult dataclass to dict for session_state serialisation
            from dataclasses import asdict
            ar = res.get("audit_result")
            if ar is not None and not isinstance(ar, dict):
                try:
                    res["audit_result"] = asdict(ar)
                except Exception:
                    res["audit_result"] = {}
            st.session_state[cache_key] = {"source": "live", "data": res}
            st.rerun()
        except Exception as exc:
            print(f"[AuditAgent error] {exc!r}")
            st.error("AuditAgent ran into a problem processing that request. Please try again.")


def _render_audit_result(case_id: str, cfg: dict, cached: dict) -> None:
    source = cached["source"]
    data = cached["data"]

    st.markdown("---")
    st.markdown("### Audit Result")

    if source == "offline":
        _render_offline_audit(cfg, data)
        return

    overall = data.get("overall", "")
    confidence = data.get("confidence", "")
    ar: dict = data.get("audit_result") or {}

    # Verdict row
    v_col, c_col, s_col = st.columns([2, 1, 2])
    with v_col:
        st.markdown(_verdict_badge(overall), unsafe_allow_html=True)
    with c_col:
        conf_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence, "⚪")
        st.markdown(f"**Confidence:** {conf_emoji} {confidence}")
    with s_col:
        rec = ar.get("recommended_alternative") or {}
        if rec.get("cdt_code") and cfg.get("savings"):
            st.markdown(_savings_pill(cfg["savings"]), unsafe_allow_html=True)

    st.markdown("&nbsp;")

    # Patient summary
    summary = ar.get("patient_summary", "")
    if summary:
        st.info(f"**Plain-language patient summary:**\n\n{summary}")

    # Recommended alternative
    if rec.get("cdt_code"):
        with st.container(border=True):
            st.markdown("#### 💡 Recommended Alternative")
            ra_col, rb_col = st.columns([1, 2])
            with ra_col:
                st.metric("CDT Code", rec["cdt_code"])
                if rec.get("estimated_fee"):
                    st.metric("Estimated Fee", f"${rec['estimated_fee']:,}")
                if cfg.get("savings"):
                    st.metric("Patient Savings", f"${cfg['savings']:,}")
            with rb_col:
                st.markdown(f"**{rec.get('description', '')}**")
                st.markdown(rec.get("rationale", ""))

    # Per-procedure verdicts
    procedures = ar.get("procedures", [])
    if procedures:
        st.markdown("#### Procedure-by-Procedure Review")
        for proc in procedures:
            verdict = proc.get("verdict", "")
            badge_label = {
                "unsupported": "⚠ Not Supported",
                "partially_supported": "⚡ Partial",
                "supported": "✓ Supported",
            }.get(verdict, verdict.replace("_", " ").title())
            label = f"{proc.get('description', 'Procedure')} [{proc.get('cdt_code', '')}]  —  {badge_label}"
            with st.expander(label):
                st.markdown(_verdict_badge(verdict), unsafe_allow_html=True)
                st.markdown("&nbsp;")
                st.markdown(proc.get("rationale", ""))
                flags = proc.get("flags", [])
                if flags:
                    st.markdown("**Clinical Flags**")
                    for flag in flags:
                        st.markdown(f"- {flag}")
                cites = proc.get("citations", [])
                if cites:
                    st.markdown("**Cited Evidence**")
                    for cite in cites:
                        st.markdown(f"- 📄 `{cite}`")

    # Missing information
    missing = ar.get("missing_information", [])
    if missing:
        with st.expander("What would improve audit confidence"):
            for item in missing:
                st.markdown(f"- {item}")

    # TC Script section for Case 2
    if cfg.get("has_tc"):
        _tc_section(case_id, data)


def _render_offline_audit(cfg: dict, expected: dict) -> None:
    st.info("Showing pre-validated result (Sample Data Mode).")
    verdict_raw = expected.get("verdict", "")
    verdict_map = {
        "LIKELY OVERTREATMENT": "unsupported",
        "QUESTIONABLE — MISSING OPTION": "partially_supported",
    }
    v_key = verdict_map.get(verdict_raw.upper(), "insufficient_evidence")
    st.markdown(_verdict_badge(v_key), unsafe_allow_html=True)
    st.markdown("&nbsp;")
    if expected.get("summary"):
        st.info(expected["summary"])
    rec = expected.get("recommended_alternative", {})
    if rec:
        with st.container(border=True):
            st.markdown("#### 💡 Recommended Alternative")
            st.markdown(f"**{rec.get('cdt_code')}** — {rec.get('description', '')}")
            if cfg.get("savings"):
                st.metric("Patient savings", f"${cfg['savings']:,}")
    cites = expected.get("citations", [])
    if cites:
        st.markdown("**Cited Evidence**")
        for c in cites:
            st.markdown(f"- 📄 `{c}`")


def _tc_section(case_id: str, audit_data: dict) -> None:
    st.markdown("---")
    st.markdown("### 💬 Treatment Coordinator Script")
    st.caption("Plain-language patient conversation guide — generated by TreatmentCoordinatorAgent.")

    tc_key = f"tc_{case_id}"
    tc_cached = st.session_state.get(tc_key)

    if tc_cached is None:
        if _api_key_present() and not _require_access_gate():
            pass  # gate prompt rendered above; wait for the user to unlock
        elif st.button("▶ Generate Patient Script", key=f"run_tc_{case_id}"):
            if _api_key_present():
                if not _consume_live_call_budget():
                    return
                with st.spinner("TreatmentCoordinatorAgent — drafting patient script…"):
                    try:
                        from src.agents.treatment_coordinator_agent import TreatmentCoordinatorAgent
                        agent = TreatmentCoordinatorAgent()
                        ar = audit_data.get("audit_result") or {}
                        res = agent.run(audit_result=ar, patient_name="Patient")
                        st.session_state[tc_key] = res
                        st.rerun()
                    except Exception as exc:
                        print(f"[TreatmentCoordinatorAgent error] {exc!r}")
                        st.error("TreatmentCoordinatorAgent ran into a problem processing that request. Please try again.")
            else:
                st.info("Live API required to generate the TC script. Run in online mode.")
    else:
        _render_tc_script(tc_cached)


def _render_tc_script(tc_result: dict) -> None:
    script = tc_result.get("script") or {}
    if not isinstance(script, dict) or not script.get("options"):
        st.warning("TC script unavailable — run the live audit first.")
        return

    opening = script.get("opening", "")
    if opening:
        st.markdown(f"> {opening}")
    st.markdown("&nbsp;")

    options = script.get("options", [])
    if options:
        opt_cols = st.columns(len(options), gap="medium")
        for col, opt in zip(opt_cols, options):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{opt.get('label', 'Option')}**")
                    st.markdown(opt.get("plain_language", ""))
                    st.markdown("---")
                    st.caption(f"**Typical outcome:** {opt.get('typical_outcome', '')}")
                    st.caption(f"**Worst case:** {opt.get('worst_case', '')}")
                    st.caption(f"**Timeline:** {opt.get('timeline', '')}")
                    cost = opt.get("estimated_cost")
                    if cost:
                        st.metric("Estimated cost", f"${cost:,}")

    rec_framing = script.get("recommendation_framing", "")
    if rec_framing:
        st.markdown("**Recommendation framing for the TC:**")
        st.markdown(f"> {rec_framing}")

    doc_note = script.get("documentation_note", "")
    if doc_note:
        with st.expander("📋 Documentation note for chart"):
            st.markdown(doc_note)

    fqs = script.get("follow_up_questions_to_anticipate", [])
    if fqs:
        with st.expander(f"Anticipated patient questions ({len(fqs)})"):
            for q in fqs:
                st.markdown(f"- {q}")


def _run_perio_case(case_id: str, cfg: dict, files: dict) -> None:
    import pandas as pd

    case = files["case"]
    patient = case.get("patient", {})

    ctx_col, tx_col = st.columns([1, 2], gap="medium")
    with ctx_col:
        with st.container(border=True):
            st.markdown("#### 📋 Patient Context")
            st.markdown(
                f"**Age:** {patient.get('age', '?')}  \n"
                f"**Visit type:** {patient.get('chief_complaint', '—')}  \n"
                f"**Perio history:** {patient.get('medical_history', '—')}"
            )
    with tx_col:
        transcript = files.get("transcript", "")
        if transcript:
            with st.container(border=True):
                st.markdown("#### 🎙️ Hygienist Voice Transcript")
                st.caption("Each line = one tooth. Simulated probe call as spoken to the assistant.")
                for line in transcript.strip().splitlines():
                    if line.strip():
                        st.code(line.strip(), language=None)

    st.markdown("&nbsp;")

    cache_key = f"result_{case_id}"
    cached = st.session_state.get(cache_key)

    if cached is None:
        if _api_key_present() and not _require_access_gate():
            pass  # gate prompt rendered above; wait for the user to unlock
        else:
            label = "▶ Run PerioChart" if _api_key_present() else "▶ Show Pre-Computed Result"
            if st.button(label, type="primary", key=f"run_{case_id}"):
                if _api_key_present():
                    if not _consume_live_call_budget():
                        return
                    with st.spinner("PerioChartAgent — parsing transcript + computing AAP stage…"):
                        try:
                            from src.agents.perio_chart_agent import PerioChartAgent
                            agent = PerioChartAgent()
                            res = agent.run(
                                transcript=transcript,
                                corpus_citations=case.get("corpus_sources", []),
                            )
                            st.session_state[cache_key] = {"source": "live", "data": res}
                            st.rerun()
                        except Exception as exc:
                            print(f"[PerioChartAgent error] {exc!r}")
                            st.error("PerioChartAgent ran into a problem processing that request. Please try again.")
                else:
                    st.session_state[cache_key] = {
                        "source": "offline",
                        "data": files.get("expected_chart", {}),
                    }
                    st.rerun()
    else:
        if st.button("↺ Clear & Re-run", key=f"clear_{case_id}"):
            st.session_state.pop(cache_key, None)
            st.rerun()
        _render_perio_result(cached)


def _render_perio_result(cached: dict) -> None:
    import pandas as pd

    source = cached["source"]
    data = cached["data"]

    if source == "offline":
        st.info("Showing pre-validated result (Sample Data Mode).")
        summary = data.get("summary", {})
        teeth = data.get("teeth", [])
    else:
        chart = data.get("chart") or {}
        summary = chart.get("summary", {})
        teeth = chart.get("teeth", [])

    st.markdown("---")
    st.markdown("### PerioChart Result")

    # AAP Stage badge
    stage = summary.get("aap_stage", "")
    grade = summary.get("aap_grade", "")
    if stage:
        st.markdown(
            _pill(f"AAP {stage}  ·  {grade}", "#2563EB"),
            unsafe_allow_html=True,
        )
        st.markdown("&nbsp;")

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Teeth charted", summary.get("teeth_charted", "—"))
    m2.metric("Worst pocket", f"{summary.get('worst_cal', '—')} mm")
    m3.metric("BOP%", f"{summary.get('bop_percent', '—')}%")
    m4.metric("Total sites", summary.get("total_sites", "—"))
    st.markdown("&nbsp;")

    # Per-tooth table
    if teeth:
        rows = []
        for t in teeth:
            sites = t.get("sites", {})
            bop = ", ".join(t.get("bleeding_sites", [])) or "—"
            rows.append({
                "Tooth": t["tooth"],
                "DB": sites.get("distobuccal", ""),
                "B":  sites.get("buccal", ""),
                "MB": sites.get("mesiobuccal", ""),
                "DL": sites.get("distolingual", ""),
                "L":  sites.get("lingual", ""),
                "ML": sites.get("mesiolingual", ""),
                "Worst": t.get("worst_depth", ""),
                "CAL": t.get("cal_proxy", ""),
                "Bleeding sites": bop,
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Recommendations
    recs = summary.get("recommended_next_steps", "")
    if recs:
        with st.container(border=True):
            st.markdown("#### 📋 Recommended Next Steps")
            st.markdown(recs)

    # Staging rationale
    rationale = summary.get("staging_rationale", "")
    if rationale:
        with st.expander("Staging rationale (AAP 2017)"):
            st.markdown(rationale)
            st.markdown(f"*Grading rationale:* {summary.get('grading_rationale', '')}")


# ── Lab Case demo page ────────────────────────────────────────────────────────

def _run_lab_case_case(case_id: str, cfg: dict, files: dict) -> None:
    import pandas as pd
    import json as _json

    st.markdown("#### 🗓️ Tomorrow's Schedule — May 22, 2026")
    st.caption("Simulated 7am morning scan. Diana (Front Desk Coordinator) checks lab case readiness before the day starts.")

    # Load appointments for display
    apts_path = ROOT / "data/mock_data/appointments.json"
    try:
        apts = _json.loads(apts_path.read_text())["appointments"]
        df = pd.DataFrame([{
            "Time": a["time"],
            "Patient": a["patient_name"],
            "Procedure": a["procedure_name"],
            "Code": a["procedure_code"],
            "Lab Case?": "✓" if a["requires_lab_case"] else "—",
        } for a in apts])
        st.dataframe(df, hide_index=True, use_container_width=True)
    except Exception as exc:
        st.error(f"Could not load appointments: {exc}")
        return

    st.markdown("&nbsp;")

    cache_key = f"result_{case_id}"
    cached = st.session_state.get(cache_key)

    if cached is None:
        if _api_key_present() and not _require_access_gate():
            pass  # gate prompt rendered above; wait for the user to unlock
        else:
            label = "▶ Run Lab Case Scan" if _api_key_present() else "▶ Show Pre-Computed Result"
            if st.button(label, type="primary", key=f"run_{case_id}"):
                if _api_key_present():
                    if not _consume_live_call_budget():
                        return
                    with st.spinner("LabCaseAgent — cross-referencing appointments with lab case statuses…"):
                        try:
                            from src.agents.lab_case_agent import LabCaseAgent
                            agent = LabCaseAgent()
                            result = agent.scan_tomorrows_appointments()
                            st.session_state[cache_key] = result
                            st.rerun()
                        except Exception as exc:
                            print(f"[LabCaseAgent error] {exc!r}")
                            st.error("LabCaseAgent ran into a problem processing that request. Please try again.")
                else:
                    import json as _json2
                    scan_path = cfg["dir"] / "expected_scan_output.json"
                    try:
                        st.session_state[cache_key] = _json2.loads(scan_path.read_text())
                    except Exception as exc:
                        st.error(f"Could not load expected_scan_output.json: {exc}")
                    st.rerun()
    else:
        if st.button("↺ Clear & Re-run", key=f"clear_{case_id}"):
            st.session_state.pop(cache_key, None)
            for k in list(st.session_state.keys()):
                if k.startswith(f"attr_{case_id}_") or k.startswith(f"resched_{case_id}_"):
                    st.session_state.pop(k, None)
            st.rerun()
        _render_lab_case_result(case_id, cached)


def _render_lab_case_result(case_id: str, scan: dict) -> None:
    import pandas as pd

    st.markdown("---")
    st.markdown("### Lab Case Scan Result")

    summary = scan.get("summary", {})

    # 4 metric cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("✅ On Track", summary.get("on_track", 0))
    m2.metric("⚡ At Risk", summary.get("at_risk", 0))
    m3.metric("🚨 Critical", summary.get("critical_missing", 0))
    m4.metric("— No Case Needed", summary.get("no_case_required", 0))

    st.markdown("&nbsp;")

    # Voice summary callout
    voice = scan.get("voice_summary", "")
    if voice:
        critical_count = summary.get("critical_missing", 0)
        if critical_count > 0:
            st.error(f"🔊 **Voice readback:** {voice}")
        elif summary.get("at_risk", 0) > 0:
            st.warning(f"🔊 **Voice readback:** {voice}")
        else:
            st.success(f"🔊 **Voice readback:** {voice}")

    st.markdown("&nbsp;")

    # Color-coded appointment list
    _RISK_COLORS = {
        "on_track":        ("#059669", "✅ On Track"),
        "at_risk":         ("#D97706", "⚡ At Risk"),
        "critical_missing":("#DC2626", "🚨 Critical"),
        "no_case_required":("#6B7280", "— No Case"),
    }

    # Compute the reschedule gate once (not per-row) — _live_ready() renders a
    # password widget with a fixed key, which would collide if called per row.
    has_critical = any(
        a.get("risk_level") == "critical_missing" and a.get("lab_case_id")
        for a in scan.get("appointments", [])
    )
    reschedule_live_ok = _live_ready() if has_critical else False

    for apt in scan.get("appointments", []):
        risk = apt.get("risk_level", "")
        color, label = _RISK_COLORS.get(risk, ("#6B7280", risk))
        badge = (
            f'<span style="background:{color};color:white;padding:2px 10px;'
            f'border-radius:10px;font-size:0.8em;font-weight:600;">{label}</span>'
        )
        with st.container(border=True):
            row_l, row_r = st.columns([3, 2])
            with row_l:
                st.markdown(
                    f"**{apt['time']}** — {apt['patient_name']}  \n"
                    f"{apt['procedure']} `{apt['procedure_code']}`"
                )
                st.markdown(badge, unsafe_allow_html=True)
            with row_r:
                action = apt.get("recommended_action", "")
                if action:
                    st.caption(action)

            # Attribution + Reschedule for critical cases
            if risk == "critical_missing" and apt.get("lab_case_id"):
                lc_id = apt["lab_case_id"]
                patient = apt["patient_name"]

                attr_key   = f"attr_{case_id}_{lc_id}"
                resched_key = f"resched_{case_id}_{lc_id}"

                acol, rcol = st.columns(2)
                with acol:
                    if st.button(f"🔍 Where did it fall through?", key=f"attr_btn_{case_id}_{lc_id}"):
                        try:
                            from src.agents.lab_case_agent import LabCaseAgent
                            result = LabCaseAgent().attribution_check(lc_id)
                            st.session_state[attr_key] = result
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Attribution error: {exc}")

                with rcol:
                    if reschedule_live_ok:
                        if st.button(f"✉️ Draft Reschedule", key=f"resched_btn_{case_id}_{lc_id}"):
                            if _consume_live_call_budget():
                                with st.spinner("Drafting reschedule message…"):
                                    try:
                                        from src.agents.lab_case_agent import LabCaseAgent
                                        drafts = LabCaseAgent().recommend_reschedules()
                                        st.session_state[resched_key] = drafts
                                        st.rerun()
                                    except Exception as exc:
                                        print(f"[LabCaseAgent reschedule error] {exc!r}")
                                        st.error("Couldn't draft the reschedule message. Please try again.")

                if attr_key in st.session_state:
                    attr = st.session_state[attr_key]
                    with st.expander(f"📋 Attribution — {patient}", expanded=True):
                        steps = attr.get("handoff_history", [])
                        broken = attr.get("broken_step")
                        step_order = ["created", "sent_to_lab", "lab_received",
                                      "lab_in_progress", "lab_shipped", "office_received"]
                        completed = {h["step"] for h in steps}
                        for step in step_order:
                            if step in completed:
                                h = next(s for s in steps if s["step"] == step)
                                st.markdown(
                                    f"✅ **{step.replace('_', ' ').title()}** — "
                                    f"{h['timestamp'][:10]}  \n"
                                    f"<span style='color:#6B7280;font-size:0.85em'>{h['notes']}</span>",
                                    unsafe_allow_html=True,
                                )
                            elif step == broken:
                                st.markdown(
                                    f"❌ **{step.replace('_', ' ').title()}** — *missing*  \n"
                                    f"<span style='color:#DC2626;font-size:0.85em'>"
                                    f"{attr.get('suggested_fix', '')}</span>",
                                    unsafe_allow_html=True,
                                )
                                break
                            else:
                                st.markdown(f"⬜ {step.replace('_', ' ').title()}")
                        st.caption(attr.get("framing_note", ""))

                if resched_key in st.session_state:
                    drafts_result = st.session_state[resched_key]
                    for d in drafts_result.get("drafts", []):
                        if d["patient_name"] == patient:
                            with st.expander(f"✉️ Reschedule draft — {patient}", expanded=True):
                                st.text_area(
                                    "Copy-ready message",
                                    value=d["draft_message"],
                                    height=120,
                                    key=f"msg_{case_id}_{lc_id}",
                                )
                                st.caption(f"Suggested new date: {d['suggested_new_date']}")


# ── Voice Command page ──────────────────────────────────────────────────────────

def _voice_keys_present() -> bool:
    return bool(_get_secret("DEEPGRAM_API_KEY")) and bool(_get_secret("ELEVENLABS_API_KEY"))


@st.cache_resource(show_spinner=False)
def _get_stt():
    from src.voice.stt import SpeechToText
    return SpeechToText()


@st.cache_resource(show_spinner=False)
def _get_tts():
    from src.voice.tts import TextToSpeech
    return TextToSpeech()


@st.cache_resource(show_spinner=False)
def _get_orchestrator():
    from src.orchestrator import Orchestrator
    return Orchestrator()


def page_voice() -> None:
    st.markdown("## 🎙️ Voice Command")
    st.markdown(
        "Speak a command the way staff would chairside — hands-free, no menus. "
        "Routed live through the same 7-agent pipeline as Case Studies."
    )

    missing = [
        name for name, present in [
            ("ANTHROPIC_API_KEY", _api_key_present()),
            ("DEEPGRAM_API_KEY", bool(_get_secret("DEEPGRAM_API_KEY"))),
            ("ELEVENLABS_API_KEY", bool(_get_secret("ELEVENLABS_API_KEY"))),
        ] if not present
    ]
    if missing:
        st.warning(
            f"Voice Command needs live API keys ({', '.join(missing)} not configured). "
            "Voice is always a live pipeline — there's no sample-data fallback for it. "
            "Try Case Studies instead, or add these keys to enable voice."
        )
        return

    if not _require_access_gate():
        return

    with st.expander("💡 Example commands", expanded=not st.session_state.get("voice_history")):
        for agent in V1_AGENTS:
            st.markdown(f"**{agent['example']}** — routes to *{agent['name']}*")

    st.markdown("&nbsp;")
    audio = st.audio_input("Press to record your command")

    if audio is not None:
        audio_bytes = audio.getvalue()
        cur_hash = hash(audio_bytes)
        if cur_hash != st.session_state.get("voice_last_audio_hash"):
            st.session_state["voice_last_audio_hash"] = cur_hash
            _process_voice_command(audio_bytes)

    st.markdown("---")
    st.markdown("### Session Transcript")
    history = st.session_state.get("voice_history", [])
    if not history:
        st.caption("No commands yet — record one above to get started.")
    else:
        for turn in reversed(history):
            with st.container(border=True):
                st.markdown(f"**🗣️ You said:** {turn['transcript']}")
                st.markdown(f"**🤖 {turn['intent']}:** {turn['response']}")
                if turn.get("audio"):
                    st.audio(turn["audio"], format="audio/mp3")
                if turn.get("details"):
                    with st.expander("Details"):
                        st.json(turn["details"])


def _process_voice_command(audio_bytes: bytes) -> None:
    if not _consume_live_call_budget():
        return
    try:
        with st.spinner("Transcribing…"):
            transcript = _get_stt().transcribe_bytes(audio_bytes, mimetype="audio/wav")

        if not transcript.strip():
            st.warning("Didn't catch that — try recording again, closer to the mic.")
            return

        with st.spinner("Routing to agent…"):
            session_id = st.session_state.setdefault("voice_session_id", str(uuid.uuid4()))
            result = _get_orchestrator().route(session_id=session_id, utterance=transcript)

        response_text = str(result.get("response") or "I'm not sure how to handle that command.")
        intent_label = str(result.get("intent", "unknown")).replace("_", " ").title()

        tts_audio = None
        try:
            with st.spinner("Synthesizing voice reply…"):
                tts_audio = _get_tts().synthesize(response_text[:200])
        except Exception as exc:
            print(f"[TTS error] {exc!r}")

        details = {k: v for k, v in result.items() if k not in ("response", "intent")}
        st.session_state.setdefault("voice_history", []).append({
            "transcript": transcript,
            "intent": intent_label,
            "response": response_text,
            "audio": tts_audio,
            "details": details,
        })
        st.rerun()
    except Exception as exc:
        print(f"[Voice command error] {exc!r}")
        st.error("Something went wrong processing that voice command. Please try again.")


# ── Architecture page ──────────────────────────────────────────────────────────

def page_architecture() -> None:
    st.markdown("## 🏗️ System Architecture")
    st.markdown("---")

    st.markdown("### Voice-to-Action Pipeline")
    st.code("""\
  Wake word detected  (OpenWakeWord)
        │
        ▼
  Speech-to-Text  (Deepgram)
        │
        ▼
  Intent Router  (Claude classifier — chart / audit / research / document / tc_script / perio / lab_case)
        │
        ├── chart     ──▶  ChartAgent              ──▶  Dentrix chart entry + CDT code
        ├── audit     ──▶  AuditAgent              ──▶  Evidence verdict + flags + citations
        │                     └── on partial/unsup ──▶  TreatmentCoordinatorAgent ──▶ patient script
        ├── research  ──▶  ResearchAgent           ──▶  RAG answer + cited sources
        ├── document  ──▶  DocumentationAgent      ──▶  SOAP draft → review → voice sign
        ├── perio     ──▶  PerioChartAgent         ──▶  Structured chart + AAP 2017 staging
        └── lab_case  ──▶  LabCaseAgent            ──▶  Risk scan · lookup · attribution · reschedule
                │                                        (complementary to Dentrix Lab Case Manager)
                ▼
      ChromaDB Vector Store                    Mock Dentrix Interface (v1)
      30 dental evidence docs                  → Henry Schein One LinkIt API (production)
      64 chunks · all-MiniLM-L6-v2""", language=None)

    st.markdown("---")
    st.markdown("### Agent Details")

    for agent in V1_AGENTS:
        with st.expander(f"{agent['icon']} **{agent['name']}** — {agent['user']}"):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"**Target user:** {agent['user']}")
                st.markdown(f"**Voice command:**")
                st.code(agent["example"], language=None)
            with c2:
                st.markdown(f"**Job:** {agent['job']}")

    st.markdown("---")
    st.markdown("### Evidence Corpus — 30 Documents · 64 Chunks")
    st.caption("Ingested into ChromaDB with sentence-transformer embeddings. Retrieved via top-7 cosine similarity at query time.")

    for category, docs in CORPUS_CATEGORIES:
        with st.expander(f"**{category}** — {len(docs)} documents"):
            for doc in docs:
                st.markdown(f"- `{doc}`")

    st.markdown("---")
    st.markdown("### v2 — Designed, Not Yet Built")

    v2 = [
        ("EducationAgent", "Any staff", "Voice-triggered procedure video on chairside screen with consent logging"),
        ("XRayRecallAgent", "Dentist", '"Pull up tooth 19" → opens correct radiograph without touching keyboard'),
        ("PhasingAgent", "Dentist / TC", "Organizes flat treatment plan into Phase 1 (urgent) through Phase 4 (maintenance)"),
        ("PriorityAgent", "Dentist", '"What should we start today?" — appointment optimization given time and clinical context'),
    ]
    v2_cols = st.columns(4, gap="medium")
    for col, (name, user, job) in zip(v2_cols, v2):
        with col:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(user)
                st.markdown(job)
    st.caption("Full specs in [docs/IDEAS.md](https://github.com/Natt1111/toothtrust/blob/main/docs/IDEAS.md)")

    st.markdown("---")
    st.markdown("### Technology Stack")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown("""
**AI Layer**
- LLM: Claude Sonnet 4.6 (Anthropic)
- Embeddings: all-MiniLM-L6-v2 (sentence-transformers)
- Vector store: ChromaDB (persistent, local)
- RAG retrieval: top-7 cosine similarity

**Voice Layer**
- STT: Deepgram SDK
- TTS: ElevenLabs
- Wake word: OpenWakeWord
""")
    with t2:
        st.markdown("""
**Backend & Tooling**
- Python 3.11 · FastAPI · Streamlit
- Dentrix mock integration (v1)
- pytest · 115 / 115 tests passing (42 anti-halluc guards)
- Built with Claude Code in 5 days

**Design Principles**
- RAG over fine-tuning (auditable citations)
- Narrow agents: one tight job per agent
- Voice-first, gloved-hands-safe
- AI never signs clinical records autonomously
""")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    _inject_css()

    # Session state init
    if "selected_case" not in st.session_state:
        st.session_state.selected_case = None

    with st.sidebar:
        st.markdown("## 🦷 ToothTrust")
        st.caption("Voice-first multi-agent dental AI")
        st.markdown("---")

        page = st.radio(
            "Navigate",
            ["🏠 Overview", "🎙️ Voice Command", "🦷 Case Studies", "🏗️ Platform"],
            label_visibility="collapsed",
        )

        st.markdown("---")
        if _api_key_present():
            st.success("🟢 System Online")
        else:
            st.warning("🟡 Sample Data Mode")
        st.markdown("---")
        st.link_button("GitHub →", GITHUB_URL)
        st.markdown("---")
        st.caption(
            "Clinical decision support — final treatment decisions "
            "remain with the licensed provider."
        )

    if page == "🏠 Overview":
        page_overview()
    elif page == "🎙️ Voice Command":
        page_voice()
    elif page == "🦷 Case Studies":
        page_demo()
    elif page == "🏗️ Platform":
        page_architecture()


if __name__ == "__main__":
    main()
