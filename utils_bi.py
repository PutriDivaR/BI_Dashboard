"""utils.py – Utility functions and styling tokens for Churn BI."""
import pandas as pd  # type: ignore
import streamlit as st  # type: ignore
from sqlalchemy import text  # type: ignore
from database.database import engine, get_db_status

# ==================================================
# THEME COLOR CONSTANTS (Mint & White)
# ==================================================
MINT = "#2EAF7D"
MINT_SOFT = "#82E0AA"
MINT_DARK = "#1A3026"
MINT_BG = "#E8F8F2"
MINT_MID = "#A2E2C9"

RED = "#E76F51"
AMBER = "#F4B400"
BLUE = "#1A73E8"
PURP = "#8B7FD4"

TEXT_DARK = "#1A3026"
TEXT_MID = "#4A5D52"
TEXT_LIGHT = "#6C7A72"

BG_CARD = "#FFFFFF"
BORDER = "#E2EFE9"

CHURN_PALETTE = ["#2EAF7D", "#E76F51"]

# ==================================================
# DATABASE UTILITIES
# ==================================================
def check_db_ready() -> bool:
    """Memeriksa apakah data warehouse sudah di-load dengan baris data"""
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM fact_churn")).fetchone()
            if res and res[0] > 0:
                return True
    except Exception:
        pass
    return False

@st.cache_data(ttl=300)
def load_bi_data() -> pd.DataFrame:
    """Mengambil data live dengan JOIN lengkap star-schema dari database"""
    query = """
    SELECT 
        fc.fact_id,
        fc.churnFlag,
        fc.monthlyCharges,
        fc.totalCharges,
        dc.customer AS customer_id,
        dc.gender,
        dc.seniorCitizen,
        dc.partner,
        dc.dependents,
        dct.contract,
        dct.contractRiskLevel,
        dct.paperlessBilling,
        dp.paymentMethod,
        dp.paymentCategory,
        dt.tenure,
        dt.tenureBucket,
        dt.tenureCategory,
        ds.internetService,
        ds.serviceCount,
        ds.onlineSecurity,
        ds.onlineBackup,
        ds.deviceProtection,
        ds.techSupport,
        ds.streamingTV,
        ds.streamingMovies
    FROM fact_churn fc
    JOIN dim_customer dc ON fc.customer_id = dc.customer_id
    JOIN dim_contract dct ON fc.contract_id = dct.contract_id
    JOIN dim_payment dp ON fc.payment_id = dp.payment_id
    JOIN dim_services ds ON fc.service_id = ds.service_id
    JOIN dim_tenure dt ON fc.tenure_id = dt.tenure_id
    """
    return pd.read_sql(query, con=engine)

# ==================================================
# PLOTLY CHART STYLING UTILITIES
# ==================================================
def theme_fig(fig, height=300):
    """Menyelaraskan tema warna & font grafik Plotly ke Mint & White"""
    fig.update_layout(
        height=height,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_family="Outfit, sans-serif",
        font_color="#1A3026",
        margin=dict(l=15, r=15, t=40, b=15)
    )
    fig.update_xaxes(showgrid=False, linecolor='#E2EFE9')
    fig.update_yaxes(showgrid=True, gridcolor='#E2EFE9', linecolor='#E2EFE9')
    return fig

