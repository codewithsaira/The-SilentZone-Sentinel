"""Authentication, User Management, and Operations Access for The SilentZone Sentinel.
Clean, professional single-card layout without sidebars, author avatars, or images.
"""
import sys
from pathlib import Path
import streamlit as st

# Ensure backend modules are reachable
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from backend.app import database as db
except ImportError:
    from app import database as db


def render_auth_page():
    """Renders a clean, non-scrolling single-card auth layout without images or sidebars."""
    st.markdown(
        """
        <style>
        /* Eliminate extra top whitespace and hide ONLY the Deploy button (keep three dots menu) */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1.8rem !important;
            padding-right: 1.8rem !important;
            max-width: 100% !important;
        }
        /* Hide Deploy button across Streamlit versions */
        .stDeployButton,
        .stAppDeployButton,
        div[data-testid="stDeployButton"],
        button[data-testid="stDeployButton"],
        div[data-testid="stAppDeployButton"],
        button[data-testid="stAppDeployButton"],
        [data-testid="stToolbarActions"],
        [data-testid="stToolbarAction"],
        header [data-testid="stToolbarActions"],
        header [data-testid="stAppDeployButton"],
        header [data-testid="stDeployButton"],
        header div:has(> button[data-testid="stDeployButton"]),
        header div:has(> button[data-testid="stAppDeployButton"]) {
            display: none !important;
            visibility: hidden !important;
            width: 0px !important;
            height: 0px !important;
            max-width: 0px !important;
            max-height: 0px !important;
            overflow: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            margin: 0px !important;
            padding: 0px !important;
            border: none !important;
        }
        /* Ensure Three-Dots Menu is visible */
        #MainMenu,
        [data-testid="stMainMenu"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        footer {
            display: none !important;
        }

        .main-title-compact {
            font-size: 2.1rem;
            font-weight: 800;
            color: #1e3d59;
            text-align: center;
            margin: 0;
            line-height: 1.2;
            letter-spacing: -0.5px;
        }
        .urdu-sub-compact {
            font-size: 1.2rem;
            color: #17b978;
            font-weight: bold;
            text-align: center;
            margin: 0.2rem 0 0.6rem 0;
        }
        .center-auth-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1.5rem 1.8rem 1.2rem 1.8rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.07);
        }
        .stTextInput {
            margin-bottom: -4px !important;
        }
        .stTextInput > div > div > input {
            padding: 6px 12px !important;
            font-size: 0.92rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    import streamlit.components.v1 as components
    components.html(
        """
        <script>
        function removeDeployBtn() {
            try {
                const targets = [
                    '[data-testid="stDeployButton"]',
                    '[data-testid="stAppDeployButton"]',
                    '.stDeployButton',
                    '.stAppDeployButton',
                    '[data-testid="stToolbarActions"]',
                    'header [data-testid="stToolbarActions"]',
                    'header [data-testid="stAppDeployButton"]',
                    'header [data-testid="stDeployButton"]'
                ];
                targets.forEach(selector => {
                    const els = window.parent.document.querySelectorAll(selector);
                    els.forEach(el => {
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('visibility', 'hidden', 'important');
                        el.style.setProperty('width', '0px', 'important');
                        el.style.setProperty('height', '0px', 'important');
                    });
                });
            } catch(e) {}
        }
        removeDeployBtn();
        setInterval(removeDeployBtn, 200);
        </script>
        """,
        height=0,
        width=0,
    )

    # Clean Center Single Layout Column
    _, col_center, _ = st.columns([1, 2.2, 1])

    with col_center:
        st.markdown(
            """
            <div class='center-auth-card'>
                <div class='main-title-compact'>🛡️ The SilentZone Sentinel</div>
                <div class='urdu-sub-compact'>خاموش زون سینٹینیل - ملٹی ایجنٹ فلڈ رسپانس سسٹم</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        tab_login, tab_signup, tab_forgot = st.tabs([
            "🔐 Login",
            "📝 Sign Up",
            "🔑 Forgot Password",
        ])

        # 1. Login Tab
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                u_ident = st.text_input("Username or Gmail", placeholder="e.g. operator or your@gmail.com")
                u_pass = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_btn = st.form_submit_button("🚀 Log In to Command Centre", type="primary", use_container_width=True)

                if submit_btn:
                    user = db.authenticate_user(u_ident, u_pass)
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        st.success(f"Welcome back, {user['name']}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please verify your username/Gmail and password.")

        # 2. Direct Sign Up Tab
        with tab_signup:
            with st.form("direct_signup_form", clear_on_submit=False):
                c_s1, c_s2 = st.columns(2)
                with c_s1:
                    s_name = st.text_input("Full Name", placeholder="e.g. Operator Name")
                    s_username = st.text_input("Username", placeholder="e.g. op_username")
                with c_s2:
                    s_email = st.text_input("Gmail Address", placeholder="e.g. user@gmail.com")
                    s_pw = st.text_input("Password", type="password", placeholder="Min 4 chars")
                s_pw_confirm = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
                signup_submit = st.form_submit_button("✨ Register Account", type="primary", use_container_width=True)

                if signup_submit:
                    if not s_email or "@" not in s_email:
                        st.error("Please enter a valid Gmail / Email address.")
                    elif s_pw != s_pw_confirm:
                        st.error("Passwords do not match!")
                    elif len(s_pw) < 4:
                        st.error("Password must be at least 4 characters long.")
                    elif len(s_username.strip()) < 3:
                        st.error("Username must be at least 3 characters long.")
                    else:
                        ok, msg = db.register_user(
                            username=s_username,
                            email=s_email,
                            password=s_pw,
                            name=s_name,
                        )
                        if ok:
                            st.success(f"🎉 {msg} Please switch to the **Login** tab.")
                        else:
                            st.error(f"⚠️ {msg}")

        # 3. Forgot Password Tab
        with tab_forgot:
            with st.form("forgot_password_form", clear_on_submit=False):
                f_ident = st.text_input("Registered Gmail or Username", placeholder="e.g. user@gmail.com or username")
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    f_new_pw = st.text_input("New Password", type="password", placeholder="Min 4 chars")
                with c_f2:
                    f_new_confirm = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
                reset_submit = st.form_submit_button("🔄 Reset Password", type="primary", use_container_width=True)

                if reset_submit:
                    if not f_ident:
                        st.error("Please enter your registered Gmail or username.")
                    elif f_new_pw != f_new_confirm:
                        st.error("New passwords do not match!")
                    elif len(f_new_pw) < 4:
                        st.error("Password must be at least 4 characters long.")
                    else:
                        ok, msg = db.reset_user_password(f_ident, f_new_pw)
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")