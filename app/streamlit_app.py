"""ToothTrust Streamlit demo — treatment plan audit + chairside research."""

from __future__ import annotations

import json

import streamlit as st

st.set_page_config(page_title="ToothTrust", page_icon="🦷", layout="wide")

st.title("🦷 ToothTrust")
st.caption("Voice-first multimodal RAG for dental clinical workflows")

# --- Sidebar: patient context ---
with st.sidebar:
    st.header("Patient Context")
    patient_id = st.text_input("Patient ID", value="mock_p001")
    patient_context = st.text_area(
        "Medical / Dental History",
        placeholder="e.g. hypertension, bisphosphonate therapy (alendronate), anxiety",
        height=120,
    )
    st.divider()
    st.caption("ToothTrust is for informational use only and does not constitute clinical advice.")

tab_audit, tab_research, tab_voice, tab_chart = st.tabs(
    ["Treatment Plan Audit", "Chairside Research", "Voice Demo", "Chart Viewer"]
)

# ─── Treatment Plan Audit ─────────────────────────────────────────────────────
with tab_audit:
    st.subheader("Treatment Plan Audit")
    st.info("Paste a treatment plan below (one procedure per line, or as JSON) to audit it against clinical evidence.")

    plan_input = st.text_area(
        "Treatment Plan",
        placeholder='[{"cdt_code": "D2740", "description": "Crown - tooth 19", "tooth": 19}]',
        height=200,
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        run_audit = st.button("Run Audit", type="primary")

    if run_audit and plan_input.strip():
        try:
            treatment_plan = json.loads(plan_input)
        except json.JSONDecodeError:
            lines = [l.strip() for l in plan_input.splitlines() if l.strip()]
            treatment_plan = [{"cdt_code": "", "description": line, "tooth": None} for line in lines]

        with st.spinner("Auditing against evidence corpus..."):
            try:
                from src.audit import audit_treatment_plan
                from src.report import to_html

                result = audit_treatment_plan(treatment_plan, patient_context=patient_context)

                overall_color = {
                    "supported": "green",
                    "partially_supported": "orange",
                    "unsupported": "red",
                    "insufficient_evidence": "gray",
                }.get(result.overall_assessment, "gray")

                st.markdown(
                    f"**Overall:** :{overall_color}[{result.overall_assessment.replace('_', ' ').title()}] "
                    f"&nbsp; Confidence: **{result.confidence}**"
                )
                st.markdown(f"> {result.patient_summary}")

                for proc in result.procedures:
                    with st.expander(f"{proc.get('description', 'Procedure')} — {proc.get('verdict', '').replace('_', ' ').title()}"):
                        st.write(proc.get("rationale", ""))
                        if proc.get("flags"):
                            st.warning("Flags: " + " · ".join(proc["flags"]))
                        if proc.get("citations"):
                            st.caption("Sources: " + ", ".join(proc["citations"]))

                if result.missing_information:
                    st.subheader("What would improve confidence")
                    for item in result.missing_information:
                        st.markdown(f"- {item}")

                with st.expander("Full HTML Report"):
                    st.components.v1.html(to_html(result), height=600, scrolling=True)

            except Exception as e:
                st.error(f"Audit failed: {e}")
                st.exception(e)
    elif run_audit:
        st.warning("Please enter a treatment plan.")

# ─── Chairside Research ───────────────────────────────────────────────────────
with tab_research:
    st.subheader("Chairside Evidence Lookup")
    st.info("Ask a clinical question — answers are grounded in the evidence corpus.")

    question = st.text_input("Clinical Question", placeholder="What are the contraindications for extraction in a patient on bisphosphonates?")
    if st.button("Search Evidence") and question.strip():
        with st.spinner("Retrieving evidence..."):
            try:
                from src.agents.research_agent import ResearchAgent

                agent = ResearchAgent()
                result = agent.run(utterance=question)
                st.markdown(result["response"])
                if result.get("sources"):
                    st.caption("Sources: " + ", ".join(set(result["sources"])))
            except Exception as e:
                st.error(f"Research failed: {e}")

# ─── Voice Demo ───────────────────────────────────────────────────────────────
with tab_voice:
    st.subheader("Voice Command Demo")
    st.info("Simulate voice input — type an utterance as if spoken to the assistant.")

    utterance = st.text_input(
        "Voice Utterance",
        placeholder="Chart MOD composite on tooth 14",
    )
    session_id = st.text_input("Session ID", value="demo_session_001")

    if st.button("Route Command") and utterance.strip():
        with st.spinner("Processing..."):
            try:
                from src.orchestrator import Orchestrator

                orch = Orchestrator()
                result = orch.route(session_id=session_id, utterance=utterance)
                st.success(f"Intent: **{result.get('intent', 'unknown')}**")
                st.markdown(result.get("response", ""))
                with st.expander("Full response"):
                    st.json({k: v for k, v in result.items() if k != "audit_result"})
            except Exception as e:
                st.error(f"Routing failed: {e}")

# ─── Chart Viewer ─────────────────────────────────────────────────────────────
with tab_chart:
    st.subheader("Mock Chart Viewer")
    st.info("View or edit mock Dentrix chart data.")

    if st.button("Load Chart"):
        try:
            from src.integrations.dentrix_mock import DentrixMock

            mock = DentrixMock()
            chart = mock.get_chart(patient_id)
            st.json(chart)
        except Exception as e:
            st.error(f"Failed to load chart: {e}")
