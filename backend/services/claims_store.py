from typing import List, Dict

_store: Dict[str, List[dict]] = {}

def add_claim(member_id: str, claim_id: str, date: str, amount: float, category: str, employee_id: str = None):
    if member_id not in _store:
        _store[member_id] = []
    _store[member_id].append({
        "claim_id":    claim_id,
        "date":        date,
        "amount":      amount,
        "category":    category,
        "employee_id": employee_id
    })

def get_claims_today(member_id: str, today: str) -> List[dict]:
    return [c for c in _store.get(member_id, []) if c["date"] == today]

def get_claims_this_month(member_id: str, year_month: str) -> List[dict]:
    return [c for c in _store.get(member_id, []) if c["date"].startswith(year_month)]

def get_all_claims(member_id: str) -> List[dict]:
    return _store.get(member_id, [])

def get_ytd_amount(member_id: str, year: str) -> float:
    return sum(
        c["amount"] for c in _store.get(member_id, [])
        if c["date"].startswith(year)
    )

def get_family_ytd_amount(employee_id: str, all_member_ids: List[str], year: str) -> float:
    total = 0.0
    for mid in all_member_ids:
        total += get_ytd_amount(mid, year)
    return total

def clear_store():
    global _store
    _store = {}