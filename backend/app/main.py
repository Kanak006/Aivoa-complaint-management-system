from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from app.config import settings
from app.database import Base, engine, get_db
from app import models, schemas
from app.langgraph_pipeline import run_pipeline
from app.file_parsing import extract_text_from_upload
from app.groq_client import call_reasoning_model

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AIVOA Customer Complaint Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# AI extraction endpoints
# ---------------------------------------------------------------------------

@app.post("/api/complaints/extract-text", response_model=schemas.ExtractResponse)
def extract_from_text(payload: schemas.ExtractTextRequest, db: Session = Depends(get_db)):
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    result = run_pipeline(payload.text, db)
    return _pipeline_result_to_response(result, payload.text)


@app.post("/api/complaints/extract-file", response_model=schemas.ExtractResponse)
async def extract_from_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw_bytes = await file.read()
    if len(raw_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit")

    text = extract_text_from_upload(file, raw_bytes)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from the uploaded file")

    result = run_pipeline(text, db)
    return _pipeline_result_to_response(result, text)


def _pipeline_result_to_response(result: dict, raw_text: str) -> schemas.ExtractResponse:
    return schemas.ExtractResponse(
        extracted=schemas.ExtractedFields(**result.get("extracted", {})),
        completeness_score=result.get("completeness_score", 0),
        missing_fields=result.get("missing_fields", []),
        risk_classification=result.get("risk_classification"),
        risk_justification=result.get("risk_justification"),
        capa_recommendation=result.get("capa_recommendation"),
        raw_source_text=raw_text,
        duplicate_matches=result.get("duplicate_matches", []),
        is_potential_duplicate=result.get("is_potential_duplicate", False),
    )


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@app.post("/api/complaints", response_model=schemas.ComplaintOut)
def create_complaint(payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    complaint = models.Complaint(**payload.model_dump())
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


@app.get("/api/complaints", response_model=List[schemas.ComplaintOut])
def list_complaints(db: Session = Depends(get_db)):
    return db.query(models.Complaint).order_by(models.Complaint.created_at.desc()).all()


@app.get("/api/complaints/{complaint_id}", response_model=schemas.ComplaintOut)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@app.put("/api/complaints/{complaint_id}", response_model=schemas.ComplaintOut)
def update_complaint(complaint_id: int, payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    for key, value in payload.model_dump().items():
        setattr(complaint, key, value)
    db.commit()
    db.refresh(complaint)
    return complaint


# ---------------------------------------------------------------------------
# AI copilot chat endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    context_text: Optional[str] = payload.context_text

    if payload.complaint_id and not context_text:
        complaint = db.query(models.Complaint).filter(models.Complaint.id == payload.complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        context_text = (
            f"Product: {complaint.product_name}, Batch: {complaint.batch_lot_number}, "
            f"Type: {complaint.complaint_type}, Severity: {complaint.initial_severity}, "
            f"Risk: {complaint.risk_classification}\n"
            f"Description: {complaint.description}\n"
            f"Risk justification: {complaint.risk_justification}\n"
            f"CAPA recommendation: {complaint.capa_recommendation}"
        )

    system_prompt = (
        "You are the AI Complaint Intake Assistant embedded in a pharmaceutical QMS. "
        "Answer the user's question using only the complaint context provided. "
        "Be concise (2-4 sentences). If the answer isn't in the context, say so plainly "
        "rather than guessing. Always remind implicitly through tone that this is a draft "
        "assessment for a human QA reviewer."
    )
    user_prompt = f"Complaint context:\n{context_text or 'No complaint loaded yet.'}\n\nQuestion: {payload.question}"

    answer = call_reasoning_model(system_prompt, user_prompt)
    return {"answer": answer.strip()}
