from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class TraceEntry(BaseModel):
    agent: str
    check: str
    result: str
    detail: str
    timestamp: str = ""
    data: Optional[Dict[str, Any]] = {}

class LineItemResult(BaseModel):
    description: str
    amount: float
    covered: bool
    reason: Optional[str] = None

class VerificationError(BaseModel):
    error_type: str
    doc_found: Optional[str] = None
    doc_required: Optional[str] = None
    detail: str

class VerificationResult(BaseModel):
    is_valid: bool
    errors: Optional[List[VerificationError]] = []
    trace: Optional[List[TraceEntry]] = []

class ParsedDocument(BaseModel):
    file_id: str
    doc_type: str
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    hospital_name: Optional[str] = None
    date: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = []
    total_amount: Optional[float] = None
    confidence: Optional[str] = "HIGH"
    raw: Optional[Dict[str, Any]] = {}

class PolicyResult(BaseModel):
    decision: str
    approved_amount: float
    rejection_reasons: Optional[List[str]] = []
    line_item_results: Optional[List[LineItemResult]] = []
    copay_amount: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    trace: Optional[List[TraceEntry]] = []

class FraudSignal(BaseModel):
    signal_type: str
    detail: str
    severity: str

class FraudResult(BaseModel):
    fraud_score: float
    signals: Optional[List[FraudSignal]] = []
    trace: Optional[List[TraceEntry]] = []

class ClaimDecision(BaseModel):
    claim_id: str
    member_id: str
    decision: str
    approved_amount: float
    confidence_score: float
    explanation: str
    rejection_reasons: Optional[List[str]] = []
    line_item_results: Optional[List[LineItemResult]] = []
    copay_amount: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    fraud_signals: Optional[List[FraudSignal]] = []
    component_status: Optional[Dict[str, str]] = {}
    trace: Optional[List[TraceEntry]] = []
from typing import Optional

class Decision(BaseModel):
    claim_id: str
    outcome: str  # "approved", "rejected", "review"
    reason: str
    approved_amount: Optional[float] = None
    fraud_score: Optional[float] = None
    confidence: Optional[float] = None
