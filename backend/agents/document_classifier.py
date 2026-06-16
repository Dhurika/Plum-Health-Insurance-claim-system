import json
import base64
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from graph.state import ClaimState
from models.decision import TraceEntry
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class ClassifiedDocument(BaseModel):
    file_id: str
    file_name: Optional[str] = None
    detected_type: str
    is_readable: bool
    confidence: str
    reason: Optional[str] = None

CLASSIFIER_PROMPT = """
You are a medical document classifier for an Indian health insurance system.

Look at this document carefully and answer two things:
1. What type of document is this?
2. Is it readable and clear enough to extract information from?

Document types you must identify:
- PRESCRIPTION — doctor's prescription with medicines, diagnosis, doctor name
- HOSPITAL_BILL — any invoice or bill from a hospital, clinic, or dental clinic showing charges and amounts. This includes dental clinic bills, eye clinic bills, pharmacy invoices, consultation bills.
- LAB_REPORT — diagnostic or pathology lab test results with test values and normal ranges
- PHARMACY_BILL — pharmacy receipt specifically showing medicine names, quantities and amounts
- DENTAL_REPORT — a clinical dental examination report or treatment notes (NOT a bill or invoice)
- UNKNOWN — cannot identify the document type

IMPORTANT RULES:
- Any document that is an INVOICE or BILL from any medical provider → HOSPITAL_BILL
- A dental clinic invoice showing treatment charges → HOSPITAL_BILL
- Only classify as DENTAL_REPORT if it is a clinical report or examination notes, not a bill
- Only classify as PHARMACY_BILL if it is specifically from a pharmacy shop

Return ONLY this JSON:
{{
  "detected_type": "PRESCRIPTION or HOSPITAL_BILL or LAB_REPORT or PHARMACY_BILL or DENTAL_REPORT or UNKNOWN",
  "is_readable": true or false,
  "confidence": "HIGH or MEDIUM or LOW",
  "reason": "one line explanation of what you saw"
}}

If the document is blurry, dark, or you cannot read key fields → set is_readable to false.
Return ONLY the JSON. No markdown. No explanation.
"""

class DocumentClassifierAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0
        )

    def run(self, state: ClaimState) -> ClaimState:
        claim = state["claim"]
        classified = []
        trace = []
        
        print(f"\n{'='*80}")
        print(f"[DocumentClassifier] Processing {len(claim.documents)} document(s)")
        print(f"{'='*80}")

        for doc in claim.documents:
            try:
                content = doc.content

                # check if real file uploaded
                has_file = False
                b64_data = None
                mime_type = "image/jpeg"

                if content is not None:
                    if isinstance(content, dict):
                        b64_data  = content.get("base64_data")
                        mime_type = content.get("mime_type", "image/jpeg")
                    else:
                        b64_data  = getattr(content, "base64_data", None)
                        mime_type = getattr(content, "mime_type", "image/jpeg")

                has_file = b64_data is not None

                if has_file:
                    print(f"  📄 {doc.file_name or doc.file_id}: Sending to Gemini Vision...")
                    # send to Gemini Vision to classify
                    prompt_text = CLASSIFIER_PROMPT.format(declared_type=doc.actual_type)
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
                    result = json.loads(raw)

                    detected_type = result.get("detected_type", "UNKNOWN")
                    # Default to True (readable) unless explicitly set to False
                    is_readable   = result.get("is_readable", True)
                    confidence    = result.get("confidence", "MEDIUM")
                    reason        = result.get("reason", "Classification completed")
                    
                    print(f"    ✓ Detected: {detected_type} | Readable: {is_readable} | Confidence: {confidence}")
                    print(f"    └─ Reason: {reason}")

                else:
                    # no real file — use the actual_type from input
                    # this handles test cases with structured JSON
                    detected_type = doc.actual_type
                    is_readable   = doc.quality != "UNREADABLE"
                    confidence    = "HIGH"
                    reason        = "Structured test data — type taken from input"
                    print(f"  📋 {doc.file_name or doc.file_id}: Using structured data")
                    print(f"    ✓ Type: {detected_type} | Readable: {is_readable}")

                classified.append(ClassifiedDocument(
                    file_id=doc.file_id,
                    file_name=doc.file_name,
                    detected_type=detected_type,
                    is_readable=is_readable,
                    confidence=confidence,
                    reason=reason
                ))

                trace.append(TraceEntry(
                    agent="DocumentClassifier",
                    check=f"classify_{doc.file_id}",
                    result="PASS" if is_readable else "FAIL",
                    detail=f"{doc.file_name or doc.file_id} → {detected_type} | Readable: {is_readable} | {reason}",
                    timestamp=datetime.now().isoformat(),
                    data={
                        "file_id":      doc.file_id,
                        "detected_type": detected_type,
                        "is_readable":  is_readable,
                        "confidence":   confidence
                    }
                ))

            except Exception as e:
                classified.append(ClassifiedDocument(
                    file_id=doc.file_id,
                    file_name=doc.file_name,
                    detected_type="UNKNOWN",
                    is_readable=False,
                    confidence="LOW",
                    reason=f"Classification failed: {str(e)}"
                ))
                trace.append(TraceEntry(
                    agent="DocumentClassifier",
                    check=f"classify_{doc.file_id}",
                    result="FAIL",
                    detail=f"Failed to classify {doc.file_id}: {str(e)}",
                    timestamp=datetime.now().isoformat(),
                    data={"file_id": doc.file_id}
                ))
                print(f"[ERROR] Classification failed for {doc.file_name}: {str(e)}")

        state["classified_documents"] = classified
        state["component_status"]["document_classifier"] = "COMPLETED"
        state["trace"] = state.get("trace", []) + trace
        
        print(f"\n[DocumentClassifier] Summary:")
        for c in classified:
            print(f"  • {c.file_name}: {c.detected_type} (readable={c.is_readable})")
        print(f"{'='*80}\n")
        
        return state

    def _clean_json(self, raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            raw = raw.strip()  # Strip whitespace after extraction
            if raw.startswith("json"):
                raw = raw[4:].strip()  # Remove "json" prefix and strip again
        return raw.strip()