import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from backend.models.claim import Claim
from backend.graph.runner import run_claim

TEST_CASES_PATH = os.path.join(os.path.dirname(__file__), "../backend/data/test_cases.json")

def run_eval():
    with open(TEST_CASES_PATH) as f:
        test_cases = json.load(f)

    results = []
    for tc in test_cases:
        claim = Claim(
            claim_id=tc["claim_id"],
            policy_id=tc["policy_id"],
            claimant_name=tc["claimant_name"],
            date_of_incident=date.fromisoformat(tc["date_of_incident"]),
            claim_type=tc["claim_type"],
            amount_requested=tc["amount_requested"],
            description=tc["description"],
            documents=tc["documents"],
        )
        decision = run_claim(claim)
        passed = decision.outcome == tc["expected_outcome"]
        results.append({
            "claim_id": tc["claim_id"],
            "expected": tc["expected_outcome"],
            "got": decision.outcome,
            "passed": passed,
            "reason": decision.reason,
        })
        status = "✅" if passed else "❌"
        print(f"{status} {tc['claim_id']}: expected={tc['expected_outcome']}, got={decision.outcome} | {decision.reason}")

    total = len(results)
    passed = sum(r["passed"] for r in results)
    print(f"\nResults: {passed}/{total} passed ({100*passed//total}%)")
    return results

if __name__ == "__main__":
    run_eval()
