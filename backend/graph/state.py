from typing import List, Optional, Dict, Annotated
import operator
from typing_extensions import TypedDict
from models.claim import ClaimInput
from models.decision import (
    VerificationResult,
    ParsedDocument,
    PolicyResult,
    FraudResult,
    ClaimDecision,
    TraceEntry
)

def merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}

def merge_confidence(a: float, b: float) -> float:
    if a == 1.0:
        return b
    if b == 1.0:
        return a
    return min(a, b)

class ClaimState(TypedDict):
    # Input
    claim_id: str
    claim: ClaimInput

    # Populated by agents
    classified_documents: Optional[List]
    verification_result: Optional[VerificationResult]
    parsed_documents: Optional[List[ParsedDocument]]
    policy_result: Optional[PolicyResult]
    fraud_result: Optional[FraudResult]
    final_decision: Optional[ClaimDecision]

    # Annotated — parallel nodes can update safely
    trace: Annotated[List[TraceEntry], operator.add]
    component_status: Annotated[Dict[str, str], merge_dicts]
    confidence_score: Annotated[float, merge_confidence]