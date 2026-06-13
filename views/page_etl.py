
"""page_etl.py – Halaman ETL & Data Quality Pipeline."""
import os
from typing import Any
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

# ── Warna tambahan (konsisten dengan halaman lain) ──────────────────────────
PURP = "#8B7FD4"
PURP_BG = "#F3F1FD"
AMBER_BG = "#FFFBF0"
RED_BG = "#FFF0F0"
BLUE_BG = "#EFF6FF"


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: ambil metrik kualitas data dari DWH secara dinamis
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def _get_dq_metrics() -> dict[str, Any]:
    """Query semua metrik kualitas data post-ETL dari DWH."""
    try:
        with engine.connect() as c:
            def q(sql) -> Any:
                res = c.execute(text(sql)).fetchone()
                return res[0] if res is not None else 0


            total          = q("SELECT COUNT(*) FROM fact_churn")
            null_tc        = q("SELECT COUNT(*) FROM fact_churn WHERE totalCharges IS NULL")
            null_mc        = q("SELECT COUNT(*) FROM fact_churn WHERE monthlyCharges IS NULL")
            null_cf        = q("SELECT COUNT(*) FROM fact_churn WHERE churnFlag IS NULL")
            distinct_cust  = q("SELECT COUNT(DISTINCT customer_id) FROM fact_churn")
            invalid_churn  = q("SELECT COUNT(*) FROM fact_churn WHERE churnFlag NOT IN (0,1)")
            neg_monthly    = q("SELECT COUNT(*) FROM fact_churn WHERE monthlyCharges <= 0")
            churn_sum      = q("SELECT SUM(churnFlag) FROM fact_churn")
            churn_rate     = q("SELECT AVG(CAST(churnFlag AS FLOAT))*100 FROM fact_churn")
            avg_monthly    = q("SELECT AVG(monthlyCharges) FROM fact_churn")
            min_monthly    = q("SELECT MIN(monthlyCharges) FROM fact_churn")
            max_monthly    = q("SELECT MAX(monthlyCharges) FROM fact_churn")
            avg_monthly_ch = q("SELECT AVG(monthlyCharges) FROM fact_churn WHERE churnFlag=1")
            avg_monthly_rt = q("SELECT AVG(monthlyCharges) FROM fact_churn WHERE churnFlag=0")

            # Referential integrity – orphan FK checks
            orphan_cust    = q("""SELECT COUNT(*) FROM fact_churn f
                                  LEFT JOIN dim_customer d ON f.customer_id=d.customer_id
                                  WHERE d.customer_id IS NULL""")
            orphan_contract= q("""SELECT COUNT(*) FROM fact_churn f
                                  LEFT JOIN dim_contract d ON f.contract_id=d.contract_id
                                  WHERE d.contract_id IS NULL""")
            orphan_payment = q("""SELECT COUNT(*) FROM fact_churn f
                                  LEFT JOIN dim_payment d ON f.payment_id=d.payment_id
                                  WHERE d.payment_id IS NULL""")
            orphan_service = q("""SELECT COUNT(*) FROM fact_churn f
                                  LEFT JOIN dim_services d ON f.service_id=d.service_id
                                  WHERE d.service_id IS NULL""")
            orphan_tenure  = q("""SELECT COUNT(*) FROM fact_churn f
                                  LEFT JOIN dim_tenure d ON f.tenure_id=d.tenure_id
                                  WHERE d.tenure_id IS NULL""")

            # Dimension row counts
            dc  = q("SELECT COUNT(*) FROM dim_customer")
            dco = q("SELECT COUNT(*) FROM dim_contract")
            dp  = q("SELECT COUNT(*) FROM dim_payment")
            ds  = q("SELECT COUNT(*) FROM dim_services")
            dt  = q("SELECT COUNT(*) FROM dim_tenure")

        # ── Hitung skor per dimensi (0–100) ─────────────────────────────────
        total_nulls       = null_tc + null_mc + null_cf
        completeness      = max(0, (1 - total_nulls / (3 * total)) * 100) if total else 0
        uniqueness        = (distinct_cust / total * 100)                  if total else 0
        validity          = max(0, (1 - (invalid_churn + neg_monthly) / (2 * total)) * 100) if total else 0
        total_orphans     = orphan_cust + orphan_contract + orphan_payment + orphan_service + orphan_tenure
        ref_integrity     = max(0, (1 - total_orphans / (5 * total)) * 100) if total else 0
        overall           = (completeness + uniqueness + validity + ref_integrity) / 4

        return {
            "ok": True,
            # Counts
            "total": total, "null_tc": null_tc, "null_mc": null_mc, "null_cf": null_cf,
            "distinct_cust": distinct_cust, "invalid_churn": invalid_churn,
            "neg_monthly": neg_monthly, "churn_sum": int(churn_sum or 0),
            "churn_rate": float(churn_rate or 0),
            "avg_monthly": float(avg_monthly or 0),
            "min_monthly": float(min_monthly or 0),
            "max_monthly": float(max_monthly or 0),
            "avg_monthly_ch": float(avg_monthly_ch or 0),
            "avg_monthly_rt": float(avg_monthly_rt or 0),
            "orphan_cust": orphan_cust, "orphan_contract": orphan_contract,
            "orphan_payment": orphan_payment, "orphan_service": orphan_service,
            "orphan_tenure": orphan_tenure,
            # Dim counts
            "dc": dc, "dco": dco, "dp": dp, "ds": ds, "dt": dt,
            # DQ Scores
            "completeness": completeness, "uniqueness": uniqueness,
            "validity": validity, "ref_integrity": ref_integrity,
            "overall": overall,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: render satu kartu KPI DQ
# ══════════════════════════════════════════════════════════════════════════════
def _dq_kpi_card(col, icon, label, value_str, sub, color, bg=None):
    bg = bg or BG_CARD
    col.markdown(f"""
    <div style="background:{bg}; border:1px solid {color}30;
         border-top:3px solid {color}; border-radius:14px;
         padding:18px 16px; height:100%;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;
             color:{TEXT_LIGHT};letter-spacing:0.5px;margin-bottom:8px;">
            {icon} {label}
        </div>
        <div style="font-size:30px;font-weight:800;color:{color};line-height:1;">
            {value_str}
        </div>
        <div style="font-size:12px;color:{TEXT_MID};margin-top:6px;">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: satu baris validasi pass/fail
# ══════════════════════════════════════════════════════════════════════════════
def _check_row(label, passed, actual, category=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    color  = MINT if passed else RED
    bg     = MINT_BG if passed else RED_BG
    cat_html = (f'<span style="font-size:10px;background:{color}20;color:{color};'
                f'border-radius:4px;padding:1px 6px;margin-right:6px;font-weight:700;">'
                f'{category}</span>') if category else ""
    st.markdown(f"""
    <div style="background:{bg}; border:1px solid {color}40;
         border-left:4px solid {color}; border-radius:10px;
         padding:12px 16px; margin-bottom:8px;
         display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div style="font-size:13px;font-weight:600;color:{TEXT_DARK};">
                {cat_html}{label}
            </div>
            <div style="font-size:11px;color:{TEXT_LIGHT};margin-top:3px;">{actual}</div>
        </div>
        <div style="font-size:12px;font-weight:700;color:{color};white-space:nowrap;
             background:{color}15;padding:4px 10px;border-radius:6px;">{status}</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════════════════════════════
def render():
    page_header("⚙️", "ETL & Data Pipeline",
                "Monitor eksekusi Extract–Transform–Load, kualitas data, dan integritas Data Warehouse")

    db_type, db_uri = get_db_status()
    is_ready = check_db_ready()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 – STATUS INFRASTRUKTUR
    # ══════════════════════════════════════════════════════════════════════════
    section_title("🖥️ Status Infrastruktur")
    s1, s2, s3, s4 = st.columns(4)

    # DB Engine
    with s1:
        c, icon, label = (MINT, "🟢", "MySQL Connected") if db_type == "MySQL" \
                          else (AMBER, "🟡", "SQLite Fallback")
        st.markdown(f"""
        <div class="card" style="border-top:3px solid {c};">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                 color:{TEXT_LIGHT};letter-spacing:0.5px;margin-bottom:8px;">Database Engine</div>
            <div style="font-size:22px;font-weight:800;color:{TEXT_DARK};">{icon} {db_type}</div>
            <div style="font-size:12px;color:{TEXT_MID};margin-top:4px;">{label}</div>
        </div>""", unsafe_allow_html=True)

    # DWH Status
    with s2:
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT COUNT(*) FROM fact_churn")).fetchone()
                fact_cnt = res[0] if res is not None else 0
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
        </div>""", unsafe_allow_html=True)

    # Dataset Sumber
    with s3:
        st.markdown(f"""
        <div class="card" style="border-top:3px solid {BLUE};">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                 color:{TEXT_LIGHT};letter-spacing:0.5px;margin-bottom:8px;">Dataset Sumber</div>
            <div style="font-size:22px;font-weight:800;color:{TEXT_DARK};">7,043</div>
            <div style="font-size:12px;color:{TEXT_MID};margin-top:4px;">
                IBM Watson Telco · 21 kolom · CSV
            </div>
        </div>""", unsafe_allow_html=True)

    # Schema
    with s4:
        st.markdown(f"""
        <div class="card" style="border-top:3px solid {MINT_SOFT};">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                 color:{TEXT_LIGHT};letter-spacing:0.5px;margin-bottom:8px;">DWH Schema</div>
            <div style="font-size:22px;font-weight:800;color:{TEXT_DARK};">6 Tabel</div>
            <div style="font-size:12px;color:{TEXT_MID};margin-top:4px;">
                5 Dimensi + 1 Fakta · Star Schema
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 – ALUR ETL PIPELINE
    # ══════════════════════════════════════════════════════════════════════════
    section_title("🔄 Alur ETL Pipeline")

    steps = [
        ("📥", "EXTRACT",      "Baca CSV\nIBM Watson Telco\n7.043 baris × 21 kolom",   MINT),
        ("⚡", "TRANSFORM",    "Cleaning + Feature Eng.\nTotalCharges, SeniorCitizen\nRisk/Bucket cols",  "#4A90D9"),
        ("🏗️", "INIT SCHEMA",  "Drop & Create Tables\nDDL di MySQL/SQLite\nStar Schema",                 PURP),
        ("📦", "LOAD DIMS",    "5 Tabel Dimensi\ndim_customer, _contract\n_payment, _services, _tenure", AMBER),
        ("⭐", "LOAD FACT",    "1 Tabel Fakta\nfact_churn\n7.043 baris dimuat",                           RED),
        ("✅", "VALIDATE",     "Cek COUNT, SUM\nChurn Rate, Join Integrity\nKPI Validation",              MINT_DARK),
    ]

    cols = st.columns([4, 1, 4, 1, 4, 1, 4, 1, 4, 1, 4])
    for i, (icon, title, desc, color) in enumerate(steps):
        with cols[2 * i]:
            desc_html = desc.replace("\n", "<br>")
            card_html = (
                f'<div style="background:{BG_CARD};border:2px solid {color}35;'
                f'border-top:4px solid {color};border-radius:14px;padding:16px 12px;'
                f'text-align:center;height:155px;'
                f'display:flex;flex-direction:column;align-items:center;justify-content:center;">'
                f'<div style="font-size:26px;margin-bottom:6px;">{icon}</div>'
                f'<div style="font-size:12px;font-weight:800;color:{color};'
                f'margin-bottom:6px;letter-spacing:0.3px;">{title}</div>'
                f'<div style="font-size:11px;color:{TEXT_LIGHT};line-height:1.5;">{desc_html}</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
        
        if i < len(steps) - 1:
            with cols[2 * i + 1]:
                arrow_html = (
                    f'<div style="display:flex;align-items:center;justify-content:center;height:155px;'
                    f'font-size:20px;color:{TEXT_LIGHT};font-weight:bold;">→</div>'
                )
                st.markdown(arrow_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 – EKSEKUSI ETL
    # ══════════════════════════════════════════════════════════════════════════
    section_title("🚀 Eksekusi ETL Pipeline")

    ex1, ex2 = st.columns([1, 1.5])

    with ex1:
        st.markdown(f"""
        <div class="card">
            <div class="card-header">
                <div class="card-icon">ℹ️</div>
                <h3>Tentang Pipeline Ini</h3>
            </div>
            <ul style="font-size:13px;color:{TEXT_MID};line-height:1.9;
                padding-left:18px;margin:0;">
                <li>Membaca dataset CSV mentah (IBM Watson Telco)</li>
                <li>Mengimputasi 11 nilai TotalCharges yang kosong</li>
                <li>Mengkonversi SeniorCitizen ke label (0→No / 1→Yes)</li>
                <li>Mengkonversi Churn string ke flag integer (0/1)</li>
                <li>Menambah kolom ContractRisk dan PaymentCategory</li>
                <li>Membuat TenureBucket dan ServiceCount</li>
                <li>Memuat 5 dimensi + 1 fact table ke DWH</li>
                <li>Validasi count, churn rate, dan FK integrity</li>
            </ul>
            <div style="margin-top:16px;padding:12px;background:{MINT_BG};
                 border-radius:10px;font-size:12px;color:{MINT_DARK};font-weight:600;">
                ⚠️ Pipeline akan menghapus data lama dan memuat ulang dari awal.
            </div>
        </div>""", unsafe_allow_html=True)

    with ex2:
        st.markdown(f"""
        <div class="card">
            <div class="card-header">
                <div class="card-icon">🚀</div>
                <h3>Jalankan Pipeline</h3>
            </div>""", unsafe_allow_html=True)

        if not is_ready:
            if st.button("▶  Jalankan ETL Pipeline Sekarang", width="stretch"):
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
                <div style="border:2px dashed {BORDER};border-radius:12px;
                     padding:30px 20px;text-align:center;color:{TEXT_LIGHT};">
                    <div style="font-size:32px;margin-bottom:8px;">▶️</div>
                    <div style="font-size:13px;">Log eksekusi akan muncul di sini</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Data Warehouse sudah terisi. ETL tidak diperlukan untuk melihat Dashboard.")
            if os.getenv("ETL_ALLOW_FORCE", "0") == "1":
                st.markdown(
                    "<small style='color:#6C7A72'>Force-run enabled by environment variable.</small>",
                    unsafe_allow_html=True)
                if st.button("▶  Jalankan ETL Pipeline (FORCE)", width="stretch"):
                    log_area = st.empty()
                    logs = []

                    def append_log_f(msg):
                        logs.append(msg)
                        log_area.code("\n".join(logs), language="bash")

                    with st.spinner("Menjalankan ETL (FORCE)..."):
                        success, message = run_etl(log_callback=append_log_f)

                    if success:
                        st.success("✅ ETL Pipeline (FORCE) berhasil!")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ ETL Gagal: {message}")
            else:
                st.markdown(
                    f"<div style='padding:12px 0;color:{TEXT_MID};font-size:13px;'>"
                    "Untuk refresh data, jalankan ETL dari CLI atau set "
                    "<code>ETL_ALLOW_FORCE=1</code>.</div>",
                    unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 – DATA QUALITY (hanya tampil jika DWH terisi)
    # ══════════════════════════════════════════════════════════════════════════
    if is_ready:
        section_title("🔬 Laporan Kualitas Data")

        dq = _get_dq_metrics()

        if not dq.get("ok"):
            st.error(f"Tidak dapat memuat metrik kualitas data: {dq.get('error')}")
        else:
            # ── 4A: DQ SCORE KPI CARDS ────────────────────────────────────────
            q1, q2, q3, q4 = st.columns(4)

            overall_color = MINT if dq["overall"] >= 99 else AMBER if dq["overall"] >= 95 else RED
            comp_color    = MINT if dq["completeness"] >= 99 else AMBER if dq["completeness"] >= 95 else RED
            uniq_color    = MINT if dq["uniqueness"] >= 99.9 else AMBER
            valid_color   = MINT if dq["validity"] >= 99.9 else AMBER
            ref_color     = MINT if dq["ref_integrity"] >= 99.9 else AMBER if dq["ref_integrity"] >= 95 else RED

            _dq_kpi_card(q1, "🏆", "Overall DQ Score",
                         f"{dq['overall']:.1f}%",
                         "Rata-rata 4 dimensi kualitas", overall_color)
            _dq_kpi_card(q2, "📋", "Completeness",
                         f"{dq['completeness']:.2f}%",
                         f"NULL: TC={dq['null_tc']} · MC={dq['null_mc']} · CF={dq['null_cf']}",
                         comp_color)
            _dq_kpi_card(q3, "🔑", "Uniqueness",
                         f"{dq['uniqueness']:.2f}%",
                         f"{dq['distinct_cust']:,} customer_id unik dari {dq['total']:,}",
                         uniq_color)
            _dq_kpi_card(q4, "✔️", "Referential Integrity",
                         f"{dq['ref_integrity']:.2f}%",
                         f"Orphan FK: {dq['orphan_cust']+dq['orphan_contract']+dq['orphan_payment']+dq['orphan_service']+dq['orphan_tenure']}",
                         ref_color)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── 4B: RADAR CHART + SOURCE ISSUES ──────────────────────────────
            rb1, rb2 = st.columns([1, 1.2])

            with rb1:
                card_open()
                card_header("📡", "DQ Score Radar – 4 Dimensi")
                dims   = ["Completeness", "Uniqueness", "Validity", "Ref. Integrity"]
                scores = [dq["completeness"], dq["uniqueness"], dq["validity"], dq["ref_integrity"]]
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=scores + [scores[0]],
                    theta=dims + [dims[0]],
                    fill="toself",
                    name="Actual",
                    line=dict(color=MINT, width=2.5),
                    fillcolor=f"rgba(46,175,125,0.18)",
                ))
                fig.add_trace(go.Scatterpolar(
                    r=[100, 100, 100, 100, 100],
                    theta=dims + [dims[0]],
                    fill="toself",
                    name="Target (100%)",
                    line=dict(color=BORDER, width=1.5, dash="dot"),
                    fillcolor="rgba(0,0,0,0.04)",
                ))
                fig.update_layout(
                    polar=dict(
                        bgcolor=BG_CARD,
                        radialaxis=dict(visible=True, range=[97, 100.5],
                                        tickfont=dict(size=10, color=TEXT_LIGHT)),
                        angularaxis=dict(tickfont=dict(size=12, color=TEXT_DARK,
                                                       family="Plus Jakarta Sans")),
                    ),
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.15, x=0.1,
                                font=dict(size=11, color=TEXT_MID)),
                )
                theme_fig(fig, 310)
                st.plotly_chart(fig, width="stretch")
                card_close()

            with rb2:
                card_open()
                card_header("🔎", "Isu yang Ditemukan di Data Sumber")

                source_issues = [
                    ("TotalCharges kosong",    11,  "0.16%", RED,  "NUMERIC",
                     "Pelanggan baru (tenure=0) tidak memiliki riwayat tagihan"),
                    ("SeniorCitizen bertipe int", 7043, "100%", AMBER, "TYPE",
                     "Kolom 0/1 dikonversi ke label No/Yes saat transform"),
                    ("Churn bertipe string",    7043, "100%", AMBER, "TYPE",
                     "Nilai Yes/No dikonversi ke flag integer 0/1"),
                    ("Duplikat baris",            0,  "0%",   MINT,  "DUPLICATE",
                     "Tidak ditemukan baris duplikat pada dataset sumber"),
                    ("Duplikat customerID",        0,  "0%",   MINT,  "DUPLICATE",
                     "Setiap customerID bersifat unik (PK valid)"),
                    ("Outlier MonthlyCharges",     0,  "0%",   MINT,  "OUTLIER",
                     "Semua nilai dalam rentang wajar $18.25–$118.75 (IQR)"),
                ]

                for label, cnt, pct, color, tag, desc in source_issues:
                    tag_bg = f"{color}20"
                    icon   = "⚠️" if color in (RED, AMBER) else "✅"
                    st.markdown(f"""
                    <div style="display:flex;align-items:flex-start;gap:10px;
                         padding:9px 0;border-bottom:1px solid {BORDER};">
                        <div style="font-size:16px;margin-top:1px;">{icon}</div>
                        <div style="flex:1;">
                            <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">
                                <span style="font-size:13px;font-weight:600;
                                     color:{TEXT_DARK};">{label}</span>
                                <span style="font-size:10px;background:{tag_bg};
                                     color:{color};border-radius:4px;
                                     padding:1px 6px;font-weight:700;">{tag}</span>
                                <span style="font-size:12px;color:{color};
                                     font-weight:700;margin-left:auto;">{cnt:,} ({pct})</span>
                            </div>
                            <div style="font-size:11px;color:{TEXT_LIGHT};
                                 line-height:1.4;">{desc}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)

                card_close()

            st.markdown("<br>", unsafe_allow_html=True)

            # ── 4C: DWH TABLE SUMMARY ─────────────────────────────────────────
            section_title("📦 Rekonsiliasi Tabel Data Warehouse")
            tc1, tc2 = st.columns([1.3, 1])

            with tc1:
                card_open()
                card_header("📊", "Aktual vs Target – Row Count per Tabel")

                table_data = [
                    ("dim_customer",  dq["dc"],  7043, "👤"),
                    ("dim_contract",  dq["dco"],    6, "📋"),
                    ("dim_payment",   dq["dp"],     4, "💳"),
                    ("dim_services",  dq["ds"],   322, "🔧"),
                    ("dim_tenure",    dq["dt"],    73, "⏳"),
                    ("fact_churn",    dq["total"],7043, "⭐"),
                ]

                names    = [f'{e} {n}' for n, _, _, e in table_data]
                actuals  = [a for _, a, _, _ in table_data]
                targets  = [t for _, _, t, _ in table_data]
                colors   = [MINT if a == t else RED for _, a, t, _ in table_data]

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name="Target", x=names, y=targets,
                    marker_color=[f"{BORDER}"] * len(names),
                    opacity=0.35,
                ))
                fig.add_trace(go.Bar(
                    name="Aktual", x=names, y=actuals,
                    marker_color=colors,
                    text=[f"{a:,}" for a in actuals],
                    textposition="outside",
                    textfont=dict(size=11),
                ))
                fig.update_layout(
                    barmode="overlay",
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.18, x=0),
                    yaxis_title="Jumlah Baris",
                    xaxis_title="",
                )
                theme_fig(fig, 320)
                st.plotly_chart(fig, width="stretch")
                card_close()

            with tc2:
                card_open()
                card_header("🔗", "Integritas Referensial (FK Check)")

                fk_checks = [
                    ("fact_churn → dim_customer",  dq["orphan_cust"],     "customer_id"),
                    ("fact_churn → dim_contract",  dq["orphan_contract"],  "contract_id"),
                    ("fact_churn → dim_payment",   dq["orphan_payment"],   "payment_id"),
                    ("fact_churn → dim_services",  dq["orphan_service"],   "service_id"),
                    ("fact_churn → dim_tenure",    dq["orphan_tenure"],    "tenure_id"),
                ]

                for rel, orphans, fk_col in fk_checks:
                    passed = orphans == 0
                    color  = MINT if passed else RED
                    icon   = "✅" if passed else "❌"
                    status = f"0 orphan – OK" if passed else f"{orphans:,} orphan FK!"
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;align-items:center;
                         padding:10px 12px;margin-bottom:7px;border-radius:10px;
                         background:{color}0F;border:1px solid {color}30;
                         border-left:3px solid {color};">
                        <div>
                            <div style="font-size:13px;font-weight:600;color:{TEXT_DARK};">
                                {icon} {rel}</div>
                            <div style="font-size:11px;color:{TEXT_LIGHT};margin-top:2px;">
                                FK: <code>{fk_col}</code></div>
                        </div>
                        <div style="font-size:12px;font-weight:700;color:{color};
                             white-space:nowrap;">{status}</div>
                    </div>""", unsafe_allow_html=True)

                # Ringkasan
                total_orphans = (dq["orphan_cust"] + dq["orphan_contract"]
                                 + dq["orphan_payment"] + dq["orphan_service"]
                                 + dq["orphan_tenure"])
                ri_bg  = MINT_BG if total_orphans == 0 else RED_BG
                ri_clr = MINT_DARK if total_orphans == 0 else RED
                ri_msg = "✅ Semua FK valid – integritas relasional 100%" \
                         if total_orphans == 0 else \
                         f"⚠️ Terdapat {total_orphans} orphan record – cek ETL log"
                st.markdown(f"""
                <div style="margin-top:12px;padding:10px 14px;background:{ri_bg};
                     border-radius:10px;font-size:12px;font-weight:700;color:{ri_clr};">
                    {ri_msg}
                </div>""", unsafe_allow_html=True)
                card_close()

            st.markdown("<br>", unsafe_allow_html=True)

            # ── 4D: EXPANDED POST-ETL VALIDATION CHECKS ──────────────────────
            section_title("✅ Validasi Post-ETL")

            vl, vr = st.columns(2)

            checks_left = [
                # (label, passed, detail, category)
                ("Jumlah baris fact_churn = 7.043",
                 dq["total"] == 7043,
                 f"Aktual: {dq['total']:,} baris",
                 "COUNT"),
                ("Total churn antara 1.800–1.950",
                 1800 < dq["churn_sum"] < 1950,
                 f"Aktual: {dq['churn_sum']:,} pelanggan churn",
                 "COUNT"),
                ("Churn rate dalam rentang 24%–29%",
                 24 < dq["churn_rate"] < 29,
                 f"Aktual: {dq['churn_rate']:.2f}%",
                 "KPI"),
                ("Avg MonthlyCharges Churn > $70",
                 dq["avg_monthly_ch"] > 70,
                 f"Aktual: ${dq['avg_monthly_ch']:.2f}",
                 "KPI"),
                ("NULL TotalCharges di DWH = 0",
                 dq["null_tc"] == 0,
                 f"Aktual: {dq['null_tc']} NULL (ETL imputasi tenure=0)",
                 "NULL"),
                ("NULL MonthlyCharges di DWH = 0",
                 dq["null_mc"] == 0,
                 f"Aktual: {dq['null_mc']} NULL",
                 "NULL"),
            ]

            checks_right = [
                ("churnFlag hanya bernilai 0 atau 1",
                 dq["invalid_churn"] == 0,
                 f"Aktual: {dq['invalid_churn']} nilai tidak valid",
                 "VALIDITY"),
                ("MonthlyCharges selalu > 0",
                 dq["neg_monthly"] == 0,
                 f"Aktual: {dq['neg_monthly']} baris ≤ 0",
                 "VALIDITY"),
                ("Avg MonthlyCharges Retained < $70",
                 dq["avg_monthly_rt"] < 70,
                 f"Aktual: ${dq['avg_monthly_rt']:.2f}",
                 "KPI"),
                ("dim_customer match fact_churn (7.043)",
                 dq["dc"] == dq["total"],
                 f"dim_customer: {dq['dc']:,} | fact_churn: {dq['total']:,}",
                 "COUNT"),
                ("Jumlah dim_contract = 6 kombinasi unik",
                 dq["dco"] == 6,
                 f"Aktual: {dq['dco']} (3 kontrak × 2 paperless billing)",
                 "COUNT"),
                ("Jumlah dim_payment = 4 metode",
                 dq["dp"] == 4,
                 f"Aktual: {dq['dp']} payment methods",
                 "COUNT"),
            ]

            with vl:
                for lbl, passed, actual, cat in checks_left:
                    _check_row(lbl, passed, actual, cat)

            with vr:
                for lbl, passed, actual, cat in checks_right:
                    _check_row(lbl, passed, actual, cat)

            # Summary badge
            total_checks = len(checks_left) + len(checks_right)
            passed_count = sum(p for _, p, _, _ in checks_left) + \
                           sum(p for _, p, _, _ in checks_right)
            failed_count = total_checks - passed_count
            badge_color  = MINT if failed_count == 0 else RED
            badge_bg     = MINT_BG if failed_count == 0 else RED_BG
            badge_msg    = (f"✅ Semua {total_checks} validasi berhasil — "
                            f"Data Warehouse siap digunakan.") if failed_count == 0 else \
                           (f"⚠️ {passed_count}/{total_checks} validasi berhasil — "
                            f"{failed_count} gagal, cek data atau jalankan ulang ETL.")
            st.markdown(f"""
            <div style="margin-top:6px;padding:14px 18px;background:{badge_bg};
                 border:1px solid {badge_color}40;border-radius:12px;
                 font-size:14px;font-weight:700;color:{badge_color};text-align:center;">
                {badge_msg}
            </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── 4E: ETL TRANSFORMATION SUMMARY ──────────────────────────────
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,{MINT}10,{BLUE}08);
                 border:1px solid {MINT}35;border-radius:16px;
                 padding:20px 24px;margin-bottom:8px;">
                <h4 style="color:{MINT_DARK};margin:0 0 14px;font-size:15px;">
                    🔧 Ringkasan Transformasi ETL
                </h4>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                    <div style="background:white;border-radius:10px;
                         padding:14px;border:1px solid {BORDER};">
                        <div style="font-size:11px;font-weight:700;color:{TEXT_LIGHT};
                             text-transform:uppercase;margin-bottom:6px;">
                            🧹 Cleaning
                        </div>
                        <div style="font-size:13px;color:{TEXT_DARK};line-height:1.7;">
                            • <b>11 TotalCharges</b> blank → diimputasi (tenure=0 → 0.0)<br>
                            • <b>SeniorCitizen</b> int(0/1) → string(No/Yes)<br>
                            • <b>Churn</b> Yes/No → churnFlag int(1/0)<br>
                            • <b>TotalCharges</b> string → float64
                        </div>
                    </div>
                    <div style="background:white;border-radius:10px;
                         padding:14px;border:1px solid {BORDER};">
                        <div style="font-size:11px;font-weight:700;color:{TEXT_LIGHT};
                             text-transform:uppercase;margin-bottom:6px;">
                            ⚙️ Feature Engineering
                        </div>
                        <div style="font-size:13px;color:{TEXT_DARK};line-height:1.7;">
                            • <b>contractRisk</b>: M2M=High, 1Y=Med, 2Y=Low<br>
                            • <b>paymentCategory</b>: Auto / Manual<br>
                            • <b>tenureBucket</b>: 4 kelompok (0–12, 13–24, 25–48, 49+)<br>
                            • <b>serviceCount</b>: total layanan aktif per pelanggan
                        </div>
                    </div>
                    <div style="background:white;border-radius:10px;
                         padding:14px;border:1px solid {BORDER};">
                        <div style="font-size:11px;font-weight:700;color:{TEXT_LIGHT};
                             text-transform:uppercase;margin-bottom:6px;">
                            📐 Normalisasi
                        </div>
                        <div style="font-size:13px;color:{TEXT_DARK};line-height:1.7;">
                            • 1 flat CSV → <b>6 tabel terstruktur</b><br>
                            • Deduplikasi untuk <b>5 tabel dimensi</b><br>
                            • Surrogate PK auto-increment per tabel<br>
                            • FK constraint di fact_churn → semua dim
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 – STAR SCHEMA (dipindah ke bawah DQ)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("📐 Star Schema – Data Warehouse")

    schema_cols = st.columns(5)
    dims = [
        ("dim_customer", "👤", MINT,
         ["customer_id (PK)", "customer", "gender", "seniorCitizen", "partner", "dependents"]),
        ("dim_contract", "📋", BLUE,
         ["contract_id (PK)", "contract", "contractRiskLevel", "paperlessBilling"]),
        ("dim_payment",  "💳", AMBER,
         ["payment_id (PK)", "paymentMethod", "paymentCategory"]),
        ("dim_services", "🔧", PURP,
         ["service_id (PK)", "phoneService", "multipleLines", "internetService", "…9 kolom"]),
        ("dim_tenure",   "⏳", RED,
         ["tenure_id (PK)", "tenure", "tenureBucket", "tenureCategory"]),
    ]

    for i, (name, icon, color, cols_) in enumerate(dims):
        with schema_cols[i]:
            rows_html = "".join(
                f'<div style="padding:2px 0;font-size:11px;color:{TEXT_MID};">{c}</div>'
                for c in cols_
            )
            st.markdown(f"""
            <div style="background:{BG_CARD};border:1.5px solid {color}45;
                 border-top:3px solid {color};border-radius:12px;
                 padding:14px 12px;text-align:center;">
                <div style="font-size:20px;">{icon}</div>
                <div style="font-size:12px;font-weight:800;color:{color};
                     margin:6px 0 10px;">{name}</div>
                {rows_html}
                <div style="margin-top:10px;padding-top:8px;border-top:1px dashed {BORDER};
                     font-size:11px;color:{color};font-weight:600;">FK → fact_churn</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Fact table
    st.markdown(f"""
    <div style="text-align:center;margin:4px 0 8px;font-size:24px;color:{TEXT_LIGHT};">↓</div>
    <div style="background:linear-gradient(135deg,{MINT}15,{RED}10);
         border:2px solid {MINT}50;border-radius:16px;
         padding:20px 28px;max-width:680px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:14px;">
            <span style="font-size:18px;">⭐</span>
            <span style="font-size:17px;font-weight:800;color:{TEXT_DARK};
                  margin-left:8px;">fact_churn</span>
            <span style="font-size:12px;color:{TEXT_LIGHT};margin-left:8px;">
                (7.043 baris)
            </span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;font-size:13px;">
            <div>
                <b style="color:{MINT_DARK};">Foreign Keys:</b><br>
                <span style="color:{TEXT_MID};">
                    customer_id, contract_id,<br>payment_id, service_id, tenure_id
                </span>
            </div>
            <div>
                <b style="color:{MINT_DARK};">Measures:</b><br>
                <span style="color:{TEXT_MID};">
                    churnFlag (0/1),<br>monthlyCharges, totalCharges
                </span>
            </div>
            <div>
                <b style="color:{MINT_DARK};">Key KPIs:</b><br>
                <span style="color:{TEXT_MID};">
                    ChurnRate, AvgCharges,<br>RevenueLoss, RetentionRate
                </span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)