import json
from pathlib import Path
from models.policy import PolicyConfig

_policy: PolicyConfig = None

def load_policy(path: str = None) -> PolicyConfig:
    global _policy
    if _policy is not None:
        return _policy
    
    if path is None:
        path = Path(__file__).parent.parent / "data" / "policy_terms.json"
    
    with open(path) as f:
        data = json.load(f)
    
    _policy = PolicyConfig(**data)
    return _policy

def get_policy() -> PolicyConfig:
    global _policy
    if _policy is None:
        _policy = load_policy()
    return _policy