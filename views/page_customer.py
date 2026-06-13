"""page_customer.py – Halaman Customer Analysis."""
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

from database.database import engine
from utils_bi import (
    MINT, MINT_SOFT, MINT_DARK, MINT_BG, MINT_MID,
    RED, AMBER, BLUE, TEXT_DARK, TEXT_MID, TEXT_LIGHT, BG_CARD, BORDER,
    theme_fig, page_header, section_title,
    card_open, card_close, card_header, empty_state, check_db_ready,
)

# ── SQL ───────────────────────────────────────────────────────────────────────
_SQL_LIST = """
SELECT dc.customer AS customer_id, dc.gender, dc.seniorCitizen, dc.partner,
       dc.dependents, dct.contract, dct.contractRiskLevel, dct.paperlessBilling,
       dp.paymentMethod, dp.paymentCategory,
       ds.phoneService, ds.multipleLines, ds.internetService, ds.onlineSecurity,
       ds.onlineBackup, ds.deviceProtection, ds.techSupport,
       ds.streamingTV, ds.streamingMovies, ds.serviceCount,
       dt.tenure, dt.tenureBucket, dt.tenureCategory,
       fc.monthlyCharges, fc.totalCharges,
       CASE WHEN fc.churnFlag=1 THEN 'Yes' ELSE 'No' END AS Churn,
       fc.churnFlag
FROM fact_churn fc
JOIN dim_customer dc  ON fc.customer_id = dc.customer_id
JOIN dim_contract dct ON fc.contract_id = dct.contract_id
JOIN dim_payment  dp  ON fc.payment_id  = dp.payment_id
JOIN dim_services ds  ON fc.service_id  = ds.service_id
JOIN dim_tenure   dt  ON fc.tenure_id   = dt.tenure_id
ORDER BY fc.churnFlag DESC, dc.customer
"""

_SQL_DETAIL = """
SELECT dc.customer AS customer_id, dc.gender, dc.seniorCitizen, dc.partner,
       dc.dependents, dct.contract, dct.contractRiskLevel, dct.paperlessBilling,
       dp.paymentMethod, dp.paymentCategory,
       ds.phoneService, ds.multipleLines, ds.internetService, ds.onlineSecurity,
       ds.onlineBackup, ds.deviceProtection, ds.techSupport,
       ds.streamingTV, ds.streamingMovies, ds.serviceCount,
       dt.tenure, dt.tenureBucket, dt.tenureCategory,
       fc.monthlyCharges, fc.totalCharges,
       CASE WHEN fc.churnFlag=1 THEN 'Yes' ELSE 'No' END AS Churn,
       fc.churnFlag
FROM fact_churn fc
JOIN dim_customer dc  ON fc.customer_id = dc.customer_id
JOIN dim_contract dct ON fc.contract_id = dct.contract_id
JOIN dim_payment  dp  ON fc.payment_id  = dp.payment_id
JOIN dim_services ds  ON fc.service_id  = ds.service_id
JOIN dim_tenure   dt  ON fc.tenure_id   = dt.tenure_id
WHERE dc.customer = :cid
LIMIT 1
"""

@st.cache_data(ttl=300)
def load_customer_list() -> pd.DataFrame:
    return pd.read_sql(_SQL_LIST, con=engine)

def get_customer_detail(cid: str):
    with engine.connect() as c:
        return c.execute(text(_SQL_DETAIL), {"cid": cid}).fetchone()

# ── Badges ────────────────────────────────────────────────────────────────────
def _svc_badge(val):
    v = str(val).lower()
    if v == "yes":
        return f'<span style="background:{MINT_BG};color:{MINT_DARK};border:1px solid {MINT_MID};padding:2px 9px;border-radius:12px;font-size:12px;font-weight:600;">✓ Aktif</span>'
    if "no phone" in v or v == "no":
        return '<span style="background:#F5F5F5;color:#9E9E9E;border:1px solid #E0E0E0;padding:2px 9px;border-radius:12px;font-size:12px;">N/A</span>'
    if v in ("fiber optic", "dsl"):  # ← internet service aktif
        return f'<span style="background:{MINT_BG};color:{MINT_DARK};border:1px solid {MINT_MID};padding:2px 9px;border-radius:12px;font-size:12px;font-weight:600;">✓ {val}</span>'
    return '<span style="background:#FFF0F0;color:#D93025;border:1px solid #FFCDD2;padding:2px 9px;border-radius:12px;font-size:12px;font-weight:600;">✗ Tidak</span>'

