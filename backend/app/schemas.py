from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, field_validator


class ExtractTextRequest(BaseModel):
    text: str


class ExtractedFields(BaseModel):
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    product_strength: Optional[str] = None
    batch_lot_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity_affected: Optional[str] = None
    complaint_type: Optional[str] = None
    complaint_date: Optional[str] = None
    description: Optional[str] = None
    initial_severity: Optional[str] = None
    priority: Optional[str] = None

    @field_validator("manufacturing_date", "expiry_date", "complaint_date", mode="before")
    @classmethod
    def _normalize_date(cls, v):
        # SQLAlchemy returns real date objects when reading from Postgres;
        # the LLM extraction path returns "YYYY-MM-DD" strings. Normalize both
        # to a plain string so the API response shape is consistent either way.
        if isinstance(v, date):
            return v.isoformat()
        return v


class ExtractResponse(BaseModel):
    extracted: ExtractedFields
    completeness_score: float
    missing_fields: List[str]
    risk_classification: Optional[str] = None
    risk_justification: Optional[str] = None
    capa_recommendation: Optional[str] = None
    raw_source_text: str
    duplicate_matches: List[Dict[str, Any]] = []
    is_potential_duplicate: bool = False


class ComplaintCreate(ExtractedFields):
    completeness_score: Optional[float] = None
    missing_fields: Optional[List[str]] = None
    risk_classification: Optional[str] = None
    risk_justification: Optional[str] = None
    capa_recommendation: Optional[str] = None
    raw_source_text: Optional[str] = None
    status: Optional[str] = "Pending Triage"
    duplicate_matches: Optional[List[Dict[str, Any]]] = None
    is_potential_duplicate: Optional[bool] = False

    @field_validator("manufacturing_date", "expiry_date", "complaint_date", mode="before")
    @classmethod
    def _validate_date_format(cls, v):
        # Treat empty strings as "no date given" rather than an invalid value.
        if v in (None, ""):
            return None
        if isinstance(v, date):
            return v.isoformat()
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValueError(
                f"must be a valid date in YYYY-MM-DD format (e.g. 2026-07-20), got {v!r}"
            )
        return v


class ComplaintOut(ComplaintCreate):
    id: int

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    complaint_id: Optional[int] = None
    context_text: Optional[str] = None
    question: str
