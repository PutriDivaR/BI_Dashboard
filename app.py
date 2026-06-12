import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import pandas as pd
from sqlalchemy import text
from database.database import engine, get_db_status
from ETL.etl_process import run_etl

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Customer Churn BI",
    page_icon="📊",
    layout="wide"
)

# ==================================================
# CUSTOM CSS THEME INJECTION (Mint & White)
# ==================================================
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', 'Inter', sans-serif;
        background-color: #F4F9F6;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2EFE9;
    }
    
    /* Custom headers styling */
    h1, h2, h3, h4, h5, h6 {
        color: #1A3026 !important;
        font-weight: 700 !important;
    }
    
    /* Metric Card Customization */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2EFE9 !important;
        border-left: 5px solid #2EAF7D !important;
        padding: 18px 15px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 10px rgba(46, 175, 125, 0.05) !important;
    }
    
    div[data-testid="stMetricValue"] {
        color: #1A3026 !important;
        font-size: 26px !important;
        font-weight: 700 !important;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #6C7A72 !important;
        font-size: 13px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Custom layout containers (Cards) */
    .custom-card {
        background-color: #FFFFFF;
        border: 1px solid #E2EFE9;
        border-radius: 12px;
        padding: 22px;
        box-shadow: 0 4px 12px rgba(46, 175, 125, 0.03);
        margin-bottom: 20px;
    }
    
    /* Database active badge styling */
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
    
    /* Button redesign */
    .stButton>button {
        background-color: #2EAF7D !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 3px 6px rgba(46, 175, 125, 0.15) !important;
    }
    .stButton>button:hover {
        background-color: #27966B !important;
        box-shadow: 0 5px 12px rgba(46, 175, 125, 0.25) !important;
        transform: translateY(-1px);
    }
    
    /* Tables design override */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #E2EFE9;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# SIDEBAR NAVIGATION
# ==================================================
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
# UTILITY FUNCTIONS FOR DATABASE CHECK & LOAD
# ==================================================
def check_db_ready():
    """Memeriksa apakah data warehouse sudah di-load dengan baris data"""
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM fact_churn")).fetchone()
            if res and res[0] > 0:
                return True
    except Exception:
        pass
    return False

@st.cache_data
def load_bi_data():
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
        ds.serviceCount
    FROM fact_churn fc
    JOIN dim_customer dc ON fc.customer_id = dc.customer_id
    JOIN dim_contract dct ON fc.contract_id = dct.contract_id
    JOIN dim_payment dp ON fc.payment_id = dp.payment_id
    JOIN dim_services ds ON fc.service_id = ds.service_id
    JOIN dim_tenure dt ON fc.tenure_id = dt.tenure_id
    """
    return pd.read_sql(query, con=engine)

def style_plotly_fig(fig):
    """Menyelaraskan tema warna & font grafik Plotly ke Mint & White"""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_family="Outfit, sans-serif",
        font_color="#1A3026",
        title_font_size=16,
        title_font_family="Outfit, sans-serif",
        title_font_color="#1A3026",
        margin=dict(l=15, r=15, t=40, b=15)
    )
    fig.update_xaxes(showgrid=False, linecolor='#E2EFE9')
    fig.update_yaxes(showgrid=True, gridcolor='#E2EFE9', linecolor='#E2EFE9')
    return fig

# Status database siap pakai
is_ready = check_db_ready()

# ==================================================
# PAGE: DASHBOARD
# ==================================================
if selected == "Dashboard":
    st.markdown("<h1>📊 Customer Churn Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #6C7A72; margin-top:-10px;'>Business Intelligence & Analytics Platform</p>", unsafe_allow_html=True)
    st.divider()

    if not is_ready:
        st.warning("⚠️ Data Warehouse belum siap atau data kosong. Silakan jalankan proses ETL di menu 'ETL & Data Quality' terlebih dahulu!")
        if st.button("Ke Halaman ETL ➡️"):
            st.info("Buka halaman ETL di sidebar untuk memulai.")
    else:
        df = load_bi_data()
        
        # ======================
        # FILTER SECTION
        # ======================
        with st.expander("🔍 Filter Analisis", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                contract_opts = ["All"] + sorted(list(df['contract'].unique()))
                contract_filter = st.selectbox("Tipe Kontrak", contract_opts)
            with f2:
                internet_opts = ["All"] + sorted(list(df['internetService'].unique()))
                internet_filter = st.selectbox("Layanan Internet", internet_opts)
            with f3:
                payment_opts = ["All"] + sorted(list(df['paymentMethod'].unique()))
                payment_filter = st.selectbox("Metode Pembayaran", payment_opts)
            with f4:
                senior_opts = ["All"] + sorted(list(df['seniorCitizen'].unique()))
                senior_filter = st.selectbox("Senior Citizen Status", senior_opts)

        # Menerapkan filter ke dataframe
        filtered_df = df.copy()
        if contract_filter != "All":
            filtered_df = filtered_df[filtered_df['contract'] == contract_filter]
        if internet_filter != "All":
            filtered_df = filtered_df[filtered_df['internetService'] == internet_filter]
        if payment_filter != "All":
            filtered_df = filtered_df[filtered_df['paymentMethod'] == payment_filter]
        if senior_filter != "All":
            filtered_df = filtered_df[filtered_df['seniorCitizen'] == senior_filter]

        # ======================
        # KPI METRICS SECTION
        # ======================
        total_cust = len(filtered_df)
        if total_cust > 0:
            total_churn = filtered_df['churnFlag'].sum()
            churn_rate = (total_churn / total_cust) * 100
            retention_rate = 100 - churn_rate
            avg_charges = filtered_df['monthlyCharges'].mean()
        else:
            total_churn = 0
            churn_rate = 0.0
            retention_rate = 0.0
            avg_charges = 0.0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Customer", f"{total_cust:,}")
        c2.metric("Total Churn", f"{total_churn:,}")
        c3.metric("Churn Rate", f"{churn_rate:.2f}%")
        c4.metric("Retention Rate", f"{retention_rate:.2f}%")
        c5.metric("Avg Monthly", f"${avg_charges:.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # ======================
        # MAIN VISUALIZATION
        # ======================
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            # Pie/Donut Chart customer distribution
            pie_data = pd.DataFrame({
                "Status": ["Retained", "Churned"],
                "Count": [total_cust - total_churn, total_churn]
            })
            fig_donut = px.pie(
                pie_data,
                names="Status",
                values="Count",
                hole=0.6,
                color="Status",
                color_discrete_map={"Retained": "#2EAF7D", "Churned": "#E76F51"},
                title="Customer Distribution (Status)"
            )
            fig_donut.update_traces(textinfo='percent+label', pull=[0, 0.08])
            fig_donut = style_plotly_fig(fig_donut)
            st.plotly_chart(fig_donut, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_right:
            st.markdown('<div class="custom-card" style="height: 100%;">', unsafe_allow_html=True)
            st.markdown("<h3 style='margin-top:0;'>⚠️ Churn Risk Summary</h3>", unsafe_allow_html=True)
            st.write("Persentase Churn Rate tertinggi pada segmen penting:")
            
            # Helper kalkulasi persentase churn
            def calc_churn_pct(col, val):
                subset = df[df[col] == val]
                if len(subset) == 0: return 0.0
                return (subset['churnFlag'].sum() / len(subset)) * 100

            r_tenure = calc_churn_pct('tenureBucket', '0-12 Bulan')
            r_contract = calc_churn_pct('contract', 'Month-to-month')
            r_payment = calc_churn_pct('paymentMethod', 'Electronic check')
            r_internet = calc_churn_pct('internetService', 'Fiber optic')

            st.error(f"Tenure 0-12 Bulan : {r_tenure:.2f}% Churn")
            st.warning(f"Month-to-Month Contract : {r_contract:.2f}% Churn")
            st.warning(f"Electronic Check Payment : {r_payment:.2f}% Churn")
            st.info(f"Fiber Optic Service : {r_internet:.2f}% Churn")
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # ======================
        # ROW 1 CHARTS (Contract, Internet, Payment)
        # ======================
        a, b, c = st.columns(3)

        with a:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            contract_churn = filtered_df.groupby('contract')['churnFlag'].mean().reset_index()
            contract_churn['Churn Rate (%)'] = contract_churn['churnFlag'] * 100
            fig_contract = px.bar(
                contract_churn,
                x="contract",
                y="Churn Rate (%)",
                text=contract_churn['Churn Rate (%)'].apply(lambda x: f"{x:.1f}%"),
                color_discrete_sequence=["#2EAF7D"],
                title="Churn Rate by Contract"
            )
            fig_contract = style_plotly_fig(fig_contract)
            st.plotly_chart(fig_contract, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with b:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            internet_churn = filtered_df.groupby('internetService')['churnFlag'].mean().reset_index()
            internet_churn['Churn Rate (%)'] = internet_churn['churnFlag'] * 100
            fig_internet = px.bar(
                internet_churn,
                x="internetService",
                y="Churn Rate (%)",
                text=internet_churn['Churn Rate (%)'].apply(lambda x: f"{x:.1f}%"),
                color_discrete_sequence=["#4AD19A"],
                title="Churn Rate by Internet Service"
            )
            fig_internet = style_plotly_fig(fig_internet)
            st.plotly_chart(fig_internet, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            payment_churn = filtered_df.groupby('paymentMethod')['churnFlag'].mean().reset_index()
            payment_churn['Churn Rate (%)'] = payment_churn['churnFlag'] * 100
            fig_payment = px.bar(
                payment_churn,
                x="paymentMethod",
                y="Churn Rate (%)",
                text=payment_churn['Churn Rate (%)'].apply(lambda x: f"{x:.1f}%"),
                color_discrete_sequence=["#27966B"],
                title="Churn Rate by Payment Method"
            )
            fig_payment = style_plotly_fig(fig_payment)
            st.plotly_chart(fig_payment, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ======================
        # ROW 2 CHARTS (Tenure, Senior Citizen, Monthly Charges)
        # ======================
        d, e, f = st.columns(3)

        with d:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            tenure_churn = filtered_df.groupby('tenureBucket')['churnFlag'].mean().reset_index()
            tenure_churn['Churn Rate (%)'] = tenure_churn['churnFlag'] * 100
            # Urutkan bucket
            bucket_order = {"0-12 Bulan": 0, "13-24 Bulan": 1, "25-48 Bulan": 2, "49+ Bulan": 3}
            tenure_churn['order'] = tenure_churn['tenureBucket'].map(bucket_order)
            tenure_churn = tenure_churn.sort_values('order')
            
            fig_tenure = px.bar(
                tenure_churn,
                x="tenureBucket",
                y="Churn Rate (%)",
                text=tenure_churn['Churn Rate (%)'].apply(lambda x: f"{x:.1f}%"),
                color_discrete_sequence=["#82E0AA"],
                title="Churn Rate by Tenure Duration"
            )
            fig_tenure = style_plotly_fig(fig_tenure)
            st.plotly_chart(fig_tenure, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with e:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            senior_churn = filtered_df.groupby('seniorCitizen')['churnFlag'].mean().reset_index()
            senior_churn['Churn Rate (%)'] = senior_churn['churnFlag'] * 100
            fig_senior = px.bar(
                senior_churn,
                x="seniorCitizen",
                y="Churn Rate (%)",
                text=senior_churn['Churn Rate (%)'].apply(lambda x: f"{x:.1f}%"),
                color_discrete_sequence=["#52BE80"],
                title="Churn Rate by Senior Citizen Status"
            )
            fig_senior = style_plotly_fig(fig_senior)
            st.plotly_chart(fig_senior, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with f:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            fig_charges = px.box(
                filtered_df,
                x="churnFlag",
                y="monthlyCharges",
                color="churnFlag",
                color_discrete_map={0: "#2EAF7D", 1: "#E76F51"},
                title="Monthly Charges Distribution"
            )
            fig_charges.update_layout(showlegend=False)
            fig_charges.update_xaxes(tickvals=[0, 1], ticktext=["Retained", "Churned"])
            fig_charges = style_plotly_fig(fig_charges)
            st.plotly_chart(fig_charges, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# PAGE: CUSTOMER ANALYSIS
# ==================================================
elif selected == "Customer Analysis":
    st.markdown("<h1>👥 Customer Profile Analysis</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #6C7A72; margin-top:-10px;'>Cari dan Analisis Karakteristik Individu Pelanggan</p>", unsafe_allow_html=True)
    st.divider()

    if not is_ready:
        st.warning("⚠️ Data Warehouse belum terisi data. Jalankan ETL terlebih dahulu!")
    else:
        # Load data detail customer
        @st.cache_data
        def load_customer_list():
            q = """
            SELECT 
                dc.customer AS customer_id, dc.gender, dc.seniorCitizen, dc.partner, dc.dependents,
                dct.contract, dp.paymentMethod, dt.tenure, fc.monthlyCharges, fc.totalCharges,
                CASE WHEN fc.churnFlag = 1 THEN 'Yes' ELSE 'No' END AS Churn
            FROM fact_churn fc
            JOIN dim_customer dc ON fc.customer_id = dc.customer_id
            JOIN dim_contract dct ON fc.contract_id = dct.contract_id
            JOIN dim_payment dp ON fc.payment_id = dp.payment_id
            JOIN dim_tenure dt ON fc.tenure_id = dt.tenure_id
            """
            return pd.read_sql(q, con=engine)
            
        df_cust = load_customer_list()
        
        # Grid Atas: Cari Customer & Data Grid
        st.subheader("🔍 Pencarian Customer")
        
        col_search, col_filter = st.columns([1, 1])
        with col_search:
            customer_search = st.text_input("Customer ID (contoh: 7590-VHVEG atau 3668-QPYBK)").strip()
        with col_filter:
            churn_filter = st.selectbox("Filter Status Churn", ["All", "Yes", "No"])
            
        display_df = df_cust.copy()
        if customer_search:
            display_df = display_df[display_df['customer_id'].str.contains(customer_search, case=False)]
        if churn_filter != "All":
            display_df = display_df[display_df['Churn'] == churn_filter]

        # Menampilkan data tabel
        st.dataframe(display_df, use_container_width=True, height=250)
        
        # Drill-down profile card
        if customer_search:
            # Query detail profile customer
            def get_customer_detail(cid):
                q = """
                SELECT 
                    dc.customer AS customer_id, dc.gender, dc.seniorCitizen, dc.partner, dc.dependents,
                    dct.contract, dct.contractRiskLevel, dct.paperlessBilling,
                    dp.paymentMethod, dp.paymentCategory,
                    ds.phoneService, ds.multipleLines, ds.internetService, ds.onlineSecurity, 
                    ds.onlineBackup, ds.deviceProtection, ds.techSupport, ds.streamingTV, ds.streamingMovies, ds.serviceCount,
                    dt.tenure, dt.tenureBucket, dt.tenureCategory,
                    fc.monthlyCharges, fc.totalCharges, fc.churnFlag
                FROM fact_churn fc
                JOIN dim_customer dc ON fc.customer_id = dc.customer_id
                JOIN dim_contract dct ON fc.contract_id = dct.contract_id
                JOIN dim_payment dp ON fc.payment_id = dp.payment_id
                JOIN dim_services ds ON fc.service_id = ds.service_id
                JOIN dim_tenure dt ON fc.tenure_id = dt.tenure_id
                WHERE dc.customer = :cid
                """
                with engine.connect() as conn:
                    return conn.execute(text(q), {"cid": cid}).fetchone()
                    
            profile = get_customer_detail(customer_search)
            if profile:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"### 👤 Detail Profil Pelanggan: **{profile.customer_id}**")
                
                # Check status
                status_html = '<span class="db-badge badge-mysql">🟢 Active (Retained)</span>' if profile.churnFlag == 0 else '<span class="db-badge badge-sqlite">🔴 Churned</span>'
                st.markdown(f"Status Pelanggan: {status_html}", unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-card">
                        <h4 style="color:#2EAF7D; margin-top:0; margin-bottom:15px;">Demografi</h4>
                        <table style="width:100%; font-size:14px;">
                            <tr><td style="padding:4px 0; color:#6C7A72;">Gender</td><td style="font-weight:600; text-align:right;">{profile.gender}</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Senior Citizen</td><td style="font-weight:600; text-align:right;">{profile.seniorCitizen}</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Memiliki Pasangan</td><td style="font-weight:600; text-align:right;">{profile.partner}</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Tanggungan</td><td style="font-weight:600; text-align:right;">{profile.dependents}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="custom-card">
                        <h4 style="color:#2EAF7D; margin-top:0; margin-bottom:15px;">Keuangan & Akun</h4>
                        <table style="width:100%; font-size:14px;">
                            <tr><td style="padding:4px 0; color:#6C7A72;">Tenure</td><td style="font-weight:600; text-align:right;">{profile.tenure} Bulan ({profile.tenureCategory})</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Biaya Bulanan</td><td style="font-weight:600; text-align:right; color:#2EAF7D;">${profile.monthlyCharges:.2f}</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Total Biaya</td><td style="font-weight:600; text-align:right; color:#2EAF7D;">${profile.totalCharges:.2f}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div class="custom-card">
                        <h4 style="color:#2EAF7D; margin-top:0; margin-bottom:15px;">Kontrak & Billing</h4>
                        <table style="width:100%; font-size:14px;">
                            <tr><td style="padding:4px 0; color:#6C7A72;">Kontrak</td><td style="font-weight:600; text-align:right;">{profile.contract}</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Risk Level</td><td style="font-weight:600; text-align:right;">{profile.contractRiskLevel} Risk</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Metode Bayar</td><td style="font-weight:600; text-align:right;">{profile.paymentMethod}</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Tipe Bayar</td><td style="font-weight:600; text-align:right;">{profile.paymentCategory}</td></tr>
                            <tr><td style="padding:4px 0; color:#6C7A72;">Paperless Billing</td><td style="font-weight:600; text-align:right;">{profile.paperlessBilling}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    def get_status_emoji(val):
                        if str(val).lower() == 'yes': return "✅ Yes"
                        if str(val).lower() == 'no' or str(val).lower() == 'no phone service' or str(val).lower() == 'no internet service': return "❌ No"
                        return f"🔌 {val}"

                    st.markdown(f"""
                    <div class="custom-card">
                        <h4 style="color:#2EAF7D; margin-top:0; margin-bottom:15px;">Layanan Aktif ({profile.serviceCount} Layanan)</h4>
                        <table style="width:100%; font-size:14px;">
                            <tr><td style="padding:3px 0; color:#6C7A72;">Phone Service</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.phoneService)}</td></tr>
                            <tr><td style="padding:3px 0; color:#6C7A72;">Multiple Lines</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.multipleLines)}</td></tr>
                            <tr><td style="padding:3px 0; color:#6C7A72;">Internet Service</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.internetService)}</td></tr>
                            <tr><td style="padding:3px 0; color:#6C7A72;">Online Security</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.onlineSecurity)}</td></tr>
                            <tr><td style="padding:3px 0; color:#6C7A72;">Online Backup</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.onlineBackup)}</td></tr>
                            <tr><td style="padding:3px 0; color:#6C7A72;">Device Protection</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.deviceProtection)}</td></tr>
                            <tr><td style="padding:3px 0; color:#6C7A72;">Tech Support</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.techSupport)}</td></tr>
                            <tr><td style="padding:3px 0; color:#6C7A72;">Streaming TV</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.streamingTV)}</td></tr>
                            <tr><td style="padding:3px 0; color:#6C7A72;">Streaming Movies</td><td style="font-weight:600; text-align:right;">{get_status_emoji(profile.streamingMovies)}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("Customer ID tidak ditemukan. Periksa kembali ID yang diinput.")

