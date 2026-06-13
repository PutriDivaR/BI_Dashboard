"""utils_bi.py – Design tokens, CSS global, dan shared helpers."""
import pandas as pd
import streamlit as st
from sqlalchemy import text
from database.database import engine

# ══════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════
MINT      = "#2EAF7D"
MINT_SOFT = "#5ECBA1"
MINT_DARK = "#1A6B4A"
MINT_BG   = "#EAF8F2"
MINT_MID  = "#A2DCCA"

RED    = "#E05252"
AMBER  = "#F59E0B"
BLUE   = "#3B82F6"
PURP   = "#8B7FD4"
TEAL   = "#0D9488"
ROSE   = "#F43F5E"

TEXT_DARK  = "#1A2E24"
TEXT_MID   = "#4A6259"
TEXT_LIGHT = "#8FA898"
BG_PAGE    = "#F0F7F3"
BG_CARD    = "#FFFFFF"
BORDER     = "#DFF0E8"

# ── Chart palette (dipakai di page_dashboard) ─────────────────────────
C_CHURN    = "#E05252"
C_RETAINED = "#2EAF7D"
C_AMBER    = "#F59E0B"
C_BLUE     = "#3B82F6"
C_PURP     = "#8B7FD4"
C_TEAL     = "#0D9488"
C_ROSE     = "#F43F5E"

FONT = "Outfit, sans-serif"

# ══════════════════════════════════════════════════════════════════════
# GLOBAL CSS — diinjeksi sekali lewat page_header() di setiap halaman
# ══════════════════════════════════════════════════════════════════════
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

/* ── Base ──────────────────────────────────────────────────────────── */
html, body, [class*="css"], .stApp {
    font-family: 'Outfit', 'Inter', sans-serif !important;
    background-color: #F0F7F3 !important;
    color: #1A2E24 !important;
}

/* ── Block container padding & layout ─────────────────────────────── */
.block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2rem !important;
    /* Slightly wider default max-width but keep comfortable gutters */
    max-width: 1400px !important;
    padding-left: 28px !important;
    padding-right: 28px !important;
}

/* ── Sidebar (minimal):
    Leave detailed sidebar layout/styling to page-level CSS (e.g. `app.py`) so
    the application can inject a branded header/brand-strip without being
    overridden by the global theme. We keep this placeholder here in case
    lightweight sidebar tweaks are needed later. */

/* NOTE: app.py injects the full branded sidebar styles. Removing the more
    opinionated sidebar rules from the global theme prevents layout conflicts
    while preserving color tokens used across pages. */

/* ── Metric containers ─────────────────────────────────────────────── */
div[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid #DFF0E8 !important;
    border-radius: 14px !important;
    padding: 18px 16px 14px !important;
    box-shadow: 0 2px 8px rgba(46,175,125,0.06) !important;
}
div[data-testid="stMetricValue"]  { font-size: 26px !important; font-weight: 800 !important; }
div[data-testid="stMetricLabel"]  { font-size: 11px !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 0.5px; color: #8FA898 !important; }

/* ── Buttons ───────────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #2EAF7D 0%, #1A6B4A 100%) !important;
    color: white !important; font-weight: 700 !important; font-size: 13px !important;
    border-radius: 10px !important; border: none !important;
    padding: 10px 22px !important;
    box-shadow: 0 4px 14px rgba(46,175,125,0.28) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(46,175,125,0.38) !important;
    transform: translateY(-1px) !important;
}

/* ── Select / text input ───────────────────────────────────────────── */
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextInput"] > div > div {
    border-radius: 10px !important;
    border: 1.5px solid #DFF0E8 !important;
    background: white !important;
}
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label {
    font-size: 11px !important; font-weight: 700 !important;
    color: #8FA898 !important; text-transform: uppercase; letter-spacing: 0.5px;
}

/* ── Expander ──────────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1.5px solid #DFF0E8 !important;
    border-radius: 14px !important;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    font-weight: 700 !important; font-size: 13px !important; color: #1A2E24 !important;
    padding: 14px 18px !important;
}

/* ── Dataframe ─────────────────────────────────────────────────────── */
div[data-testid="stDataFrame"] {
    border: 1.5px solid #DFF0E8 !important;
    border-radius: 12px !important; overflow: hidden;
}

/* ── Scrollbar ─────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #F0F7F3; }
::-webkit-scrollbar-thumb { background: #A2DCCA; border-radius: 10px; }

/* ── Hide default streamlit chrome ────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden !important; }

/* ── Responsif: saat sidebar terbuka, konten tetap readable ─────────
   Streamlit otomatis mengatur lebar kolom; kita hanya perlu
   memastikan tidak ada overflow-x tersembunyi.                       */
.main > div { overflow-x: hidden !important; }

