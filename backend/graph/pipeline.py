import copy
from langgraph.graph import StateGraph, END
from graph.state import ClaimState
from agents.document_classifier import DocumentClassifierAgent
from agents.document_verifier import DocumentVerifierAgent
from agents.document_parser import DocumentParserAgent
from agents.policy_engine import PolicyEngineAgent
from agents.fraud_detector import FraudDetectorAgent
from agents.decision_agent import DecisionAgent

classifier     = DocumentClassifierAgent()
verifier       = DocumentVerifierAgent()
parser         = DocumentParserAgent()
policy_engine  = PolicyEngineAgent()
fraud_detector = FraudDetectorAgent()
decision_agent = DecisionAgent()

def run_classifier(state: ClaimState) -> dict:
    old_len = len(state["trace"])
    result  = classifier.run(copy.deepcopy(state))
    return {
        "classified_documents": result["classified_documents"],
        "trace":                result["trace"][old_len:],
        "component_status":     result["component_status"],
        "confidence_score":     result["confidence_score"],
    }

def run_verifier(state: ClaimState) -> dict:
    old_len = len(state["trace"])
    result  = verifier.run(copy.deepcopy(state))
    return {
        "verification_result": result["verification_result"],
        "trace":               result["trace"][old_len:],
        "component_status":    result["component_status"],
        "confidence_score":    result["confidence_score"],
    }

def run_parser(state: ClaimState) -> dict:
    old_len = len(state["trace"])
    result  = parser.run(copy.deepcopy(state))
    return {
        "parsed_documents":    result["parsed_documents"],
        "verification_result": result.get("verification_result"),
        "trace":               result["trace"][old_len:],
        "component_status":    result["component_status"],
        "confidence_score":    result["confidence_score"],
    }

def run_policy_engine(state: ClaimState) -> dict:
    result = policy_engine.run(copy.deepcopy(state))
    return {
        "policy_result":    result["policy_result"],
        "component_status": result["component_status"],
        "confidence_score": result["confidence_score"],
    }

def run_fraud_detector(state: ClaimState) -> dict:
    result = fraud_detector.run(copy.deepcopy(state))
    return {
        "fraud_result":     result["fraud_result"],
        "component_status": result["component_status"],
        "confidence_score": result["confidence_score"],
    }

def run_decision_agent(state: ClaimState) -> dict:
    old_len = len(state["trace"])
    result  = decision_agent.run(copy.deepcopy(state))
    return {
        "final_decision":   result["final_decision"],
        "component_status": result["component_status"],
        "trace":            result["trace"][old_len:],
        "confidence_score": result["confidence_score"],
    }

def early_exit(state: ClaimState) -> dict:
    from models.decision import ClaimDecision
    errors         = state["verification_result"].errors
    error_messages = [e.detail for e in errors]
    confidence_score = max(
        0.0,
        min(1.0, state.get("confidence_score", 1.0)) - min(0.7, 0.2 * len(errors))
    )
    return {
        "final_decision": ClaimDecision(
            claim_id=state["claim_id"],
            member_id=state["claim"].member_id,
            decision="REJECTED",
            approved_amount=0.0,
            confidence_score=round(confidence_score, 2),
            explanation="Document verification failed. " + " | ".join(error_messages),
            rejection_reasons=["DOCUMENT_VERIFICATION_FAILED"]
        ),
        "component_status": {"early_exit": "COMPLETED"},
        "confidence_score": confidence_score
    }

def route_after_verification(state: ClaimState) -> str:
    result = state.get("verification_result")
    if result and not result.is_valid:
        return "early_exit"
    return "parser"

def route_after_parser(state: ClaimState) -> str:
    result = state.get("verification_result")
    if result and not result.is_valid:
        return "early_exit"
    return "policy_engine"

def build_pipeline():
    graph = StateGraph(ClaimState)

    graph.add_node("classifier",     run_classifier)
    graph.add_node("verifier",       run_verifier)
    graph.add_node("parser",         run_parser)
    graph.add_node("policy_engine",  run_policy_engine)
    graph.add_node("fraud_detector", run_fraud_detector)
    graph.add_node("decision_agent", run_decision_agent)
    graph.add_node("early_exit",     early_exit)

    graph.set_entry_point("classifier")

    graph.add_edge("classifier", "verifier")

    graph.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "early_exit": "early_exit",
            "parser":     "parser"
        }
    )

    graph.add_conditional_edges(
        "parser",
        route_after_parser,
        {
            "early_exit":    "early_exit",
            "policy_engine": "policy_engine"
        }
    )

    graph.add_edge("parser",         "fraud_detector")
    graph.add_edge("policy_engine",  "decision_agent")
    graph.add_edge("fraud_detector", "decision_agent")
    graph.add_edge("early_exit",     END)
    graph.add_edge("decision_agent", END)

    return graph.compile()

pipeline = build_pipeline()