# ==================================================
# PAGE: ETL & DATA QUALITY
# ==================================================
else:
    st.markdown("<h1>⚙️ ETL & Data Quality Pipeline</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #6C7A72; margin-top:-10px;'>Monitor and execute data engineering operations from CSV to MySQL DWH</p>", unsafe_allow_html=True)
    st.divider()

    db_type, db_uri = get_db_status()

    # Grid 1: Database Status
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("Database Target")
        if db_type == "MySQL":
            st.markdown('<span class="db-badge badge-mysql">🟢 MySQL Server Connected</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="db-badge badge-sqlite">🟡 SQLite Fallback Mode</span>', unsafe_allow_html=True)
        st.write(f"**URI**: `{db_uri.split('@')[1] if '@' in db_uri else db_uri}`")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("Data Warehouse Readiness")
        if is_ready:
            st.success("🟢 Warehouse Ready & Populated")
            try:
                with engine.connect() as conn:
                    fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_churn")).fetchone()[0]
                st.write(f"Total baris transaksi: **{fact_count:,} baris**")
            except Exception:
                pass
        else:
            st.error("🔴 Empty / Not Configured")
            st.write("Silakan jalankan pipeline ETL di bawah.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("Data Quality Stats")
        st.write("Dataset: `dataset_TelcoCustomerChurn.csv`")
        st.write("- **Total Dataset Baris**: `7.043` kolom")
        st.write("- **Baris Kualitas TotalCharges**: `11` kosong (dibersihkan)")
        st.write("- **Jumlah Tabel DWH**: 5 Dimensi, 1 Fakta")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Grid 2: ETL Pipeline Trigger & Live Status
    st.subheader("🚀 Eksekusi ETL Pipeline")
    st.write("Proses ini akan membersihkan data, menambahkan fitur bisnis (Risk Level, Payment Type, Service Count, Tenure Buckets), menghapus data lama, lalu memuat data baru ke Data Warehouse.")
    
    if st.button("Jalankan ETL Pipeline Sekarang"):
        # Jalankan ETL dengan callback visual logs
        with st.status("Menjalankan pipeline ETL...", expanded=True) as status:
            log_container = st.empty()
            logs = []
            
            def append_log(msg):
                logs.append(msg)
                log_container.code("\n".join(logs))
                
            success, message = run_etl(log_callback=append_log)
            
            if success:
                status.update(label="Pipeline ETL Berhasil Terbuka!", state="complete", expanded=True)
                st.success("Data Warehouse berhasil dibuat dan diisi! Silakan buka menu **Dashboard** untuk menjelajah.")
                st.balloons()
                # Clear cache agar dashboard mendeteksi data baru
                st.cache_data.clear()
                # Set refresh trigger
                st.rerun()
            else:
                status.update(label="Pipeline ETL Gagal!", state="error", expanded=True)
                st.error(f"Pesan error: {message}")

    st.divider()

    # DWH Schema View
    st.subheader("📐 Model Data Warehouse (Star-Schema)")
    st.write("Hubungan antar tabel dimensi dengan tabel fakta:")
    st.markdown("""
    ```text
     [dim_customer] ---------- (1:N) ----------+
                                               |
     [dim_contract] ---------- (1:N) ----------|
                                               |
     [dim_payment]  ---------- (1:N) ---------> [fact_churn] <--- (MonthlyCharges, TotalCharges, churnFlag)
                                               |
     [dim_services] ---------- (1:N) ----------|
                                               |
     [dim_tenure]   ---------- (1:N) ----------+
    ```
    """)