# ==================================================
# UI CONTAINER & HEADER UTILITIES
# ==================================================
def page_header(icon, title, subtitle):
    """Renders the standard page header with custom CSS injection."""
    st.markdown(f"""
    <style>
        /* Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"], .stApp {{
            font-family: 'Outfit', 'Inter', sans-serif;
            background-color: #F4F9F6;
        }}
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {{
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2EFE9;
        }}
        
        /* Custom headers styling */
        h1, h2, h3, h4, h5, h6 {{
            color: #1A3026 !important;
            font-weight: 700 !important;
        }}
        
        /* Metric Card Customization */
        div[data-testid="metric-container"] {{
            background-color: #FFFFFF !important;
            border: 1px solid #E2EFE9 !important;
            border-left: 5px solid #2EAF7D !important;
            padding: 18px 15px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 10px rgba(46, 175, 125, 0.05) !important;
        }}
        
        div[data-testid="stMetricValue"] {{
            color: #1A3026 !important;
            font-size: 26px !important;
            font-weight: 700 !important;
        }}
        
        div[data-testid="stMetricLabel"] {{
            color: #6C7A72 !important;
            font-size: 13px !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        /* Custom layout containers (Cards) */
        .custom-card, .card {{
            background-color: #FFFFFF;
            border: 1px solid #E2EFE9;
            border-radius: 12px;
            padding: 22px;
            box-shadow: 0 4px 12px rgba(46, 175, 125, 0.03);
            margin-bottom: 20px;
        }}
        
        .card-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 15px;
        }}
        .card-icon {{
            font-size: 20px;
        }}
        .card-header h3 {{
            margin: 0 !important;
            font-size: 16px !important;
            color: #1A3026 !important;
        }}
        
        /* Database active badge styling */
        .db-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .badge-mysql {{
            background-color: #E8F8F2;
            color: #2EAF7D;
            border: 1px solid #A2E2C9;
        }}
        .badge-sqlite {{
            background-color: #FFF3CD;
            color: #856404;
            border: 1px solid #FFEBAA;
        }}
        
        /* Button redesign */
        .stButton>button {{
            background-color: #2EAF7D !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 8px 20px !important;
            transition: all 0.2s ease-in-out !important;
            box-shadow: 0 3px 6px rgba(46, 175, 125, 0.15) !important;
        }}
        .stButton>button:hover {{
            background-color: #27966B !important;
            box-shadow: 0 5px 12px rgba(46, 175, 125, 0.25) !important;
            transform: translateY(-1px);
        }}
        
        /* Tables design override */
        div[data-testid="stDataFrame"] {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #E2EFE9;
            padding: 10px;
        }}
        
        /* Risk Badges for Customer Details */
        .risk-high {{
            background-color: #FFF0F0;
            color: #E76F51;
            border: 1px solid #E76F5140;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }}
        .risk-medium {{
            background-color: #FFF8E1;
            color: #C68000;
            border: 1px solid #C6800040;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }}
        .risk-low {{
            background-color: #E8F8F2;
            color: #2EAF7D;
            border: 1px solid #2EAF7D40;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"<h1>{icon} {title}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #6C7A72; margin-top:-10px;'>{subtitle}</p>", unsafe_allow_html=True)
    st.divider()

def section_title(title):
    """Renders a formatted section title."""
    st.markdown(f"<h3 style='margin-top:20px; margin-bottom:15px; color:#1A3026;'>{title}</h3>", unsafe_allow_html=True)

def card_open():
    """Opens a styled card container."""
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)

def card_close():
    """Closes a styled card container."""
    st.markdown('</div>', unsafe_allow_html=True)

def card_header(icon, title):
    """Renders a header inside a card."""
    st.markdown(f"""
    <div class="card-header">
        <div class="card-icon">{icon}</div>
        <h3>{title}</h3>
    </div>
    """, unsafe_allow_html=True)

def empty_state():
    """Renders an empty state warning when the database is empty."""
    st.warning("⚠️ Data Warehouse belum siap atau data kosong. Silakan jalankan proses ETL di menu 'ETL & Data Quality' terlebih dahulu!")

def churn_rate_bar(label, rate, max_rate=100):
    """Renders a beautiful horizontal progress bar for segment churn rates."""
    color = RED if rate >= 40 else AMBER if rate >= 20 else MINT
    width_pct = min(100.0, (rate / max_rate * 100)) if max_rate else 0
    st.markdown(f"""
    <div style="margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px;">
            <span style="font-weight:600; color:{TEXT_DARK};">{label}</span>
            <span style="font-weight:700; color:{color};">{rate:.1f}%</span>
        </div>
        <div style="background:#E2EFE9; border-radius:6px; height:8px; width:100%; overflow:hidden;">
            <div style="background:{color}; width:{width_pct}%; height:100%; border-radius:6px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)