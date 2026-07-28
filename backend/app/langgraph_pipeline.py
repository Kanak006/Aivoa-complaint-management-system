"""
LangGraph pipeline for the AI Complaint Intake Assistant.

Graph shape:

    extract_fields --> check_duplicates --> check_completeness --> classify_risk --> recommend_capa --> END
                                                     |
                                                     v (if too incomplete to assess risk)
                                               flag_for_manual_review --> END

This mirrors the demo workflow: a document/email/pasted text goes in, the
Log Customer Complaint form fields come out, plus AI Copilot risk assessment,
CAPA recommendation, and a duplicate-complaint check against saved history.
"""

import re
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.groq_client import call_extraction_model, call_reasoning_model, extract_json
from app.duplicate_detection import find_potential_duplicates


def strip_markdown(text: Optional[str]) -> Optional[str]:
    """
    Small LLMs love to sprinkle **bold** and *italic* markers even when asked for
    plain prose. The frontend renders these fields as plain text, so strip the
    common markdown formatting characters rather than showing literal asterisks.
    """
    if not text:
        return text
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)   # **bold**
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"\1", text)  # *italic*
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)  # # headings
    text = re.sub(r"^[-*]\s+", "- ", text, flags=re.MULTILINE)  # normalize bullet markers
    return text.strip()


MANDATORY_FIELDS = [
    "complaint_source",
    "customer_name",
    "product_name",
    "batch_lot_number",
    "complaint_type",
    "description",
]

ALL_FIELDS = [
    "complaint_source",
    "customer_name",
    "product_name",
    "product_strength",
    "batch_lot_number",
    "manufacturing_date",
    "expiry_date",
    "quantity_affected",
    "complaint_type",
    "complaint_date",
    "description",
    "initial_severity",
    "priority",
]

COMPLETENESS_THRESHOLD = 0.4  # below this, skip risk/CAPA and flag for manual review


class ComplaintState(TypedDict, total=False):
    raw_text: str
    extracted: dict
    duplicate_matches: List[Dict[str, Any]]
    is_potential_duplicate: bool
    completeness_score: float
    missing_fields: List[str]
    risk_classification: Optional[str]
    risk_justification: Optional[str]
    capa_recommendation: Optional[str]
    status: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def extract_fields_node(state: ComplaintState) -> ComplaintState:
    system_prompt = (
        "You are a data-extraction assistant for a pharmaceutical manufacturer's "
        "Quality Management System (QMS) Customer Complaint module. Extract structured "
        "fields from the complaint document/email/text provided. "
        "Respond with ONLY a valid JSON object (no prose, no markdown fences) with these "
        f"exact keys: {ALL_FIELDS}. "
        "Use null for any field not present in the text. "
        "Dates must be formatted as YYYY-MM-DD if found, otherwise null. "
        "initial_severity must be one of: Critical, Major, Minor, Unknown. "
        "priority must be one of: High, Medium, Low, Unknown. "
        "complaint_type should be a short QMS-style category, e.g. 'Product Quality Defect', "
        "'Adverse Event', 'Packaging Defect', 'Labeling Error', 'Delivery/Shipping Issue'."
    )
    user_prompt = f"Complaint source document:\n---\n{state['raw_text']}\n---"

    raw = call_extraction_model(system_prompt, user_prompt)
    try:
        fields = extract_json(raw)
    except Exception:
        fields = {k: None for k in ALL_FIELDS}

    # Ensure all expected keys exist even if the model omitted some
    normalized = {k: fields.get(k) for k in ALL_FIELDS}
    return {"extracted": normalized}


def make_check_duplicates_node(db: Session):
    """
    Factory so the node closes over the request's DB session. LangGraph node
    functions only receive `state`, so this is the cleanest way to give a node
    access to something request-scoped like a SQLAlchemy session.
    """

    def check_duplicates_node(state: ComplaintState) -> ComplaintState:
        matches = find_potential_duplicates(db, state["extracted"])
        return {
            "duplicate_matches": matches,
            "is_potential_duplicate": len(matches) > 0,
        }

    return check_duplicates_node


