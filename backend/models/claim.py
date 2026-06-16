from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class DocumentContent(BaseModel):
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    patient_name: Optional[str] = None
    date: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    medicines: Optional[List[str]] = None
    tests_ordered: Optional[List[str]] = None
    hospital_name: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    total: Optional[float] = None
    test_name: Optional[str] = None
    base64_data: Optional[str] = None
    mime_type: Optional[str] = None
    filename: Optional[str] = None

class DocumentInput(BaseModel):
    file_id: str
    file_name: Optional[str] = None
    actual_type: str
    quality: Optional[str] = "GOOD"
    patient_name_on_doc: Optional[str] = None
    content: Optional[DocumentContent] = None

class PriorClaim(BaseModel):
    """For claims history tracking"""
    date: str
    amount: float
    category: str

class ClaimInput(BaseModel):
    employee_id: str
    member_id: str
    policy_id: str
    claim_category: str
    treatment_date: str
    claimed_amount: float
    hospital_name: Optional[str] = None
    documents: List[DocumentInput]
    simulate_component_failure: Optional[bool] = False
    # Injected by main.py for fraud detection and policy checks
    claims_history: Optional[List[PriorClaim]] = []
    ytd_claims_amount: Optional[float] = 0.0
    family_member_ids: Optional[List[str]] = []