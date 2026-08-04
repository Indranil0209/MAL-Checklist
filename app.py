+import streamlit as st
+from datetime import datetime
+
+st.set_page_config(page_title="Checklist // Secure Access", layout="wide")
+
+st.markdown(
+    """
+    <style>
+    .stApp {
+        background: radial-gradient(circle at 20% 40%, rgba(255, 107, 157, .15), transparent 40%),
+                    radial-gradient(circle at 80% 60%, rgba(103, 232, 249, .12), transparent 35%),
+                    #05040a;
+        color: #f0eefc;
+    }
+    div[data-testid="stForm"] {
+        background: rgba(14, 12, 30, .92);
+        border: 1px solid rgba(255,255,255,.08);
+        border-radius: 18px;
+        padding: 24px;
+    }
+    </style>
+    """,
+    unsafe_allow_html=True,
+)
+
+ADMIN_ID = "admin"
+ADMIN_PIN = "1111"
+ROLE_KEY = "intimation-tracker-role"
+ID_KEY = "intimation-tracker-userid"
+NAME_KEY = "intimation-tracker-loginname"
+
+if "forgot_open" not in st.session_state:
+    st.session_state.forgot_open = False
+if "login_error" not in st.session_state:
+    st.session_state.login_error = ""
+if "forgot_status" not in st.session_state:
+    st.session_state.forgot_status = ""
+
+left, right = st.columns([1, 1])
+
+with left:
+    st.title("Checklist")
+    st.subheader("Secure Access")
+    st.write("Sign in with your employee ID to access your secure workspace.")
+    st.info("Streamlit version of the login page")
+
+with right:
+    st.markdown("### Login")
+    if st.session_state.login_error:
+        st.error(st.session_state.login_error)
+
+    with st.form("login_form", clear_on_submit=False):
+        emp_id = st.text_input("Employee ID", placeholder="Enter employee ID")
+        pin = st.text_input("PIN", type="password", placeholder="Enter your PIN")
+        submitted = st.form_submit_button("Initialize workspace")
+
+    if submitted:
+        emp_id_clean = emp_id.strip().lower()
+        if not emp_id_clean or not pin:
+            st.session_state.login_error = "Please enter both your employee ID and PIN."
+            st.rerun()
+
+        if emp_id_clean == ADMIN_ID:
+            if pin == ADMIN_PIN:
+                st.session_state[ROLE_KEY] = "admin"
+                st.session_state[ID_KEY] = ADMIN_ID
+                st.session_state[NAME_KEY] = "Admin"
+                st.success("Admin login successful.")
+                st.write("Redirect to admin_dashboard.html")
+            else:
+                st.session_state.login_error = "Incorrect ID or PIN."
+                st.rerun()
+        else:
+            st.session_state.login_error = ""
+            st.info("Firebase login needs a Python Firestore client and config in Streamlit.")
+            st.write(f"Employee ID entered: `{emp_id_clean}`")
+
+    st.divider()
+
+    if st.button("Forgot your PIN?"):
+        st.session_state.forgot_open = not st.session_state.forgot_open
+
+    if st.session_state.forgot_open:
+        st.markdown("### Reset PIN")
+        with st.form("forgot_form"):
+            forgot_id = st.text_input("Employee ID", placeholder="Enter employee ID", key="forgot_id")
+            send = st.form_submit_button("Send reset request")
+
+        if send:
+            forgot_id_clean = forgot_id.strip().lower()
+            if not forgot_id_clean:
+                st.session_state.forgot_status = "Please enter your employee ID."
+            else:
+                st.session_state.forgot_status = f"Reset request queued for `{forgot_id_clean}` at {datetime.now().isoformat()}."
+            st.write(st.session_state.forgot_status)
