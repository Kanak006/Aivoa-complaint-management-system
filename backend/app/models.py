from sqlalchemy import Column, Integer, String, Text, Date, DateTime, JSON, Float, Boolean
from sqlalchemy.sql import func

from app.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)

    # 1. Origin & customer details
    complaint_source = Column(String(120))
    customer_name = Column(String(200))

    # 2. Product & batch identification
    product_name = Column(String(200))
    product_strength = Column(String(120))
    batch_lot_number = Column(String(120))
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    quantity_affected = Column(String(60))

    # 3. Complaint details
    complaint_type = Column(String(120))
    complaint_date = Column(Date, nullable=True)
    description = Column(Text)

    # 4. Initial assessment & priority
    initial_severity = Column(String(40))
    priority = Column(String(40))

    # AI-generated fields (bonus features)
    completeness_score = Column(Float, nullable=True)
    missing_fields = Column(JSON, nullable=True)
    risk_classification = Column(String(40), nullable=True)
    risk_justification = Column(Text, nullable=True)
    capa_recommendation = Column(Text, nullable=True)
    is_potential_duplicate = Column(Boolean, default=False)
    duplicate_matches = Column(JSON, nullable=True)

    raw_source_text = Column(Text, nullable=True)
    status = Column(String(40), default="Pending Triage")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