def _risk_badge(level):
    m = {"high": ("risk-high", "🔴 High Risk"), "medium": ("risk-medium", "🟡 Medium Risk")}
    cls, txt = m.get(str(level).lower(), ("risk-low", "🟢 Low Risk"))
    return f'<span class="{cls}">{txt}</span>'

# ── KPI Card ──────────────────────────────────────────────────────────────────
def _kpi(col, icon, label, value, color):
    with col:
        st.markdown(f"""
        <div style="border-top:3px solid {color};border-radius:12px;background:#FFFFFF;
             box-shadow:0 1px 4px rgba(0,0,0,.08);padding:16px 18px;height:120px;
             box-sizing:border-box;display:flex;flex-direction:column;justify-content:space-between;">
            <div style="display:flex;align-items:flex-start;gap:6px;">
                <span style="font-size:13px;line-height:1.3;">{icon}</span>
                <span style="font-size:10px;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.5px;color:{TEXT_LIGHT};line-height:1.3;">{label}</span>
            </div>
            <div style="font-size:24px;font-weight:800;color:{TEXT_DARK};line-height:1;">{value}</div>
        </div>""", unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def render():
    page_header("👥", "Customer Analysis", "Profil, segmentasi, dan analisis individual pelanggan")

    if not check_db_ready():
        empty_state(); return

    df = load_customer_list()

    # KPI Cards
    total, churned = len(df), int(df["churnFlag"].sum())
    cols = st.columns(6)
    for c, icon, lbl, val, clr in zip(cols, ["👥","❌","✅","⚠️","🔧","💰"],
        ["Total Customer","Total Churn","Total Retained","High Risk Contract",
         "Avg Active Services","Avg Monthly Charges"],
        [f"{total:,}", f"{churned:,}", f"{total-churned:,}",
         f"{(df['contractRiskLevel']=='High').sum():,}",
         f"{df['serviceCount'].mean():.1f}", f"${df['monthlyCharges'].mean():.2f}"],
        [MINT, RED, MINT_DARK, AMBER, BLUE, MINT_SOFT]):
        _kpi(c, icon, lbl, val, clr)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabel + Filter ────────────────────────────────────────────────────────
    section_title("🔍 Daftar & Pencarian Pelanggan")
    fc1, fc2, fc3, fc4 = st.columns([2,1,1,1])
    search     = fc1.text_input("Cari Customer ID", placeholder="contoh: 7590-VHVEG").strip()
    churn_f    = fc2.selectbox("Status Churn",  ["Semua","Yes","No"], key="cust_churn")
    risk_f     = fc3.selectbox("Risk Level",    ["Semua","High","Medium","Low"], key="cust_risk")
    internet_f = fc4.selectbox("Internet",      ["Semua"]+sorted(df["internetService"].dropna().unique().tolist()), key="cust_inet")

    disp = df.copy()
    if search:        disp = disp[disp["customer_id"].str.contains(search, case=False, na=False)]
    if churn_f    != "Semua": disp = disp[disp["Churn"]             == churn_f]
    if risk_f     != "Semua": disp = disp[disp["contractRiskLevel"] == risk_f]
    if internet_f != "Semua": disp = disp[disp["internetService"]   == internet_f]

    COLS = ["customer_id","gender","seniorCitizen","tenure","tenureBucket",
            "contract","contractRiskLevel","internetService",
            "paymentMethod","monthlyCharges","totalCharges","serviceCount","Churn"]
    RENAME = {"customer_id":"Customer ID","gender":"Gender","seniorCitizen":"Senior",
              "tenure":"Tenure (Bln)","tenureBucket":"Bucket","contract":"Kontrak",
              "contractRiskLevel":"Risk","internetService":"Internet",
              "paymentMethod":"Payment","monthlyCharges":"Monthly ($)",
              "totalCharges":"Total ($)","serviceCount":"Services","Churn":"Churn?"}

    st.dataframe(
        disp[COLS].rename(columns=RENAME).style
            .apply(lambda r: ["background:#FFF5F5" if r["Churn?"]=="Yes" else "" for _ in r], axis=1)
            .format({"Monthly ($)":"${:.2f}", "Total ($)":"${:.2f}"}),
        use_container_width=True, height=300, hide_index=True,
    )
    cap, dl = st.columns([3,1])
    cap.caption(f"Menampilkan {len(disp):,} dari {total:,} pelanggan")
    dl.download_button("⬇️ Export CSV", disp[COLS].to_csv(index=False).encode(),
                       "customer_export.csv", "text/csv", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Detail Profil ─────────────────────────────────────────────────────────
    section_title("👤 Detail Profil Pelanggan")
    col_s, _ = st.columns([1,2])
    detail_id = col_s.text_input("Masukkan Customer ID untuk detail lengkap",
                                  value=search or "", placeholder="7590-VHVEG",
                                  key="detail_search").strip()
    if detail_id:
        p = get_customer_detail(detail_id)
        if p is None:
            st.error(f"Customer ID `{detail_id}` tidak ditemukan.")
        else:
            is_churn = p.churnFlag == 1
            sc, st_txt, si = (RED,"Churned","❌") if is_churn else (MINT,"Retained (Aktif)","✅")
            st.markdown(f"""
            <div style="background:{'#FFF5F5' if is_churn else MINT_BG};border:1.5px solid {sc}40;
                 border-radius:14px;padding:16px 22px;margin-bottom:16px;
                 display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
                <div style="font-size:36px;">{si}</div>
                <div>
                    <div style="font-size:20px;font-weight:800;color:{TEXT_DARK};">{p.customer_id}</div>
                    <div style="font-size:13px;font-weight:600;color:{sc};margin-top:2px;">{st_txt}</div>
                </div>
                <div style="margin-left:auto;display:flex;gap:10px;flex-wrap:wrap;">
                    {_risk_badge(p.contractRiskLevel)}
                    <span style="background:#EEF4FF;color:{BLUE};border:1px solid #C7DCFF;
                          padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;">
                        {p.tenureCategory} ({p.tenure} bln)</span>
                    <span style="background:#F5F0FF;color:{BLUE};border:1px solid #D8C9FF;
                          padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;">
                        {p.serviceCount} Layanan Aktif</span>
                </div>
            </div>""", unsafe_allow_html=True)

            d1, d2, d3 = st.columns(3)

            def _row(label, val, first=False):
                border = "" if first else f"border-top:1px solid {BORDER};"
                return f"""<tr style="{border}">
                    <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;
                         text-transform:uppercase;">{label}</td>
                    <td style="text-align:right;font-weight:600;font-size:13px;">{val}</td></tr>"""

            with d1:
                st.markdown(f"""
                <div class="card">
                    <div class="card-header"><div class="card-icon">👤</div><h3>Demografi & Akun</h3></div>
                    <table style="width:100%;font-size:13px;border-collapse:collapse;">
                        {_row("Gender", p.gender, True)}
                        {_row("Senior Citizen", p.seniorCitizen)}
                        {_row("Partner", p.partner)}
                        {_row("Tanggungan", p.dependents)}
                        {_row("Tenure", f"{p.tenure} bln ({p.tenureBucket})")}
                    </table>
                    <div style="border-top:1px solid {BORDER};margin-top:14px;padding-top:14px;">
                        <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                             color:{TEXT_LIGHT};margin-bottom:10px;">Tagihan</div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                            <span style="font-size:13px;color:{TEXT_MID};">Monthly Charges</span>
                            <span style="font-size:16px;font-weight:800;color:{MINT_DARK};">${p.monthlyCharges:.2f}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;">
                            <span style="font-size:13px;color:{TEXT_MID};">Total Charges</span>
                            <span style="font-size:16px;font-weight:800;color:{MINT_DARK};">${p.totalCharges:.2f}</span>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

            with d2:
                rmap = {"High":("#FFF0F0",RED),"Medium":("#FFF8E1","#C68000"),"Low":(MINT_BG,MINT_DARK)}
                rb, rt = rmap.get(str(p.contractRiskLevel),(MINT_BG,MINT_DARK))
                risk_span = f'<span style="background:{rb};color:{rt};border:1px solid {rt}40;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700;">{p.contractRiskLevel}</span>'
                st.markdown(f"""
                <div class="card">
                    <div class="card-header"><div class="card-icon">📋</div><h3>Kontrak & Pembayaran</h3></div>
                    <table style="width:100%;font-size:13px;border-collapse:collapse;">
                        {_row("Tipe Kontrak", p.contract, True)}
                        {_row("Risk Level", risk_span)}
                        {_row("Paperless Billing", p.paperlessBilling)}
                        {_row("Metode Bayar", p.paymentMethod)}
                        {_row("Kategori Bayar", p.paymentCategory)}
                        {_row("Tenure Category", p.tenureCategory)}
                    </table>
                </div>""", unsafe_allow_html=True)

            with d3:
                svcs = [("📞 Phone Service",p.phoneService),("📡 Multiple Lines",p.multipleLines),
                        ("🌐 Internet Service",p.internetService),("🔒 Online Security",p.onlineSecurity),
                        ("☁️ Online Backup",p.onlineBackup),("🛡️ Device Protection",p.deviceProtection),
                        ("🔧 Tech Support",p.techSupport),("📺 Streaming TV",p.streamingTV),
                        ("🎬 Streaming Movies",p.streamingMovies)]
                rows = "".join(f'<tr style="border-top:1px solid {BORDER};"><td style="padding:7px 0;color:{TEXT_MID};font-size:12px;">{l}</td><td style="text-align:right;">{_svc_badge(v)}</td></tr>' for l,v in svcs)
                st.markdown(f"""
                <div class="card">
                    <div class="card-header"><div class="card-icon">🔌</div><h3>Layanan ({p.serviceCount} Aktif)</h3></div>
                    <table style="width:100%;font-size:13px;border-collapse:collapse;">{rows}</table>
                </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Segmentasi ────────────────────────────────────────────────────────────
    section_title("📊 Segmentasi Pelanggan")

    g1, g2 = st.columns(2)
    with g1:
        card_open(); card_header("📦","Distribusi Contract Risk Level")
        rc = df["contractRiskLevel"].value_counts().reset_index()
        rc.columns = ["Risk Level","Jumlah"]
        fig = px.pie(rc, names="Risk Level", values="Jumlah", hole=0.5,
                     color="Risk Level", color_discrete_map={"High":RED,"Medium":AMBER,"Low":MINT})
        fig.update_traces(textinfo="percent+label", textfont_size=12,
                          marker=dict(line=dict(color="white",width=2)))
        theme_fig(fig,280); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False}); card_close()

    with g2:
        card_open(); card_header("⏱️","Distribusi Tenure Category")
        tc = df["tenureCategory"].value_counts().reset_index()
        tc.columns = ["Kategori","Jumlah"]
        fig = px.bar(tc, x="Kategori", y="Jumlah", color="Kategori",
                     color_discrete_sequence=[RED,AMBER,MINT], text="Jumlah")
        fig.update_traces(textposition="outside",marker_line_width=0)
        fig.update_layout(showlegend=False,xaxis_title="",yaxis_title="Jumlah Pelanggan",
                          yaxis=dict(range=[0, tc["Jumlah"].max() * 1.15]))
        theme_fig(fig,280); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False}); card_close()

    g3, g4 = st.columns(2)
    for col, icon, title, grp_col in [
        (g3,"🌐","Churn Rate by Internet Service","internetService"),
        (g4,"📋","Churn Rate by Tipe Kontrak","contract"),
    ]:
        with col:
            card_open(); card_header(icon, title)
            grp = df.groupby([grp_col,"Churn"]).size().reset_index(name="count")
            y_max = grp["count"].max()
            fig = px.bar(grp, x=grp_col, y="count", color="Churn", barmode="group",
                         color_discrete_map={"Yes":RED,"No":MINT}, text="count")
            fig.update_traces(texttemplate="%{text:,}",textposition="outside",textfont_size=11)
            fig.update_layout(showlegend=True,xaxis_title="",yaxis_title="Jumlah Pelanggan",
                              yaxis=dict(range=[0, y_max * 1.15]),
                              legend=dict(orientation="h",yanchor="bottom",y=1.02,
                                          xanchor="right",x=1,font=dict(size=11)))
            theme_fig(fig,280); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False}); card_close()

    st.markdown("<br>", unsafe_allow_html=True)