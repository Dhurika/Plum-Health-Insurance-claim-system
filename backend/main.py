import uuid
from services.console import configure_console_output

configure_console_output()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from models.claim import ClaimInput
from graph.runner import run_claim
from services.policy_loader import load_policy
from services.claims_store import add_claim, get_all_claims, get_family_ytd_amount
import os
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_policy()
    print("Policy loaded successfully")
    yield

app = FastAPI(
    title="Plum AI Claims Processing System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "Plum AI Claims Processing System"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/claims/submit")
def submit_claim(claim: ClaimInput):
    try:
        policy = load_policy()

        # get all member ids in this family
        member = next((m for m in policy.members if m.member_id == claim.employee_id), None)
        family_member_ids = [claim.employee_id]
        if member:
            family_member_ids += (member.dependents or [])

        # get prior claims for fraud detection
        from services.claims_store import get_claims_today, get_claims_this_month
        year        = claim.treatment_date[:4]
        year_month  = claim.treatment_date[:7]

        prior_claims_today    = get_claims_today(claim.member_id, claim.treatment_date)
        prior_claims_month    = get_claims_this_month(claim.member_id, year_month)
        family_ytd            = get_family_ytd_amount(claim.employee_id, family_member_ids, year)

        print(f"\n[Main] Enriching claim with historical data:")
        print(f"  Prior claims today: {len(prior_claims_today)}")
        print(f"  Prior claims this month: {len(prior_claims_month)}")
        print(f"  Family YTD: ₹{family_ytd}")

        # inject into claim for pipeline use
        claim_dict = claim.dict()
        claim_dict["claims_history"]     = prior_claims_today + prior_claims_month
        claim_dict["ytd_claims_amount"]  = family_ytd
        claim_dict["family_member_ids"]  = family_member_ids
        
        # Reconstruct claim with injected fields
        claim_with_history = ClaimInput(**claim_dict)

        result = run_claim(claim_with_history)

        # store claim after processing
        add_claim(
            member_id=claim.member_id,
            claim_id=result["claim_id"],
            date=claim.treatment_date,
            amount=claim.claimed_amount,
            category=claim.claim_category,
            employee_id=claim.employee_id
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/claims/history/{member_id}")
def get_member_history(member_id: str):
    claims = get_all_claims(member_id)
    return {"member_id": member_id, "claims": claims}

@app.get("/policy/members")
def get_members():
    policy = load_policy()

    dependent_map = {}
    for m in policy.members:
        if m.relationship != "SELF":
            dependent_map[m.member_id] = m

    result = []
    for m in policy.members:
        if m.relationship != "SELF":
            continue

        dependents = []
        for dep_id in (m.dependents or []):
            dep = dependent_map.get(dep_id)
            if dep:
                dependents.append({
                    "member_id":     dep.member_id,
                    "name":          dep.name,
                    "relationship":  dep.relationship,
                    "date_of_birth": dep.date_of_birth,
                    "gender":        dep.gender
                })

        result.append({
            "member_id":     m.member_id,
            "name":          m.name,
            "relationship":  m.relationship,
            "join_date":     m.join_date,
            "date_of_birth": m.date_of_birth,
            "gender":        m.gender,
            "dependents":    dependents
        })

    return {"members": result}

@app.get("/policy/info")
def get_policy_info():
    policy = load_policy()
    return {
        "policy_id":              policy.policy_id,
        "policy_name":            policy.policy_name,
        "insurer":                policy.insurer,
        "coverage": {
            "sum_insured_per_employee": policy.coverage.sum_insured_per_employee,
            "annual_opd_limit":         policy.coverage.annual_opd_limit,
            "per_claim_limit":          policy.coverage.per_claim_limit
        },
        "covered_relationships":  policy.coverage.family_floater.covered_relationships,
        "family_floater_limit":   policy.coverage.family_floater.combined_limit
    }
