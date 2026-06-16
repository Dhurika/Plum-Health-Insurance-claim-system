from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class FamilyFloater(BaseModel):
    enabled: bool
    combined_limit: float
    covered_relationships: List[str]

class Coverage(BaseModel):
    sum_insured_per_employee: float
    annual_opd_limit: float
    per_claim_limit: float
    family_floater: FamilyFloater

class OpdCategory(BaseModel):
    sub_limit: float
    copay_percent: float
    network_discount_percent: Optional[float] = 0.0
    requires_prescription: Optional[bool] = False
    requires_pre_auth: Optional[bool] = False
    pre_auth_threshold: Optional[float] = None
    high_value_tests_requiring_pre_auth: Optional[List[str]] = []
    covered: bool
    covered_procedures: Optional[List[str]] = []
    excluded_procedures: Optional[List[str]] = []
    covered_items: Optional[List[str]] = []
    excluded_items: Optional[List[str]] = []
    covered_systems: Optional[List[str]] = []
    generic_mandatory: Optional[bool] = False
    branded_drug_copay_percent: Optional[float] = 0.0
    requires_dental_report: Optional[bool] = False
    requires_registered_practitioner: Optional[bool] = False
    max_sessions_per_year: Optional[int] = None

class WaitingPeriods(BaseModel):
    initial_waiting_period_days: int
    pre_existing_conditions_days: int
    specific_conditions: Dict[str, int]

class Exclusions(BaseModel):
    conditions: List[str]
    dental_exclusions: Optional[List[str]] = []
    vision_exclusions: Optional[List[str]] = []

class PreAuthorization(BaseModel):
    required_for: List[str]
    validity_days: int

class SubmissionRules(BaseModel):
    deadline_days_from_treatment: int
    minimum_claim_amount: float
    currency: str

class FraudThresholds(BaseModel):
    same_day_claims_limit: int
    monthly_claims_limit: int
    high_value_claim_threshold: float
    auto_manual_review_above: float
    fraud_score_manual_review_threshold: float

class Member(BaseModel):
    member_id: str
    name: str
    date_of_birth: str
    gender: str
    relationship: str
    join_date: Optional[str] = None
    dependents: Optional[List[str]] = []
    primary_member_id: Optional[str] = None

class PolicyHolder(BaseModel):
    company_name: str
    employee_count: int
    policy_start_date: str
    policy_end_date: str
    renewal_status: str

class PolicyConfig(BaseModel):
    policy_id: str
    policy_name: str
    insurer: str
    policy_holder: PolicyHolder
    coverage: Coverage
    opd_categories: Dict[str, OpdCategory]
    waiting_periods: WaitingPeriods
    exclusions: Exclusions
    pre_authorization: PreAuthorization
    network_hospitals: List[str]
    submission_rules: SubmissionRules
    document_requirements: Dict[str, Dict[str, List[str]]]
    fraud_thresholds: FraudThresholds
    members: List[Member]