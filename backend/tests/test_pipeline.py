import json
from unittest.mock import patch, MagicMock
from datetime import date
from backend.models.claim import Claim
from backend.models.policy import Policy
from backend.graph.runner import run_claim

MOCK_POLICY = Policy(
    policy_id="POL-001",
    holder_name="Jane Doe",
    policy_type="health",
    coverage_limit=50000.0,
    deductible=500.0,
    covered_events=["medical"],
    exclusions=["dental"],
)

def _mock_bedrock():
    def side_effect(**kwargs):
        body_str = json.loads(kwargs["body"])
        prompt = body_str["messages"][0]["content"]
        if "verification" in prompt.lower() or "required documents" in prompt.lower():
            text = json.dumps({"verified": True, "missing_documents": [], "issues": []})
        else:
            text = json.dumps({
                "incident_date": "2024-01-15",
                "incident_location": "NYC",
                "parties_involved": [],
                "damages": ["appendicitis"],
                "estimated_cost": 3000,
                "supporting_evidence": ["discharge_summary.pdf"],
            })
        body = MagicMock()
        body.read.return_value = json.dumps({"content": [{"text": text}]}).encode()
        return {"body": body}

    mock_client = MagicMock()
    mock_client.invoke_model.side_effect = side_effect
    return mock_client

@patch("backend.agents.document_verifier.bedrock", _mock_bedrock())
@patch("backend.agents.document_parser.bedrock", _mock_bedrock())
@patch("backend.agents.policy_engine.get_policy", return_value=MOCK_POLICY)
def test_full_pipeline_approved(mock_policy):
    claim = Claim(
        claim_id="CLM-PIPE-1",
        policy_id="POL-001",
        claimant_name="Jane Doe",
        date_of_incident=date(2024, 1, 15),
        claim_type="medical",
        amount_requested=3000,
        description="Emergency surgery",
        documents=["hospital_bill.pdf", "discharge_summary.pdf"],
    )
    decision = run_claim(claim)
    assert decision.outcome == "approved"
    assert decision.claim_id == "CLM-PIPE-1"

@patch("backend.agents.document_verifier.bedrock", _mock_bedrock())
@patch("backend.agents.document_parser.bedrock", _mock_bedrock())
@patch("backend.agents.policy_engine.get_policy", return_value=MOCK_POLICY)
def test_full_pipeline_rejected_exclusion(mock_policy):
    claim = Claim(
        claim_id="CLM-PIPE-2",
        policy_id="POL-001",
        claimant_name="Jane Doe",
        date_of_incident=date(2024, 1, 15),
        claim_type="dental",
        amount_requested=800,
        description="Dental implant",
        documents=["dental_invoice.pdf"],
    )
    decision = run_claim(claim)
    assert decision.outcome == "rejected"
