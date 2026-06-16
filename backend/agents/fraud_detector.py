from datetime import datetime
from graph.state import ClaimState
from models.decision import FraudResult, FraudSignal, TraceEntry
from services.policy_loader import get_policy

class FraudDetectorAgent:
    def run(self, state: ClaimState) -> ClaimState:
        try:
            policy = get_policy()
            claim = state["claim"]
            thresholds = policy.fraud_thresholds
            signals = []
            trace = []
            fraud_score = 0.0
            
            print(f"\n{'='*80}")
            print(f"[FraudDetector] Scanning for fraud signals")
            print(f"{'='*80}")

            # --- 1. Same day claims check ---
            claims_history = getattr(claim, 'claims_history', None) or []
            print(f"  Claims history: {len(claims_history)} prior claims found")
            
            same_day_claims = [
                c for c in claims_history
                if (hasattr(c, 'date') and c.date == claim.treatment_date) or 
                   (isinstance(c, dict) and c.get('date') == claim.treatment_date)
            ]
            same_day_count = len(same_day_claims)

            if same_day_count >= thresholds.same_day_claims_limit:
                fraud_score = max(
                    fraud_score,
                    thresholds.fraud_score_manual_review_threshold
                )
                print(f"  ⚠️  Same-day claims: {same_day_count} (threshold: {thresholds.same_day_claims_limit})")
                signals.append(FraudSignal(
                    signal_type="SAME_DAY_CLAIMS",
                    detail=f"Member has {same_day_count} existing claims on {claim.treatment_date}. This would be claim number {same_day_count + 1}. Limit is {thresholds.same_day_claims_limit}.",
                    severity="HIGH"
                ))
                trace.append(TraceEntry(
                    agent="FraudDetector",
                    check="same_day_claims",
                    result="FLAG",
                    detail=f"{same_day_count} same-day claims found. Threshold is {thresholds.same_day_claims_limit}.",
                    timestamp=datetime.now().isoformat(),
                    data={
                        "same_day_count": same_day_count,
                        "threshold": thresholds.same_day_claims_limit,
                        "treatment_date": claim.treatment_date
                    }
                ))
            else:
                trace.append(TraceEntry(
                    agent="FraudDetector",
                    check="same_day_claims",
                    result="PASS",
                    detail=f"{same_day_count} same-day claims found. Within threshold of {thresholds.same_day_claims_limit}.",
                    timestamp=datetime.now().isoformat(),
                    data={"same_day_count": same_day_count}
                ))

            # --- 2. Monthly claims check ---
            year_month = claim.treatment_date[:7]
            monthly_claims = [
                c for c in claims_history
                if (hasattr(c, 'date') and c.date.startswith(year_month)) or
                   (isinstance(c, dict) and c.get('date', '').startswith(year_month))
            ]
            monthly_count = len(monthly_claims)

            if monthly_count >= thresholds.monthly_claims_limit:
                fraud_score += 0.3
                print(f"  ⚠️  Monthly claims: {monthly_count} (threshold: {thresholds.monthly_claims_limit})")
                signals.append(FraudSignal(
                    signal_type="MONTHLY_CLAIMS_EXCEEDED",
                    detail=f"Member has {monthly_count} claims this month. Limit is {thresholds.monthly_claims_limit}.",
                    severity="MEDIUM"
                ))
                trace.append(TraceEntry(
                    agent="FraudDetector",
                    check="monthly_claims",
                    result="FLAG",
                    detail=f"{monthly_count} claims this month. Threshold is {thresholds.monthly_claims_limit}.",
                    timestamp=datetime.now().isoformat(),
                    data={
                        "monthly_count": monthly_count,
                        "threshold": thresholds.monthly_claims_limit
                    }
                ))
            else:
                trace.append(TraceEntry(
                    agent="FraudDetector",
                    check="monthly_claims",
                    result="PASS",
                    detail=f"{monthly_count} claims this month. Within threshold of {thresholds.monthly_claims_limit}.",
                    timestamp=datetime.now().isoformat(),
                    data={"monthly_count": monthly_count}
                ))

            # --- 3. High value claim check ---
            if claim.claimed_amount > thresholds.high_value_claim_threshold:
                fraud_score += 0.2
                signals.append(FraudSignal(
                    signal_type="HIGH_VALUE_CLAIM",
                    detail=f"Claimed amount Rs.{claim.claimed_amount} exceeds high-value threshold of Rs.{thresholds.high_value_claim_threshold}.",
                    severity="MEDIUM"
                ))
                trace.append(TraceEntry(
                    agent="FraudDetector",
                    check="high_value_claim",
                    result="FLAG",
                    detail=f"Claim amount Rs.{claim.claimed_amount} exceeds threshold Rs.{thresholds.high_value_claim_threshold}.",
                    timestamp=datetime.now().isoformat(),
                    data={
                        "claimed_amount": claim.claimed_amount,
                        "threshold": thresholds.high_value_claim_threshold
                    }
                ))
            else:
                trace.append(TraceEntry(
                    agent="FraudDetector",
                    check="high_value_claim",
                    result="PASS",
                    detail=f"Claim amount Rs.{claim.claimed_amount} is within normal range.",
                    timestamp=datetime.now().isoformat(),
                    data={"claimed_amount": claim.claimed_amount}
                ))

            # --- 4. Multiple providers same day ---
            if same_day_count > 0:
                providers = set(
                c.get("provider") if isinstance(c, dict) else getattr(c, "provider", None)
                for c in same_day_claims
                )
                providers = {p for p in providers if p}
                if len(providers) > 1:
                    fraud_score += 0.2
                    signals.append(FraudSignal(
                        signal_type="MULTIPLE_PROVIDERS_SAME_DAY",
                        detail=f"Claims from {len(providers)} different providers on the same day: {', '.join(providers)}",
                        severity="HIGH"
                    ))
                    trace.append(TraceEntry(
                        agent="FraudDetector",
                        check="multiple_providers",
                        result="FLAG",
                        detail=f"Multiple providers detected on same day: {', '.join(providers)}",
                        timestamp=datetime.now().isoformat(),
                        data={"providers": list(providers)}
                    ))

            fraud_score = min(fraud_score, 1.0)

            trace.append(TraceEntry(
                agent="FraudDetector",
                check="fraud_score",
                result="FLAG" if fraud_score >= thresholds.fraud_score_manual_review_threshold else "PASS",
                detail=f"Final fraud score: {fraud_score:.2f}. Threshold for manual review: {thresholds.fraud_score_manual_review_threshold}",
                timestamp=datetime.now().isoformat(),
                data={"fraud_score": fraud_score}
            ))

            state["fraud_result"] = FraudResult(
                fraud_score=fraud_score,
                signals=signals,
                trace=trace
            )
            state["component_status"]["fraud_detector"] = "COMPLETED"
            
            print(f"\n[FraudDetector] Result:")
            print(f"  Fraud Score: {fraud_score:.2f} (threshold for review: {thresholds.fraud_score_manual_review_threshold})")
            if signals:
                for sig in signals:
                    print(f"  ⚠️  {sig.signal_type} ({sig.severity}): {sig.detail}")
            else:
                print(f"  ✓ No fraud signals detected")
            print(f"{'='*80}\n")

        except Exception as e:
            trace_entry = TraceEntry(
                agent="FraudDetector",
                check="fraud_detection",
                result="FAIL",
                detail=f"Fraud detector failed: {str(e)}",
                timestamp=datetime.now().isoformat(),
                data={}
            )
            state["fraud_result"] = FraudResult(
                fraud_score=0.0,
                signals=[],
                trace=[trace_entry]
            )
            state["component_status"]["fraud_detector"] = "FAILED"
            state["confidence_score"] -= 0.15
            print(f"\n[FraudDetector] ERROR: {str(e)}")
            print(f"{'='*80}\n")

        return state
