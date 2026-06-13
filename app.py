"""app.py – Main entrypoint for Customer Churn BI application."""
import streamlit as st
from streamlit_option_menu import option_menu
from database.database import get_db_status

# Import modular pages from views directory
import importlib
from views import page_dashboard, page_customer, page_etl
importlib.reload(page_dashboard)
importlib.reload(page_customer)
importlib.reload(page_etl)

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Customer Churn BI",
    page_icon="📊",
    layout="wide"
)

# ==================================================
# SIDEBAR NAVIGATION & CUSTOM STYLE INJECTION
# ==================================================
# Inject minimal styling for sidebar db-badge before main page styling loads
st.markdown("""
<style>
    .db-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .badge-mysql {
        background-color: #E8F8F2;
        color: #2EAF7D;
        border: 1px solid #A2E2C9;
    }
    .badge-sqlite {
        background-color: #FFF3CD;
        color: #856404;
        border: 1px solid #FFEBAA;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #2EAF7D; margin-bottom: 25px;'>📊 Churn BI</h2>", unsafe_allow_html=True)
    selected = option_menu(
        menu_title=None,
        options=[
            "Dashboard",
            "Customer Analysis",
            "ETL & Data Quality"
        ],
        icons=[
            "speedometer2",
            "people",
            "database-fill-gear"
        ],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#6C7A72", "font-size": "16px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"5px 0px", "border-radius": "8px", "color": "#1A3026"},
            "nav-link-selected": {"background-color": "#2EAF7D", "color": "white", "font-weight": "600"},
        }
    )
    
    # Menampilkan Status DB Terkoneksi di Sidebar
    db_type, _ = get_db_status()
    if db_type == "MySQL":
        st.markdown(f'<div style="text-align:center; margin-top:50px;"><span class="db-badge badge-mysql">🟢 DB: MySQL Aktif</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="text-align:center; margin-top:50px;"><span class="db-badge badge-sqlite">🟡 DB: SQLite Fallback</span></div>', unsafe_allow_html=True)

# ==================================================
# PAGE ROUTING
# ==================================================
if selected == "Dashboard":
    page_dashboard.render()
elif selected == "Customer Analysis":
    page_customer.render()
elif selected == "ETL & Data Quality":
    page_etl.render()