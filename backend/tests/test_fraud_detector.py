from datetime import date
from backend.models.claim import Claim
from backend.agents.fraud_detector import detect_fraud

def _make_state(amount, docs, parsed):
    return {
        "claim": Claim(
            claim_id="CLM-F",
            policy_id="POL-001",
            claimant_name="Test User",
            date_of_incident=date(2024, 1, 1),
            claim_type="medical",
            amount_requested=amount,
            description="Test",
            documents=docs,
        ),
        "documents_verified": True,
        "parsed_data": parsed,
        "policy_check": None,
        "fraud_score": None,
        "decision": None,
        "errors": [],
    }

def test_low_risk():
    state = detect_fraud(_make_state(1000, ["bill.pdf"], {"supporting_evidence": ["x"], "incident_location": "NYC"}))
    assert state["fraud_score"] < 0.7

def test_high_risk_no_docs():
    state = detect_fraud(_make_state(15000, [], {}))
    assert state["fraud_score"] >= 0.7
    assert any("fraud" in e.lower() for e in state["errors"])
