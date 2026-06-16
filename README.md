# 🌸 Plum AI — Insurance Claims Processor

A multi-agent AI system for automated insurance claim adjudication, built with **LangGraph** and **Amazon Bedrock**.

## Architecture

```
Claim → Verify Docs → Parse Docs → Policy Check → Fraud Detection → Decision
```

See [docs/architecture.md](docs/architecture.md) for full details.

## Setup

```bash
pip install -r backend/requirements.txt
```

Configure AWS credentials with Bedrock access:
```bash
aws configure
```

## Run API

```bash
uvicorn backend.main:app --reload
```

## Run Frontend

```bash
streamlit run frontend/app.py
```

## Run Tests

```bash
pytest backend/tests/
```

## Run Eval

```bash
python -m eval.run_eval
```

## Project Structure

```
backend/
  agents/        # Individual AI agents (verify, parse, policy, fraud, decide)
  graph/         # LangGraph pipeline and state
  models/        # Pydantic models (Claim, Decision, Policy)
  services/      # Policy loader and claims store
  prompts/       # LLM prompt templates
  data/          # Sample policies and test cases
  tests/         # Unit tests
frontend/
  app.py         # Streamlit UI
eval/
  run_eval.py    # Batch evaluation runner
docs/            # Architecture, contracts, eval report
```