def check_completeness_node(state: ComplaintState) -> ComplaintState:
    extracted = state["extracted"]
    missing = [f for f in MANDATORY_FIELDS if not extracted.get(f)]
    score = 1 - (len(missing) / len(MANDATORY_FIELDS))
    return {"completeness_score": round(score, 2), "missing_fields": missing}


def route_after_completeness(state: ComplaintState) -> str:
    if state["completeness_score"] < COMPLETENESS_THRESHOLD:
        return "flag_for_manual_review"
    return "classify_risk"


def flag_for_manual_review_node(state: ComplaintState) -> ComplaintState:
    return {
        "status": "Manual Review Required",
        "risk_classification": "Unassessed",
        "risk_justification": (
            "Too many mandatory fields are missing ("
            + ", ".join(state["missing_fields"])
            + ") to reliably assess risk. A QA reviewer should complete intake manually."
        ),
        "capa_recommendation": None,
    }


def classify_risk_node(state: ComplaintState) -> ComplaintState:
    system_prompt = (
        "You are a QA risk-assessment assistant inside a pharmaceutical complaint "
        "management system. Given extracted complaint details, classify the risk level. "
        "Respond with ONLY valid JSON with keys: "
        '"risk_classification" (one of: Critical, High, Medium, Low) and '
        '"risk_justification" (1-3 sentences, referencing the specific complaint details, '
        "e.g. whether it implicates patient safety, GMP/sterility, labeling accuracy, or is a minor "
        "cosmetic/shipping issue)."
    )
    user_prompt = f"Extracted complaint fields:\n{state['extracted']}"

    raw = call_reasoning_model(system_prompt, user_prompt)
    try:
        result = extract_json(raw)
    except Exception:
        result = {"risk_classification": "Unknown", "risk_justification": raw[:300]}

    return {
        "risk_classification": result.get("risk_classification", "Unknown"),
        "risk_justification": strip_markdown(result.get("risk_justification")),
        "status": "Pending Triage",
    }


def recommend_capa_node(state: ComplaintState) -> ComplaintState:
    system_prompt = (
        "You are a CAPA (Corrective and Preventive Action) advisor for a pharmaceutical "
        "QMS. Given the complaint details and its risk classification, suggest a brief, "
        "actionable CAPA recommendation a QA team could start from. Keep it to 3-5 sentences "
        "covering: immediate containment action, likely investigation step, and a preventive "
        "action category. This is a draft suggestion for a human QA reviewer, not a final CAPA."
    )
    user_prompt = (
        f"Complaint fields: {state['extracted']}\n"
        f"Risk classification: {state.get('risk_classification')}\n"
        f"Risk justification: {state.get('risk_justification')}"
    )
    capa_text = call_reasoning_model(system_prompt, user_prompt)
    return {"capa_recommendation": strip_markdown(capa_text)}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph(db: Session):
    graph = StateGraph(ComplaintState)

    graph.add_node("extract_fields", extract_fields_node)
    graph.add_node("check_duplicates", make_check_duplicates_node(db))
    graph.add_node("check_completeness", check_completeness_node)
    graph.add_node("flag_for_manual_review", flag_for_manual_review_node)
    graph.add_node("classify_risk", classify_risk_node)
    graph.add_node("recommend_capa", recommend_capa_node)

    graph.set_entry_point("extract_fields")
    graph.add_edge("extract_fields", "check_duplicates")
    graph.add_edge("check_duplicates", "check_completeness")
    graph.add_conditional_edges(
        "check_completeness",
        route_after_completeness,
        {
            "flag_for_manual_review": "flag_for_manual_review",
            "classify_risk": "classify_risk",
        },
    )
    graph.add_edge("flag_for_manual_review", END)
    graph.add_edge("classify_risk", "recommend_capa")
    graph.add_edge("recommend_capa", END)

    return graph.compile()


def run_pipeline(raw_text: str, db: Session) -> ComplaintState:
    # Built fresh per call (cheap) since it closes over a request-scoped DB session,
    # rather than caching a single compiled graph the way the pre-duplicate-detection
    # version did.
    graph = build_graph(db)
    initial_state: ComplaintState = {"raw_text": raw_text, "status": "Pending Triage"}
    final_state = graph.invoke(initial_state)
    return final_state
