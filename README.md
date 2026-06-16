# Plum AI — Health Insurance Claims Processing System

AI-powered claims processing pipeline that automates health insurance claim decisions for Plum's Group Health Insurance platform.

---

## What This Does

When an employee submits a health insurance claim, the system:

1. Reads each uploaded document using Gemini Vision
2. Verifies the right documents are present
3. Extracts structured data from prescriptions, bills, and lab reports
4. Applies all policy rules from the insurance policy
5. Checks for fraud patterns
6. Produces a decision — APPROVED, PARTIAL, REJECTED, or MANUAL_REVIEW — with a full audit trace

---

## Project Structure
Plum AI/

├── backend/

│   ├── main.py                    # FastAPI entry point

│   ├── requirements.txt

│   ├── .env                       # API keys (not committed)

│   ├── agents/

│   │   ├── document_classifier.py # Agent 1 — identify document types

│   │   ├── document_verifier.py   # Agent 2 — check required docs present

│   │   ├── document_parser.py     # Agent 3 — extract fields from documents

│   │   ├── policy_engine.py       # Agent 4 — apply policy rules

│   │   ├── fraud_detector.py      # Agent 5 — detect suspicious patterns

│   │   └── decision_agent.py      # Agent 6 — final decision + explanation

│   ├── graph/

│   │   ├── state.py               # ClaimState — shared state schema

│   │   ├── pipeline.py            # LangGraph graph definition

│   │   └── runner.py              # Pipeline entry point

│   ├── models/

│   │   ├── claim.py               # ClaimInput, DocumentInput

│   │   ├── decision.py            # ClaimDecision, TraceEntry

│   │   └── policy.py              # PolicyConfig, Member

│   ├── services/

│   │   ├── policy_loader.py       # Loads policy_terms.json at startup

│   │   └── claims_store.py        # In-memory claim history

│   ├── prompts/

│   │   ├── verifier_prompt.py     # Prompt templates

│   │   └── parser_prompt.py

│   ├── tests/

│   │   ├── test_policy_engine.py

│   │   ├── test_fraud_detector.py

│   │   ├── test_document_verifier.py

│   │   └── test_pipeline.py

│   └── data/

│       ├── policy_terms.json      # Policy configuration

│       └── test_cases.json        # 12 eval test cases

├── frontend/

│   └── app.py                     # Streamlit UI

│   └── .streamlit/

│       └── config.toml            # Light theme config

├── eval/

│   └── run_eval.py                # Runs all 12 test cases

├── docs/

│   ├── architecture.md

│   ├── contracts.md

│   └── eval_report.md

└── README.md

---

## Setup

### Prerequisites

- Python 3.10 or higher
- A Google Gemini API key (free tier works)
  - Get one at https://aistudio.google.com

---

### Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd "Plum AI"
```

---

### Step 2 — Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

### Step 3 — Add your API key

Create a `.env` file inside the `backend/` folder:
GOOGLE_API_KEY=your_gemini_api_key_here

---

### Step 4 — Run the backend

```bash
cd backend
uvicorn main:app --reload
```

You should see:
Policy loaded successfully

INFO: Uvicorn running on http://127.0.0.1:8000

---

### Step 5 — Run the frontend

Open a second terminal:

```bash
cd "Plum AI/frontend"
streamlit run app.py
```

The UI opens at http://localhost:8501

---

## How to Submit a Claim

1. Select the employee from the dropdown
2. Select who the claim is for (self or dependent)
3. Choose treatment type
4. Enter treatment date and total bill amount
5. Enter hospital name if applicable
6. Upload your documents (prescription, bill, lab report)
7. Click Submit Claim

The system processes the claim and returns a decision with full audit trace.

---

## Running the Eval Report

To run all 12 test cases:

```bash
cd backend
python ../eval/run_eval.py
```

Results are printed to console and saved to `docs/eval_report.md`.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /claims/submit | Submit a claim |
| GET | /claims/history/{member_id} | Get claim history |
| GET | /policy/members | Get all members and dependents |
| GET | /policy/info | Get policy summary |

---

## Policy Configuration

All policy rules are loaded from `backend/data/policy_terms.json` at startup. No rules are hardcoded. To change any rule — waiting periods, sub-limits, co-pay percentages, network hospitals — edit the JSON file and restart the backend.

---

## Key Design Decisions

**LLMs for understanding, Python for calculation**
Gemini Vision reads and classifies documents. All financial calculations — co-pay, network discount, sub-limits, waiting periods — are pure Python. This makes the most critical part of the system deterministic and fully testable.

**Multi-agent pipeline**
Each agent has one job. Document Classifier identifies types. Document Verifier checks requirements. Document Parser extracts data. Policy Engine applies rules. Fraud Detector checks patterns. Decision Agent produces the final output. Failures in one agent do not crash the system — the pipeline continues and reflects the degraded state in the output.

**Early exit on document problems**
Document issues are caught before any processing begins. The member gets a specific, actionable error message — not a generic failure.

---

## Known Limitations

- Claim history is in-memory and lost on backend restart
- Confidence score display has a known bug (always shows 0%) — claim decisions are unaffected
- Treatment dates in test cases were updated to 2026 to avoid 30-day submission deadline rejections during evaluation
- TC010 approved amount differs from expected due to sub-limit applied before network discount calculation

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Agent orchestration | LangGraph |
| LLM / Vision | Google Gemini 2.5 Flash |
| Frontend | Streamlit |
| Policy logic | Pure Python |
| Storage | In-memory |

---

## Policy Details

- **Policy ID:** PLUM_GHI_2024
- **Insurer:** ICICI Lombard General Insurance
- **Sum Insured:** Rs. 5,00,000 per employee
- **Annual OPD Limit:** Rs. 50,000
- **Per Claim Limit:** Rs. 5,000
- **Family Floater:** Rs. 1,50,000 combined

---

## Members Covered

10 employees (EMP001–EMP010) with select dependents. Full roster in `policy_terms.json`.

---
