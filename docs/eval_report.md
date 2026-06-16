# Eval Report

## Test Cases

| Claim ID | Type | Expected | Result | Notes |
|---|---|---|---|---|
| CLM-001 | medical | approved | — | Run `eval/run_eval.py` |
| CLM-002 | dental | rejected | — | Excluded by policy |
| CLM-003 | accident | approved | — | All docs present |

## How to Run

```bash
cd "Plum AI"
python -m eval.run_eval
```

## Scoring

- Each test case is pass/fail based on `outcome == expected_outcome`
- Final score is `passed / total` cases

## Metrics to Track

- Accuracy (outcome match rate)
- False positive rate (legitimate claims rejected)
- False negative rate (fraudulent claims approved)
- Average processing latency per claim
