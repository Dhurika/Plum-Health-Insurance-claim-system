import uuid
from services.console import configure_console_output

configure_console_output()

from graph.pipeline import pipeline
from graph.state import ClaimState
from models.claim import ClaimInput

def run_claim(claim: ClaimInput) -> dict:
    claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"

    initial_state: ClaimState = {
        "claim_id":             claim_id,
        "claim":                claim,
        "classified_documents": None,
        "verification_result":  None,
        "parsed_documents":     None,
        "policy_result":        None,
        "fraud_result":         None,
        "final_decision":       None,
        "trace":                [],
        "component_status":     {},
        "confidence_score":     1.0
    }

    try:
        final_state = pipeline.invoke(initial_state)
    except Exception as e:
        return {
            "claim_id":         claim_id,
            "decision":         "MANUAL_REVIEW",
            "approved_amount":  0.0,
            "confidence_score": 0.2,
            "explanation":      f"Pipeline failed: {str(e)}",
            "rejection_reasons":["PIPELINE_ERROR"],
            "trace":            [],
            "component_status": {"pipeline": "FAILED"},
            "fraud_signals":    [],
            "line_item_results":[]
        }

    decision = final_state.get("final_decision")

    if decision is None:
        confidence_score = final_state.get("confidence_score", 0.2)
        return {
            "claim_id":         claim_id,
            "decision":         "MANUAL_REVIEW",
            "approved_amount":  0.0,
            "confidence_score": round(min(1.0, max(0.0, confidence_score)), 2),
            "explanation":      "Pipeline completed but no decision was produced.",
            "rejection_reasons":["NO_DECISION"],
            "trace":            [t.dict() for t in final_state.get("trace", [])],
            "component_status": final_state.get("component_status", {}),
            "fraud_signals":    [],
            "line_item_results":[]
        }

    return {
        "claim_id":          claim_id,
        "decision":          decision.decision,
        "approved_amount":   decision.approved_amount,
        "confidence_score":  decision.confidence_score,
        "explanation":       decision.explanation,
        "rejection_reasons": decision.rejection_reasons,
        "copay_amount":      decision.copay_amount,
        "discount_amount":   decision.discount_amount,
        "fraud_signals":     [s.dict() for s in (decision.fraud_signals or [])],
        "line_item_results": [i.dict() for i in (decision.line_item_results or [])],
        "component_status":  final_state.get("component_status", {}),
        "trace":             [t.dict() for t in (decision.trace or [])]
    }
