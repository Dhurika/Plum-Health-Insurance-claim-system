import json
from unittest.mock import patch, MagicMock
from datetime import date
from backend.models.claim import Claim
from backend.agents.document_verifier import verify_documents

def _make_state(docs):
    return {
        "claim": Claim(
            claim_id="CLM-V",
            policy_id="POL-001",
            claimant_name="Jane Doe",
            date_of_incident=date(2024, 1, 1),
            claim_type="medical",
            amount_requested=1000,
            description="Test",
            documents=docs,
        ),
        "documents_verified": None,
        "parsed_data": None,
        "policy_check": None,
        "fraud_score": None,
        "decision": None,
        "errors": [],
    }

def _mock_bedrock_response(verified: bool):
    body = MagicMock()
    body.read.return_value = json.dumps({
        "content": [{"text": json.dumps({"verified": verified, "missing_documents": [], "issues": []})}]
    }).encode()
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = {"body": body}
    return mock_client

@patch("backend.agents.document_verifier.bedrock", _mock_bedrock_response(True))
def test_verified():
    state = verify_documents(_make_state(["hospital_bill.pdf", "discharge_summary.pdf"]))
    assert state["documents_verified"] is True

@patch("backend.agents.document_verifier.bedrock", _mock_bedrock_response(False))
def test_not_verified():
    state = verify_documents(_make_state([]))
    assert state["documents_verified"] is False
    assert len(state["errors"]) > 0
