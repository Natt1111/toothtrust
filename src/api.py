"""FastAPI application: REST endpoints for the ToothTrust platform."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.audit import audit_treatment_plan
from src.orchestrator import Orchestrator
from src.report import to_html, to_text
from src.vision import analyze_xray

app = FastAPI(title="ToothTrust API", version="0.1.0")
_orchestrator = Orchestrator()


# --- Request / Response models ---

class TreatmentProcedure(BaseModel):
    cdt_code: str
    description: str
    tooth: int | None = None


class AuditRequest(BaseModel):
    treatment_plan: list[TreatmentProcedure]
    patient_context: str = ""
    format: str = "json"


class VoiceRouteRequest(BaseModel):
    session_id: str
    utterance: str
    patient_id: str = ""


# --- Endpoints ---

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "toothtrust"}


@app.post("/audit")
def audit(req: AuditRequest) -> dict:
    plan = [p.model_dump() for p in req.treatment_plan]
    result = audit_treatment_plan(plan, patient_context=req.patient_context)

    if req.format == "html":
        return {"html": to_html(result)}
    if req.format == "text":
        return {"text": to_text(result)}

    return {
        "overall_assessment": result.overall_assessment,
        "confidence": result.confidence,
        "procedures": result.procedures,
        "missing_information": result.missing_information,
        "patient_summary": result.patient_summary,
    }


@app.get("/audit/{session_id}/report", response_class=HTMLResponse)
def audit_report_html(session_id: str) -> str:
    session = _orchestrator._sessions.get(session_id)
    if not session or session.audit_result is None:
        raise HTTPException(404, "No audit result found for this session.")
    return to_html(session.audit_result)


@app.post("/vision/analyze")
async def vision_analyze(file: UploadFile = File(...), clinical_context: str = "") -> dict:
    suffix = Path(file.filename or "upload.png").suffix
    tmp_path = Path(f"/tmp/toothtrust_upload{suffix}")
    tmp_path.write_bytes(await file.read())
    findings = analyze_xray(tmp_path, clinical_context=clinical_context)
    tmp_path.unlink(missing_ok=True)
    return findings


@app.post("/voice/route")
def voice_route(req: VoiceRouteRequest) -> dict:
    return _orchestrator.route(
        session_id=req.session_id,
        utterance=req.utterance,
        patient_id=req.patient_id,
    )
