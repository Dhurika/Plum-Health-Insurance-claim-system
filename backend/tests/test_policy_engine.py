import pytest
from unittest.mock import patch
from datetime import date
from backend.models.claim import Claim
from backend.models.policy import Policy
from backend.agents.policy_engine import check_policy

MOCK_POLICY = Policy(
    policy_id="POL-001",
    holder_name="Jane Doe",
    policy_type="health",
    coverage_limit=50000.0,
    deductible=500.0,
    covered_events=["medical", "surgery"],
    exclusions=["dental"],
)

def _make_state(claim_type, amount):
    return {
        "claim": Claim(
            claim_id="CLM-TEST",
            policy_id="POL-001",
            claimant_name="Jane Doe",
            date_of_incident=date(2024, 1, 1),
            claim_type=claim_type,
            amount_requested=amount,
            description="Test claim",
        ),
        "documents_verified": True,
        "parsed_data": {},
        "policy_check": None,
        "fraud_score": None,
        "decision": None,
        "errors": [],
    }

@patch("backend.agents.policy_engine.get_policy", return_value=MOCK_POLICY)
def test_eligible_claim(mock_get):
    state = check_policy(_make_state("medical", 3000))
    assert state["policy_check"]["eligible"] is True
    assert state["policy_check"]["payable_amount"] == 2500.0

@patch("backend.agents.policy_engine.get_policy", return_value=MOCK_POLICY)
def test_excluded_claim(mock_get):
    state = check_policy(_make_state("dental", 500))
    assert state["policy_check"]["eligible"] is False

@patch("backend.agents.policy_engine.get_policy", return_value=MOCK_POLICY)
def test_exceeds_coverage(mock_get):
    state = check_policy(_make_state("medical", 99999))
    assert state["policy_check"]["eligible"] is False

@patch("backend.agents.policy_engine.get_policy", return_value=None)
def test_policy_not_found(mock_get):
    state = check_policy(_make_state("medical", 1000))
    assert state["policy_check"]["eligible"] is False
    assert len(state["errors"]) > 0
