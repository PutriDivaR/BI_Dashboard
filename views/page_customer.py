"""page_customer.py – Halaman Customer Analysis."""
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import streamlit as st  # type: ignore
from sqlalchemy import text  # type: ignore

from database.database import engine
from utils_bi import (
    MINT, MINT_SOFT, MINT_DARK, MINT_BG, MINT_MID,
    RED, AMBER, BLUE, TEXT_DARK, TEXT_MID, TEXT_LIGHT, BG_CARD, BORDER,
    CHURN_PALETTE, theme_fig, page_header, section_title,
    card_open, card_close, card_header, empty_state, check_db_ready, load_bi_data,
)


@st.cache_data(ttl=300)
def load_customer_list() -> pd.DataFrame:
    q = """
    SELECT
        dc.customer AS customer_id, dc.gender, dc.seniorCitizen,
        dc.partner, dc.dependents,
        dct.contract, dct.contractRiskLevel, dct.paperlessBilling,
        dp.paymentMethod, dp.paymentCategory,
        dt.tenure, dt.tenureBucket, dt.tenureCategory,
        ds.internetService, ds.serviceCount,
        fc.monthlyCharges, fc.totalCharges,
        CASE WHEN fc.churnFlag = 1 THEN 'Yes' ELSE 'No' END AS Churn,
        fc.churnFlag
    FROM fact_churn fc
    JOIN dim_customer dc  ON fc.customer_id  = dc.customer_id
    JOIN dim_contract dct ON fc.contract_id  = dct.contract_id
    JOIN dim_payment  dp  ON fc.payment_id   = dp.payment_id
    JOIN dim_services ds  ON fc.service_id   = ds.service_id
    JOIN dim_tenure   dt  ON fc.tenure_id    = dt.tenure_id
    ORDER BY fc.churnFlag DESC, dc.customer
    """
    return pd.read_sql(q, con=engine)


def get_customer_detail(cid: str):
    q = """
    SELECT
        dc.customer AS customer_id, dc.gender, dc.seniorCitizen,
        dc.partner, dc.dependents,
        dct.contract, dct.contractRiskLevel, dct.paperlessBilling,
        dp.paymentMethod, dp.paymentCategory,
        ds.phoneService, ds.multipleLines, ds.internetService,
        ds.onlineSecurity, ds.onlineBackup, ds.deviceProtection,
        ds.techSupport, ds.streamingTV, ds.streamingMovies, ds.serviceCount,
        dt.tenure, dt.tenureBucket, dt.tenureCategory,
        fc.monthlyCharges, fc.totalCharges, fc.churnFlag
    FROM fact_churn fc
    JOIN dim_customer dc  ON fc.customer_id  = dc.customer_id
    JOIN dim_contract dct ON fc.contract_id  = dct.contract_id
    JOIN dim_payment  dp  ON fc.payment_id   = dp.payment_id
    JOIN dim_services ds  ON fc.service_id   = ds.service_id
    JOIN dim_tenure   dt  ON fc.tenure_id    = dt.tenure_id
    WHERE dc.customer = :cid
    LIMIT 1
    """
    with engine.connect() as c:
        row = c.execute(text(q), {"cid": cid}).fetchone()
    return row


def _svc_badge(val):
    v = str(val).lower()
    if v == "yes":
        return f'<span style="background:{MINT_BG};color:{MINT_DARK};border:1px solid {MINT_MID};padding:2px 9px;border-radius:12px;font-size:12px;font-weight:600;">✓ Aktif</span>'
    if v in ("no phone service", "no internet service"):
        return '<span style="background:#F5F5F5;color:#9E9E9E;border:1px solid #E0E0E0;padding:2px 9px;border-radius:12px;font-size:12px;">N/A</span>'
    return '<span style="background:#FFF0F0;color:#D93025;border:1px solid #FFCDD2;padding:2px 9px;border-radius:12px;font-size:12px;font-weight:600;">✗ Tidak</span>'


