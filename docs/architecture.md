# Architecture

## Overview

Plum AI is a multi-agent insurance claims processing system built on **LangGraph** and **Amazon Bedrock**.

## Pipeline Flow

```
Claim Input
    │
    ▼
[Document Verifier] ──(fail fast)──► [Decision Agent]
    │
    ▼
[Document Parser]
    │
    ▼
[Policy Engine]
    │
    ▼
[Fraud Detector]
    │
    ▼
[Decision Agent]
    │
    ▼
Decision Output
```

## Components

| Component | File | Responsibility |
|---|---|---|
| Document Verifier | `agents/document_verifier.py` | Uses Claude via Bedrock to verify submitted documents |
| Document Parser | `agents/document_parser.py` | Extracts structured data from claim documents |
| Policy Engine | `agents/policy_engine.py` | Checks coverage, exclusions, and limits |
| Fraud Detector | `agents/fraud_detector.py` | Scores claim risk using heuristic rules |
| Decision Agent | `agents/decision_agent.py` | Aggregates all signals into a final decision |
| Pipeline | `graph/pipeline.py` | LangGraph StateGraph wiring all agents |
| Runner | `graph/runner.py` | Entry point to invoke the pipeline |

## Tech Stack

- **LangGraph** — stateful agent orchestration
- **Amazon Bedrock** (Claude 3 Sonnet) — LLM for document verification and parsing
- **FastAPI** — REST API
- **Streamlit** — frontend UI
- **Pydantic v2** — data validation
