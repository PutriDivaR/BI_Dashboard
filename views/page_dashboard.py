"""page_dashboard.py – Halaman utama Dashboard BI."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils_bi import (
    MINT, MINT_SOFT, MINT_DARK, RED, AMBER, BLUE, PURP, TEXT_DARK, TEXT_LIGHT,
    BG_CARD, BORDER, CHURN_PALETTE,
    theme_fig, page_header, section_title, card_open, card_close, card_header,
    empty_state, churn_rate_bar, load_bi_data, check_db_ready,
)


def render():
    page_header("📊", "Customer Churn Dashboard",
                "Analisis performa retensi pelanggan berbasis data warehouse")

    if not check_db_ready():
        empty_state()
        return

    df = load_bi_data()

    # ─────────────────────────────────────────────────
    # FILTER BAR
    # ─────────────────────────────────────────────────
    with st.expander("🔍  Filter & Segmentasi", expanded=False):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            opts = ["Semua"] + sorted(df["contract"].dropna().unique().tolist())
            sel_contract = st.selectbox("Tipe Kontrak", opts, key="f_contract")
        with f2:
            opts = ["Semua"] + sorted(df["internetService"].dropna().unique().tolist())
            sel_internet = st.selectbox("Layanan Internet", opts, key="f_internet")
        with f3:
            opts = ["Semua"] + sorted(df["paymentMethod"].dropna().unique().tolist())
            sel_pay = st.selectbox("Metode Pembayaran", opts, key="f_pay")
        with f4:
            opts = ["Semua", "No", "Yes"]
            sel_senior = st.selectbox("Senior Citizen", opts, key="f_senior")

    fdf = df.copy()
    if sel_contract != "Semua":  fdf = fdf[fdf["contract"]       == sel_contract]
    if sel_internet != "Semua":  fdf = fdf[fdf["internetService"] == sel_internet]
    if sel_pay      != "Semua":  fdf = fdf[fdf["paymentMethod"]   == sel_pay]
    if sel_senior   != "Semua":  fdf = fdf[fdf["seniorCitizen"]   == sel_senior]

    # ─────────────────────────────────────────────────
    # KPI ROW
    # ─────────────────────────────────────────────────
    total     = len(fdf)
    churned   = int(fdf["churnFlag"].sum())
    retained  = total - churned
    churn_rt  = churned / total * 100 if total else 0
    ret_rt    = 100 - churn_rt
    avg_m     = fdf["monthlyCharges"].mean() if total else 0
    avg_churn = fdf.loc[fdf["churnFlag"]==1,"monthlyCharges"].mean() if churned else 0

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("👥 Total Customer",  f"{total:,}")
    k2.metric("❌ Total Churn",      f"{churned:,}")
    k3.metric("✅ Retained",         f"{retained:,}")
    k4.metric("📉 Churn Rate",       f"{churn_rt:.2f}%",
              delta=f"-{100-churn_rt:.1f}% retained", delta_color="normal")
    k5.metric("🔒 Retention Rate",   f"{ret_rt:.2f}%")
    k6.metric("💰 Avg Monthly",      f"${avg_m:.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ROW 1 — Donut + Risk Summary
    # ─────────────────────────────────────────────────
    section_title("📌 Distribusi & Ringkasan Risiko")
    r1a, r1b = st.columns([1.1, 0.9])

    with r1a:
        card_open()
        card_header("🍩", "Distribusi Customer (Churn vs Retained)")
        pie = pd.DataFrame({
            "Status": ["Retained", "Churned"],
            "Jumlah": [retained, churned]
        })
        fig = px.pie(pie, names="Status", values="Jumlah", hole=0.62,
                     color="Status",
                     color_discrete_map={"Retained": MINT, "Churned": RED})
        fig.update_traces(
            textinfo="percent+label",
            textfont_size=13,
            pull=[0, 0.06],
            marker=dict(line=dict(color="white", width=2.5)),
        )
        fig.add_annotation(
            text=f"<b>{total:,}</b><br><span style='font-size:11px'>Total</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=18, color=TEXT_DARK, family="Plus Jakarta Sans"),
        )
        theme_fig(fig, 300)
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1, x=0.2))
        st.plotly_chart(fig, use_container_width=True)
        card_close()

    with r1b:
        card_open()
        card_header("⚠️", "Churn Risk Summary (Top Faktor)")

        def cr(col, val, df_=df):
            s = df_[df_[col] == val]
            return (s["churnFlag"].sum() / len(s) * 100) if len(s) else 0

        risks = [
            ("Tenure 0–12 Bulan",       cr("tenureBucket",   "0-12 Bulan")),
            ("Month-to-Month",           cr("contract",       "Month-to-month")),
            ("Electronic Check",         cr("paymentMethod",  "Electronic check")),
            ("Fiber Optic Internet",     cr("internetService","Fiber optic")),
            ("Senior Citizen",           cr("seniorCitizen",  "Yes")),
            ("Paperless Billing",        cr("paperlessBilling","Yes")),
        ]
        for label, rate in risks:
            churn_rate_bar(label, rate)
        card_close()

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ROW 2 — Contract, Internet, Payment
    # ─────────────────────────────────────────────────
    section_title("📋 Analisis Churn per Segmen Utama")
    c1, c2, c3 = st.columns(3)

    # Contract
    with c1:
        card_open()
        card_header("📃", "Churn Rate by Contract")
        d = fdf.groupby("contract")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d = d.sort_values("pct", ascending=False)
        colors = [RED if v >= 40 else AMBER if v >= 20 else MINT for v in d["pct"]]
        fig = px.bar(d, x="contract", y="pct",
                     text=d["pct"].apply(lambda x: f"{x:.1f}%"),
                     color="contract",
                     color_discrete_sequence=colors)
        fig.update_traces(textposition="outside", marker_line_width=0,
                          textfont_size=12)
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Churn Rate (%)")
        theme_fig(fig, 300)
        st.plotly_chart(fig, use_container_width=True)
        card_close()

    # Internet
    with c2:
        card_open()
        card_header("🌐", "Churn Rate by Internet Service")
        d = fdf.groupby("internetService")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d = d.sort_values("pct", ascending=False)
        colors = [RED if v >= 40 else AMBER if v >= 20 else MINT for v in d["pct"]]
        fig = px.bar(d, x="internetService", y="pct",
                     text=d["pct"].apply(lambda x: f"{x:.1f}%"),
                     color="internetService",
                     color_discrete_sequence=colors)
        fig.update_traces(textposition="outside", marker_line_width=0, textfont_size=12)
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Churn Rate (%)")
        theme_fig(fig, 300)
        st.plotly_chart(fig, use_container_width=True)
        card_close()

    # Payment
    with c3:
        card_open()
        card_header("💳", "Churn Rate by Payment Method")
        d = fdf.groupby("paymentMethod")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d = d.sort_values("pct", ascending=False)
        colors = [RED if v >= 40 else AMBER if v >= 20 else MINT for v in d["pct"]]
        fig = px.bar(d, y="paymentMethod", x="pct", orientation="h",
                     text=d["pct"].apply(lambda x: f"{x:.1f}%"),
                     color="paymentMethod",
                     color_discrete_sequence=colors)
        fig.update_traces(textposition="outside", marker_line_width=0, textfont_size=12)
        fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="Churn Rate (%)")
        theme_fig(fig, 300)
        st.plotly_chart(fig, use_container_width=True)
        card_close()

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ROW 3 — Tenure, Senior, Monthly Charges
    # ─────────────────────────────────────────────────
    section_title("📈 Analisis Lanjutan")
    c4, c5, c6 = st.columns(3)

    # Tenure line-bar
    with c4:
        card_open()
        card_header("⏳", "Churn Rate by Tenure")
        order = {"0-12 Bulan": 0,"13-24 Bulan": 1,"25-48 Bulan": 2,"49+ Bulan": 3}
        d = fdf.groupby("tenureBucket")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d["ord"] = d["tenureBucket"].map(order)
        d = d.sort_values("ord")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=d["tenureBucket"], y=d["pct"],
            marker_color=[RED,AMBER,MINT,MINT_SOFT],
            text=[f"{v:.1f}%" for v in d["pct"]],
            textposition="outside",
            name="Churn Rate",
        ))
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Churn Rate (%)")
        theme_fig(fig, 300)
        st.plotly_chart(fig, use_container_width=True)
        card_close()

    # Senior Citizen
    with c5:
        card_open()
        card_header("👴", "Churn by Senior Citizen Status")
        d = fdf.groupby("seniorCitizen")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        labels = {"No": "Non-Senior", "Yes": "Senior"}
        d["label"] = d["seniorCitizen"].map(labels).fillna(d["seniorCitizen"])
        colors = [RED if v >= 35 else MINT for v in d["pct"]]
        fig = px.bar(d, x="label", y="pct",
                     text=d["pct"].apply(lambda x: f"{x:.1f}%"),
                     color="label", color_discrete_sequence=colors)
        fig.update_traces(textposition="outside", marker_line_width=0, textfont_size=13)
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Churn Rate (%)")
        theme_fig(fig, 300)
        st.plotly_chart(fig, use_container_width=True)
        card_close()

    # Monthly Charges Distribution
    with c6:
        card_open()
        card_header("💵", "Monthly Charges: Churn vs Retained")
        fig = go.Figure()
        fig.add_trace(go.Box(
            y=fdf[fdf["churnFlag"]==0]["monthlyCharges"],
            name="Retained",
            marker_color=MINT,
            line_color=MINT_DARK,
            fillcolor="rgba(46, 175, 125, 0.13)",
            boxmean=True,
        ))
        fig.add_trace(go.Box(
            y=fdf[fdf["churnFlag"]==1]["monthlyCharges"],
            name="Churned",
            marker_color=RED,
            line_color="#C03030",
            fillcolor="rgba(231, 111, 81, 0.13)",
            boxmean=True,
        ))
        fig.update_layout(yaxis_title="Monthly Charges (USD)")
        theme_fig(fig, 300)
        st.plotly_chart(fig, use_container_width=True)
        card_close()

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ROW 4 — Gender, Services Heatmap, Partner
    # ─────────────────────────────────────────────────
    section_title("🔬 Analisis Demografis & Layanan")
    c7, c8 = st.columns([1, 1.4])

    with c7:
        card_open()
        card_header("👫", "Churn by Demografis")

        for col, label_map in [
            ("gender",     {"Male":"Pria","Female":"Wanita"}),
            ("partner",    {"No":"Tanpa Pasangan","Yes":"Punya Pasangan"}),
            ("dependents", {"No":"Tanpa Tanggungan","Yes":"Punya Tanggungan"}),
        ]:
            d = fdf.groupby(col)["churnFlag"].mean().reset_index()
            d["pct"] = d["churnFlag"] * 100
            for _, row in d.iterrows():
                lbl = label_map.get(row[col], row[col])
                churn_rate_bar(lbl, row["pct"], max_rate=50)
            st.markdown('<hr style="border-color:#EBF4EF; margin:10px 0">', unsafe_allow_html=True)
        card_close()

    with c8:
        card_open()
        card_header("🔧", "Layanan Tambahan vs Churn Rate")
        svc_cols = ["onlineSecurity","onlineBackup","deviceProtection",
                    "techSupport","streamingTV","streamingMovies","multipleLines"]
        svc_labels = {
            "onlineSecurity":   "Online Security",
            "onlineBackup":     "Online Backup",
            "deviceProtection": "Device Protection",
            "techSupport":      "Tech Support",
            "streamingTV":      "Streaming TV",
            "streamingMovies":  "Streaming Movies",
            "multipleLines":    "Multiple Lines",
        }
        rows_ = []
        for s in svc_cols:
            if s not in fdf.columns: continue
            for v in ["Yes","No"]:
                sub = fdf[fdf[s]==v]
                if len(sub) == 0: continue
                rows_.append({
                    "Layanan": svc_labels.get(s,s),
                    "Status":  v,
                    "Churn Rate (%)": sub["churnFlag"].mean()*100,
                })
        df_heat = pd.DataFrame(rows_)
        if not df_heat.empty:
            pivot = df_heat.pivot(index="Layanan", columns="Status", values="Churn Rate (%)")
            fig = px.imshow(
                pivot,
                color_continuous_scale=["#C8F0E0","#FFD59A","#E05252"],
                text_auto=".1f",
                aspect="auto",
                labels=dict(color="Churn %"),
            )
            fig.update_traces(textfont_size=12)
            theme_fig(fig, 320)
            fig.update_layout(coloraxis_colorbar=dict(title="Churn %", thickness=12))
            st.plotly_chart(fig, use_container_width=True)
        card_close()

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # FOOTER INSIGHT BOX
    # ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{MINT}15,{BLUE}10);
         border:1px solid {MINT}40; border-radius:16px; padding:22px 26px; margin-top:8px;">
        <h4 style="color:{MINT_DARK}; margin:0 0 12px; font-size:15px;">
            💡 Key Insights dari Dashboard
        </h4>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px;">
            <div style="background:white; border-radius:10px; padding:14px; border:1px solid {BORDER};">
                <div style="font-size:11px; font-weight:700; color:{TEXT_LIGHT}; text-transform:uppercase; margin-bottom:6px;">Risiko Tertinggi</div>
                <div style="font-size:13px; color:{TEXT_DARK}; font-weight:500;">Pelanggan <b>Month-to-month</b> + <b>Electronic Check</b> + <b>Fiber Optic</b> memiliki probabilitas churn &gt;40%</div>
            </div>
            <div style="background:white; border-radius:10px; padding:14px; border:1px solid {BORDER};">
                <div style="font-size:11px; font-weight:700; color:{TEXT_LIGHT}; text-transform:uppercase; margin-bottom:6px;">Periode Kritis</div>
                <div style="font-size:13px; color:{TEXT_DARK}; font-weight:500;">Hampir <b>1 dari 2</b> pelanggan baru (0–12 bulan) meninggalkan layanan — masa onboarding paling krusial</div>
            </div>
            <div style="background:white; border-radius:10px; padding:14px; border:1px solid {BORDER};">
                <div style="font-size:11px; font-weight:700; color:{TEXT_LIGHT}; text-transform:uppercase; margin-bottom:6px;">Retensi Terbaik</div>
                <div style="font-size:13px; color:{TEXT_DARK}; font-weight:500;">Kontrak <b>Two Year</b> hanya 2,8% churn — upgrade kontrak adalah strategi retensi paling efektif</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)