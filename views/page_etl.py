"""page_etl.py – Halaman ETL & Data Quality Pipeline."""
import pandas as pd  # type: ignore
import plotly.graph_objects as go  # type: ignore
import streamlit as st  # type: ignore
from sqlalchemy import text  # type: ignore

from database.database import engine, get_db_status
from ETL.etl_process import run_etl
from utils_bi import (
    MINT, MINT_SOFT, MINT_DARK, MINT_BG, MINT_MID,
    RED, AMBER, BLUE, TEXT_DARK, TEXT_MID, TEXT_LIGHT, BG_CARD, BORDER,
    theme_fig, page_header, section_title, card_open, card_close, card_header,
    check_db_ready,
)


def render():
    page_header("⚙️", "ETL & Data Pipeline",
                "Monitor dan eksekusi proses Extract–Transform–Load ke Data Warehouse")

    db_type, db_uri = get_db_status()
    is_ready = check_db_ready()

    # ─────────────────────────────────────────────────
    # STATUS ROW
    # ─────────────────────────────────────────────────
    section_title("🖥️ Status Infrastruktur")
    s1, s2, s3, s4 = st.columns(4)

    # DB type
    with s1:
        if db_type == "MySQL":
            color, icon, label = MINT, "🟢", "MySQL Connected"
        else:
            color, icon, label = AMBER, "🟡", "SQLite Fallback"
        st.markdown(f"""
        <div class="card" style="border-top:3px solid {color};">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                 color:{TEXT_LIGHT};letter-spacing:0.5px;margin-bottom:8px;">Database Engine</div>
            <div style="font-size:22px;font-weight:800;color:{TEXT_DARK};">{icon} {db_type}</div>
            <div style="font-size:12px;color:{TEXT_MID};margin-top:4px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    # DWH status
    with s2:
        try:
            with engine.connect() as c:
                fact_cnt = c.execute(text("SELECT COUNT(*) FROM fact_churn")).fetchone()[0]
        except Exception:
            fact_cnt = 0
        wh_color = MINT if is_ready else RED
        wh_icon  = "✅" if is_ready else "❌"
        wh_label = "Ready & Populated" if is_ready else "Empty / Not Loaded"
        st.markdown(f"""
        <div class="card" style="border-top:3px solid {wh_color};">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                 color:{TEXT_LIGHT};letter-spacing:0.5px;margin-bottom:8px;">Data Warehouse</div>
            <div style="font-size:22px;font-weight:800;color:{TEXT_DARK};">{wh_icon} {fact_cnt:,}</div>
            <div style="font-size:12px;color:{TEXT_MID};margin-top:4px;">{wh_label}</div>
        </div>
        """, unsafe_allow_html=True)

    # Dataset info
    with s3:
        st.markdown(f"""
        <div class="card" style="border-top:3px solid {BLUE};">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                 color:{TEXT_LIGHT};letter-spacing:0.5px;margin-bottom:8px;">Dataset Sumber</div>
            <div style="font-size:22px;font-weight:800;color:{TEXT_DARK};">7,043</div>
            <div style="font-size:12px;color:{TEXT_MID};margin-top:4px;">
                IBM Watson Telco · 21 kolom · CSV
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Schema info
    with s4:
        st.markdown(f"""
        <div class="card" style="border-top:3px solid {MINT_SOFT};">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                 color:{TEXT_LIGHT};letter-spacing:0.5px;margin-bottom:8px;">DWH Schema</div>
            <div style="font-size:22px;font-weight:800;color:{TEXT_DARK};">6 Tabel</div>
            <div style="font-size:12px;color:{TEXT_MID};margin-top:4px;">
                5 Dimensi + 1 Fakta · Star Schema
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ETL FLOW DIAGRAM
    # ─────────────────────────────────────────────────
    section_title("🔄 Alur ETL Pipeline")

    steps = [
        ("📥", "EXTRACT",     "Baca CSV\nIBM Watson Telco\n7.043 baris × 21 kolom",  MINT),
        ("⚡", "TRANSFORM",   "Cleaning + Feature Eng.\nTotalCharges, SeniorCitizen\nRisk/Bucket columns", "#4A90D9"),
        ("🏗️", "INIT SCHEMA", "Drop & Create Tables\nDDL di MySQL/SQLite\nStar Schema",  "#8B7FD4"),
        ("📦", "LOAD DIMS",   "5 Tabel Dimensi\ndim_customer, _contract\n_payment, _services, _tenure", AMBER),
        ("⭐", "LOAD FACT",   "1 Tabel Fakta\nfact_churn\n7.043 baris dimuat", RED),
        ("✅", "VALIDATE",    "Cek COUNT, SUM\nChurn Rate, Join Integrity\nKPI Validation",  MINT_DARK),
    ]

    cols = st.columns(len(steps))
    for i, (icon, title, desc, color) in enumerate(steps):
        with cols[i]:
            connector = "" if i == len(steps)-1 else f"""
            <div style="position:absolute; right:-12px; top:30px; z-index:1;
                 width:24px; height:24px; background:white; border:2px solid {BORDER};
                 border-radius:50%; display:flex; align-items:center; justify-content:center;
                 font-size:14px;">→</div>"""
            st.markdown(f"""
            <div style="background:{BG_CARD}; border:2px solid {color}40;
                 border-top:4px solid {color}; border-radius:14px; padding:16px 14px;
                 text-align:center; position:relative; height:150px;
                 display:flex; flex-direction:column; align-items:center; justify-content:center;">
                <div style="font-size:26px; margin-bottom:6px;">{icon}</div>
                <div style="font-size:13px; font-weight:800; color:{color}; margin-bottom:6px;
                     letter-spacing:0.3px;">{title}</div>
                <div style="font-size:11px; color:{TEXT_LIGHT}; line-height:1.5;
                     white-space:pre-line;">{desc}</div>
                {connector}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ETL EXECUTION
    # ─────────────────────────────────────────────────
    section_title("🚀 Eksekusi ETL Pipeline")

    ex1, ex2 = st.columns([1, 1.5])

    with ex1:
        st.markdown(f"""
        <div class="card">
            <div class="card-header">
                <div class="card-icon">ℹ️</div>
                <h3>Tentang Pipeline Ini</h3>
            </div>
            <ul style="font-size:13px; color:{TEXT_MID}; line-height:1.9; padding-left:18px; margin:0;">
                <li>Membaca dataset CSV mentah</li>
                <li>Membersihkan nilai kosong TotalCharges</li>
                <li>Mengkonversi SeniorCitizen ke label</li>
                <li>Menambah kolom ContractRisk, PaymentCategory</li>
                <li>Membuat TenureBucket & ServiceCount</li>
                <li>Membangun 5 dimensi + 1 fact table</li>
                <li>Validasi hasil load</li>
            </ul>
            <div style="margin-top:16px; padding:12px; background:{MINT_BG};
                 border-radius:10px; font-size:12px; color:{MINT_DARK}; font-weight:600;">
                ⚠️ Pipeline akan menghapus data lama dan memuat ulang dari awal.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with ex2:
        st.markdown(f"""
        <div class="card">
            <div class="card-header">
                <div class="card-icon">🚀</div>
                <h3>Jalankan Pipeline</h3>
            </div>
        """, unsafe_allow_html=True)

        # UX decision: for a single viewer scenario we usually don't want a visible
        # "Run ETL" button when the data warehouse is already populated. Keep
        # the button visible only when DW is empty (is_ready == False). If an
        # operator wants to force a reload, set environment variable
        # ETL_ALLOW_FORCE=1 to reveal a force-run control.
        import os

        if not is_ready:
            if st.button("▶  Jalankan ETL Pipeline Sekarang", use_container_width=True):
                log_area = st.empty()
                logs = []

                def append_log(msg):
                    logs.append(msg)
                    log_area.code("\n".join(logs), language="bash")

                with st.spinner("Menjalankan ETL..."):
                    success, message = run_etl(log_callback=append_log)

                if success:
                    st.success("✅ ETL Pipeline berhasil! Data Warehouse siap digunakan.")
                    st.balloons()
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ ETL Gagal: {message}")
            else:
                st.markdown(f"""
                <div style="border:2px dashed {BORDER}; border-radius:12px; padding:30px 20px;
                     text-align:center; color:{TEXT_LIGHT};">
                    <div style="font-size:32px; margin-bottom:8px;">▶️</div>
                    <div style="font-size:13px;">Log eksekusi akan muncul di sini</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # When DW is populated hide the button for ordinary viewers and show
            # an informational message. Allow forced runs only when explicitly
            # enabled by an env var to avoid accidental reloads by viewers.
            st.info("Data Warehouse sudah terisi. ETL tidak diperlukan untuk melihat Dashboard.")
            if os.getenv("ETL_ALLOW_FORCE", "0") == "1":
                st.markdown("<small style='color:#6C7A72'>Force-run enabled by environment variable.</small>", unsafe_allow_html=True)
                if st.button("▶  Jalankan ETL Pipeline (FORCE)", use_container_width=True):
                    log_area = st.empty()
                    logs = []

                    def append_log(msg):
                        logs.append(msg)
                        log_area.code("\n".join(logs), language="bash")

                    with st.spinner("Menjalankan ETL (FORCE)..."):
                        success, message = run_etl(log_callback=append_log)

                    if success:
                        st.success("✅ ETL Pipeline (FORCE) berhasil! Data Warehouse siap digunakan.")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ ETL Gagal: {message}")
            else:
                st.markdown(f"<div style='padding:12px 0; color:{TEXT_MID}; font-size:13px;'>Jika butuh refresh data untuk debugging atau development, jalankan ETL dari server/CLI atau set environment variable <code>ETL_ALLOW_FORCE=1</code>.</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # STAR SCHEMA DIAGRAM
    # ─────────────────────────────────────────────────
    section_title("📐 Star Schema – Data Warehouse")

    schema_cols = st.columns([1,1,1,1,1])
    dims = [
        ("dim_customer",  "👤", MINT,  ["customer_id (PK)","customer","gender","seniorCitizen","partner","dependents"]),
        ("dim_contract",  "📋", BLUE,  ["contract_id (PK)","contract","contractRiskLevel","paperlessBilling"]),
        ("dim_payment",   "💳", AMBER, ["payment_id (PK)","paymentMethod","paymentCategory"]),
        ("dim_services",  "🔧", "#8B7FD4",["service_id (PK)","phoneService","multipleLines","internetService","...9 kolom"]),
        ("dim_tenure",    "⏳", RED,   ["tenure_id (PK)","tenure","tenureBucket","tenureCategory"]),
    ]

    for i,(name, icon, color, cols_) in enumerate(dims):
        with schema_cols[i]:
            rows = "".join([f'<div style="padding:3px 0;font-size:11px;color:{TEXT_MID};">{c}</div>' for c in cols_])
            st.markdown(f"""
            <div style="background:{BG_CARD}; border:1.5px solid {color}50;
                 border-top:3px solid {color}; border-radius:12px; padding:14px 12px;
                 text-align:center;">
                <div style="font-size:20px;">{icon}</div>
                <div style="font-size:12px;font-weight:800;color:{color};margin:6px 0 10px;">{name}</div>
                {rows}
                <div style="margin-top:10px;padding-top:8px;border-top:1px dashed {BORDER};
                     font-size:11px;color:{color};font-weight:600;">FK → fact_churn</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Fact table center
    st.markdown(f"""
    <div style="text-align:center; margin: 4px 0 8px; font-size:24px; color:{TEXT_LIGHT};">↓</div>
    <div style="background:linear-gradient(135deg,{MINT}15,{RED}10);
         border:2px solid {MINT}50; border-radius:16px; padding:20px 28px; max-width:680px; margin:0 auto;">
        <div style="text-align:center; margin-bottom:14px;">
            <span style="font-size:18px;">⭐</span>
            <span style="font-size:17px; font-weight:800; color:{TEXT_DARK}; margin-left:8px;">fact_churn</span>
            <span style="font-size:12px; color:{TEXT_LIGHT}; margin-left:8px;">(7.043 baris)</span>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; font-size:13px;">
            <div><b style="color:{MINT_DARK};">Foreign Keys:</b><br>
                <span style="color:{TEXT_MID};">customer_id, contract_id, payment_id, service_id, tenure_id</span></div>
            <div><b style="color:{MINT_DARK};">Measures:</b><br>
                <span style="color:{TEXT_MID};">churnFlag (0/1), monthlyCharges, totalCharges</span></div>
            <div><b style="color:{MINT_DARK};">Key KPIs:</b><br>
                <span style="color:{TEXT_MID};">ChurnRate, AvgCharges, RevenueLoss, RetentionRate</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # DATA QUALITY REPORT
    # ─────────────────────────────────────────────────
    if is_ready:
        section_title("📊 Data Quality & Validasi Post-ETL")

        try:
            with engine.connect() as c:
                fact_cnt   = c.execute(text("SELECT COUNT(*) FROM fact_churn")).fetchone()[0]
                churn_sum  = c.execute(text("SELECT SUM(churnFlag) FROM fact_churn")).fetchone()[0]
                avg_rate   = c.execute(text("SELECT AVG(CAST(churnFlag AS FLOAT))*100 FROM fact_churn")).fetchone()[0]
                avg_m_churn= c.execute(text("SELECT AVG(monthlyCharges) FROM fact_churn WHERE churnFlag=1")).fetchone()[0]
                avg_m_ret  = c.execute(text("SELECT AVG(monthlyCharges) FROM fact_churn WHERE churnFlag=0")).fetchone()[0]
                null_total = c.execute(text("SELECT COUNT(*) FROM fact_churn WHERE totalCharges IS NULL")).fetchone()[0]

            checks = [
                ("COUNT fact_churn = 7.043",      fact_cnt == 7043,  f"Actual: {fact_cnt:,}"),
                ("SUM(churnFlag) ≈ 1.869",         1800 < churn_sum < 1950, f"Actual: {churn_sum:,}"),
                ("Churn Rate ≈ 26.5%",             24 < avg_rate < 29, f"Actual: {avg_rate:.2f}%"),
                ("Avg MonthlyCharges Churn > $70",  avg_m_churn and avg_m_churn > 70, f"Actual: ${avg_m_churn:.2f}"),
                ("Avg MonthlyCharges Retained < $70",avg_m_ret and avg_m_ret < 70,    f"Actual: ${avg_m_ret:.2f}"),
                ("TotalCharges NULL = 0",           null_total == 0,   f"Actual: {null_total}"),
            ]

            q1, q2 = st.columns(2)
            for i, (check, passed, actual) in enumerate(checks):
                col = q1 if i % 2 == 0 else q2
                with col:
                    status = "✅ PASS" if passed else "❌ FAIL"
                    color  = MINT if passed else RED
                    bg     = MINT_BG if passed else "#FFF0F0"
                    st.markdown(f"""
                    <div style="background:{bg}; border:1px solid {color}40;
                         border-left:4px solid {color}; border-radius:10px;
                         padding:12px 16px; margin-bottom:10px;
                         display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:13px; font-weight:600; color:{TEXT_DARK};">{check}</div>
                            <div style="font-size:12px; color:{TEXT_LIGHT}; margin-top:2px;">{actual}</div>
                        </div>
                        <div style="font-size:13px; font-weight:700; color:{color}; white-space:nowrap;">{status}</div>
                    </div>
                    """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Tidak dapat memuat validasi: {e}")