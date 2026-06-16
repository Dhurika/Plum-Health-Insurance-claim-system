# Contracts

## ClaimState (LangGraph shared state)

```python
{
    "claim": Claim,                    # Input claim object
    "documents_verified": bool | None, # Output of document_verifier
    "parsed_data": dict | None,        # Output of document_parser
    "policy_check": dict | None,       # Output of policy_engine
    "fraud_score": float | None,       # Output of fraud_detector (0.0–1.0)
    "decision": Decision | None,       # Final decision output
    "errors": list[str],               # Accumulated error messages
}
```

## Claim (Input)

| Field | Type | Description |
|---|---|---|
| claim_id | str | Unique identifier |
| policy_id | str | Associated policy |
| claimant_name | str | Full name |
| date_of_incident | date | When the incident occurred |
| claim_type | str | e.g. medical, accident, theft |
| amount_requested | float | Dollar amount claimed |
| description | str | Narrative description |
| documents | list[str] | Submitted document filenames |

## Decision (Output)

| Field | Type | Description |
|---|---|---|
| claim_id | str | Matches input claim |
| outcome | str | `approved`, `rejected`, or `review` |
| reason | str | Human-readable explanation |
| approved_amount | float? | Amount approved after deductible |
| fraud_score | float? | Risk score 0.0–1.0 |
| confidence | float? | Model confidence 0.0–1.0 |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/claims` | Submit and process a claim |
| GET | `/claims/{claim_id}/decision` | Retrieve a decision |
| GET | `/claims` | List all submitted claims |
| GET | `/health` | Health check |