/* ── Alert ─────────────────────────────────────────────────────────── */
div[data-testid="stAlert"] { border-radius: 12px !important; }
"""

def inject_css():
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# DATABASE HELPERS
# ══════════════════════════════════════════════════════════════════════
def check_db_ready() -> bool:
    try:
        with engine.connect() as c:
            r = c.execute(text("SELECT COUNT(*) FROM fact_churn")).fetchone()
            return bool(r and r[0] > 0)
    except Exception:
        return False

@st.cache_data(ttl=300)
def load_bi_data() -> pd.DataFrame:
    q = """
    SELECT fc.fact_id, fc.churnFlag, fc.monthlyCharges, fc.totalCharges,
           dc.customer AS customer_id, dc.gender, dc.seniorCitizen,
           dc.partner, dc.dependents,
           dct.contract, dct.contractRiskLevel, dct.paperlessBilling,
           dp.paymentMethod, dp.paymentCategory,
           dt.tenure, dt.tenureBucket, dt.tenureCategory,
           ds.internetService, ds.phoneService, ds.multipleLines,
           ds.onlineSecurity, ds.onlineBackup, ds.deviceProtection,
           ds.techSupport, ds.streamingTV, ds.streamingMovies, ds.serviceCount
    FROM fact_churn fc
    JOIN dim_customer dc  ON fc.customer_id  = dc.customer_id
    JOIN dim_contract dct ON fc.contract_id  = dct.contract_id
    JOIN dim_payment  dp  ON fc.payment_id   = dp.payment_id
    JOIN dim_services ds  ON fc.service_id   = ds.service_id
    JOIN dim_tenure   dt  ON fc.tenure_id    = dt.tenure_id
    """
    return pd.read_sql(q, con=engine)

# ══════════════════════════════════════════════════════════════════════
# REUSABLE PLOTLY THEME
# ══════════════════════════════════════════════════════════════════════
def theme_fig(fig, height=300):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_family=FONT, font_color=TEXT_DARK, height=height,
        margin=dict(l=8, r=8, t=40, b=8), font_size=12,
        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDER, tickfont_size=11)
    fig.update_yaxes(showgrid=True,  gridcolor="#E6F4EE", zeroline=False,
                     linecolor=BORDER, tickfont_size=11)
    return fig

# ══════════════════════════════════════════════════════════════════════
# UI PRIMITIVES
# ══════════════════════════════════════════════════════════════════════
def page_header(icon, title, subtitle):
    inject_css()
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{MINT} 0%,{MINT_DARK} 100%);
         border-radius:20px; padding:26px 30px; margin-bottom:22px; position:relative; overflow:hidden;">
        <div style="position:absolute;top:-30px;right:-30px;width:140px;height:140px;
             background:rgba(255,255,255,0.07);border-radius:50%;"></div>
        <div style="position:absolute;bottom:-50px;right:100px;width:180px;height:180px;
             background:rgba(255,255,255,0.04);border-radius:50%;"></div>
        <h1 style="color:white!important;font-size:24px!important;font-weight:900!important;
             margin:0 0 5px!important;position:relative;z-index:1;">{icon} {title}</h1>
        <p style="color:rgba(255,255,255,0.78)!important;font-size:13px!important;
             margin:0!important;position:relative;z-index:1;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

def section_title(text):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;margin:22px 0 14px;">
        <div style="width:4px;height:18px;background:{MINT};border-radius:3px;"></div>
        <span style="font-size:14px;font-weight:800;color:{TEXT_DARK};letter-spacing:-0.2px;">{text}</span>
        <div style="flex:1;height:1px;background:{BORDER};margin-left:4px;"></div>
    </div>
    """, unsafe_allow_html=True)

def card_open():
    st.markdown(f'<div style="background:{BG_CARD};border:1.5px solid {BORDER};border-radius:16px;padding:20px;box-shadow:0 2px 12px rgba(46,175,125,0.05);margin-bottom:4px;">', unsafe_allow_html=True)

def card_close():
    st.markdown('</div>', unsafe_allow_html=True)

def card_header(icon, title):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;
         padding-bottom:10px;border-bottom:1px solid {BORDER};">
        <div style="width:32px;height:32px;background:{MINT_BG};border-radius:8px;
             display:flex;align-items:center;justify-content:center;font-size:16px;">{icon}</div>
        <span style="font-size:14px;font-weight:800;color:{TEXT_DARK};">{title}</span>
    </div>
    """, unsafe_allow_html=True)

def empty_state(msg="Data Warehouse belum siap. Jalankan ETL terlebih dahulu."):
    st.markdown(f"""
    <div style="text-align:center;padding:60px 20px;background:{BG_CARD};
         border-radius:20px;border:2px dashed {BORDER};">
        <div style="font-size:48px;margin-bottom:14px;">🗄️</div>
        <h3 style="color:{TEXT_MID};font-size:18px;margin-bottom:8px;">Data Warehouse Kosong</h3>
        <p style="color:{TEXT_LIGHT};font-size:13px;">{msg}</p>
    </div>
    """, unsafe_allow_html=True)

def churn_rate_bar(label, rate, max_rate=55):
    color = C_CHURN if rate >= 40 else C_AMBER if rate >= 25 else C_RETAINED
    pct = min(rate / max_rate * 100, 100)
    st.markdown(f"""
    <div style="margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:12px;font-weight:600;color:{TEXT_DARK};">{label}</span>
            <span style="font-size:12px;font-weight:800;color:{color};">{rate:.1f}%</span>
        </div>
        <div style="background:#E6F4EE;border-radius:8px;height:7px;overflow:hidden;">
            <div style="width:{pct:.1f}%;height:100%;
                 background:linear-gradient(90deg,{color}CC,{color});
                 border-radius:8px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)