def _risk_badge(level):
    if str(level).lower() == "high":
        return '<span class="risk-high">🔴 High Risk</span>'
    if str(level).lower() == "medium":
        return '<span class="risk-medium">🟡 Medium Risk</span>'
    return '<span class="risk-low">🟢 Low Risk</span>'


def render():
    page_header("👥", "Customer Analysis",
                "Profil, segmentasi, dan analisis individual pelanggan")

    if not check_db_ready():
        empty_state()
        return

    df = load_customer_list()

    # ─────────────────────────────────────────────────
    # SUMMARY CARDS
    # ─────────────────────────────────────────────────
    total    = len(df)
    churned  = int(df["churnFlag"].sum())
    high_r   = int((df["contractRiskLevel"]=="High").sum())
    avg_svc  = df["serviceCount"].mean()

    s1,s2,s3,s4 = st.columns(4)
    s1.metric("👥 Total Customer",   f"{total:,}")
    s2.metric("❌ Total Churn",       f"{churned:,}")
    s3.metric("⚠️ High Risk Contract",f"{high_r:,}")
    s4.metric("🔧 Avg Active Services",f"{avg_svc:.1f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # TABEL + FILTER
    # ─────────────────────────────────────────────────
    section_title("🔍 Daftar & Pencarian Pelanggan")

    fc1, fc2, fc3, fc4 = st.columns([2,1,1,1])
    with fc1:
        search = st.text_input("Cari Customer ID", placeholder="contoh: 7590-VHVEG").strip()
    with fc2:
        churn_f = st.selectbox("Status Churn", ["Semua","Yes","No"], key="cust_churn")
    with fc3:
        risk_f  = st.selectbox("Risk Level", ["Semua","High","Medium","Low"], key="cust_risk")
    with fc4:
        internet_f = st.selectbox("Internet", ["Semua"]+sorted(df["internetService"].dropna().unique().tolist()), key="cust_inet")

    disp = df.copy()
    if search:       disp = disp[disp["customer_id"].str.contains(search, case=False, na=False)]
    if churn_f   != "Semua": disp = disp[disp["Churn"]               == churn_f]
    if risk_f    != "Semua": disp = disp[disp["contractRiskLevel"]    == risk_f]
    if internet_f!= "Semua": disp = disp[disp["internetService"]      == internet_f]

    # Kolom yang ditampilkan di tabel
    show_cols = ["customer_id","gender","seniorCitizen","tenure","contract",
                 "contractRiskLevel","internetService","paymentMethod",
                 "monthlyCharges","totalCharges","Churn"]
    show_df = disp[show_cols].rename(columns={
        "customer_id":"Customer ID","gender":"Gender","seniorCitizen":"Senior",
        "tenure":"Tenure (Bln)","contract":"Kontrak","contractRiskLevel":"Risk",
        "internetService":"Internet","paymentMethod":"Payment",
        "monthlyCharges":"Monthly ($)","totalCharges":"Total ($)","Churn":"Churn?"
    })

    st.dataframe(
        show_df.style.apply(
            lambda r: ["background:#FFF5F5" if r["Churn?"]=="Yes" else "" for _ in r],
            axis=1
        ),
        use_container_width=True, height=280,
    )
    st.caption(f"Menampilkan {len(disp):,} dari {total:,} pelanggan")

    # ─────────────────────────────────────────────────
    # DETAIL CARD
    # ─────────────────────────────────────────────────
    section_title("👤 Detail Profil Pelanggan")

    col_search, _ = st.columns([1,2])
    with col_search:
        detail_id = st.text_input("Masukkan Customer ID untuk detail lengkap",
                                  value=search or "",
                                  placeholder="7590-VHVEG",
                                  key="detail_search").strip()

    if detail_id:
        p = get_customer_detail(detail_id)
        if p is None:
            st.error(f"Customer ID `{detail_id}` tidak ditemukan.")
        else:
            # Status header
            is_churn = p.churnFlag == 1
            status_color = RED if is_churn else MINT
            status_text  = "Churned" if is_churn else "Retained (Aktif)"
            status_icon  = "❌" if is_churn else "✅"

            st.markdown(f"""
            <div style="background:{'#FFF5F5' if is_churn else MINT_BG};
                 border:1.5px solid {status_color}40;
                 border-radius:14px; padding:16px 22px; margin-bottom:16px;
                 display:flex; align-items:center; gap:16px;">
                <div style="font-size:36px;">{status_icon}</div>
                <div>
                    <div style="font-size:20px; font-weight:800; color:{TEXT_DARK};">
                        {p.customer_id}
                    </div>
                    <div style="font-size:13px; font-weight:600; color:{status_color}; margin-top:2px;">
                        {status_text}
                    </div>
                </div>
                <div style="margin-left:auto; display:flex; gap:10px; flex-wrap:wrap;">
                    {_risk_badge(p.contractRiskLevel)}
                    <span style="background:#EEF4FF;color:{BLUE};border:1px solid #C7DCFF;
                          padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;">
                        {p.tenureCategory} ({p.tenure} bln)
                    </span>
                    <span style="background:#F5F0FF;color:{BLUE};border:1px solid #D8C9FF;
                          padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;">
                        {p.serviceCount} Layanan Aktif
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            d1, d2, d3 = st.columns(3)

            # Card 1: Demografi & Keuangan
            with d1:
                st.markdown(f"""
                <div class="card">
                    <div class="card-header">
                        <div class="card-icon">👤</div>
                        <h3>Demografi & Akun</h3>
                    </div>
                    <table style="width:100%;font-size:13px;border-collapse:collapse;">
                        <tr><td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Gender</td>
                            <td style="text-align:right;font-weight:600;">{p.gender}</td></tr>
                        <tr style="border-top:1px solid {BORDER};">
                            <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Senior Citizen</td>
                            <td style="text-align:right;font-weight:600;">{p.seniorCitizen}</td></tr>
                        <tr style="border-top:1px solid {BORDER};">
                            <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Partner</td>
                            <td style="text-align:right;font-weight:600;">{p.partner}</td></tr>
                        <tr style="border-top:1px solid {BORDER};">
                            <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Tanggungan</td>
                            <td style="text-align:right;font-weight:600;">{p.dependents}</td></tr>
                        <tr style="border-top:1px solid {BORDER};">
                            <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Tenure</td>
                            <td style="text-align:right;font-weight:600;">{p.tenure} bln ({p.tenureBucket})</td></tr>
                    </table>
                    <div style="border-top:1px solid {BORDER};margin-top:14px;padding-top:14px;">
                        <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:{TEXT_LIGHT};margin-bottom:10px;">Tagihan</div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                            <span style="font-size:13px;color:{TEXT_MID};">Monthly Charges</span>
                            <span style="font-size:16px;font-weight:800;color:{MINT_DARK};">${p.monthlyCharges:.2f}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;">
                            <span style="font-size:13px;color:{TEXT_MID};">Total Charges</span>
                            <span style="font-size:16px;font-weight:800;color:{MINT_DARK};">${p.totalCharges:.2f}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Card 2: Kontrak & Pembayaran
            with d2:
                risk_colors = {"High":"#FFF0F0","Medium":"#FFF8E1","Low":MINT_BG}
                risk_text   = {"High":RED,"Medium":"#C68000","Low":MINT_DARK}
                rc = risk_colors.get(p.contractRiskLevel, MINT_BG)
                rt = risk_text.get(p.contractRiskLevel, MINT_DARK)
                st.markdown(f"""
                <div class="card">
                    <div class="card-header">
                        <div class="card-icon">📋</div>
                        <h3>Kontrak & Pembayaran</h3>
                    </div>
                    <table style="width:100%;font-size:13px;border-collapse:collapse;">
                        <tr><td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Tipe Kontrak</td>
                            <td style="text-align:right;font-weight:600;">{p.contract}</td></tr>
                        <tr style="border-top:1px solid {BORDER};">
                            <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Risk Level</td>
                            <td style="text-align:right;">
                                <span style="background:{rc};color:{rt};border:1px solid {rt}40;
                                     padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700;">
                                    {p.contractRiskLevel}
                                </span>
                            </td></tr>
                        <tr style="border-top:1px solid {BORDER};">
                            <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Paperless Billing</td>
                            <td style="text-align:right;font-weight:600;">{p.paperlessBilling}</td></tr>
                        <tr style="border-top:1px solid {BORDER};">
                            <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Metode Bayar</td>
                            <td style="text-align:right;font-weight:600;font-size:12px;">{p.paymentMethod}</td></tr>
                        <tr style="border-top:1px solid {BORDER};">
                            <td style="padding:7px 0;color:{TEXT_LIGHT};font-size:11px;font-weight:700;text-transform:uppercase;">Kategori Bayar</td>
                            <td style="text-align:right;font-weight:600;">{p.paymentCategory}</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)

            # Card 3: Layanan
            with d3:
                services = [
                    ("phoneService",     "📞 Phone Service",     p.phoneService),
                    ("multipleLines",    "📡 Multiple Lines",     p.multipleLines),
                    ("internetService",  "🌐 Internet Service",   p.internetService),
                    ("onlineSecurity",   "🔒 Online Security",    p.onlineSecurity),
                    ("onlineBackup",     "☁️ Online Backup",      p.onlineBackup),
                    ("deviceProtection","🛡️ Device Protection",  p.deviceProtection),
                    ("techSupport",      "🔧 Tech Support",       p.techSupport),
                    ("streamingTV",      "📺 Streaming TV",       p.streamingTV),
                    ("streamingMovies",  "🎬 Streaming Movies",   p.streamingMovies),
                ]
                rows_html = ""
                for _, label, val in services:
                    rows_html += f"""
                    <tr style="border-top:1px solid {BORDER};">
                        <td style="padding:7px 0;color:{TEXT_MID};font-size:12px;">{label}</td>
                        <td style="text-align:right;">{_svc_badge(val)}</td>
                    </tr>"""

                st.markdown(f"""
                <div class="card">
                    <div class="card-header">
                        <div class="card-icon">🔌</div>
                        <h3>Layanan ({p.serviceCount} Aktif)</h3>
                    </div>
                    <table style="width:100%;font-size:13px;border-collapse:collapse;">
                        {rows_html}
                    </table>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # SEGMENT ANALYTICS
    # ─────────────────────────────────────────────────
    section_title("📊 Segmentasi Pelanggan")
    g1, g2 = st.columns(2)

    with g1:
        card_open()
        card_header("📦", "Distribusi Contract Risk Level")
        rc = df["contractRiskLevel"].value_counts().reset_index()
        rc.columns = ["Risk Level","Jumlah"]
        colors_map = {"High":RED,"Medium":AMBER,"Low":MINT}
        rc["color"] = rc["Risk Level"].map(colors_map).fillna(MINT)
        fig = px.pie(rc, names="Risk Level", values="Jumlah", hole=0.5,
                     color="Risk Level",
                     color_discrete_map=colors_map)
        fig.update_traces(
            textinfo="percent+label", textfont_size=12,
            marker=dict(line=dict(color="white", width=2)),
        )
        theme_fig(fig, 280)
        st.plotly_chart(fig, use_container_width=True)
        card_close()

    with g2:
        card_open()
        card_header("⏱️", "Distribusi Tenure Category")
        tc = df["tenureCategory"].value_counts().reset_index()
        tc.columns = ["Kategori","Jumlah"]
        fig = px.bar(tc, x="Kategori", y="Jumlah",
                     color="Kategori",
                     color_discrete_sequence=[RED, AMBER, MINT],
                     text="Jumlah")
        fig.update_traces(textposition="outside", marker_line_width=0)
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Jumlah Pelanggan")
        theme_fig(fig, 280)
        st.plotly_chart(fig, use_container_width=True)
        card_close()