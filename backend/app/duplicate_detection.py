"""
Duplicate Complaint Detection (bonus AI feature).

Deliberately dependency-light: rather than standing up a vector DB / embeddings
pipeline for a bonus feature, this uses two cheap, explainable signals:

1. Exact match on batch/lot number and/or product name (the strongest signal —
   two complaints about the same batch are very likely related or duplicates).
2. Text similarity between complaint descriptions, via Python's built-in
   difflib.SequenceMatcher (no extra dependency, good enough to catch near-
   duplicate wording without an embeddings model).

This is intentionally simple and explainable for a QA reviewer, and is a
natural place to swap in real embeddings + a vector store later if needed.
"""

from difflib import SequenceMatcher
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app import models

DESCRIPTION_SIMILARITY_THRESHOLD = 0.55
MAX_CANDIDATES_SCANNED = 200
MAX_MATCHES_RETURNED = 3


def find_potential_duplicates(db: Session, extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    batch = (extracted.get("batch_lot_number") or "").strip().lower()
    product = (extracted.get("product_name") or "").strip().lower()
    description = (extracted.get("description") or "").strip()

    if not batch and not product:
        return []

    candidates = (
        db.query(models.Complaint)
        .order_by(models.Complaint.created_at.desc())
        .limit(MAX_CANDIDATES_SCANNED)
        .all()
    )

    matches = []
    for c in candidates:
        reasons = []
        score = 0.0

        if batch and c.batch_lot_number and c.batch_lot_number.strip().lower() == batch:
            reasons.append("same batch/lot number")
            score += 0.6

        if product and c.product_name and c.product_name.strip().lower() == product:
            reasons.append("same product")
            score += 0.2

        if description and c.description:
            similarity = SequenceMatcher(None, description.lower(), c.description.lower()).ratio()
            if similarity >= DESCRIPTION_SIMILARITY_THRESHOLD:
                reasons.append(f"{round(similarity * 100)}% similar description text")
                score += similarity * 0.3

        if reasons:
            matches.append(
                {
                    "id": c.id,
                    "product_name": c.product_name,
                    "batch_lot_number": c.batch_lot_number,
                    "customer_name": c.customer_name,
                    "complaint_date": c.complaint_date.isoformat() if c.complaint_date else None,
                    "status": c.status,
                    "match_score": round(min(score, 1.0), 2),
                    "match_reasons": reasons,
                }
            )

    matches.sort(key=lambda m: m["match_score"], reverse=True)
    return matches[:MAX_MATCHES_RETURNED]
