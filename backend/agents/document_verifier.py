import json
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from graph.state import ClaimState
from models.decision import VerificationResult, VerificationError, TraceEntry
import os
from dotenv import load_dotenv

load_dotenv()

DOCUMENT_REQUIREMENTS = {
    "CONSULTATION":         ["PRESCRIPTION", "HOSPITAL_BILL"],
    "DIAGNOSTIC":           ["PRESCRIPTION", "LAB_REPORT", "HOSPITAL_BILL"],
    "PHARMACY":             ["PRESCRIPTION", "PHARMACY_BILL"],
    "DENTAL":               ["HOSPITAL_BILL"],
    "VISION":               ["PRESCRIPTION", "HOSPITAL_BILL"],
    "ALTERNATIVE_MEDICINE": ["PRESCRIPTION", "HOSPITAL_BILL"],
}

class DocumentVerifierAgent:
    def run(self, state: ClaimState) -> ClaimState:
        try:
            claim            = state["claim"]
            classified       = state.get("classified_documents", [])
            errors           = []
            trace            = []
            required_docs    = DOCUMENT_REQUIREMENTS.get(claim.claim_category, [])

            # get detected types from classifier
            detected_types   = [c.detected_type for c in classified]
            unreadable_docs  = [c for c in classified if not c.is_readable]

            print(f"\n{'='*80}")
            print(f"[DocumentVerifier] Verifying {claim.claim_category} claim")
            print(f"{'='*80}")
            print(f"  Required documents: {', '.join(required_docs)}")
            print(f"  Detected documents: {', '.join(detected_types) if detected_types else 'NONE'}")
            print(f"  Readable documents: {len([c for c in classified if c.is_readable])}/{len(classified)}")
            print()

            # ── 1. Readability check ──────────────────────────
            for doc in unreadable_docs:
                print(f"  ❌ UNREADABLE: {doc.file_name}")
                errors.append(VerificationError(
                    error_type="UNREADABLE_DOCUMENT",
                    doc_found=doc.detected_type,
                    doc_required=doc.detected_type,
                    detail=f"The document '{doc.file_name or doc.file_id}' is blurry or unreadable. Please re-upload a clear photo of this document."
                ))
                trace.append(TraceEntry(
                    agent="DocumentVerifier",
                    check="readability_check",
                    result="FAIL",
                    detail=f"Document {doc.file_name or doc.file_id} is unreadable. Reason: {doc.reason}",
                    timestamp=datetime.now().isoformat(),
                    data={"file_id": doc.file_id, "reason": doc.reason}
                ))

            if not unreadable_docs:
                print(f"  ✓ All documents are readable")
                trace.append(TraceEntry(
                    agent="DocumentVerifier",
                    check="readability_check",
                    result="PASS",
                    detail="All documents are readable",
                    timestamp=datetime.now().isoformat(),
                    data={}
                ))

            # ── 2. Document type check ────────────────────────
            for required_type in required_docs:
                if required_type not in detected_types:
                    # find what was uploaded instead
                    uploaded_types = ", ".join(detected_types) if detected_types else "no documents"
                    print(f"  ❌ MISSING: {required_type} (found: {uploaded_types})")
                    errors.append(VerificationError(
                        error_type="WRONG_DOCUMENT_TYPE",
                        doc_found=uploaded_types,
                        doc_required=required_type,
                        detail=f"Your {claim.claim_category.replace('_',' ').lower()} claim requires a {required_type.replace('_',' ').lower()}. You uploaded: {uploaded_types.replace('_',' ').lower()}. Please upload the missing {required_type.replace('_',' ').lower()}."
                    ))
                    trace.append(TraceEntry(
                        agent="DocumentVerifier",
                        check="document_type_check",
                        result="FAIL",
                        detail=f"Required {required_type} not found. Detected: {uploaded_types}",
                        timestamp=datetime.now().isoformat(),
                        data={
                            "required": required_type,
                            "detected": detected_types
                        }
                    ))
                else:
                    print(f"  ✓ Found: {required_type}")
                    trace.append(TraceEntry(
                        agent="DocumentVerifier",
                        check="document_type_check",
                        result="PASS",
                        detail=f"{required_type} found in uploaded documents",
                        timestamp=datetime.now().isoformat(),
                        data={"required": required_type}
                    ))

            # ── 3. Patient name consistency check ─────────────
            patient_names = list(set(
                c.file_name for c in classified
                if c.file_name and c.is_readable
            ))

            # we rely on parser for actual name extraction
            # here just flag if we have readable docs
            if len(classified) > 0 and not unreadable_docs:
                trace.append(TraceEntry(
                    agent="DocumentVerifier",
                    check="patient_consistency",
                    result="PASS",
                    detail="Patient name consistency will be verified during parsing",
                    timestamp=datetime.now().isoformat(),
                    data={}
                ))
                print(f"  ✓ Patient name consistency check deferred to parser stage")

            is_valid = len(errors) == 0

            state["verification_result"] = VerificationResult(
                is_valid=is_valid,
                errors=errors,
                trace=trace
            )
            state["component_status"]["document_verifier"] = "COMPLETED"
            state["trace"] = state.get("trace", []) + trace
            
            print(f"\n[DocumentVerifier] Result: {'✓ PASS' if is_valid else '✗ FAIL'}")
            if not is_valid:
                for err in errors:
                    print(f"  • {err.error_type}: {err.detail}")
            print(f"{'='*80}\n")

        except Exception as e:
            trace_entry = TraceEntry(
                agent="DocumentVerifier",
                check="document_verification",
                result="FAIL",
                detail=f"Verifier failed: {str(e)}",
                timestamp=datetime.now().isoformat(),
                data={}
            )
            state["verification_result"] = VerificationResult(
                is_valid=False,
                errors=[VerificationError(
                    error_type="VERIFIER_ERROR",
                    detail=f"Document verification could not be completed: {str(e)}"
                )]
            )
            state["trace"] = state.get("trace", []) + [trace_entry]
            state["component_status"]["document_verifier"] = "FAILED"
            state["confidence_score"] -= 0.2

        return state