import streamlit as st
import requests
import json
import base64

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Plum Claims", page_icon="🌿", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=DM+Sans:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"],
[data-testid="stAppViewContainer"] > .main,
.main,
[data-testid="stBottomBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] { background: #f7f4ff !important; }
.block-container { padding: 0 2rem 4rem !important; max-width: 1200px !important; margin: auto !important; }
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none; }

/* HEADER */
.plum-header {
    background: #6c1e4f; margin: 0 -2rem 1.8rem;
    padding: 0.9rem 2rem; display: flex; align-items: center; gap: 0.9rem;
}
.plum-wordmark { font-family:'Nunito',sans-serif; font-size:1.8rem; font-weight:900; color:#ff4d6d; letter-spacing:-1px; line-height:1; }
.plum-header-sub { font-family:'DM Sans',sans-serif; font-size:0.72rem; color:rgba(255,255,255,0.45); margin-top:1px; }
.plum-divider { width:1px; height:28px; background:rgba(255,255,255,0.15); margin:0 0.3rem; }
.plum-header-title { font-family:'DM Sans',sans-serif; font-size:0.9rem; font-weight:600; color:white; }

/* CARDS */
.scard { background:white; border-radius:14px; border:1px solid #ede8f5; padding:1.2rem 1.3rem; margin-bottom:1rem; }
.scard-title {
    font-family:'DM Sans',sans-serif; font-size:0.68rem; font-weight:700;
    color:#b090c0; text-transform:uppercase; letter-spacing:0.1em;
    margin-bottom:0.85rem; display:flex; align-items:center; gap:0.4rem;
}
.scard-title span {
    width:18px; height:18px; background:#6c1e4f; border-radius:50%;
    color:white; font-size:0.62rem; font-weight:900;
    display:inline-flex; align-items:center; justify-content:center;
    font-family:'Nunito',sans-serif;
}

/* MEMBER CHIP */
.member-chip {
    display:flex; align-items:center; gap:0.6rem;
    background:#fff0f4; border:1.5px solid #ffb3c1;
    border-radius:10px; padding:0.55rem 0.9rem; margin-top:0.7rem;
}
.mavatar {
    width:32px; height:32px; border-radius:50%; background:#ff4d6d; color:white;
    font-family:'Nunito',sans-serif; font-size:0.75rem; font-weight:900;
    display:flex; align-items:center; justify-content:center; flex-shrink:0;
}
.mname { font-family:'DM Sans',sans-serif; font-size:0.85rem; font-weight:600; color:#6c1e4f; }
.mmeta { font-family:'DM Sans',sans-serif; font-size:0.72rem; color:#a06080; }

/* DOC LIST */
.doc-list { display:flex; flex-direction:column; gap:0.4rem; margin-top:0.5rem; }
.doc-item {
    display:flex; align-items:center; gap:0.6rem;
    background:#f7f4ff; border:1px solid #ede8f5;
    border-radius:9px; padding:0.55rem 0.8rem;
    font-family:'DM Sans',sans-serif; font-size:0.8rem; color:#3d2a50;
}
.doc-item-icon { font-size:1.1rem; flex-shrink:0; }
.doc-item-name { flex:1; font-weight:500; }
.doc-item-size { color:#a090b0; font-size:0.7rem; white-space:nowrap; }
.doc-item-type {
    background:#ede8f5; border-radius:4px;
    padding:0.12rem 0.45rem; font-size:0.65rem;
    font-weight:700; color:#5a3a70; text-transform:uppercase;
    letter-spacing:0.05em; white-space:nowrap;
}
.doc-empty {
    background:#faf8ff; border:2px dashed #ddd6f0;
    border-radius:9px; padding:1.2rem;
    text-align:center; color:#b090c0;
    font-family:'DM Sans',sans-serif; font-size:0.82rem;
}

/* ── ALL LABELS ── */
label,
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label,
[data-testid="stCheckbox"] label,
[data-testid="stFileUploader"] label,
[data-testid="stRadio"] label {
    font-family:'DM Sans',sans-serif !important;
    font-size:0.72rem !important; font-weight:600 !important;
    color:#7a5c80 !important; text-transform:uppercase !important;
    letter-spacing:0.06em !important;
}

/* ── ALL INPUT BACKGROUNDS ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea {
    background:#faf8ff !important;
    background-color:#faf8ff !important;
    border:1.5px solid #ddd6f0 !important;
    border-radius:9px !important;
    color:#1a0a2e !important;
    -webkit-text-fill-color:#1a0a2e !important;
    font-family:'DM Sans',sans-serif !important;
    font-size:0.88rem !important;
    font-weight:500 !important;
}

/* ── SELECTBOX — every layer ── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stSelectbox"] > div > div > div,
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] > div > div {
    background: #faf8ff !important;
    background-color: #faf8ff !important;
    border: 1.5px solid #ddd6f0 !important;
    border-radius: 9px !important;
    color: #1a0a2e !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
}
/* the selected value text */
[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stSelectbox"] [data-baseweb="select"] div[class*="ValueContainer"] *,
[data-testid="stSelectbox"] [data-baseweb="select"] div[class*="singleValue"],
[data-testid="stSelectbox"] [data-baseweb="select"] input {
    color: #1a0a2e !important;
    -webkit-text-fill-color: #1a0a2e !important;
    background: transparent !important;
}
/* dropdown arrow */
[data-testid="stSelectbox"] svg { fill: #6c1e4f !important; }

/* ── DROPDOWN POPUP ── */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"] {
    background: #fff !important;
    border: 1px solid #ede8f5 !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 24px rgba(108,30,79,0.1) !important;
}
div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li {
    background: transparent !important;
    color: #1a0a2e !important;
    font-family:'DM Sans',sans-serif !important;
    font-size: 0.85rem !important;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="menu"] li:hover {
    background: #fff0f4 !important;
    color: #6c1e4f !important;
}

/* ── NUMBER INPUT BUTTONS ── */
[data-testid="stNumberInput"] button {
    background: #fff !important;
    border: 1px solid #ddd6f0 !important;
    color: #6c1e4f !important;
}
[data-testid="stNumberInput"] button svg { fill: #6c1e4f !important; }

/* ── CHECKBOX ── */
[data-testid="stCheckbox"] label {
    color: #6b5a7a !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"] {
    background: #faf8ff !important;
    background-color: #faf8ff !important;
    border: 2px dashed #c9b8f0 !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] *,
[data-testid="stFileUploaderDropzone"] * {
    color: #7a5c80 !important;
    background: transparent !important;
}
[data-testid="stFileUploader"] button {
    background: #fff !important;
    border: 1px solid #ddd6f0 !important;
    border-radius: 8px !important;
    color: #6c1e4f !important;
}
[data-testid="stFileUploader"] button svg,
[data-testid="stFileUploaderDropzone"] svg { fill: #6c1e4f !important; color: #6c1e4f !important; }

/* ── DATE PICKER POPUP ── */
div[data-baseweb="calendar"],
div[data-baseweb="datepicker"] {
    background: #fff !important;
    border: 1px solid #ede8f5 !important;
    border-radius: 12px !important;
}
div[data-baseweb="calendar"] * { color: #1a0a2e !important; background: transparent !important; }
div[data-baseweb="calendar"] button:hover { background: #fff0f4 !important; }

/* ── SPINNER ── */
[data-testid="stSpinner"] p { color: #6c1e4f !important; }
[data-testid="stInfo"] {
    background:#f0ebff !important; border:1px solid #c9b8f0 !important;
    border-radius:10px !important; color:#4a2d7a !important;
    font-family:'DM Sans',sans-serif !important; font-size:0.8rem !important;
}
[data-testid="stSuccess"] { background:#f0fdf4 !important; border:1px solid #86efac !important; border-radius:10px !important; }
[data-testid="stWarning"] { background:#fffbeb !important; border:1px solid #fde68a !important; border-radius:10px !important; }
[data-testid="stError"]   { background:#fff1f2 !important; border:1px solid #fda4af !important; border-radius:10px !important; }
[data-testid="stExpander"] {
    background:white !important;
    border:1px solid #ede8f5 !important;
    border-radius:12px !important;
}
[data-testid="stExpander"] > div {
    background: white !important;
}
[data-testid="stExpander"] summary {
    font-family:'DM Sans',sans-serif !important;
    font-size:0.83rem !important;
    color:#5a4070 !important;
    font-weight:600 !important;
    background: white !important;
}
[data-testid="stExpander"] summary:hover {
    color: #6c1e4f !important;
}

/* SUBMIT */
div.stButton > button {
    background:#ff4d6d !important; color:white !important;
    border:none !important; border-radius:50px !important;
    padding:0.8rem 2rem !important; font-family:'Nunito',sans-serif !important;
    font-size:1rem !important; font-weight:900 !important; width:100% !important;
    letter-spacing:0.03em !important; box-shadow:0 6px 20px rgba(255,77,109,0.28) !important;
    transition:all 0.18s !important;
}
div.stButton > button:hover {
    background:#e6003a !important; box-shadow:0 8px 26px rgba(255,77,109,0.38) !important;
    transform:translateY(-1px) !important;
}

/* RESULT */
.result-wrap {
    background:white; border-radius:16px; border:1px solid #ede8f5;
    padding:1.8rem 2rem; margin-top:1rem;
    box-shadow:0 4px 24px rgba(108,30,79,0.08);
}
.result-badge {
    display:inline-flex; align-items:center; gap:0.3rem;
    padding:0.25rem 0.8rem; border-radius:50px;
    font-family:'DM Sans',sans-serif; font-size:0.7rem; font-weight:700;
    text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.6rem;
}
.badge-approved { background:#dcfce7; color:#15803d; }
.badge-rejected { background:#fee2e2; color:#b91c1c; }
.badge-partial  { background:#fef9c3; color:#a16207; }
.badge-manual   { background:#dbeafe; color:#1d4ed8; }

.result-amount { font-family:'Nunito',sans-serif; font-size:2.8rem; font-weight:900; line-height:1; margin-bottom:0.4rem; }
.result-amount-approved { color:#15803d; }
.result-amount-rejected { color:#b91c1c; }
.result-amount-partial  { color:#a16207; }
.result-amount-manual   { color:#1d4ed8; }
.result-explanation { font-family:'DM Sans',sans-serif; font-size:0.88rem; color:#6b5a7a; line-height:1.65; margin-top:0.35rem; }

.metrics-row { display:flex; gap:0.5rem; margin:1.2rem 0 0.5rem; flex-wrap:wrap; }
.metric-box { flex:1; min-width:80px; background:#f7f4ff; border:1px solid #ede8f5; border-radius:10px; padding:0.65rem 0.7rem; text-align:center; }
.metric-box .mlabel { font-family:'DM Sans',sans-serif; font-size:0.6rem; font-weight:700; color:#a090b0; text-transform:uppercase; letter-spacing:0.07em; }
.metric-box .mvalue { font-family:'Nunito',sans-serif; font-size:1rem; font-weight:800; color:#1a0a2e; margin-top:0.15rem; }

.section-label { font-family:'DM Sans',sans-serif; font-size:0.68rem; font-weight:700; color:#a090b0; text-transform:uppercase; letter-spacing:0.08em; margin:1.1rem 0 0.45rem; }
.li-row { display:flex; justify-content:space-between; align-items:center; padding:0.45rem 0; border-bottom:1px solid #f0ebf8; font-family:'DM Sans',sans-serif; font-size:0.83rem; color:#3d2a50; gap:0.7rem; }
.li-covered  { color:#15803d; font-weight:600; white-space:nowrap; }
.li-excluded { color:#b91c1c; font-weight:600; white-space:nowrap; }

.fraud-item { background:#fff1f2; border:1px solid #fda4af; border-radius:8px; padding:0.6rem 0.85rem; margin-bottom:0.35rem; font-family:'DM Sans',sans-serif; font-size:0.8rem; color:#7a2030; }
.pill { display:inline-block; padding:0.2rem 0.6rem; border-radius:50px; font-family:'DM Sans',sans-serif; font-size:0.7rem; font-weight:700; margin:0.12rem; }
.pill-ok  { background:#dcfce7; color:#15803d; }
.pill-err { background:#fee2e2; color:#b91c1c; }

.trace-wrap { max-height:320px; overflow-y:auto; }
.trace-item { padding:0.38rem 0.7rem; border-radius:7px; margin-bottom:0.25rem; font-family:'DM Sans',sans-serif; font-size:0.76rem; border-left:3px solid transparent; line-height:1.5; color:#3d2a50; }
.t-pass { background:#f0fdf4; border-left-color:#22c55e; }
.t-fail { background:#fff1f2; border-left-color:#ef4444; }
.t-flag { background:#fffbeb; border-left-color:#f59e0b; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────

def file_to_base64(fb):
    return base64.b64encode(fb).decode("utf-8")

@st.cache_data
def fetch_members():
    try:
        r = requests.get(f"{API_URL}/policy/members", timeout=5)
        return r.json().get("members", [])
    except:
        return []

def initials(name):
    p = name.strip().split()
    return (p[0][0] + (p[-1][0] if len(p) > 1 else "")).upper()

def detect_doc_type(filename: str) -> str:
    name = filename.lower()
    if any(x in name for x in ["prescription", "rx", "presc"]):
        return "PRESCRIPTION"
    if any(x in name for x in ["bill", "invoice", "receipt", "hospital"]):
        return "HOSPITAL_BILL"
    if any(x in name for x in ["lab", "report", "test", "diagnostic"]):
        return "LAB_REPORT"
    if any(x in name for x in ["pharmacy", "pharma", "medicine", "drug"]):
        return "PHARMACY_BILL"
    if any(x in name for x in ["dental", "teeth", "tooth"]):
        return "DENTAL_REPORT"
    return "UNKNOWN"

def show_result(result, claimed_amount):
    decision    = result.get("decision", "")
    amount      = result.get("approved_amount", 0)
    confidence  = result.get("confidence_score", 0)
    explanation = result.get("explanation", "")
    claim_id    = result.get("claim_id", "")
    discount    = result.get("discount_amount", 0)
    copay       = result.get("copay_amount", 0)

    cfg = {
        "APPROVED":      ("badge-approved", "result-amount-approved", "✅ Approved"),
        "REJECTED":      ("badge-rejected", "result-amount-rejected", "❌ Rejected"),
        "PARTIAL":       ("badge-partial",  "result-amount-partial",  "⚠️ Partially Approved"),
        "MANUAL_REVIEW": ("badge-manual",   "result-amount-manual",   "🔍 Manual Review"),
    }
    bc, ac, bt = cfg.get(decision, ("badge-manual", "result-amount-manual", "🔍 Manual Review"))

    st.markdown(f"""
    <div class="result-wrap">
        <div class="result-badge {bc}">{bt}</div>
        <div class="result-amount {ac}">₹{amount:,.2f}</div>
        <div class="result-explanation">{explanation}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metrics-row">
        <div class="metric-box"><div class="mlabel">Claim ID</div><div class="mvalue" style="font-size:0.65rem;word-break:break-all">{claim_id}</div></div>
        <div class="metric-box"><div class="mlabel">Claimed</div><div class="mvalue">₹{claimed_amount:,.0f}</div></div>
        <div class="metric-box"><div class="mlabel">Discount</div><div class="mvalue">₹{discount:,.0f}</div></div>
        <div class="metric-box"><div class="mlabel">Co-pay</div><div class="mvalue">₹{copay:,.0f}</div></div>
        <div class="metric-box"><div class="mlabel">Confidence</div><div class="mvalue">{confidence:.0%}</div></div>
    </div>
    """, unsafe_allow_html=True)

    line_items = result.get("line_item_results", [])
    if line_items:
        st.markdown('<div class="section-label">Line Item Breakdown</div>', unsafe_allow_html=True)
        for item in line_items:
            css = "li-covered" if item.get("covered") else "li-excluded"
            tag = "✅ Covered" if item.get("covered") else "❌ Excluded"
            st.markdown(f'<div class="li-row"><span style="flex:1">{item.get("description","")}</span><span style="color:#5a4070;font-weight:500">₹{float(item.get("amount",0)):,.2f}</span><span class="{css}">{tag}</span></div>', unsafe_allow_html=True)

    signals = result.get("fraud_signals", [])
    if signals:
        st.markdown('<div class="section-label" style="margin-top:1rem">Fraud Signals</div>', unsafe_allow_html=True)
        for s in signals:
            st.markdown(f'<div class="fraud-item"><b>{s.get("signal_type")}</b> · {s.get("severity")} severity<br><span>{s.get("detail")}</span></div>', unsafe_allow_html=True)

    comp = result.get("component_status", {})
    if comp:
        st.markdown('<div class="section-label" style="margin-top:1rem">Component Status</div>', unsafe_allow_html=True)
        pills = "".join(f'<span class="pill {"pill-ok" if s=="COMPLETED" else "pill-err"}">{"✅" if s=="COMPLETED" else "❌"} {n.replace("_"," ").title()}</span>' for n, s in comp.items())
        st.markdown(f'<div style="margin:0.3rem 0 0.6rem">{pills}</div>', unsafe_allow_html=True)

    trace = result.get("trace", [])
    if trace:
        with st.expander("🔍 Full Audit Trace"):
            st.markdown('<div class="trace-wrap">', unsafe_allow_html=True)
            for e in trace:
                r   = e.get("result", "")
                css = "t-pass" if r == "PASS" else "t-fail" if r == "FAIL" else "t-flag"
                ico = "✅" if r == "PASS" else "❌" if r == "FAIL" else "⚠️"
                st.markdown(f'<div class="trace-item {css}">{ico} <b>[{e.get("agent")}]</b> {e.get("check")} — {e.get("detail")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)


# ── header ────────────────────────────────────────────────

st.markdown("""
<div class="plum-header">
    <div><div class="plum-wordmark">plum</div><div class="plum-header-sub">Health Insurance</div></div>
    <div class="plum-divider"></div>
    <div class="plum-header-title">Claims Portal</div>
</div>
""", unsafe_allow_html=True)

try:
    requests.get(f"{API_URL}/health", timeout=3)
except:
    st.error("⚠️ Backend not running. Start with: uvicorn main:app --reload")
    st.stop()

members = fetch_members()

doc_requirements = {
    "CONSULTATION":         ["PRESCRIPTION", "HOSPITAL_BILL"],
    "DIAGNOSTIC":           ["PRESCRIPTION", "LAB_REPORT", "HOSPITAL_BILL"],
    "PHARMACY":             ["PRESCRIPTION", "PHARMACY_BILL"],
    "DENTAL":               ["HOSPITAL_BILL"],
    "VISION":               ["PRESCRIPTION", "HOSPITAL_BILL"],
    "ALTERNATIVE_MEDICINE": ["PRESCRIPTION", "HOSPITAL_BILL"],
}


# ── row 1: who + treatment (side by side) ─────────────────

col_who, col_treat = st.columns(2, gap="large")

with col_who:
    st.markdown('<div class="scard"><div class="scard-title"><span>1</span> Who is this claim for?</div>', unsafe_allow_html=True)

    employee_options      = {f"{m['name']} ({m['member_id']})": m for m in members}
    selected_employee_key = st.selectbox("Employee", list(employee_options.keys()))
    selected_employee     = employee_options[selected_employee_key]

    claim_for_options = {
        f"Myself — {selected_employee['name']}": {
            "member_id":    selected_employee["member_id"],
            "name":         selected_employee["name"],
            "join_date":    selected_employee.get("join_date"),
            "dob":          selected_employee.get("date_of_birth"),
            "gender":       selected_employee.get("gender"),
            "relationship": "SELF"
        }
    }
    for dep in selected_employee.get("dependents", []):
        claim_for_options[f"{dep['relationship'].title()} — {dep['name']}"] = {
            "member_id":    dep["member_id"],
            "name":         dep["name"],
            "dob":          dep.get("date_of_birth"),
            "gender":       dep.get("gender"),
            "relationship": dep["relationship"]
        }

    selected_claimant_key = st.selectbox("Claiming for", list(claim_for_options.keys()))
    selected_claimant     = claim_for_options[selected_claimant_key]

    rel    = selected_claimant["relationship"]
    dob    = selected_claimant.get("dob", "N/A")
    gender = selected_claimant.get("gender", "N/A")
    joined = selected_employee.get("join_date", "")
    meta   = [rel, f"DOB: {dob}", f"Gender: {gender}"]
    if rel == "SELF" and joined:
        meta.append(f"Joined: {joined}")
    else:
        meta.append(f"Primary: {selected_employee['name']}")

    st.markdown(f"""
    <div class="member-chip">
        <div class="mavatar">{initials(selected_claimant['name'])}</div>
        <div>
            <div class="mname">{selected_claimant['name']}</div>
            <div class="mmeta">{"  ·  ".join(meta)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_treat:
    st.markdown('<div class="scard"><div class="scard-title"><span>2</span> Treatment details</div>', unsafe_allow_html=True)

    claim_category = st.selectbox("Treatment Type", list(doc_requirements.keys()))
    treatment_date = st.date_input("Treatment Date")

    ca, cb = st.columns(2)
    with ca:
        claimed_amount = st.number_input("Total Bill Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
    with cb:
        hospital_name = st.text_input("Hospital / Clinic", placeholder="e.g. Apollo Hospitals")

    simulate_failure = st.checkbox("🔧 Simulate component failure (TC011 only)", value=False)
    st.markdown('</div>', unsafe_allow_html=True)


# ── row 2: upload left, doc list right ────────────────────

required_docs = doc_requirements[claim_category]

col_upload, col_doclist = st.columns(2, gap="large")

with col_upload:
    st.markdown('<div class="scard"><div class="scard-title"><span>3</span> Upload documents</div>', unsafe_allow_html=True)

    req_text = " · ".join(d.replace("_", " ").title() for d in required_docs)
    st.info(f"**{claim_category.replace('_',' ').title()}** needs: {req_text}")

    uploaded_files = st.file_uploader(
        "Select all your documents at once",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="docs"
    )

    st.markdown('</div>', unsafe_allow_html=True)

with col_doclist:
    st.markdown('<div class="scard"><div class="scard-title">📋 Uploaded Documents</div>', unsafe_allow_html=True)

    if uploaded_files:
        st.markdown('<div class="doc-list">', unsafe_allow_html=True)
        for f in uploaded_files:
            icon      = "🖼️" if f.type.startswith("image") else "📄"
            size      = f"{round(f.size/1024, 1)} KB"
            detected  = detect_doc_type(f.name)
            dtype_lbl = detected.replace("_", " ").title() if detected != "UNKNOWN" else "Unknown Type"
            st.markdown(f"""
            <div class="doc-item">
                <span class="doc-item-icon">{icon}</span>
                <span class="doc-item-name">{f.name}</span>
                <span class="doc-item-type">{dtype_lbl}</span>
                <span class="doc-item-size">{size}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # show images inline
        for f in uploaded_files:
            if f.type.startswith("image"):
                st.image(f, width=200)

        if len(uploaded_files) < len(required_docs):
            st.warning(f"⚠️ {len(required_docs) - len(uploaded_files)} more document(s) needed for {claim_category.replace('_',' ').title()}.")
        else:
            st.success(f"✅ {len(uploaded_files)} document(s) ready to submit.")
    else:
        st.markdown("""
        <div class="doc-empty">
            📎 No documents uploaded yet.<br>
            <span style="font-size:0.72rem;opacity:0.7">Upload your documents on the left.</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ── submit ────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
submitted = st.button("Submit Claim →", use_container_width=True)

if submitted:
    if claimed_amount <= 0:
        st.error("Please enter the total bill amount.")
        st.stop()

    if not uploaded_files:
        st.error("Please upload at least one document.")
        st.stop()

    # build documents list from uploaded files
    # detect type from filename, fallback to required_docs order
    documents = []
    for i, f in enumerate(uploaded_files):
        detected = detect_doc_type(f.name)
        if detected == "UNKNOWN" and i < len(required_docs):
            detected = required_docs[i]

        f.seek(0)
        raw = f.read()
        documents.append({
            "file_id":             f"F{i+1:03d}",
            "file_name":           f.name,
            "actual_type":         detected,
            "quality":             "GOOD",
            "patient_name_on_doc": selected_claimant["name"],
            "content": {
                "base64_data": file_to_base64(raw),
                "mime_type":   f.type,
                "filename":    f.name
            }
        })

    payload = {
        "employee_id":                selected_employee["member_id"],
        "member_id":                  selected_claimant["member_id"],
        "policy_id":                  "PLUM_GHI_2024",
        "claim_category":             claim_category,
        "treatment_date":             str(treatment_date),
        "claimed_amount":             claimed_amount,
        "hospital_name":              hospital_name or None,
        "documents":                  documents,
        "simulate_component_failure": simulate_failure
    }

    with st.spinner("Analysing your claim…"):
        try:
            response = requests.post(
                f"{API_URL}/claims/submit",
                json=payload,
                timeout=120
            )
            if response.status_code == 200:
                st.markdown("---")
                st.markdown("### 📋 Claim Decision")
                show_result(response.json(), claimed_amount)
            else:
                st.error(f"Error {response.status_code}: {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
