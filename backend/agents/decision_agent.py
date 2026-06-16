from datetime import datetime
from graph.state import ClaimState
from models.decision import ClaimDecision, TraceEntry
from services.policy_loader import get_policy

class DecisionAgent:
    def run(self, state: ClaimState) -> ClaimState:
        try:
            policy = get_policy()
            claim = state["claim"]
            policy_result = state.get("policy_result")
            fraud_result = state.get("fraud_result")
            confidence_score = state.get("confidence_score", 1.0)
            trace = list(state.get("trace", []))
            component_status = state.get("component_status", {})
            
            print(f"\n{'='*80}")
            print(f"[DecisionAgent] Making final claim decision")
            print(f"{'='*80}")

            # collect all trace entries from all agents
            if policy_result and policy_result.trace:
                trace.extend(policy_result.trace)
            if fraud_result and fraud_result.trace:
                trace.extend(fraud_result.trace)

            # --- handle missing results due to component failures ---
            if policy_result is None:
                trace.append(TraceEntry(
                    agent="DecisionAgent",
                    check="policy_result_check",
                    result="FAIL",
                    detail="Policy engine result missing. Routing to manual review.",
                    timestamp=datetime.now().isoformat(),
                    data={}
                ))
                state["final_decision"] = ClaimDecision(
                    claim_id=state["claim_id"],
                    member_id=claim.member_id,
                    decision="MANUAL_REVIEW",
                    approved_amount=0.0,
                    confidence_score=max(0.0, confidence_score - 0.35),
                    explanation="Policy engine failed to produce a result. Manual review required.",
                    rejection_reasons=["POLICY_ENGINE_ERROR"],
                    component_status=component_status,
                    trace=trace
                )
                state["component_status"]["decision_agent"] = "COMPLETED"
                return state

            # --- fraud check ---
            fraud_score = fraud_result.fraud_score if fraud_result else 0.0
            fraud_threshold = policy.fraud_thresholds.fraud_score_manual_review_threshold

            if fraud_score >= fraud_threshold:
                trace.append(TraceEntry(
                    agent="DecisionAgent",
                    check="fraud_check",
                    result="FLAG",
                    detail=f"Fraud score {fraud_score:.2f} exceeds threshold {fraud_threshold}. Routing to manual review.",
                    timestamp=datetime.now().isoformat(),
                    data={"fraud_score": fraud_score, "threshold": fraud_threshold}
                ))
                state["final_decision"] = ClaimDecision(
                    claim_id=state["claim_id"],
                    member_id=claim.member_id,
                    decision="MANUAL_REVIEW",
                    approved_amount=0.0,
                    confidence_score=max(0.0, confidence_score - 0.2),
                    explanation=f"Claim flagged for manual review due to suspicious activity. Fraud score: {fraud_score:.2f}. Signals: " + 
                        "; ".join([s.detail for s in (fraud_result.signals or [])]),
                    rejection_reasons=["FRAUD_REVIEW"],
                    fraud_signals=fraud_result.signals if fraud_result else [],
                    line_item_results=policy_result.line_item_results,
                    copay_amount=policy_result.copay_amount,
                    discount_amount=policy_result.discount_amount,
                    component_status=component_status,
                    trace=trace
                )
                state["component_status"]["decision_agent"] = "COMPLETED"
                return state

            # --- high value auto manual review ---
            auto_review_threshold = policy.fraud_thresholds.auto_manual_review_above
            if claim.claimed_amount > auto_review_threshold:
                trace.append(TraceEntry(
                    agent="DecisionAgent",
                    check="high_value_check",
                    result="FLAG",
                    detail=f"Claim amount Rs.{claim.claimed_amount} exceeds auto manual review threshold Rs.{auto_review_threshold}.",
                    timestamp=datetime.now().isoformat(),
                    data={
                        "claimed_amount": claim.claimed_amount,
                        "threshold": auto_review_threshold
                    }
                ))
                confidence_score = max(0.0, confidence_score - 0.1)

            # --- component failure check ---
            failed_components = [k for k, v in component_status.items() if v == "FAILED"]
            if failed_components:
                confidence_score = max(0.0, confidence_score - 0.1 * len(failed_components))
                trace.append(TraceEntry(
                    agent="DecisionAgent",
                    check="component_failure_check",
                    result="FLAG",
                    detail=f"Components failed: {', '.join(failed_components)}. Confidence reduced. Manual review recommended.",
                    timestamp=datetime.now().isoformat(),
                    data={"failed_components": failed_components}
                ))

            # --- final decision ---
            decision = policy_result.decision
            approved_amount = policy_result.approved_amount
            rejection_reasons = policy_result.rejection_reasons or []

            # if component failed and policy says approved, still recommend manual review
            if failed_components and decision == "APPROVED":
                explanation = (
                    f"Claim approved for Rs.{approved_amount:.2f} based on available information. "
                    f"Note: {', '.join(failed_components)} failed during processing. "
                    f"Manual review recommended. Confidence score: {confidence_score:.2f}."
                )
            elif decision == "APPROVED":
                explanation = self._build_approval_explanation(
                    approved_amount,
                    policy_result.discount_amount,
                    policy_result.copay_amount,
                    claim.claimed_amount,
                    confidence_score
                )
            elif decision == "PARTIAL":
                explanation = self._build_partial_explanation(
                    approved_amount,
                    policy_result.line_item_results,
                    confidence_score
                )
            elif decision == "REJECTED":
                explanation = self._build_rejection_explanation(
                    rejection_reasons,
                    policy_result.trace
                )
            else:
                explanation = "Manual review required."

            trace.append(TraceEntry(
                agent="DecisionAgent",
                check="final_decision",
                result=decision,
                detail=explanation,
                timestamp=datetime.now().isoformat(),
                data={
                    "decision": decision,
                    "approved_amount": approved_amount,
                    "confidence_score": confidence_score
                }
            ))

            state["final_decision"] = ClaimDecision(
                claim_id=state["claim_id"],
                member_id=claim.member_id,
                decision=decision,
                approved_amount=round(approved_amount, 2),
                confidence_score=round(min(1.0, max(0.0, confidence_score)), 2),
                explanation=explanation,
                rejection_reasons=rejection_reasons,
                line_item_results=policy_result.line_item_results,
                copay_amount=policy_result.copay_amount,
                discount_amount=policy_result.discount_amount,
                fraud_signals=fraud_result.signals if fraud_result else [],
                component_status=component_status,
                trace=trace
            )
            state["component_status"]["decision_agent"] = "COMPLETED"
            
            print(f"\n[DecisionAgent] FINAL DECISION: {decision}")
            print(f"  Amount: ₹{round(approved_amount, 2)} | Confidence: {round(min(1.0, max(0.0, confidence_score)), 2):.0%}")
            print(f"  Explanation: {explanation[:100]}...")
            print(f"{'='*80}\n")

        except Exception as e:
            confidence_score = max(0.0, state.get("confidence_score", 1.0) - 0.35)
            trace_entry = TraceEntry(
                agent="DecisionAgent",
                check="final_decision",
                result="FAIL",
                detail=f"Decision agent failed: {str(e)}",
                timestamp=datetime.now().isoformat(),
                data={}
            )
            state["final_decision"] = ClaimDecision(
                claim_id=state["claim_id"],
                member_id=state["claim"].member_id,
                decision="MANUAL_REVIEW",
                approved_amount=0.0,
                confidence_score=round(confidence_score, 2),
                explanation=f"Decision agent encountered an error: {str(e)}",
                rejection_reasons=["DECISION_AGENT_ERROR"],
                component_status=state.get("component_status", {}),
                trace=state.get("trace", []) + [trace_entry]
            )
            state["component_status"]["decision_agent"] = "FAILED"
            print(f"\n[DecisionAgent] ERROR: {str(e)}")
            print(f"{'='*80}\n")

        return state

    def _build_approval_explanation(self, approved_amount, discount_amount, copay_amount, claimed_amount, confidence):
        parts = [f"Claim approved for Rs.{approved_amount:.2f}."]
        if discount_amount and discount_amount > 0:
            parts.append(f"Network hospital discount of Rs.{discount_amount:.2f} applied.")
        if copay_amount and copay_amount > 0:
            parts.append(f"Co-pay deduction of Rs.{copay_amount:.2f} applied.")
        parts.append(f"Confidence score: {confidence:.2f}.")
        return " ".join(parts)

    def _build_partial_explanation(self, approved_amount, line_items, confidence):
        excluded = [i for i in (line_items or []) if not i.covered]
        covered = [i for i in (line_items or []) if i.covered]
        parts = [f"Claim partially approved for Rs.{approved_amount:.2f}."]
        if covered:
            parts.append(f"Covered: {', '.join([i.description for i in covered])}.")
        if excluded:
            parts.append(f"Excluded: {', '.join([i.description for i in excluded])} — not covered under policy.")
        parts.append(f"Confidence score: {confidence:.2f}.")
        return " ".join(parts)

    def _build_rejection_explanation(self, rejection_reasons, trace):
        reason_messages = {
            "WAITING_PERIOD": "Treatment is within the waiting period for this condition.",
            "INITIAL_WAITING_PERIOD": "Treatment is within the initial 30-day waiting period.",
            "EXCLUDED_CONDITION": "Treatment or condition is explicitly excluded under this policy.",
            "PRE_AUTH_MISSING": "Pre-authorization was required but not obtained. Please get pre-auth and resubmit.",
            "PER_CLAIM_EXCEEDED": "Claimed amount exceeds the per-claim limit.",
            "CATEGORY_NOT_COVERED": "This treatment category is not covered under the policy.",
            "MEMBER_NOT_FOUND": "Member not found in the policy roster."
        }
        parts = ["Claim rejected."]
        for reason in rejection_reasons:
            msg = reason_messages.get(reason, reason)
            parts.append(msg)

        # add eligible date from trace if waiting period
        if "WAITING_PERIOD" in rejection_reasons or "INITIAL_WAITING_PERIOD" in rejection_reasons:
            for entry in (trace or []):
                if "eligible_from" in (entry.data or {}):
                    parts.append(f"Eligible from: {entry.data['eligible_from']}.")
                    break

        return " ".join(parts)
