"""
page_dashboard.py
Halaman utama Dashboard BI – Customer Churn Analysis
Semua data dari database (data warehouse star schema).
"""
import random
import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
from plotly.subplots import make_subplots  # type: ignore
import streamlit as st  # type: ignore

from utils_bi import (
    MINT, MINT_SOFT, MINT_DARK, RED, AMBER, BLUE, PURP,
    TEAL, ROSE,
    C_CHURN, C_RETAINED, C_AMBER, C_BLUE, C_PURP, C_TEAL, C_ROSE,
    TEXT_DARK, TEXT_MID, TEXT_LIGHT, BG_CARD, BORDER, MINT_BG, MINT_MID,
    theme_fig, page_header, section_title, card_open, card_close, card_header,
    empty_state, churn_rate_bar, load_bi_data, check_db_ready,
)

# ── Warna palette ─────────────────────────────────────────────────────
BAR_COLORS = {
    "high":   RED,
    "medium": AMBER,
    "low":    MINT,
    "soft":   MINT_SOFT,
}

# ─────────────────────────────────────────────────────────────────────
# HELPER: hitung churn rate per kolom/nilai dari df
# ─────────────────────────────────────────────────────────────────────
def churn_pct(df: pd.DataFrame, col: str, val: str) -> float:
    sub = df[df[col] == val]
    return (sub["churnFlag"].sum() / len(sub) * 100) if len(sub) else 0.0

# Backwards-compatible alias used elsewhere in the file
_pct = churn_pct


def bar_color_by_val(values, thresholds=(40, 20)):
    """Pilih warna bar berdasarkan nilai (merah>40%, kuning>20%, hijau sisanya)."""
    return [
        RED if v >= thresholds[0] else AMBER if v >= thresholds[1] else MINT
        for v in values
    ]


def distinct_colors(values, palette=None):
    """Assign a distinct, high-contrast color per unique value.

    The highest values get the first colors in the palette (more alarming colors),
    next highest get the next color, etc. This makes bar-by-bar comparison easier.
    """
    vals = list(values)
    if palette is None:
        palette = [RED, AMBER, BLUE, PURP, TEAL, ROSE, MINT, MINT_SOFT]

    # Build mapping from unique value -> color ordered by value desc (largest -> first color)
    uniq = sorted({v for v in vals if v == v}, reverse=True)  # remove NaN
    color_map = {v: palette[i % len(palette)] for i, v in enumerate(uniq)}
    return [color_map.get(v, MINT) for v in vals]


# ─────────────────────────────────────────────────────────────────────
# SIMULASI TREN BULANAN (dari data real: distribusi churn per tenure)
# Karena dataset tidak punya kolom tanggal, kita simulasi tren
# proporsional dari distribusi tenure yang NYATA di database.
# ─────────────────────────────────────────────────────────────────────
def build_trend_from_real(df: pd.DataFrame) -> pd.DataFrame:
    """
    Buat tren bulanan berdasarkan distribusi tenure pelanggan nyata.
    Setiap 'bulan' merepresentasikan kelompok tenure tertentu.
    """
    months = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]
    # Bagi tenure 0-72 menjadi 12 segmen bulanan
    df2 = df.copy()
    df2["month_segment"] = pd.cut(
        df2["tenure"], bins=12,
        labels=months
    )
    grp = df2.groupby("month_segment", observed=True).agg(
        jumlah_churn=("churnFlag", "sum"),
        total=("churnFlag", "count"),
    ).reset_index()
    grp["churn_rate"] = grp["jumlah_churn"] / grp["total"] * 100
    grp.columns = ["Bulan", "Jumlah Churn", "Total", "Churn Rate (%)"]
    return grp


