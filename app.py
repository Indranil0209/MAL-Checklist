import streamlit as st
import requests

# ── Firebase / Firestore config (same project as your existing app) ──
FIREBASE_API_KEY = "AIzaSyAHzVTjMA0ErfhEhP7a1kQJBCNEV9yMxRo"
PROJECT_ID = "pss-checklist"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

ADMIN_ID = "admin"
ADMIN_PIN = "1111"

st.set_page_config(page_title="Checklist Login", page_icon="✅", layout="centered")

# ── Styling to loosely match your dark themed login screen ──
st.markdown("""
    <style>
    .stApp { background-color: #0b0b12; }
    .login-title { font-size: 2rem; font-weight: 800; color: white; margin-bottom: 0.2rem; }
    .login-sub { color: #9aa0ac; margin-bottom: 1.5rem; }
    .badge { display:inline-block; background: linear-gradient(90deg,#ff5f7e,#ffb85f);
             padding: 4px 10px; border-radius: 6px; color:#1a1a1a; font-weight:700;
             font-size: 0.75rem; letter-spacing: 1px; margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)


def get_employee(employee_id: str):
    """Fetch an employee document from Firestore via REST API."""
    url = f"{FIRESTORE_URL}/employees/{employee_id}?key={FIREBASE_API_KEY}"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    fields = data.get("fields", {})

    def _val(field):
        if field is None:
            return None
        for t in ("stringValue", "booleanValue", "integerValue", "doubleValue"):
            if t in field:
                return field[t]
        return None

    return {
        "pin": _val(fields.get("pin")),
        "name": _val(fields.get("name")),
        "active": fields.get("active", {}).get("booleanValue", True) if "active" in fields else True,
    }


def login(employee_id: str, pin: str):
    employee_id = employee_id.strip().lower()
    pin = pin.strip()

    if not employee_id or not pin:
        return False, "Please enter both your employee ID and PIN.", None

    if employee_id == ADMIN_ID:
        if pin == ADMIN_PIN:
            return True, None, {"role": "admin", "id": ADMIN_ID, "name": "Admin"}
        return False, "Incorrect ID or PIN.", None

    employee = get_employee(employee_id)
    if not employee or employee.get("pin") != pin or employee.get("active") is False:
        return False, "Incorrect ID or PIN.", None

    return True, None, {
        "role": "employee",
        "id": employee_id,
        "name": employee.get("name") or employee_id,
    }


# ── Session state ──
if "auth" not in st.session_state:
    st.session_state.auth = None

if st.session_state.auth:
    user = st.session_state.auth
    st.markdown('<div class="badge">CHECKLIST</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="login-title">Welcome, {user["name"]} 👋</div>', unsafe_allow_html=True)
    st.write(f"Signed in as **{user['role']}** (ID: `{user['id']}`)")

    if st.button("Log out"):
        st.session_state.auth = None
        st.rerun()

    st.info("This is just the login screen for now — the admin and employee "
            "dashboards can be built next as separate pages.")
else:
    st.markdown('<div class="badge">CHECKLIST</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Welcome back</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Sign in with your employee ID to access your secure workspace.</div>',
                unsafe_allow_html=True)

    with st.form("login_form"):
        employee_id = st.text_input("Employee ID", placeholder="e.g. 6006")
        pin = st.text_input("PIN", type="password", placeholder="••••")
        submitted = st.form_submit_button("Initialize Workspace", use_container_width=True)

    if submitted:
        with st.spinner("Authenticating…"):
            ok, error, user = login(employee_id, pin)
        if ok:
            st.session_state.auth = user
            st.rerun()
        else:
            st.error(error)

    st.caption("🔒 Secure workspace connection")
