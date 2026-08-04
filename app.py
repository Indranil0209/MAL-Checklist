import datetime
import streamlit as st
from firestore_helpers import (
    get_document, set_document, list_collection,
    sites_for_date, date_key, ADMIN_ID, ADMIN_PIN,
)

st.set_page_config(page_title="Checklist", page_icon="✅", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0b12; }
    .badge { display:inline-block; background: linear-gradient(90deg,#ff5f7e,#ffb85f);
             padding: 4px 10px; border-radius: 6px; color:#1a1a1a; font-weight:700;
             font-size: 0.75rem; letter-spacing: 1px; margin-bottom: 1rem; }
    .login-title { font-size: 2rem; font-weight: 800; color: white; margin-bottom: 0.2rem; }
    .login-sub { color: #9aa0ac; margin-bottom: 1.5rem; }
    </style>
""", unsafe_allow_html=True)

if "auth" not in st.session_state:
    st.session_state.auth = None


# ───────────────────────── LOGIN ─────────────────────────

def do_login(employee_id: str, pin: str):
    employee_id = employee_id.strip().lower()
    pin = pin.strip()
    if not employee_id or not pin:
        return False, "Please enter both your employee ID and PIN.", None

    if employee_id == ADMIN_ID:
        if pin == ADMIN_PIN:
            return True, None, {"role": "admin", "id": ADMIN_ID, "name": "Admin"}
        return False, "Incorrect ID or PIN.", None

    employee = get_document(f"employees/{employee_id}")
    if not employee or employee.get("pin") != pin or employee.get("active") is False:
        return False, "Incorrect ID or PIN.", None

    return True, None, {"role": "employee", "id": employee_id, "name": employee.get("name") or employee_id}


def login_screen():
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
            ok, error, user = do_login(employee_id, pin)
        if ok:
            st.session_state.auth = user
            st.rerun()
        else:
            st.error(error)

    st.caption("🔒 Secure workspace connection")


# ───────────────────────── EMPLOYEE CHECKLIST ─────────────────────────

def load_sheet():
    sheet = get_document("sheet/current") or {}
    sites = sheet.get("sites") or []
    blocked = set(sheet.get("blocked") or [])
    return sites, blocked


def load_state(employee_id):
    return get_document(f"employees/{employee_id}/state/main") or {}


def save_state(employee_id, state):
    state["updatedAt"] = datetime.datetime.utcnow().isoformat()
    set_document(f"employees/{employee_id}/state/main", state, merge=True)


def save_progress(employee_id, name, date_k, total, done, work_items):
    set_document(f"employees/{employee_id}", {
        "name": name,
        "progress": {date_k: {
            "total": total, "done": done,
            "workItems": work_items,
            "updatedAt": datetime.datetime.utcnow().isoformat(),
        }}
    }, merge=True)


def employee_view(user):
    st.markdown('<div class="badge">CHECKLIST</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="login-title">Welcome, {user["name"]}</div>', unsafe_allow_html=True)

    top_l, top_r = st.columns([3, 1])
    with top_r:
        if st.button("Log out"):
            st.session_state.auth = None
            st.rerun()

    picked_date = st.date_input("Date", value=datetime.date.today())
    k = date_key(picked_date)

    sites, blocked = load_sheet()
    if not sites:
        st.warning("No sheet data found yet — ask your admin to upload the site sheet.")
        return

    todays_sites = sites_for_date(sites, blocked, picked_date)
    if not todays_sites:
        st.info("No sites scheduled for this date.")
        return

    state = load_state(user["id"])
    all_dates_state = state.get("allDatesState") or {}
    day_state = all_dates_state.get(k) or {}

    st.subheader(f"Sites for {picked_date.strftime('%A, %d %b %Y')}  ·  {len(todays_sites)} total")

    done_count = 0
    work_items = []
    updated_day_state = dict(day_state)

    for site in todays_sites:
        sid = site["id"]
        checked_key = sid
        remark_key = f"{sid}_remark"

        checked_before = bool(day_state.get(checked_key))
        cols = st.columns([0.5, 3, 4])
        with cols[0]:
            checked = st.checkbox("", value=checked_before, key=f"chk_{k}_{sid}")
        with cols[1]:
            st.write(f"**{site.get('name')}**")
            st.caption(site.get("freq", ""))
        with cols[2]:
            remark = st.text_input("Remark / work done", value=day_state.get(remark_key, ""),
                                    key=f"rem_{k}_{sid}", label_visibility="collapsed",
                                    placeholder="Remark / work done (optional)")

        updated_day_state[checked_key] = checked
        updated_day_state[remark_key] = remark
        if checked:
            done_count += 1
            work_items.append({"name": site.get("name"), "remark": remark})

    st.divider()
    prog = done_count / len(todays_sites) if todays_sites else 0
    st.progress(prog, text=f"{done_count} / {len(todays_sites)} completed")

    if st.button("💾 Save progress", type="primary", use_container_width=True):
        all_dates_state[k] = updated_day_state
        state["allDatesState"] = all_dates_state
        with st.spinner("Saving…"):
            save_state(user["id"], state)
            save_progress(user["id"], user["name"], k, len(todays_sites), done_count, work_items)
        st.success("Saved.")


# ───────────────────────── ADMIN DASHBOARD ─────────────────────────

def admin_view(user):
    st.markdown('<div class="badge">CHECKLIST · ADMIN</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Admin Dashboard</div>', unsafe_allow_html=True)

    top_l, top_r = st.columns([3, 1])
    with top_r:
        if st.button("Log out"):
            st.session_state.auth = None
            st.rerun()

    tab_employees, tab_sheet = st.tabs(["👥 Employees & Progress", "📋 Site Sheet"])

    with tab_employees:
        with st.spinner("Loading employees…"):
            employees = list_collection("employees")
        if not employees:
            st.info("No employees found yet.")
        else:
            today_k = date_key(datetime.date.today())
            rows = []
            for emp_id, data in employees:
                progress = (data.get("progress") or {}).get(today_k) or {}
                rows.append({
                    "Employee ID": emp_id,
                    "Name": data.get("name") or "",
                    "Active": data.get("active", True),
                    "Today Done": progress.get("done", 0),
                    "Today Total": progress.get("total", 0),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

    with tab_sheet:
        st.write("Current site sheet:")
        sites, blocked = load_sheet()
        if sites:
            st.dataframe(
                [{"ID": s.get("id"), "Name": s.get("name"), "Freq": s.get("freq")} for s in sites],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No sheet uploaded yet.")

        st.divider()
        st.write("Add a new site:")
        with st.form("add_site_form", clear_on_submit=True):
            new_id = st.text_input("Site ID (unique, e.g. site_101)")
            new_name = st.text_input("Site name")
            new_freq = st.selectbox("Frequency", ["E (everyday)", "Alt (alternating)", "Twice a week"])
            add_submitted = st.form_submit_button("Add site")

        if add_submitted:
            if not new_id or not new_name:
                st.error("Site ID and name are required.")
            else:
                freq_code = "E" if new_freq.startswith("E") else ("Alt" if new_freq.startswith("Alt") else "T")
                updated_sites = sites + [{"id": new_id, "name": new_name, "freq": freq_code}]
                with st.spinner("Saving sheet…"):
                    set_document("sheet/current", {"sites": updated_sites, "blocked": list(blocked)}, merge=True)
                st.success(f"Added '{new_name}'.")
                st.rerun()


# ───────────────────────── ROUTER ─────────────────────────

if not st.session_state.auth:
    login_screen()
else:
    user = st.session_state.auth
    if user["role"] == "admin":
        admin_view(user)
    else:
        employee_view(user)