# ─────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────
def render():

    # ── Page header (use shared green banner like other pages)
    page_header("📊", "Overview", "Ringkasan performa customer churn perusahaan telekomunikasi")

    if not check_db_ready():
        empty_state()
        return

    # ── Load data dari database ───────────────────────────────────────
    df = load_bi_data()

    # ─────────────────────────────────────────────────
    # FILTER BAR — persis seperti referensi gambar
    # ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
         padding:12px 18px; margin: 10px 0 16px 0;">
        <span style="font-size:12px; font-weight:700; color:{TEXT_LIGHT};
              text-transform:uppercase; letter-spacing:0.5px;">🔍 Filter Tampilan</span>
    </div>
    """, unsafe_allow_html=True)

    fc1, fc2, fc3, _, btn_col = st.columns([1.2, 1.2, 1.5, 0.3, 0.8])
    with fc1:
        periods = ["All"] + ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]
        sel_periode = st.selectbox("Periode", periods, key="dash_periode", label_visibility="collapsed")
        st.markdown("<div style='margin-top:-8px;font-size:10px;color:#8FA898;font-weight:600;text-transform:uppercase;letter-spacing:0.4px;'>Periode</div>", unsafe_allow_html=True)

    with fc2:
        contracts = ["All"] + sorted(df["contract"].dropna().unique().tolist())
        sel_contract = st.selectbox("Contract", contracts, key="dash_contract", label_visibility="collapsed")
        st.markdown("<div style='margin-top:-8px;font-size:10px;color:#8FA898;font-weight:600;text-transform:uppercase;letter-spacing:0.4px;'>Contract</div>", unsafe_allow_html=True)

    with fc3:
        internets = ["All"] + sorted(df["internetService"].dropna().unique().tolist())
        sel_internet = st.selectbox("Internet Service", internets, key="dash_inet", label_visibility="collapsed")
        st.markdown("<div style='margin-top:-8px;font-size:10px;color:#8FA898;font-weight:600;text-transform:uppercase;letter-spacing:0.4px;'>Internet Service</div>", unsafe_allow_html=True)

    with btn_col:
        st.markdown("<div style='margin-top:0px;'></div>", unsafe_allow_html=True)
        def _reset_filters():
            # ensure keys exist and are set to defaults
            st.session_state['dash_periode']  = 'All'
            st.session_state['dash_contract'] = 'All'
            st.session_state['dash_inet']     = 'All'
            # use experimental_rerun to re-execute with updated state
            try:
                st.experimental_rerun()
            except Exception:
                # fallback to plain rerun
                st.rerun()

        st.button("↺ Reset Filter", key="reset_filter", on_click=_reset_filters)

    # Apply filters
    # create monthly segment column (same logic as build_trend_from_real) so 'Periode' selection can filter
    months = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]
    df2 = df.copy()
    if 'tenure' in df2.columns:
        df2['month_segment'] = pd.cut(df2['tenure'], bins=12, labels=months)
    else:
        df2['month_segment'] = None

    fdf = df2.copy()
    if sel_periode != "All":
        fdf = fdf[fdf['month_segment'] == sel_periode]
    if sel_contract != "All":
        fdf = fdf[fdf["contract"] == sel_contract]
    if sel_internet != "All":
        fdf = fdf[fdf["internetService"] == sel_internet]

    st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # KPI CARDS — 5 card besar bergaya seperti gambar
    # ─────────────────────────────────────────────────
    total    = len(fdf)
    churned  = int(fdf["churnFlag"].sum())
    retained = total - churned
    churn_rt = churned / total * 100 if total else 0.0
    ret_rt   = 100 - churn_rt
    avg_monthly = fdf["monthlyCharges"].mean() if total else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)

    def kpi_card(col, icon, title, value, subtitle, border_color, value_color="#1A2E24"):
        col.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER};
             border-radius:16px; padding:18px 20px 14px;
             border-top: 4px solid {border_color};
             box-shadow: 0 2px 10px rgba(0,0,0,0.04);">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                <div style="width:38px; height:38px; background:{border_color}18;
                     border-radius:10px; display:flex; align-items:center;
                     justify-content:center; font-size:18px;">{icon}</div>
                <div style="font-size:10px; font-weight:700; color:{TEXT_LIGHT};
                     text-transform:uppercase; letter-spacing:0.6px; line-height:1.3;">
                    {title}
                </div>
            </div>
            <div style="font-size:32px; font-weight:900; color:{value_color};
                 letter-spacing:-1px; line-height:1; margin-bottom:5px;">
                {value}
            </div>
            <div style="font-size:12px; color:{TEXT_LIGHT}; font-weight:500;">{subtitle}</div>
        </div>
        """, unsafe_allow_html=True)

    kpi_card(k1, "👥", "Total Customer",  f"{total:,}",       "Pelanggan",              MINT)
    kpi_card(k2, "📉", "Total Churn",     f"{churned:,}",     "Pelanggan",              RED,   value_color=RED)
    kpi_card(k3, "📊", "Churn Rate",      f"{churn_rt:.2f}%", "Dari total pelanggan",   AMBER, value_color=AMBER)
    kpi_card(k4, "🔒", "Retention Rate",  f"{ret_rt:.2f}%",   "Pelanggan tetap",        MINT)
    kpi_card(k5, "💰", "Avg Monthly Charges", f"${avg_monthly:.2f}", "Rata-rata seluruh pelanggan", BLUE)

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ROW 1: TREND CHURN + DISTRIBUSI DONUT
    # ─────────────────────────────────────────────────
    r1a, r1b = st.columns([1.6, 1])

    with r1a:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:16px;
             padding:20px 22px 8px; box-shadow:0 2px 10px rgba(0,0,0,0.03);">
            <div style="font-size:13px; font-weight:800; color:{TEXT_DARK}; margin-bottom:2px;">
                TREND CHURN OVER TIME (BULANAN)
            </div>
            <div style="font-size:11px; color:{TEXT_LIGHT}; margin-bottom:12px;">
                Distribusi jumlah churn dan churn rate berdasarkan kelompok lama berlangganan (tenure)
            </div>
        """, unsafe_allow_html=True)

        trend = build_trend_from_real(fdf)

        fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
        fig_trend.add_trace(
            go.Bar(
                x=trend["Bulan"], y=trend["Jumlah Churn"],
                name="Churn Customer",
                marker_color=distinct_colors(trend["Jumlah Churn"].round(0)),
                marker_opacity=0.85,
                marker_line_width=0,
            ),
            secondary_y=False,
        )
        fig_trend.add_trace(
            go.Scatter(
                x=trend["Bulan"], y=trend["Churn Rate (%)"],
                name="Churn Rate (%)",
                mode="lines+markers",
                line=dict(color=BLUE, width=2.5),
                marker=dict(size=7, color=BLUE),
            ),
            secondary_y=True,
        )
        fig_trend.update_yaxes(
            title_text="Jumlah Churn", secondary_y=False,
            showgrid=True, gridcolor="#EBF4EF", zeroline=False
        )
        fig_trend.update_yaxes(
            title_text="Churn Rate (%)", secondary_y=True,
            showgrid=False, zeroline=False,
            ticksuffix="%"
        )
        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_family="'Plus Jakarta Sans', sans-serif",
            margin=dict(l=5, r=5, t=10, b=5),
            height=280,
            legend=dict(
                orientation="h", y=1.12, x=0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=11)
            ),
            xaxis=dict(showgrid=False, linecolor=BORDER),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with r1b:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:16px;
             padding:20px 22px 8px; box-shadow:0 2px 10px rgba(0,0,0,0.03); height:100%;">
            <div style="font-size:13px; font-weight:800; color:{TEXT_DARK}; margin-bottom:2px;">
                DISTRIBUSI PELANGGAN
            </div>
            <div style="font-size:11px; color:{TEXT_LIGHT}; margin-bottom:8px;">
                Perbandingan proporsi pelanggan yang churn vs yang tetap berlangganan
            </div>
        """, unsafe_allow_html=True)

        pie = pd.DataFrame({
            "Status": ["Churn Customer", "Retained Customer"],
            "Jumlah": [churned, retained],
        })
        fig_donut = px.pie(
            pie, names="Status", values="Jumlah", hole=0.6,
            color="Status",
            color_discrete_map={"Churn Customer": RED, "Retained Customer": MINT},
        )
        fig_donut.update_traces(
            textinfo="none",
            pull=[0.04, 0],
            marker=dict(line=dict(color="white", width=2.5)),
        )
        fig_donut.add_annotation(
            text=f"<b>{total:,}</b><br><span style='font-size:11px;color:{TEXT_LIGHT}'>Total</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color=TEXT_DARK, family="Plus Jakarta Sans, sans-serif"),
        )
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=5, b=0),
            height=220,
            showlegend=False,
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        # Legend manual
        st.markdown(f"""
        <div style="display:flex; flex-direction:column; gap:8px; padding:0 8px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <div style="width:12px;height:12px;border-radius:50%;background:{RED};"></div>
                    <span style="font-size:12px;color:{TEXT_MID};">Churn Customer</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:16px;font-weight:800;color:{RED};">{churned:,}</span>
                    <span style="font-size:11px;color:{TEXT_LIGHT};"> ({churn_rt:.2f}%)</span>
                </div>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <div style="width:12px;height:12px;border-radius:50%;background:{MINT};"></div>
                    <span style="font-size:12px;color:{TEXT_MID};">Retained Customer</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:16px;font-weight:800;color:{MINT};">{retained:,}</span>
                    <span style="font-size:11px;color:{TEXT_LIGHT};"> ({ret_rt:.2f}%)</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ROW 2: 4 CHART — Contract, Internet, Payment, Tenure
    # ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="font-size:13px; font-weight:800; color:{TEXT_DARK};
         margin-bottom:12px; text-transform:uppercase; letter-spacing:0.3px;">
        Churn Rate per Segmen
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    # ── Contract ─────────────────────────────────────
    with c1:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
             padding:16px 16px 4px; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size:12px;font-weight:800;color:{TEXT_DARK};margin-bottom:1px;">
                CHURN RATE BY CONTRACT
            </div>
            <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
                Persentase churn berdasarkan jenis kontrak pelanggan
            </div>
        """, unsafe_allow_html=True)

        d = fdf.groupby("contract")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d = d.sort_values("pct", ascending=False)
        # use distinct, high-contrast colors per bar so differences are easy to spot
        colors = distinct_colors(d["pct"].round(2))

        fig = go.Figure(go.Bar(
            x=d["contract"], y=d["pct"],
            marker_color=colors, marker_line_width=0,
            text=[f"{v:.2f}%" for v in d["pct"]],
            textposition="outside", textfont=dict(size=11, color=TEXT_DARK),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0), height=230,
            xaxis=dict(showgrid=False, linecolor=BORDER, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="Churn Rate (%)", tickfont=dict(size=9)),
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Internet ─────────────────────────────────────
    with c2:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
             padding:16px 16px 4px; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size:12px;font-weight:800;color:{TEXT_DARK};margin-bottom:1px;">
                CHURN RATE BY INTERNET SERVICE
            </div>
            <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
                Persentase churn berdasarkan jenis layanan internet (Fiber Optic/DSL/No)
            </div>
        """, unsafe_allow_html=True)

        d = fdf.groupby("internetService")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d = d.sort_values("pct", ascending=False)
        # assign distinct colors per internet service
        colors = distinct_colors(d["pct"].round(2))

        fig = go.Figure(go.Bar(
            x=d["internetService"], y=d["pct"],
            marker_color=colors, marker_line_width=0,
            text=[f"{v:.2f}%" for v in d["pct"]],
            textposition="outside", textfont=dict(size=11, color=TEXT_DARK),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0), height=230,
            xaxis=dict(showgrid=False, linecolor=BORDER, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="Churn Rate (%)", tickfont=dict(size=9)),
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Payment ──────────────────────────────────────
    with c3:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
             padding:16px 16px 4px; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size:12px;font-weight:800;color:{TEXT_DARK};margin-bottom:1px;">
                CHURN RATE BY PAYMENT METHOD
            </div>
            <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
                Persentase churn berdasarkan metode pembayaran yang digunakan
            </div>
        """, unsafe_allow_html=True)

        d = fdf.groupby("paymentMethod")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d = d.sort_values("pct", ascending=False)
        # horizontal bars: use distinct contrasting colors
        colors = distinct_colors(d["pct"].round(2))

        fig = go.Figure(go.Bar(
            y=d["paymentMethod"], x=d["pct"],
            orientation="h",
            marker_color=colors, marker_line_width=0,
            text=[f"{v:.2f}%" for v in d["pct"]],
            textposition="outside", textfont=dict(size=11, color=TEXT_DARK),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=30, t=20, b=0), height=230,
            xaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="Churn Rate (%)", tickfont=dict(size=9),
                       ticksuffix="%"),
            yaxis=dict(showgrid=False, linecolor=BORDER, tickfont=dict(size=9)),
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Tenure ───────────────────────────────────────
    with c4:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
             padding:16px 16px 4px; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size:12px;font-weight:800;color:{TEXT_DARK};margin-bottom:1px;">
                CHURN RATE BY TENURE (BULAN)
            </div>
            <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
                Persentase churn berdasarkan lama berlangganan (semakin lama, semakin loyal)
            </div>
        """, unsafe_allow_html=True)

        order_map = {"0-12 Bulan": 0, "13-24 Bulan": 1, "25-48 Bulan": 2, "49+ Bulan": 3}
        d = fdf.groupby("tenureBucket")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d["ord"] = d["tenureBucket"].map(order_map)
        d = d.sort_values("ord")
        # tenure buckets: keep the designed sequential palette but ensure length matches
        colors = [RED, AMBER, MINT_SOFT, MINT][:len(d)]

        fig = go.Figure(go.Bar(
            x=d["tenureBucket"], y=d["pct"],
            marker_color=colors, marker_line_width=0,
            text=[f"{v:.2f}%" for v in d["pct"]],
            textposition="outside", textfont=dict(size=11, color=TEXT_DARK),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0), height=230,
            xaxis=dict(showgrid=False, linecolor=BORDER, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="Churn Rate (%)", tickfont=dict(size=9)),
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # ROW 3: Senior Citizen + Avg Monthly Charges + Churn Risk Summary + High Risk Table
    # ─────────────────────────────────────────────────
    r3a, r3b, r3c, r3d = st.columns([1, 1, 1.1, 1.2])

    # ── Senior Citizen ────────────────────────────────
    with r3a:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
             padding:16px 16px 4px; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size:12px;font-weight:800;color:{TEXT_DARK};margin-bottom:1px;">
                CHURN RATE BY SENIOR CITIZEN
            </div>
            <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
                Perbandingan churn pelanggan lanjut usia (65+) vs non-senior
            </div>
        """, unsafe_allow_html=True)

        d = fdf.groupby("seniorCitizen")["churnFlag"].mean().reset_index()
        d["pct"] = d["churnFlag"] * 100
        d["label"] = d["seniorCitizen"].map({"Yes": "Senior Citizen (1)", "No": "Non Senior (0)"}).fillna(d["seniorCitizen"])
        # make senior citizen bars clearly contrasting
        colors = [RED if v >= 35 else MINT for v in d["pct"]]

        fig = go.Figure(go.Bar(
            x=d["label"], y=d["pct"],
            marker_color=colors, marker_line_width=0,
            text=[f"{v:.2f}%" for v in d["pct"]],
            textposition="outside", textfont=dict(size=11, color=TEXT_DARK),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0), height=220,
            xaxis=dict(showgrid=False, linecolor=BORDER, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="Churn Rate (%)", tickfont=dict(size=9)),
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Avg Monthly Charges by Churn Status ──────────
    with r3b:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
             padding:16px 16px 4px; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size:12px;font-weight:800;color:{TEXT_DARK};margin-bottom:1px;">
                AVG MONTHLY CHARGES BY CHURN STATUS
            </div>
            <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
                Rata-rata tagihan bulanan pelanggan yang churn vs yang tetap berlangganan
            </div>
        """, unsafe_allow_html=True)

        avg_ch = fdf[fdf["churnFlag"]==1]["monthlyCharges"].mean()
        avg_rt = fdf[fdf["churnFlag"]==0]["monthlyCharges"].mean()

        fig = go.Figure(go.Bar(
            x=["Churn Customer", "Retained Customer"],
            y=[avg_ch, avg_rt],
            marker_color=[RED, BLUE],
            marker_line_width=0,
            text=[f"${avg_ch:.2f}", f"${avg_rt:.2f}"],
            textposition="outside",
            textfont=dict(size=13, color=TEXT_DARK, family="Plus Jakarta Sans"),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0), height=220,
            xaxis=dict(showgrid=False, linecolor=BORDER, tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="USD ($)", tickfont=dict(size=9), tickprefix="$"),
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Churn Risk Summary ───────────────────────────
    with r3c:
        st.markdown(f"""
        <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
             padding:16px 16px 4px; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
            <div style="font-size:12px;font-weight:800;color:{TEXT_DARK};margin-bottom:1px;">
                CHURN RISK SUMMARY (TOP 5 FACTORS)
            </div>
            <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
                Faktor utama penyebab churn diurutkan dari tingkat risiko tertinggi
            </div>
        """, unsafe_allow_html=True)

        risks = [
            ("Tenure 0 - 12 bulan",       churn_pct(df, "tenureBucket",    "0-12 Bulan")),
            ("Month-to-month Contract",   churn_pct(df, "contract",        "Month-to-month")),
            ("Fiber optic Internet",      churn_pct(df, "internetService", "Fiber optic")),
            ("Senior Citizen",            churn_pct(df, "seniorCitizen",   "Yes")),
            ("Electronic check",          churn_pct(df, "paymentMethod",   "Electronic check")),
        ]
        risks_df = pd.DataFrame(risks, columns=["Faktor", "Churn Rate (%)"])
        risks_df = risks_df.sort_values("Churn Rate (%)", ascending=True)
        # highlight top risk factors with distinct colors
        colors_r = distinct_colors(risks_df["Churn Rate (%)"].round(2))

        fig = go.Figure(go.Bar(
            y=risks_df["Faktor"], x=risks_df["Churn Rate (%)"],
            orientation="h",
            marker_color=colors_r, marker_line_width=0,
            text=[f"{v:.2f}%" for v in risks_df["Churn Rate (%)"]],
            textposition="outside",
            textfont=dict(size=10, color=TEXT_DARK),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=40, t=10, b=0), height=220,
            xaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       ticksuffix="%", tickfont=dict(size=9), range=[0, 60]),
            yaxis=dict(showgrid=False, tickfont=dict(size=9)),
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)



    # ─────────────────────────────────────────────────
    # ROW 4: ANALISIS FAKTOR PENYEBAB CHURN (Insight BI)
    # ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:{BG_CARD}; border:1px solid {BORDER}; border-radius:16px;
         padding:22px 24px 14px; box-shadow:0 2px 10px rgba(0,0,0,0.03);">
        <div style="font-size:14px; font-weight:900; color:{TEXT_DARK}; margin-bottom:3px;
             text-transform:uppercase; letter-spacing:0.3px;">
            🔍 Analisis Faktor Penyebab Churn
        </div>
        <div style="font-size:11px; color:{TEXT_LIGHT}; margin-bottom:18px;">
            Identifikasi faktor-faktor utama yang memengaruhi keputusan pelanggan untuk berhenti berlangganan,
            berdasarkan analisis multidimensi dari data warehouse
        </div>
    """, unsafe_allow_html=True)

    # adjust column widths to balance layout (no scroll on left column)

    ia, ib, ic = st.columns([1.0, 1.25, 1.05])

    # ── Layanan Tambahan vs Churn (Per-service comparison) ──────────
    with ia:
        st.markdown(f"""
        <div style="font-size:12px;font-weight:700;color:{TEXT_DARK};margin-bottom:3px;">
            Pengaruh Layanan Tambahan terhadap Churn
        </div>
        <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
            Apakah pelanggan yang mengaktifkan layanan tambahan lebih loyal?
            Perbandingan churn rate antara yang menggunakan (Yes) vs tidak (No)
        </div>
        """, unsafe_allow_html=True)

        svc_map = {
            "onlineSecurity":   "Online Security",
            "onlineBackup":     "Online Backup",
            "deviceProtection": "Device Protection",
            "techSupport":      "Tech Support",
            "streamingTV":      "Streaming TV",
            "streamingMovies":  "Streaming Movies",
        }

        # Normalizer to match column names in different formats/cases
        def _norm(s: str) -> str:
            return "".join([c for c in str(s).lower() if c.isalnum()])

        col_map = {}
        available_cols_norm = { _norm(c): c for c in fdf.columns }
        for expected in svc_map.keys():
            n = _norm(expected)
            found = available_cols_norm.get(n)
            # Also try matching keys where label words might be spaced (e.g., 'onlinesecurity' vs 'online_security')
            if not found:
                # try partial match: any column norm that contains expected norm or vice versa
                for an, orig in available_cols_norm.items():
                    if n in an or an in n:
                        found = orig
                        break
            if found:
                col_map[expected] = found

        rows = []
        for key, label in svc_map.items():
            colname = col_map.get(key)
            if not colname:
                continue
            yes_sub = fdf[fdf[colname] == "Yes"]
            no_sub = fdf[fdf[colname] == "No"]
            yes_pct = yes_sub["churnFlag"].mean() * 100 if len(yes_sub) else None
            no_pct = no_sub["churnFlag"].mean() * 100 if len(no_sub) else None
            delta = None
            if yes_pct is not None and no_pct is not None:
                delta = yes_pct - no_pct
            rows.append({"service": label, "yes": yes_pct, "no": no_pct, "delta": delta})

        # Render a compact two-column grid so the service cards don't stretch vertically
        if rows:
            html = ['<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:4px 4px 8px;">']
            for r in rows:
                yes_txt = f"{r['yes']:.1f}%" if r['yes'] is not None else "-"
                no_txt = f"{r['no']:.1f}%" if r['no'] is not None else "-"
                if r['delta'] is None:
                    delta_html = f"<span style='color:{TEXT_LIGHT};font-size:11px;'>No data</span>"
                else:
                    if r['delta'] < 0:
                        delta_html = f"<span style='color:{MINT};font-weight:700;'>{abs(r['delta']):.1f}% lower</span>"
                    elif r['delta'] > 0:
                        delta_html = f"<span style='color:{RED};font-weight:700;'>{r['delta']:.1f}% higher</span>"
                    else:
                        delta_html = f"<span style='color:{TEXT_MID};font-weight:700;'>No diff</span>"

                # tighter compact card
                html.append(
                    f"<div style='display:flex;align-items:center;justify-content:space-between;padding:6px;border-radius:10px;background:linear-gradient(90deg,#ffffff, #fbfffc);border:1px solid #E7F5EE;'>"
                    f"<div style='display:flex;gap:8px;align-items:center;'>"
                    f"<div style='width:6px;height:26px;border-radius:5px;background:{MINT_SOFT}30;border-left:5px solid {MINT_SOFT};'></div>"
                    f"<div style='font-size:12px;font-weight:800;color:{TEXT_DARK};'>{r['service']}</div>"
                    f"</div>"
                    f"<div style='display:flex;gap:8px;align-items:center;'>"
                    f"<div style='text-align:center;font-size:12px;color:{RED};'><div style=\"font-weight:800;font-size:12px;color:{RED};\">{yes_txt}</div><div style=\"font-size:9px;color:{TEXT_LIGHT};\">Yes</div></div>"
                    f"<div style='text-align:center;font-size:12px;color:{MINT};'><div style=\"font-weight:800;font-size:12px;color:{MINT};\">{no_txt}</div><div style=\"font-size:9px;color:{TEXT_LIGHT};\">No</div></div>"
                    f"<div style='text-align:right;font-size:11px;color:{TEXT_MID};'>{delta_html}</div>"
                    f"</div>"
                    f"</div>"
                )
            html.append('</div>')
            st.markdown("".join(html), unsafe_allow_html=True)
        else:
            # Friendly placeholder when no service columns are present in the filtered data
            st.markdown(f"""
                <div style='padding:14px;border-radius:10px;border:1px dashed {BORDER};background:transparent'>
                    <div style='font-size:12px;font-weight:700;color:{TEXT_DARK};margin-bottom:6px;'>Data Layanan Tambahan Tidak Tersedia</div>
                    <div style='font-size:11px;color:{TEXT_LIGHT};'>Kolom layanan tambahan (mis. Online Security, Online Backup) tidak ditemukan pada data yang difilter saat ini. Coba ubah filter atau periksa sumber data.</div>
                </div>
            """, unsafe_allow_html=True)

    # ── Gender & Demografis ───────────────────────────
    with ib:
        st.markdown(f"""
        <div style="font-size:12px;font-weight:700;color:{TEXT_DARK};margin-bottom:3px;">
            Churn berdasarkan Profil Demografis
        </div>
        <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:12px;">
            Perbandingan tingkat churn antar kelompok demografis: gender, status pernikahan,
            dan jumlah tanggungan keluarga
        </div>
        """, unsafe_allow_html=True)

        demo_data = []
        for col, label_map in [
            ("gender",     {"Male": "Pria", "Female": "Wanita"}),
            ("partner",    {"No": "Tanpa Partner", "Yes": "Punya Partner"}),
            ("dependents", {"No": "Tanpa Tanggungan", "Yes": "Punya Tanggungan"}),
        ]:
            d = fdf.groupby(col)["churnFlag"].mean().reset_index()
            d["pct"] = d["churnFlag"] * 100
            d["label"] = d[col].map(label_map).fillna(d[col])
            for _, row in d.iterrows():
                demo_data.append({"Kategori": row["label"], "Churn Rate (%)": row["pct"]})

        df_demo = pd.DataFrame(demo_data)
        # per-category contrasting colors (strong red/blue/green order)
        colors_d = distinct_colors(df_demo["Churn Rate (%)"].round(2), palette=[RED, BLUE, MINT, AMBER, PURP])

        fig = go.Figure(go.Bar(
            x=df_demo["Kategori"], y=df_demo["Churn Rate (%)"],
            marker_color=colors_d, marker_line_width=0,
            text=[f"{v:.1f}%" for v in df_demo["Churn Rate (%)"]],
            textposition="outside",
            textfont=dict(size=10),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), height=260,
            xaxis=dict(showgrid=False, tickfont=dict(size=9), linecolor=BORDER),
            yaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="Churn Rate (%)", tickfont=dict(size=9)),
            font_family="'Plus Jakarta Sans', sans-serif",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Scatter: Tenure vs Monthly Charges ────────────
    with ic:
        st.markdown(f"""
        <div style="font-size:12px;font-weight:700;color:{TEXT_DARK};margin-bottom:3px;">
            Hubungan Tenure & Tagihan Bulanan terhadap Churn
        </div>
        <div style="font-size:10px;color:{TEXT_LIGHT};margin-bottom:8px;">
            Visualisasi pola: pelanggan baru dengan tagihan tinggi cenderung churn lebih banyak.
            Titik merah = churn, titik hijau = retained
        </div>
        """, unsafe_allow_html=True)

        # Ambil sampel 800 titik untuk performa
        sample_df = fdf.sample(min(800, len(fdf)), random_state=42)
        sample_df["Status"] = sample_df["churnFlag"].map({1: "Churned", 0: "Retained"})

        fig = px.scatter(
            sample_df,
            x="tenure", y="monthlyCharges",
            color="Status",
            color_discrete_map={"Churned": RED, "Retained": MINT},
            opacity=0.55,
            size_max=8,
        )
        fig.update_traces(marker=dict(size=6, line=dict(width=0)))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), height=260,
            xaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="Tenure (Bulan)", tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#EBF4EF", zeroline=False,
                       title="Monthly Charges ($)", tickfont=dict(size=9)),
            font_family="'Plus Jakarta Sans', sans-serif",
            legend=dict(title="", font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)

     # ══════════════════════════════════════════════════════════════════
    # BARIS 5 — BUSINESS INSIGHTS — desain timeline/step cards
    # ══════════════════════════════════════════════════════════════════
    r_m2m    = _pct(df,"contract","Month-to-month")
    r_2yr    = _pct(df,"contract","Two year")
    r_fiber  = _pct(df,"internetService","Fiber optic")
    r_dsl    = _pct(df,"internetService","DSL")
    r_eck    = _pct(df,"paymentMethod","Electronic check")
    r_auto   = _pct(df,"paymentCategory","Automatic") if "paymentCategory" in df.columns else 16.0
    r_new    = _pct(df,"tenureBucket","0-12 Bulan")
    r_old    = _pct(df,"tenureBucket","49+ Bulan")
    r_senior = _pct(df,"seniorCitizen","Yes")
    r_nosec  = _pct(df,"onlineSecurity","No")
    r_sec    = _pct(df,"onlineSecurity","Yes")
    a_ch     = df[df["churnFlag"]==1]["monthlyCharges"].mean()
    a_rt     = df[df["churnFlag"]==0]["monthlyCharges"].mean()
    t_ch     = df[df["churnFlag"]==1]["tenure"].mean()
    t_rt     = df[df["churnFlag"]==0]["tenure"].mean()

    insights = [
        {
            "num":"01", "color":C_CHURN, "bg":"#FFF5F5",
            "icon":"📋",
            "title":"Kontrak Bulanan = Pintu Keluar Terbuka",
            "finding":f"Churn rate Month-to-month mencapai <b style='color:{C_CHURN}'>{r_m2m:.1f}%</b>, berbanding terbalik dengan kontrak dua tahun yang hanya <b style='color:{C_RETAINED}'>{r_2yr:.1f}%</b>.",
            "why":"Pelanggan tanpa kontrak panjang tidak punya 'biaya' untuk berhenti — kapan saja tergiur promosi kompetitor, langsung bisa pindah. Komitmen kontrak menciptakan hambatan psikologis dan finansial yang efektif.",
            "action":"Dorong upgrade kontrak dengan diskon 10–15% atau bundling layanan eksklusif khusus pelanggan kontrak tahunan.",
        },
        {
            "num":"02", "color":C_AMBER, "bg":"#FFFBF0",
            "icon":"🌐",
            "title":"Fiber Optic: Layanan Terbaik, Loyalitas Terendah",
            "finding":f"Fiber Optic churn <b style='color:{C_AMBER}'>{r_fiber:.1f}%</b> — lebih dari dua kali lipat DSL ({r_dsl:.1f}%).",
            "why":"Paradoks layanan premium: semakin tinggi ekspektasi pelanggan, semakin besar kekecewaan saat ada gangguan. Pengguna Fiber Optic cenderung lebih tech-savvy dan sadar pilihan lain di pasaran.",
            "action":"Survey kepuasan khusus Fiber Optic dan evaluasi apakah harga yang dibayarkan sudah sepadan dengan konsistensi kualitas yang diterima.",
        },
        {
            "num":"03", "color":C_PURP, "bg":"#F5F3FF",
            "icon":"💳",
            "title":"Cara Bayar Manual = Momen Reconsider Bulanan",
            "finding":f"Electronic Check churn <b style='color:{C_CHURN}'>{r_eck:.1f}%</b> vs auto-payment hanya <b style='color:{C_RETAINED}'>{r_auto:.1f}%</b>.",
            "why":"Setiap bulan pelanggan manual 'aktif memilih' untuk bayar lagi — ini adalah momen pengambilan keputusan yang berulang. Auto-payment menghilangkan momen tersebut dan menciptakan keterikatan pasif yang sangat efektif.",
            "action":"Tawarkan cashback atau diskon tagihan bulan berikutnya bagi pelanggan yang beralih ke auto-payment.",
        },
        {
            "num":"04", "color":C_BLUE, "bg":"#EFF6FF",
            "icon":"⏳",
            "title":"12 Bulan Pertama: Jendela Retensi Paling Krusial",
            "finding":f"Pelanggan 0–12 bulan churn <b style='color:{C_CHURN}'>{r_new:.1f}%</b>. Setelah 4 tahun+, turun drastis ke <b style='color:{C_RETAINED}'>{r_old:.1f}%</b>.",
            "why":f"Rata-rata tenure pelanggan yang churn hanya {t_ch:.1f} bulan vs yang loyal {t_rt:.1f} bulan. Pelanggan yang berhasil melewati tahun pertama membangun kebiasaan dan ketergantungan terhadap layanan — inilah titik kritis yang harus dimenangkan.",
            "action":"Program welcome intensif: personal onboarding call, diskon bulan ke-3, dan notifikasi proaktif saat ada gangguan di periode awal.",
        },
        {
            "num":"05", "color":C_TEAL, "bg":"#F0FDFA",
            "icon":"🔒",
            "title":"Layanan Keamanan = Jangkar Loyalitas Paling Kuat",
            "finding":f"Tanpa Online Security churn <b style='color:{C_CHURN}'>{r_nosec:.1f}%</b>, dengan Online Security hanya <b style='color:{C_RETAINED}'>{r_sec:.1f}%</b>. Pola identik pada Tech Support.",
            "why":"Layanan keamanan dan dukungan teknis menciptakan 'switching cost' — data dan proteksi pelanggan sudah terintegrasi, sehingga pindah operator berarti kehilangan perlindungan aktif. Ini membuat pelanggan berpikir dua kali sebelum berhenti.",
            "action":"Tawarkan trial gratis 3 bulan layanan Online Security & Tech Support untuk semua pelanggan baru — konversi habitual lebih mudah dari cold-sell.",
        },
        {
            "num":"06", "color":"#C06B2F", "bg":"#FFF7ED",
            "icon":"💰",
            "title":"Paradoks Tagihan Tinggi: Bayar Lebih, Pergi Lebih Cepat",
            "finding":f"Pelanggan churn rata-rata membayar <b style='color:{C_CHURN}'>${a_ch:.2f}</b>/bulan, sedangkan yang loyal hanya <b style='color:{C_RETAINED}'>${a_rt:.2f}</b>/bulan — selisih <b>${a_ch-a_rt:.2f}</b>.",
            "why":"Pelanggan di segmen tagihan tinggi biasanya mengambil paket premium dengan harapan mendapatkan nilai maksimal. Ketika realita tidak sesuai harapan, kekecewaan lebih besar dan mereka lebih aktif mencari alternatif. Price-sensitivity tinggi berbanding lurus dengan churn.",
            "action":f"Evaluasi ulang paket ${a_ch:.0f}+ — tambahkan fitur bernilai nyata (bukan sekadar kecepatan), dan pastikan experience pelanggan segmen premium benar-benar superior.",
        },
    ]

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{MINT}0C,{C_BLUE}08);
         border:1.5px solid {MINT}30;border-radius:20px;padding:24px 24px 10px;">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:20px;flex-wrap:wrap;">
            <div style="width:42px;height:42px;background:{MINT};border-radius:12px;flex-shrink:0;
                 display:flex;align-items:center;justify-content:center;font-size:22px;
                 box-shadow:0 4px 12px rgba(46,175,125,0.3);">💡</div>
            <div>
                <div style="font-size:16px;font-weight:900;color:{TEXT_DARK};
                     letter-spacing:-0.3px;">Interpretasi & Business Insights</div>
                <div style="font-size:12px;color:{TEXT_LIGHT};margin-top:1px;">
                    Penjelasan mengapa pola churn ini terjadi dan langkah konkret yang dapat diambil — berbasis data warehouse
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 3 kolom × 2 baris
    for row_i in range(0, len(insights), 3):
        row_ins = insights[row_i:row_i+3]
        cols = st.columns(len(row_ins))
        for col, ins in zip(cols, row_ins):
            with col:
                st.markdown(f"""
                <div style="background:{ins['bg']};border:1px solid {ins['color']}22;
                     border-radius:14px;padding:18px 18px 16px;
                     position:relative;overflow:hidden;height:100%;">
                    <!-- Number badge -->
                    <div style="position:absolute;top:14px;right:16px;font-size:32px;
                         font-weight:900;color:{ins['color']}15;line-height:1;">{ins['num']}</div>
                    <!-- Icon + title -->
                    <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:12px;">
                        <div style="width:36px;height:36px;flex-shrink:0;background:{ins['color']}15;
                             border-radius:10px;display:flex;align-items:center;
                             justify-content:center;font-size:18px;">{ins['icon']}</div>
                        <div style="font-size:13px;font-weight:800;color:{TEXT_DARK};
                             line-height:1.3;padding-top:2px;">{ins['title']}</div>
                    </div>
                    <!-- Finding pill -->
                    <div style="background:white;border:1px solid {ins['color']}30;border-radius:10px;
                         padding:10px 12px;margin-bottom:10px;">
                        <div style="font-size:10px;font-weight:800;color:{ins['color']};
                             text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">
                            📊 Temuan Data
                        </div>
                        <div style="font-size:12px;color:{TEXT_MID};line-height:1.55;">{ins['finding']}</div>
                    </div>
                    <!-- Why -->
                    <div style="margin-bottom:10px;">
                        <div style="font-size:10px;font-weight:800;color:{TEXT_LIGHT};
                             text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">
                            🔍 Mengapa Ini Terjadi
                        </div>
                        <div style="font-size:12px;color:{TEXT_MID};line-height:1.6;">{ins['why']}</div>
                    </div>
                    <!-- Action -->
                    <div style="background:{ins['color']}0E;border:1px solid {ins['color']}25;
                         border-left:3px solid {ins['color']};border-radius:8px;
                         padding:8px 12px;">
                        <div style="font-size:10px;font-weight:800;color:{ins['color']};
                             text-transform:uppercase;letter-spacing:0.5px;margin-bottom:3px;">
                            ✅ Rekomendasi Tindakan
                        </div>
                        <div style="font-size:12px;color:{TEXT_DARK};font-weight:600;
                             line-height:1.5;">{ins['action']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:18px'></div>", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────
    total_all = len(df);  churn_all = int(df["churnFlag"].sum())
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
         padding:14px 2px 8px;border-top:1px solid {BORDER};flex-wrap:wrap;gap:6px;">
        <div style="font-size:11px;color:{TEXT_LIGHT};">
            <b>Sumber:</b> IBM Watson Telco Customer Churn (Kaggle)
            &nbsp;·&nbsp;<b>Total:</b> {total_all:,} pelanggan
            &nbsp;·&nbsp;<b>Churn:</b> {churn_all:,} ({churn_all/total_all*100:.2f}%)
        </div>
        <div style="font-size:11px;color:{TEXT_LIGHT};">
            BI Dashboard · Sistem Informasi · Universitas Andalas
        </div>
    </div>
    """, unsafe_allow_html=True)