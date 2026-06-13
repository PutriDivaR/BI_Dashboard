"""app.py – Main entrypoint for Customer Churn BI."""
import streamlit as st
from database.database import get_db_status

# ── page views ───────────────────────────────────────────────────────
import importlib
from views import page_dashboard, page_customer, page_etl
importlib.reload(page_dashboard)
importlib.reload(page_customer)
importlib.reload(page_etl)

# ── page config (HARUS dipanggil sebelum element lain) ───────────────
st.set_page_config(
    page_title="Customer Churn BI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── session state: active page ────────────────────────────────────────
PAGES = ["Dashboard", "Customer Analysis", "ETL & Pipeline"]

if "active_page" not in st.session_state:
    # Baca dari query param kalau ada
    qp = st.query_params.get("page", "Dashboard")
    st.session_state.active_page = qp if qp in PAGES else "Dashboard"

# ── inject CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Outfit', sans-serif !important; }

/* Sembunyikan sidebar bawaan Streamlit */
section[data-testid="stSidebar"] { display: none !important; }

/* ── FIXED NAVBAR ── */
.navbar-wrapper {
    position: fixed;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    width: calc(100% - 40px);
    max-width: 1400px;
    z-index: 9999;
    background: rgba(255,255,255,0.95);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(46,175,125,0.18);
    border-radius: 18px;
    padding: 10px 22px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.07), 0 2px 8px rgba(46,175,125,0.08);
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.navbar-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
}

.navbar-logo {
    background: linear-gradient(135deg, #2EAF7D, #1A6B4A);
    color: white;
    padding: 9px 14px;
    border-radius: 12px;
    font-weight: 800;
    font-size: 15px;
    line-height: 1;
}

.navbar-subtitle {
    color: #4A6259;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
}

/* Nav links */
.navbar-nav {
    display: flex;
    align-items: center;
    gap: 4px;
}

.nav-btn {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 9px 18px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    color: #4A6259;
    cursor: pointer;
    border: none;
    background: transparent;
    text-decoration: none;
    transition: background 0.18s, color 0.18s, box-shadow 0.18s;
    white-space: nowrap;
    font-family: 'Outfit', sans-serif;
}

.nav-btn:hover {
    background: rgba(46,175,125,0.10);
    color: #1A6B4A;
}

.nav-btn.active {
    background: linear-gradient(135deg, #2EAF7D, #1A6B4A);
    color: white !important;
    box-shadow: 0 4px 12px rgba(46,175,125,0.30);
}

/* Push page content below fixed navbar */
.block-container {
    padding-top: 100px !important;
    max-width: 1400px;
}

/* db badge */
.db-pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 14px; border-radius: 20px;
    font-size: 12px; font-weight: 700; margin-top: 6px;
}
.db-mysql  { background: #EAF8F2; color: #2EAF7D; border: 1px solid #A2DCCA; }
.db-sqlite { background: #FFF8E1; color: #856404; border: 1px solid #FFE082; }

@media (max-width: 768px) {
    .block-container { padding-left: 12px !important; padding-right: 12px !important; }
    .navbar-subtitle { display: none; }
    .nav-btn { padding: 8px 11px; font-size: 12px; }
}
</style>
""", unsafe_allow_html=True)

# ── Navbar HTML (full, fixed — tidak bergantung widget Streamlit) ─────
NAV_ICONS = {
    "Dashboard":         "📊",
    "Customer Analysis": "👥",
    "ETL & Pipeline":    "⚙️",
}

def _nav_html(active: str) -> str:
    buttons = ""
    for page in PAGES:
        cls = "nav-btn active" if page == active else "nav-btn"
        icon = NAV_ICONS[page]
        # Klik tombol kirim query param via JS → lalu Streamlit re-run
        # Cara paling andal: pakai st.query_params + rerun via anchor link
        safe = page.replace(" ", "+").replace("&", "%26")
        buttons += (
            f'<a href="?page={safe}" class="{cls}" '
            f'target="_self" style="text-decoration:none;">'
            f'{icon} {page}</a>'
        )
    return f"""
    <div class="navbar-wrapper">
        <div class="navbar-brand">
            <div class="navbar-logo">📊 Churn BI</div>
            <div class="navbar-subtitle">Customer Intelligence Dashboard</div>
        </div>
        <nav class="navbar-nav">
            {buttons}
        </nav>
    </div>
    """

st.markdown(_nav_html(st.session_state.active_page), unsafe_allow_html=True)

# ── Sync query param → session state setiap load ─────────────────────
qp_page = st.query_params.get("page", "Dashboard")
# decode tanda + dan %26 yang mungkin datang dari URL
qp_page = qp_page.replace("+", " ").replace("%26", "&")
if qp_page in PAGES and qp_page != st.session_state.active_page:
    st.session_state.active_page = qp_page

selected = st.session_state.active_page

# ── Router ────────────────────────────────────────────────────────────
if selected == "Dashboard":
    page_dashboard.render()
elif selected == "Customer Analysis":
    page_customer.render()
elif selected == "ETL & Pipeline":
    page_etl.render()