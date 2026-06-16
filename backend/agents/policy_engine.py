import json
import re
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from graph.state import ClaimState
from models.decision import PolicyResult, TraceEntry, LineItemResult
from services.name_normalizer import normalize_person_name
from services.policy_loader import get_policy

load_dotenv()

DIAGNOSIS_TO_WAITING = {
    "diabetes": "diabetes",
    "type 2 diabetes": "diabetes",
    "t2dm": "diabetes",
    "hypertension": "hypertension",
    "htn": "hypertension",
    "thyroid": "thyroid_disorders",
    "hypothyroidism": "thyroid_disorders",
    "hyperthyroidism": "thyroid_disorders",
    "joint replacement": "joint_replacement",
    "maternity": "maternity",
    "pregnancy": "maternity",
    "mental health": "mental_health",
    "depression": "mental_health",
    "anxiety": "mental_health",
    "obesity": "obesity_treatment",
    "hernia": "hernia",
    "cataract": "cataract"
}

class PolicyEngineAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0
        )

    def _check_exclusion_with_gemini(self, diagnosis, treatment_text, policy) -> dict:
        try:
            exclusions_list = "\n".join(f"- {e}" for e in policy.exclusions.conditions)
            prompt = f"""
You are an insurance policy exclusion checker for Indian health insurance.

DIAGNOSIS: {diagnosis or "Not specified"}
TREATMENT / LINE ITEMS: {treatment_text or "Not specified"}

EXCLUDED CONDITIONS AND PROCEDURES:
{exclusions_list}

Question: Does this diagnosis or treatment CLEARLY and DIRECTLY match any excluded condition?

IMPORTANT RULES:
- Medicines prescribed by a doctor for a diagnosed condition are NEVER excluded as supplements
- Vitamin C, B12, D3 prescribed alongside antibiotics or fever medication = COVERED (prescribed treatment, not supplement)
- Only flag "Health supplements and tonics" if the patient is buying supplements WITHOUT a diagnosis or prescription
- Only flag "Obesity" if the primary diagnosis IS obesity or weight loss
- Only flag "Cosmetic" if the procedure is purely aesthetic with no medical necessity
- Only flag "Experimental" if the treatment is not an approved standard of care
- When in doubt — do NOT flag as excluded

Answer ONLY with this JSON:
{{
  "is_excluded": true or false,
  "matched_exclusion": "exact exclusion that matched or null",
  "reason": "one line explanation"
}}

Be very strict — only flag if there is an OBVIOUS direct match.
A prescribed medicine is NEVER a supplement.
Return ONLY the JSON. No markdown.
"""
            response = self.llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception as e:
            return {"is_excluded": False, "matched_exclusion": None, "reason": f"Exclusion check failed: {str(e)}"}

    def run(self, state: ClaimState) -> ClaimState:
        try:
            policy      = get_policy()
            claim       = state["claim"]
            parsed_docs = state.get("parsed_documents", [])
            trace       = []
            rejection_reasons = []
            line_item_results = []
            approved_amount   = claim.claimed_amount
            copay_amount      = 0.0
            discount_amount   = 0.0
            is_partial        = False

            print(f"\n{'='*80}")
            print(f"[PolicyEngine] Processing {claim.claim_category} claim for Rs.{claim.claimed_amount}")
            print(f"{'='*80}")

            # ── 1. Find member ────────────────────────────────
            member = next(
                (m for m in policy.members if m.member_id == claim.member_id),
                None
            )

            if not member:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="member_eligibility",
                    result="FAIL",
                    detail=f"Member {claim.member_id} not found in policy",
                    timestamp=datetime.now().isoformat(),
                    data={"member_id": claim.member_id}
                ))
                rejection_reasons.append("MEMBER_NOT_FOUND")
                state["policy_result"] = PolicyResult(
                    decision="REJECTED",
                    approved_amount=0.0,
                    rejection_reasons=rejection_reasons,
                    trace=trace
                )
                state["component_status"]["policy_engine"] = "COMPLETED"
                return state

            trace.append(TraceEntry(
                agent="PolicyEngine",
                check="member_eligibility",
                result="PASS",
                detail=f"Member {member.name} found in policy",
                timestamp=datetime.now().isoformat(),
                data={"member_id": claim.member_id, "name": member.name}
            ))

            # ── 1b. Patient name consistency ──────────────────
            if parsed_docs:
                patient_names_in_docs = [
                    d.patient_name for d in parsed_docs if d.patient_name
                ]
                names_by_normalized = {}
                for name in patient_names_in_docs:
                    normalized = normalize_person_name(name)
                    if normalized:
                        names_by_normalized.setdefault(normalized, name)

                if len(names_by_normalized) > 1:
                    names_str = ", ".join(patient_names_in_docs)
                    print(f"  ❌ Patient name mismatch: {names_str}")
                    rejection_reasons.append("PATIENT_MISMATCH")
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="patient_name_consistency",
                        result="FAIL",
                        detail=f"Documents belong to different patients: {names_str}",
                        timestamp=datetime.now().isoformat(),
                        data={"patient_names": patient_names_in_docs}
                    ))
                    state["policy_result"] = PolicyResult(
                        decision="REJECTED",
                        approved_amount=0.0,
                        rejection_reasons=rejection_reasons,
                        trace=trace
                    )
                    state["component_status"]["policy_engine"] = "COMPLETED"
                    return state
                elif patient_names_in_docs:
                    doc_patient = next(iter(names_by_normalized.values()), patient_names_in_docs[0])
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="patient_name_consistency",
                        result="PASS",
                        detail=f"Patient name consistent: {doc_patient}",
                        timestamp=datetime.now().isoformat(),
                        data={"patient_name": doc_patient}
                    ))

            # ── 2. Dependent relationship check ───────────────
            if member.relationship != "SELF":
                covered_relationships = policy.coverage.family_floater.covered_relationships

                if member.relationship.upper() not in [r.upper() for r in covered_relationships]:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="dependent_eligibility",
                        result="FAIL",
                        detail=f"Relationship {member.relationship} is not covered. Covered: {', '.join(covered_relationships)}",
                        timestamp=datetime.now().isoformat(),
                        data={"relationship": member.relationship}
                    ))
                    rejection_reasons.append("RELATIONSHIP_NOT_COVERED")
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="dependent_eligibility",
                        result="PASS",
                        detail=f"Relationship {member.relationship} is covered under family floater",
                        timestamp=datetime.now().isoformat(),
                        data={"relationship": member.relationship}
                    ))

                primary_member = next(
                    (m for m in policy.members if m.member_id == member.primary_member_id),
                    None
                )
                join_date_str = primary_member.join_date if primary_member else None

                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="dependent_primary_member",
                    result="PASS" if primary_member else "FAIL",
                    detail=f"Primary member: {primary_member.name if primary_member else 'NOT FOUND'}",
                    timestamp=datetime.now().isoformat(),
                    data={"primary_member_id": member.primary_member_id}
                ))
            else:
                join_date_str = member.join_date

            # ── 3. Family floater limit ───────────────────────
            if member.relationship != "SELF":
                family_floater_limit = policy.coverage.family_floater.combined_limit
                ytd_amount = getattr(claim, 'ytd_claims_amount', 0.0) or 0.0

                if ytd_amount + claim.claimed_amount > family_floater_limit:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="family_floater_limit",
                        result="FAIL",
                        detail=f"Family floater limit Rs.{family_floater_limit} would be exceeded. YTD: Rs.{ytd_amount}, This claim: Rs.{claim.claimed_amount}",
                        timestamp=datetime.now().isoformat(),
                        data={"family_floater_limit": family_floater_limit, "ytd_amount": ytd_amount}
                    ))
                    rejection_reasons.append("FAMILY_FLOATER_LIMIT_EXCEEDED")
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="family_floater_limit",
                        result="PASS",
                        detail=f"Within family floater limit of Rs.{family_floater_limit}",
                        timestamp=datetime.now().isoformat(),
                        data={"family_floater_limit": family_floater_limit}
                    ))

            # ── 4. Initial waiting period ─────────────────────
            if join_date_str:
                join_date          = datetime.strptime(join_date_str, "%Y-%m-%d").date()
                treatment_date     = datetime.strptime(claim.treatment_date, "%Y-%m-%d").date()
                days_since_joining = (treatment_date - join_date).days
                initial_wait       = policy.waiting_periods.initial_waiting_period_days

                if days_since_joining < initial_wait:
                    eligible_date = join_date + timedelta(days=initial_wait)
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="initial_waiting_period",
                        result="FAIL",
                        detail=f"Member joined {join_date_str}. Initial waiting period is {initial_wait} days. Eligible from {eligible_date}.",
                        timestamp=datetime.now().isoformat(),
                        data={
                            "join_date": join_date_str,
                            "treatment_date": claim.treatment_date,
                            "waiting_days": initial_wait,
                            "eligible_from": str(eligible_date)
                        }
                    ))
                    rejection_reasons.append("INITIAL_WAITING_PERIOD")
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="initial_waiting_period",
                        result="PASS",
                        detail=f"Initial waiting period cleared. {days_since_joining} days since joining.",
                        timestamp=datetime.now().isoformat(),
                        data={"days_since_joining": days_since_joining}
                    ))
            else:
                days_since_joining = 9999
                treatment_date     = datetime.strptime(claim.treatment_date, "%Y-%m-%d").date()

            # ── 5. Diagnosis specific waiting period ──────────
            diagnosis = ""
            for doc in parsed_docs:
                if doc.diagnosis:
                    diagnosis = doc.diagnosis.lower()
                    break

            for keyword, condition_key in DIAGNOSIS_TO_WAITING.items():
                if keyword in diagnosis:
                    wait_days = policy.waiting_periods.specific_conditions.get(condition_key, 0)
                    if wait_days > 0 and days_since_joining < wait_days:
                        eligible_date = join_date + timedelta(days=wait_days)
                        trace.append(TraceEntry(
                            agent="PolicyEngine",
                            check=f"waiting_period.{condition_key}",
                            result="FAIL",
                            detail=f"{condition_key} waiting period is {wait_days} days. Eligible from {eligible_date}.",
                            timestamp=datetime.now().isoformat(),
                            data={
                                "join_date": join_date_str,
                                "waiting_days": wait_days,
                                "eligible_from": str(eligible_date),
                                "treatment_date": claim.treatment_date
                            }
                        ))
                        rejection_reasons.append("WAITING_PERIOD")
                    else:
                        trace.append(TraceEntry(
                            agent="PolicyEngine",
                            check=f"waiting_period.{condition_key}",
                            result="PASS",
                            detail=f"Waiting period for {condition_key} cleared.",
                            timestamp=datetime.now().isoformat(),
                            data={"days_since_joining": days_since_joining, "wait_days": wait_days}
                        ))
                    break

            # ── 6. Submission deadline ────────────────────────
            today                = datetime.now().date()
            deadline_days        = policy.submission_rules.deadline_days_from_treatment
            days_since_treatment = (today - treatment_date).days

            if days_since_treatment > deadline_days:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="submission_deadline",
                    result="FAIL",
                    detail=f"Claim submitted {days_since_treatment} days after treatment. Deadline is {deadline_days} days.",
                    timestamp=datetime.now().isoformat(),
                    data={"days_since_treatment": days_since_treatment, "deadline_days": deadline_days}
                ))
                rejection_reasons.append("SUBMISSION_DEADLINE_EXCEEDED")
            else:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="submission_deadline",
                    result="PASS",
                    detail=f"Submitted within deadline. {days_since_treatment} days since treatment.",
                    timestamp=datetime.now().isoformat(),
                    data={"days_since_treatment": days_since_treatment}
                ))

            # ── 7. Exclusion check — Gemini powered ──────────
            if claim.claim_category not in ["DENTAL", "VISION"]:
                treatment_text = " ".join(
                    str(item.get("description", ""))
                    for doc in parsed_docs
                    for item in (doc.line_items or [])
                )
                exclusion_result = self._check_exclusion_with_gemini(
                    diagnosis, treatment_text, policy
                )

                if exclusion_result.get("is_excluded"):
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="exclusion_check",
                        result="FAIL",
                        detail=f"Treatment matches excluded condition: {exclusion_result.get('matched_exclusion')}. {exclusion_result.get('reason')}",
                        timestamp=datetime.now().isoformat(),
                        data={"matched_exclusion": exclusion_result.get("matched_exclusion")}
                    ))
                    rejection_reasons.append("EXCLUDED_CONDITION")
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="exclusion_check",
                        result="PASS",
                        detail=f"No excluded conditions found. {exclusion_result.get('reason')}",
                        timestamp=datetime.now().isoformat(),
                        data={}
                    ))
            else:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="exclusion_check",
                    result="PASS",
                    detail=f"{claim.claim_category} — exclusions checked at line item level",
                    timestamp=datetime.now().isoformat(),
                    data={}
                ))

            # ── 8. Coverage check ─────────────────────────────
            category_key = claim.claim_category.lower()
            opd_category = policy.opd_categories.get(category_key)

            if not opd_category or not opd_category.covered:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="coverage_check",
                    result="FAIL",
                    detail=f"Category {claim.claim_category} is not covered under this policy",
                    timestamp=datetime.now().isoformat(),
                    data={"category": claim.claim_category}
                ))
                rejection_reasons.append("CATEGORY_NOT_COVERED")
            else:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="coverage_check",
                    result="PASS",
                    detail=f"Category {claim.claim_category} is covered. Sub-limit: Rs.{opd_category.sub_limit}",
                    timestamp=datetime.now().isoformat(),
                    data={"category": claim.claim_category, "sub_limit": opd_category.sub_limit}
                ))

            # ── 9. Pre authorization check ────────────────────
            if opd_category:
                high_value_tests   = opd_category.high_value_tests_requiring_pre_auth or []
                pre_auth_threshold = opd_category.pre_auth_threshold or 0
                needs_pre_auth     = False

                for doc in parsed_docs:
                    for item in (doc.line_items or []):
                        desc = str(item.get("description", "")).upper()
                        for test in high_value_tests:
                            if test.upper() in desc:
                                if claim.claimed_amount > pre_auth_threshold:
                                    needs_pre_auth = True

                if needs_pre_auth:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="pre_authorization",
                        result="FAIL",
                        detail=f"Pre-authorization required for this procedure above Rs.{pre_auth_threshold}. Please obtain pre-auth and resubmit.",
                        timestamp=datetime.now().isoformat(),
                        data={"pre_auth_threshold": pre_auth_threshold, "claimed_amount": claim.claimed_amount}
                    ))
                    rejection_reasons.append("PRE_AUTH_MISSING")
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="pre_authorization",
                        result="PASS",
                        detail="No pre-authorization required for this claim",
                        timestamp=datetime.now().isoformat(),
                        data={}
                    ))

            # ── 10. Minimum claim amount ──────────────────────
            min_claim = policy.submission_rules.minimum_claim_amount
            if claim.claimed_amount < min_claim:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="minimum_claim_amount",
                    result="FAIL",
                    detail=f"Claimed amount Rs.{claim.claimed_amount} is below minimum of Rs.{min_claim}",
                    timestamp=datetime.now().isoformat(),
                    data={"claimed_amount": claim.claimed_amount, "minimum": min_claim}
                ))
                rejection_reasons.append("BELOW_MINIMUM_CLAIM")
            else:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="minimum_claim_amount",
                    result="PASS",
                    detail=f"Claimed amount Rs.{claim.claimed_amount} meets minimum of Rs.{min_claim}",
                    timestamp=datetime.now().isoformat(),
                    data={}
                ))

            # ── 11. Line item check — DENTAL / VISION ─────────
            if claim.claim_category in ["DENTAL", "VISION"] and opd_category:
                excluded_procedures = (opd_category.excluded_procedures or []) + (opd_category.excluded_items or [])

                for doc in parsed_docs:
                    for item in (doc.line_items or []):
                        desc   = str(item.get("description", ""))
                        amount = float(item.get("amount", 0))
                        is_excluded = any(
                            ex.lower() in desc.lower()
                            for ex in excluded_procedures
                        )
                        if is_excluded:
                            line_item_results.append(LineItemResult(
                                description=desc,
                                amount=amount,
                                covered=False,
                                reason=f"Excluded procedure: {desc}"
                            ))
                            approved_amount -= amount
                            is_partial = True
                        else:
                            line_item_results.append(LineItemResult(
                                description=desc,
                                amount=amount,
                                covered=True,
                                reason="Covered procedure"
                            ))

                if is_partial:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="line_item_check",
                        result="FLAG",
                        detail=f"Some line items excluded. Approved amount after exclusions: Rs.{approved_amount}",
                        timestamp=datetime.now().isoformat(),
                        data={"line_items": [i.dict() for i in line_item_results]}
                    ))
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="line_item_check",
                        result="PASS",
                        detail="All line items covered",
                        timestamp=datetime.now().isoformat(),
                        data={}
                    ))

            # ── 12. Per claim limit ───────────────────────────
            if claim.claim_category not in ["DENTAL", "VISION", "ALTERNATIVE_MEDICINE"]:
                if claim.claimed_amount > policy.coverage.per_claim_limit:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="per_claim_limit",
                        result="FAIL",
                        detail=f"Claimed amount Rs.{claim.claimed_amount} exceeds per-claim limit of Rs.{policy.coverage.per_claim_limit}",
                        timestamp=datetime.now().isoformat(),
                        data={
                            "claimed_amount": claim.claimed_amount,
                            "per_claim_limit": policy.coverage.per_claim_limit
                        }
                    ))
                    rejection_reasons.append("PER_CLAIM_EXCEEDED")
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="per_claim_limit",
                        result="PASS",
                        detail=f"Claimed amount Rs.{claim.claimed_amount} within per-claim limit of Rs.{policy.coverage.per_claim_limit}",
                        timestamp=datetime.now().isoformat(),
                        data={
                            "claimed_amount": claim.claimed_amount,
                            "per_claim_limit": policy.coverage.per_claim_limit
                        }
                    ))
            else:
                trace.append(TraceEntry(
                    agent="PolicyEngine",
                    check="per_claim_limit",
                    result="PASS",
                    detail=f"{claim.claim_category} uses category sub-limit of Rs.{opd_category.sub_limit if opd_category else 'N/A'} — per-claim limit not applied",
                    timestamp=datetime.now().isoformat(),
                    data={}
                ))

            # ── 13. Sub limit check ───────────────────────────
            if opd_category:
                sub_limit = opd_category.sub_limit
                if approved_amount > sub_limit:
                    approved_amount = sub_limit
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="sub_limit",
                        result="FLAG",
                        detail=f"Approved amount Rs.{approved_amount} exceeds sub-limit Rs.{sub_limit}. Capping at sub-limit.",
                        timestamp=datetime.now().isoformat(),
                        data={"approved_amount": approved_amount, "sub_limit": sub_limit}
                    ))
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="sub_limit",
                        result="PASS",
                        detail=f"Approved amount Rs.{approved_amount} within sub-limit Rs.{sub_limit}",
                        timestamp=datetime.now().isoformat(),
                        data={"approved_amount": approved_amount, "sub_limit": sub_limit}
                    ))

            # ── 14. Network discount + copay ──────────────────
            if not rejection_reasons and opd_category:
                hospital_name = claim.hospital_name or ""
                for doc in parsed_docs:
                    if doc.hospital_name:
                        hospital_name = doc.hospital_name
                        break

                is_network = any(
                    n.lower() in hospital_name.lower()
                    for n in policy.network_hospitals
                ) if hospital_name else False

                if is_network:
                    network_discount = opd_category.network_discount_percent / 100
                    discount_amount  = approved_amount * network_discount
                    approved_amount  = approved_amount - discount_amount
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="network_discount",
                        result="PASS",
                        detail=f"Network hospital discount of {opd_category.network_discount_percent}% applied. Discount: Rs.{discount_amount:.2f}",
                        timestamp=datetime.now().isoformat(),
                        data={
                            "hospital": hospital_name,
                            "discount_percent": opd_category.network_discount_percent,
                            "discount_amount": discount_amount
                        }
                    ))
                else:
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="network_discount",
                        result="PASS",
                        detail=f"Non-network hospital. No discount applied.",
                        timestamp=datetime.now().isoformat(),
                        data={"hospital": hospital_name}
                    ))

                copay_percent = opd_category.copay_percent / 100
                if copay_percent > 0:
                    copay_amount    = approved_amount * copay_percent
                    approved_amount = approved_amount - copay_amount
                    trace.append(TraceEntry(
                        agent="PolicyEngine",
                        check="copay",
                        result="PASS",
                        detail=f"Co-pay of {opd_category.copay_percent}% applied. Co-pay: Rs.{copay_amount:.2f}",
                        timestamp=datetime.now().isoformat(),
                        data={
                            "copay_percent": opd_category.copay_percent,
                            "copay_amount": copay_amount
                        }
                    ))

            # ── 15. Final decision ────────────────────────────
            if rejection_reasons:
                decision        = "REJECTED"
                approved_amount = 0.0
            elif is_partial:
                decision = "PARTIAL"
            else:
                decision = "APPROVED"

            state["policy_result"] = PolicyResult(
                decision=decision,
                approved_amount=round(approved_amount, 2),
                rejection_reasons=rejection_reasons,
                line_item_results=line_item_results,
                copay_amount=round(copay_amount, 2),
                discount_amount=round(discount_amount, 2),
                trace=trace
            )
            state["component_status"]["policy_engine"] = "COMPLETED"

            print(f"\n[PolicyEngine] Decision: {decision}")
            print(f"  Approved: Rs.{round(approved_amount, 2)} | Copay: Rs.{round(copay_amount, 2)} | Discount: Rs.{round(discount_amount, 2)}")
            if rejection_reasons:
                print(f"  Rejections: {', '.join(rejection_reasons)}")
            print(f"{'='*80}\n")

        except Exception as e:
            trace_entry = TraceEntry(
                agent="PolicyEngine",
                check="policy_engine",
                result="FAIL",
                detail=f"Policy engine failed: {str(e)}",
                timestamp=datetime.now().isoformat(),
                data={}
            )
            state["policy_result"] = PolicyResult(
                decision="MANUAL_REVIEW",
                approved_amount=0.0,
                rejection_reasons=["POLICY_ENGINE_ERROR"],
                trace=[trace_entry]
            )
            state["component_status"]["policy_engine"] = "FAILED"
            state["confidence_score"] -= 0.35
            print(f"\n[PolicyEngine] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"{'='*80}\n")

        return state
