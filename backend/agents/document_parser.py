import json
import base64
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from graph.state import ClaimState
from models.decision import ParsedDocument, TraceEntry
from prompts.parser_prompt import PARSER_PROMPT
from services.name_normalizer import normalize_person_name
import os
from dotenv import load_dotenv

load_dotenv()

class DocumentParserAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0
        )

    def run(self, state: ClaimState) -> ClaimState:
        claim = state["claim"]
        parsed_documents = []

        print(f"\n{'='*80}")
        print(f"[DocumentParser] Parsing {len(claim.documents)} document(s)")
        print(f"{'='*80}")

        for doc in claim.documents:
            try:
                content = doc.content
                has_real_file = (
                    content is not None and
                    isinstance(content, dict) and
                    content.get("base64_data") is not None
                ) or (
                    hasattr(content, 'base64_data') and
                    content.base64_data is not None
                )

                mode_name = "Vision API" if has_real_file else "Structured"
                print(f"  📄 {doc.file_name} ({doc.actual_type}): Parsing with {mode_name}...")

                if has_real_file:
                    parsed_doc = self._parse_real_file(doc)
                else:
                    parsed_doc = self._parse_structured(doc)

                parsed_documents.append(parsed_doc)
                print(f"    ✓ Parsed | Patient: {parsed_doc.patient_name or 'N/A'} | Confidence: {parsed_doc.confidence}")

                if parsed_doc.diagnosis:
                    print(f"      └─ Diagnosis: {parsed_doc.diagnosis}")
                if parsed_doc.doctor_name:
                    print(f"      └─ Doctor: {parsed_doc.doctor_name}")
                if parsed_doc.hospital_name:
                    print(f"      └─ Hospital: {parsed_doc.hospital_name}")
                if parsed_doc.line_items:
                    print(f"      └─ {len(parsed_doc.line_items)} items extracted")

                trace_entry = TraceEntry(
                    agent="DocumentParser",
                    check=f"parse_{doc.actual_type}_{doc.file_id}",
                    result="PASS",
                    detail=f"Parsed {doc.actual_type} using {'vision' if has_real_file else 'structured'} mode. Confidence: {parsed_doc.confidence}",
                    timestamp=datetime.now().isoformat(),
                    data={
                        "file_id": doc.file_id,
                        "confidence": parsed_doc.confidence,
                        "mode": "vision" if has_real_file else "structured"
                    }
                )
                state["trace"].append(trace_entry)

                if parsed_doc.confidence == "LOW":
                    state["confidence_score"] -= 0.1

            except Exception as e:
                print(f"    ❌ ERROR parsing {doc.file_name}: {str(e)}")
                import traceback
                traceback.print_exc()

                trace_entry = TraceEntry(
                    agent="DocumentParser",
                    check=f"parse_{doc.actual_type}_{doc.file_id}",
                    result="FAIL",
                    detail=f"Failed to parse {doc.file_id}: {str(e)}",
                    timestamp=datetime.now().isoformat(),
                    data={"file_id": doc.file_id}
                )
                state["trace"].append(trace_entry)
                state["confidence_score"] -= 0.2

        state["parsed_documents"] = parsed_documents
        state["component_status"]["document_parser"] = "COMPLETED"

        # ── Cross-document validation ──────────────────────
        print(f"\n[DocumentParser] Cross-Document Validation:")

        if parsed_documents:

            # 1. Patient name consistency
            patient_names = [d.patient_name for d in parsed_documents if d.patient_name]
            names_by_normalized = {}
            for name in patient_names:
                normalized = normalize_person_name(name)
                if normalized:
                    names_by_normalized.setdefault(normalized, name)

            if len(names_by_normalized) > 1:
                names_display = ", ".join(
                    d.patient_name for d in parsed_documents if d.patient_name
                )
                print(f"  ❌ Patient name mismatch: {names_display}")
                from models.decision import VerificationResult, VerificationError
                state["verification_result"] = VerificationResult(
                    is_valid=False,
                    errors=[VerificationError(
                        error_type="PATIENT_MISMATCH",
                        doc_found=names_display,
                        doc_required="Same patient name on all documents",
                        detail=f"Patient names do not match across documents: {names_display}. All documents must belong to the same patient."
                    )]
                )
                state["trace"].append(TraceEntry(
                    agent="DocumentParser",
                    check="patient_name_consistency",
                    result="FAIL",
                    detail=f"Patient name mismatch found: {names_display}",
                    timestamp=datetime.now().isoformat(),
                    data={"patient_names": patient_names}
                ))
                state["component_status"]["document_parser"] = "COMPLETED"
                return state
            elif patient_names:
                patient_name = next(iter(names_by_normalized.values()), patient_names[0])
                print(f"  ✓ Patient name consistent: {patient_names[0]}")
                state["trace"].append(TraceEntry(
                    agent="DocumentParser",
                    check="patient_name_consistency",
                    result="PASS",
                    detail=f"Patient name consistent across all documents: {patient_name}",
                    timestamp=datetime.now().isoformat(),
                    data={"patient_name": patient_name}
                ))

            # 2. Date consistency
            dates        = [d.date for d in parsed_documents if d.date]
            unique_dates = set(dates)

            if len(unique_dates) > 1:
                print(f"  ⚠️  Different dates found: {', '.join(unique_dates)}")
                state["confidence_score"] -= 0.1
                state["trace"].append(TraceEntry(
                    agent="DocumentParser",
                    check="date_consistency",
                    result="FLAG",
                    detail=f"Different dates found across documents: {', '.join(unique_dates)}. Please verify treatment dates.",
                    timestamp=datetime.now().isoformat(),
                    data={"dates": list(unique_dates)}
                ))
            elif dates:
                print(f"  ✓ Date consistent: {dates[0]}")
                state["trace"].append(TraceEntry(
                    agent="DocumentParser",
                    check="date_consistency",
                    result="PASS",
                    detail=f"Treatment date consistent across documents: {dates[0]}",
                    timestamp=datetime.now().isoformat(),
                    data={"date": dates[0]}
                ))

            # 3. Doctor name cross-validation
            prescription_docs      = [d for d in parsed_documents if d.doc_type == "PRESCRIPTION"]
            bill_docs_with_doctor  = [
                d for d in parsed_documents
                if d.doctor_name and d.doc_type in ["HOSPITAL_BILL", "LAB_REPORT"]
            ]

            if prescription_docs and bill_docs_with_doctor:
                rx_doctor = prescription_docs[0].doctor_name
                for bill in bill_docs_with_doctor:
                    if rx_doctor and bill.doctor_name:
                        rx_last   = rx_doctor.split()[-1].lower()
                        bill_last = bill.doctor_name.split()[-1].lower()
                        if rx_last != bill_last:
                            print(f"  ⚠️  Doctor mismatch: Prescription={rx_doctor}, Bill={bill.doctor_name}")
                            state["confidence_score"] -= 0.1
                            state["trace"].append(TraceEntry(
                                agent="DocumentParser",
                                check="doctor_name_consistency",
                                result="FLAG",
                                detail=f"Doctor name differs: Prescription has {rx_doctor}, Bill has {bill.doctor_name}",
                                timestamp=datetime.now().isoformat(),
                                data={"rx_doctor": rx_doctor, "bill_doctor": bill.doctor_name}
                            ))
                        else:
                            print(f"  ✓ Doctor name consistent: {rx_doctor}")
                            state["trace"].append(TraceEntry(
                                agent="DocumentParser",
                                check="doctor_name_consistency",
                                result="PASS",
                                detail=f"Doctor name consistent: {rx_doctor}",
                                timestamp=datetime.now().isoformat(),
                                data={"doctor": rx_doctor}
                            ))

            # 4. Claimed amount vs bill total
            bill_docs = [
                d for d in parsed_documents
                if d.doc_type in ["HOSPITAL_BILL", "PHARMACY_BILL"]
            ]
            for bill in bill_docs:
                if bill.total_amount and claim.claimed_amount:
                    diff = abs(bill.total_amount - claim.claimed_amount)
                    if diff > 50:
                        print(f"  ⚠️  Amount mismatch: Bill=₹{bill.total_amount}, Claimed=₹{claim.claimed_amount}")
                        state["confidence_score"] -= 0.1
                        state["trace"].append(TraceEntry(
                            agent="DocumentParser",
                            check="amount_cross_validation",
                            result="FLAG",
                            detail=f"Bill total Rs.{bill.total_amount} differs from claimed amount Rs.{claim.claimed_amount}. Difference: Rs.{diff:.2f}",
                            timestamp=datetime.now().isoformat(),
                            data={
                                "bill_total":     bill.total_amount,
                                "claimed_amount": claim.claimed_amount,
                                "difference":     diff
                            }
                        ))
                    else:
                        print(f"  ✓ Amount matches: ₹{bill.total_amount}")
                        state["trace"].append(TraceEntry(
                            agent="DocumentParser",
                            check="amount_cross_validation",
                            result="PASS",
                            detail=f"Bill total Rs.{bill.total_amount} matches claimed amount Rs.{claim.claimed_amount}",
                            timestamp=datetime.now().isoformat(),
                            data={}
                        ))

            # 5. Extracted details summary
            print(f"\n  Extracted Details Summary:")
            for doc in parsed_documents:
                print(f"    {doc.doc_type}:")
                details = []
                if doc.patient_name:  details.append(f"Patient={doc.patient_name}")
                if doc.doctor_name:   details.append(f"Doctor={doc.doctor_name}")
                if doc.hospital_name: details.append(f"Hospital={doc.hospital_name}")
                if doc.diagnosis:     details.append(f"Diagnosis={doc.diagnosis}")
                if doc.date:          details.append(f"Date={doc.date}")
                if doc.total_amount:  details.append(f"Total=₹{doc.total_amount}")
                if details:
                    for detail in details:
                        print(f"      • {detail}")
                else:
                    print(f"      ⚠️  No extracted details")

        print(f"{'='*80}\n")

        # simulate failure for TC011
        if state.get("claim") and state["claim"].simulate_component_failure:
            state["component_status"]["document_parser"] = "FAILED"
            state["confidence_score"] -= 0.2
            state["trace"].append(TraceEntry(
                agent="DocumentParser",
                check="simulated_failure",
                result="FAIL",
                detail="Component failure simulated as requested",
                timestamp=datetime.now().isoformat(),
                data={}
            ))

        return state

    # ── Mode 1: Real file — Gemini Vision ─────────────────
    def _parse_real_file(self, doc) -> ParsedDocument:
        content = doc.content

        if isinstance(content, dict):
            b64_data  = content.get("base64_data")
            mime_type = content.get("mime_type", "image/jpeg")
        else:
            b64_data  = getattr(content, "base64_data", None)
            mime_type = getattr(content, "mime_type", "image/jpeg")

        prompt_text = f"""
You are a medical document parser for Indian health insurance claims.

Read this {doc.actual_type.replace('_', ' ').lower()} carefully and extract all information.

Return ONLY a JSON object with these fields:
{{
  "file_id": "{doc.file_id}",
  "doc_type": "{doc.actual_type}",
  "patient_name": "full name or null",
  "doctor_name": "full name or null",
  "doctor_registration": "registration number or null",
  "diagnosis": "diagnosis or null",
  "treatment": "treatment description or null",
  "hospital_name": "hospital or clinic name or null",
  "date": "date in YYYY-MM-DD format or null",
  "line_items": [
    {{"description": "item name", "amount": 0.0}}
  ],
  "total_amount": 0.0,
  "confidence": "HIGH or MEDIUM or LOW"
}}

Set confidence LOW if document is blurry or fields are missing.
Return ONLY the JSON. No markdown. No explanation.
"""

        message = HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{b64_data}"
                }
            },
            {
                "type": "text",
                "text": prompt_text
            }
        ])

        response = self.llm.invoke([message])
        raw = self._clean_json(response.content)

        try:
            result_data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"    [JSON ERROR] Failed to parse Gemini response: {str(e)}")
            print(f"    [RAW] {raw[:200]}...")
            raise ValueError(f"Invalid JSON from Gemini: {str(e)}")

        return self._build_parsed_doc(result_data, doc)

    # ── Mode 2: Structured JSON content (test cases) ───────
    def _parse_structured(self, doc) -> ParsedDocument:
        content = doc.content

        if content is None:
            return ParsedDocument(
                file_id=doc.file_id,
                doc_type=doc.actual_type,
                patient_name=doc.patient_name_on_doc,
                confidence="LOW"
            )

        if hasattr(content, 'dict'):
            content_dict = content.dict()
        elif isinstance(content, dict):
            content_dict = content
        else:
            content_dict = {}

        content_str = json.dumps(content_dict, indent=2)

        prompt = PARSER_PROMPT.format(
            file_id=doc.file_id,
            doc_type=doc.actual_type,
            content=content_str
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        raw = self._clean_json(response.content)

        try:
            result_data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"    [JSON ERROR] Failed to parse Gemini response: {str(e)}")
            print(f"    [RAW] {raw[:200]}...")
            raise ValueError(f"Invalid JSON from Gemini: {str(e)}")

        return self._build_parsed_doc(result_data, doc)

    # ── shared helpers ─────────────────────────────────────
    def _clean_json(self, raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return raw.strip()

    def _build_parsed_doc(self, result_data: dict, doc) -> ParsedDocument:
        return ParsedDocument(
            file_id=result_data.get("file_id", doc.file_id),
            doc_type=result_data.get("doc_type", doc.actual_type),
            patient_name=result_data.get("patient_name") or doc.patient_name_on_doc,
            doctor_name=result_data.get("doctor_name"),
            doctor_registration=result_data.get("doctor_registration"),
            diagnosis=result_data.get("diagnosis"),
            treatment=result_data.get("treatment"),
            hospital_name=result_data.get("hospital_name"),
            date=result_data.get("date"),
            line_items=result_data.get("line_items", []),
            total_amount=result_data.get("total_amount"),
            confidence=result_data.get("confidence", "HIGH"),
            raw=result_data
        )
