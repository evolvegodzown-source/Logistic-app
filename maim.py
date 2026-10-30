"""
DrugStoc Pharma Logistics Dashboard
=====================================
Cleaned, bug-fixed Streamlit application for logistics KPI monitoring.
Original code rearranged with all duplicate definitions, unreachable code,
and logic errors resolved.

Run with:  streamlit run drugstoc_logistics_dashboard.py
"""

import base64
import io
import hmac
import os
import textwrap
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="DrugStoc Pharma Logistics Dashboard",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# ASSET CONFIGURATION
# ============================================================================
DATA_PATH = (
    r"https://drugstock-my.sharepoint.com/:x:/g/personal/it_drugstoc_com/"
    r"IQA5yp0kdh82Ra7YcCr-be0vAXufIjkPsYHD4yoBbt6byhs?e=MFF4su&download=1"
)
COVER_LOGO_URL = (
    r"https://drugstock-my.sharepoint.com/:i:/g/personal/it_drugstoc_com/"
    r"IQCURjcRKFhMQ4HunFjm4IxrAfQqHn3s3TDz3jUrWgzgw5g?e=dNiGIh&download=1"
)
FILTER_YEAR = 2026

BRAND = {
    "blue": "#1686D9",
    "blue_dark": "#0B5FA5",
    "green": "#10B981",
    "navy": "#071A2D",
    "teal": "#14B8A6",
    "amber": "#F59E0B",
    "red": "#EF4444",
}

THEME = {
    "page": "#FFFFFF",
    "surface": "#FFFFFF",
    "surface_2": "#EAF1F7",
    "text": "#0F2333",
    "muted": "#4A6178",
    "border": "rgba(15,35,51,.12)",
    "grid": "rgba(15,35,51,.10)",
    "plot_bg": "#FFFFFF",
    "accent_soft": "rgba(22,134,217,.12)",
}


# ============================================================================
# LOGIN CREDENTIALS
# ============================================================================
def get_login_credentials():
    try:
        auth_settings = st.secrets.get("auth", {})
    except StreamlitSecretNotFoundError:
        auth_settings = {}
    username = os.getenv("DASHBOARD_USERNAME") or auth_settings.get("username")
    password = os.getenv("DASHBOARD_PASSWORD") or auth_settings.get("password")
    return username, password


# ============================================================================
# HELPERS — DATE / WEEK
# ============================================================================
def fri_thu_week(dates):
    """
    Week number, week-start (Friday) and label-year for a datetime Series.
    Weeks run Friday-Thursday and are numbered by the ISO week of the week's
    Friday (so 16-22 Oct 2026 is W42 and 23-29 Oct 2026 is W43).
    """
    week_start = dates - pd.to_timedelta((dates.dt.weekday - 4) % 7, unit="D")
    iso = week_start.dt.isocalendar()
    return iso["week"], week_start, iso["year"]


def week_start_from_label(year, week):
    """Friday start of the Fri-Thu week numbered (year, week) by its Friday."""
    iso_monday = pd.Timestamp.fromisocalendar(int(year), int(week), 1)
    return iso_monday + pd.Timedelta(days=4)


def week_label_with_span(week_num, week_year, week_start):
    """Vectorised Fri-Thu week labels with the date span, e.g. 'W42 - 2026 (16 Oct–22 Oct)'."""
    end = week_start + pd.Timedelta(days=6)
    start_day = week_start.dt.day.fillna(0).astype(int).astype(str)
    end_day = end.dt.day.fillna(0).astype(int).astype(str)
    start_mon = week_start.dt.strftime("%b").fillna("")
    end_mon = end.dt.strftime("%b").fillna("")
    label = (
        "W" + week_num.astype(str).str.zfill(2)
        + " - " + week_year.fillna(0).astype(int).astype(str)
    )
    span = (
        " (" + start_day + " " + start_mon + "\u2013" + end_day + " " + end_mon + ")"
    )
    return label + span.where(week_start.notna(), "")


def build_timestamp(data_df, date_c, time_c):
    """Combine a date column and optional time column into a datetime Series."""
    if not date_c or date_c not in data_df.columns:
        return pd.Series(pd.NaT, index=data_df.index)
    dates = pd.to_datetime(data_df[date_c], errors="coerce")
    if time_c and time_c in data_df.columns:
        times = (
            data_df[time_c]
            .astype(str)
            .str.strip()
            .replace(["nan", "None", "<NaT>", ""], "00:00:00")
        )
        combined = dates.dt.strftime("%Y-%m-%d") + " " + times
        return pd.to_datetime(combined, errors="coerce")
    return dates


# ============================================================================
# HELPERS — COLUMN MAPPING
# ============================================================================
def find_col(df, candidates, exact_only=False):
    """Return the first matching column name from a list of candidates."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    if exact_only:
        for cand in candidates:
            if cand in df.columns:
                return cand
        return None
    cols_lower = {str(c).lower().strip(): c for c in df.columns}
    for cand in candidates:
        key = str(cand).lower().strip()
        if key in cols_lower:
            return cols_lower[key]
    for cand in candidates:
        key = str(cand).lower().strip()
        for col in df.columns:
            if key in str(col).lower().strip():
                return col
    return None


# ============================================================================
# HELPERS — FORMATTING
# ============================================================================
def money(value):
    """Compact naira format: ₦1.5M, ₦450.0K, ₦850."""
    value = float(value) if value is not None else 0.0
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return f"₦{value / 1_000_000_000:.1f}B"
    if magnitude >= 1_000_000:
        return f"₦{value / 1_000_000:.1f}M"
    if magnitude >= 1_000:
        return f"₦{value / 1_000:.1f}K"
    return f"₦{value:,.0f}"


def fmt_num(value):
    return f"{value:,.0f}"


def pct_change(current, previous):
    """Percentage change between two values; None if not computable."""
    if previous is None or pd.isna(previous) or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100.0


# ============================================================================
# HELPERS — PLOTLY THEME
# ============================================================================
def plotly_theme(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=THEME["plot_bg"],
        plot_bgcolor=THEME["plot_bg"],
        font=dict(color=THEME["text"]),
        margin=dict(l=24, r=24, t=60, b=28),
        hoverlabel=dict(bgcolor=THEME["surface"], font_color=THEME["text"]),
        autosize=True,
    )
    fig.update_xaxes(showgrid=False, color=THEME["muted"], tickfont=dict(color=THEME["muted"]))
    fig.update_yaxes(gridcolor=THEME["grid"], color=THEME["muted"], tickfont=dict(color=THEME["muted"]))
    return fig


def show_empty_chart(message):
    st.info(message)


# ============================================================================
# HELPERS — KPI CARDS & SECTIONS
# ============================================================================
def kpi_card(label, value, description, icon="•", accent=None, weekly=None):
    accent = accent or BRAND["blue"]
    if accent == BRAND["green"]:
        soft = "rgba(16,185,129,.12)"
    elif accent == BRAND["amber"]:
        soft = "rgba(245,158,11,.13)"
    elif accent == BRAND["red"]:
        soft = "rgba(239,68,68,.12)"
    else:
        soft = "rgba(22,134,217,.12)"
    weekly_html = ""
    if weekly:
        def _fmt_h(v):
            return f"{v:.1f}h" if v is not None and pd.notna(v) else "N/A"

        cw_txt = _fmt_h(weekly.get("cw"))
        pw_txt = _fmt_h(weekly.get("pw"))
        delta = weekly.get("delta")
        if delta is None:
            delta_html = (
                f"<span style='color:{THEME['muted']};font-size:.75rem;font-weight:800;'>Δ N/A</span>"
            )
        else:
            up = delta >= 0
            delta_color = BRAND["red"] if up else BRAND["green"]
            arrow = "▲" if up else "▼"
            delta_html = (
                f"<span style='color:{delta_color};'>{arrow} {abs(delta):.1f}% WoW</span>"
            )
        # Single line: a multi-line string here would inject a whitespace-only
        # line into the markdown and break the raw HTML block.
        weekly_html = (
            f'<div class="kpi-weekly">'
            f'<div class="kpi-weekly-row"><span>CW · {cw_txt}</span><span>PW · {pw_txt}</span></div>'
            f'<div class="kpi-delta">{delta_html}</div>'
            f'</div>'
        )
    return f"""
        <div class="kpi-card" style="--kpi-accent:{accent};--kpi-soft:{soft};">
            <div class="kpi-top">
                <div class="kpi-label">{label}</div>
                <div class="kpi-icon">{icon}</div>
            </div>
            <div class="kpi-value">{value}</div>
            {weekly_html}
        </div>
    """


def render_kpis(cards):
    for row_start in range(0, len(cards), 4):
        row = cards[row_start : row_start + 4]
        cols = st.columns(4)
        for col, card in zip(cols, row):
            label, value, description, icon, accent, *extra = card
            weekly = extra[0] if extra else None
            with col:
                st.markdown(
                    kpi_card(label=label, value=value, description=description, icon=icon, accent=accent, weekly=weekly),
                    unsafe_allow_html=True,
                )


def section_header(title, note=""):
    st.markdown(
        f"""
        <div class="section-head">
            <div class="section-title">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# HELPERS — COMPARISON / WoW / MoM
# ============================================================================
COMPARE_KPIS = [
    "Order Volume",
    "Delivery Rate",
    "TAT: Order to Delivery",
    "TAT: Dispatch to Delivery",
    "TAT: Invoice to Dispatch",
    "Fuel Cost",
]


def comparison_anchor(data_df, col_date, selected_week, selected_month):
    """Anchor date for WoW/MoM: selected week > selected month > latest date."""
    if selected_week != "All Weeks":
        try:
            _wk = int(selected_week[1:3])
            _yr = int(selected_week.split(" - ")[1].split()[0])
            return week_start_from_label(_yr, _wk)
        except (ValueError, TypeError):
            pass
    if selected_month != "All Months" and "Month Label" in data_df.columns and col_date:
        month_dates = data_df.loc[data_df["Month Label"] == selected_month, col_date].dropna()
        if not month_dates.empty:
            return month_dates.max()
    if col_date:
        dated = data_df[col_date].dropna()
        return dated.max() if not dated.empty else None
    return None


def comparison_periods(data_df, col_date, selected_week, selected_month):
    """Return current/previous week and month masks + date bounds."""
    if col_date is None or col_date not in data_df.columns:
        return None
    dated = data_df[col_date].dropna()
    if dated.empty:
        return None
    anchor = comparison_anchor(data_df, col_date, selected_week, selected_month)
    if anchor is None:
        return None
    latest_date = anchor.normalize()
    current_week_start = latest_date - pd.Timedelta(days=(latest_date.weekday() - 4) % 7)
    current_month_start = latest_date.replace(day=1)
    previous_month_end = current_month_start - pd.Timedelta(days=1)
    return {
        "WoW": (
            data_df[col_date].ge(current_week_start)
            & data_df[col_date].lt(current_week_start + pd.Timedelta(days=7)),
            data_df[col_date].ge(current_week_start - pd.Timedelta(days=7))
            & data_df[col_date].lt(current_week_start),
            (current_week_start, current_week_start + pd.Timedelta(days=7)),
            (current_week_start - pd.Timedelta(days=7), current_week_start),
        ),
        "MoM": (
            data_df[col_date].ge(current_month_start)
            & data_df[col_date].lt(current_month_start + pd.offsets.MonthBegin(1)),
            data_df[col_date].ge(previous_month_end.replace(day=1))
            & data_df[col_date].lt(current_month_start),
            (current_month_start, current_month_start + pd.offsets.MonthBegin(1)),
            (previous_month_end.replace(day=1), current_month_start),
        ),
    }


def compute_period_kpis(frame, col_client):
    """Compute core operational KPIs for a dataframe slice."""
    orders = int(frame[col_client].count()) if col_client and col_client in frame.columns else len(frame)
    delivered = int(frame["Is Delivered"].sum()) if orders else 0
    fulfil = (delivered / orders * 100.0) if orders else 0.0
    tat_order = frame["Creation_Delivery_TAT"].mean()
    tat_dispatch = frame["Shipping_TAT"].mean()
    tat_invoice_dispatch = frame["Invoice_Dispatch_TAT"].mean()
    return {
        "Order Volume": float(orders),
        "Delivery Rate": float(fulfil),
        "TAT: Order to Delivery": float(tat_order) if pd.notna(tat_order) else 0.0,
        "TAT: Dispatch to Delivery": float(tat_dispatch) if pd.notna(tat_dispatch) else 0.0,
        "TAT: Invoice to Dispatch": float(tat_invoice_dispatch) if pd.notna(tat_invoice_dispatch) else 0.0,
    }


def fuel_cost_between(fuel_df, col_fuel_date, col_fuel_cost, start, end_exclusive):
    """Total fuel cost within a date window."""
    if fuel_df is None or not col_fuel_date or not col_fuel_cost:
        return 0.0
    mask = (fuel_df[col_fuel_date] >= start) & (fuel_df[col_fuel_date] < end_exclusive)
    return float(fuel_df.loc[mask, col_fuel_cost].sum())


def format_kpi_value(kpi_name, value):
    if kpi_name == "Order Volume":
        return fmt_num(value)
    if kpi_name == "Delivery Rate":
        return f"{value:.1f}%"
    if kpi_name == "Fuel Cost":
        return money(value)
    return f"{value:.1f} hrs"


def comparison_pie(kpi_name, current_val, previous_val, current_label, previous_label):
    """Donut pie chart comparing current vs previous period for a single KPI."""
    curr = max(float(current_val), 0.0)
    prev = max(float(previous_val), 0.0)
    delta = pct_change(curr, prev)
    lower_is_better = kpi_name.startswith("TAT") or kpi_name == "Fuel Cost"
    if delta is None:
        delta_color = THEME["muted"]
        delta_text = "Δ N/A (no baseline)"
    else:
        improved = (delta < 0) if lower_is_better else (delta > 0)
        delta_color = BRAND["green"] if improved else BRAND["red"]
        arrow = "▲" if delta >= 0 else "▼"
        period_text = "WoW" if "W" in current_label else "MoM"
        delta_text = f"{arrow} {abs(delta):.1f}% {period_text}"
    fig = go.Figure(
        data=[
            go.Pie(
                labels=[f"Current · {current_label}", f"Previous · {previous_label}"],
                values=[curr, prev],
                hole=0.58,
                sort=False,
                direction="clockwise",
                marker=dict(colors=[BRAND["blue"], "#4C6A86"]),
                textinfo="label+percent",
                textfont=dict(color=THEME["text"], size=11),
                customdata=[format_kpi_value(kpi_name, curr), format_kpi_value(kpi_name, prev)],
                hovertemplate=(
                    "%{label}<br>Value: %{customdata}<br>"
                    "Share of combined: %{percent}<extra></extra>"
                ),
            )
        ]
    )
    fig = plotly_theme(fig)
    fig.update_layout(
        title=dict(
            text=(
                f"{kpi_name}<br>"
                f"<span style='font-size:11px;color:{THEME['muted']}'>"
                f"Current: {format_kpi_value(kpi_name, curr)} &nbsp;·&nbsp; "
                f"Previous: {format_kpi_value(kpi_name, prev)} &nbsp;·&nbsp; "
                f"<span style='color:{delta_color};font-weight:800;'>{delta_text}</span>"
                f"</span>"
            ),
            font=dict(size=13, color=THEME["text"]),
        ),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.25, x=0.5, xanchor="center",
            font=dict(size=10, color=THEME["muted"]),
        ),
        height=330,
        margin=dict(l=10, r=10, t=92, b=10),
    )
    return fig


COMPARE_METRIC_ORDER = [
    "Order Volume",
    "Delivery Rate",
    "TAT: Order to Delivery",
    "TAT: Dispatch to Delivery",
    "TAT: Invoice to Dispatch",
    "Fuel Cost",
]
COMPARE_LOWER_IS_BETTER = (
    "TAT: Order to Delivery",
    "TAT: Dispatch to Delivery",
    "TAT: Invoice to Dispatch",
    "Fuel Cost",
)


def _period_kpis_with_fuel(data_df, current_mask, previous_mask, curr_bounds, prev_bounds,
                           col_client, fuel_df, col_fuel_date, col_fuel_cost):
    current = compute_period_kpis(data_df.loc[current_mask], col_client)
    previous = compute_period_kpis(data_df.loc[previous_mask], col_client)
    current["Fuel Cost"] = fuel_cost_between(fuel_df, col_fuel_date, col_fuel_cost, curr_bounds[0], curr_bounds[1])
    previous["Fuel Cost"] = fuel_cost_between(fuel_df, col_fuel_date, col_fuel_cost, prev_bounds[0], prev_bounds[1])
    return current, previous


def _render_period_cards(comparison_name, current, previous):
    cards = []
    for metric in COMPARE_METRIC_ORDER:
        current_value = current[metric]
        previous_value = previous[metric]
        change = current_value - previous_value
        change_pct = (change / previous_value * 100) if previous_value else 0.0
        if change == 0:
            change_class, change_color = "", THEME["muted"]
        else:
            improved = (change < 0) if metric in COMPARE_LOWER_IS_BETTER else (change > 0)
            change_class = "increase" if improved else "decrease"
            change_color = BRAND["green"] if improved else BRAND["red"]
        change_symbol = "▲" if change >= 0 else "▼"
        cards.append(
            textwrap.dedent(
                f"""
                <div class='comparison-card'>
                    <div class='comparison-title'>{metric}</div>
                    <div class='comparison-values'>
                        <div><span class='comparison-label'>Current</span><strong>{format_kpi_value(metric, current_value)}</strong></div>
                        <div><span class='comparison-label'>Previous</span><strong>{format_kpi_value(metric, previous_value)}</strong></div>
                    </div>
                    <div class='comparison-change {change_class}' style='color: {change_color} !important;'>{change_symbol} {abs(change_pct):.1f}% vs previous</div>
                </div>
                """
            ).strip()
        )
    st.markdown(f"<h3 class='comparison-period'>{comparison_name}</h3>", unsafe_allow_html=True)
    st.markdown("<div class='comparison-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def quarter_anchor(data_df, col_date, selected_quarter, selected_week, selected_month):
    """Anchor date for QoQ: selected quarter > selected week/month > latest date."""
    if selected_quarter != "All Quarters" and "Quarter Label" in data_df.columns and col_date:
        q_dates = data_df.loc[data_df["Quarter Label"] == selected_quarter, col_date].dropna()
        if not q_dates.empty:
            return q_dates.max()
    return comparison_anchor(data_df, col_date, selected_week, selected_month)


def qoq_periods(data_df, col_date, selected_quarter, selected_week, selected_month):
    """Current vs previous quarter windows, cut on col_date like WoW/MoM."""
    if col_date is None or col_date not in data_df.columns:
        return None
    if data_df[col_date].dropna().empty:
        return None
    anchor = quarter_anchor(data_df, col_date, selected_quarter, selected_week, selected_month)
    if anchor is None:
        return None
    latest = anchor.normalize()
    current_q_start = pd.Timestamp(year=latest.year, month=3 * ((latest.month - 1) // 3) + 1, day=1)
    previous_q_start = current_q_start - pd.DateOffset(months=3)
    current_q_end = current_q_start + pd.DateOffset(months=3)
    return (
        data_df[col_date].ge(current_q_start) & data_df[col_date].lt(current_q_end),
        data_df[col_date].ge(previous_q_start) & data_df[col_date].lt(current_q_start),
        (current_q_start, current_q_end),
        (previous_q_start, current_q_start),
    )


def render_qoq_section(data_df, fuel_df, col_date, col_client, col_fuel_date, col_fuel_cost,
                       selected_quarter, selected_week, selected_month):
    """Quarter-on-Quarter comparison cards (current quarter vs the previous one)."""
    qoq = qoq_periods(data_df, col_date, selected_quarter, selected_week, selected_month)
    if qoq is None:
        show_empty_chart("No dated records are available for QoQ comparison.")
        return
    current, previous = _period_kpis_with_fuel(
        data_df, *qoq, col_client, fuel_df, col_fuel_date, col_fuel_cost
    )
    _render_period_cards("QoQ", current, previous)


def render_comparison_section(data_df, fuel_df, col_date, col_client, col_fuel_date, col_fuel_cost,
                               selected_week, selected_month):
    periods = comparison_periods(data_df, col_date, selected_week, selected_month)
    if periods is None:
        show_empty_chart("No dated records are available for WoW/MoM comparison.")
        return
    st.markdown(
        """
        <div class='comparison-legend'>
        <span><i class='legend-current'></i>Current period</span>
        <span><i class='legend-previous'></i>Previous period</span>
        <span><i class='legend-increase'></i>Improvement (green)</span>
        <span><i class='legend-decrease'></i>Decline (red) — for TAT and Fuel Cost metrics the colours are reversed: lower is green</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for comparison_name, (current_mask, previous_mask, curr_bounds, prev_bounds) in periods.items():
        current, previous = _period_kpis_with_fuel(
            data_df, current_mask, previous_mask, curr_bounds, prev_bounds,
            col_client, fuel_df, col_fuel_date, col_fuel_cost,
        )
        _render_period_cards(comparison_name, current, previous)


# ============================================================================
# HELPERS — PERFORMANCE TREND
# ============================================================================
def render_performance_trend(data_df):
    trend_df = data_df.dropna(subset=["Created_DT"]).copy()
    if trend_df.empty:
        show_empty_chart("No dated records are available for the performance trend.")
        return
    control_date, control_metric = st.columns(2)
    with control_date:
        date_granularity = st.selectbox("Order Date", ["Week", "Month"], key="performance_trend_date")
    with control_metric:
        metric_label = st.selectbox(
            "Metric",
            ["Delivery Rate", "TAT: Creation to Delivery", "TAT: Dispatch to Delivery", "TAT: Invoice to Dispatch"],
            key="performance_trend_metric",
        )
    if date_granularity == "Week":
        trend_df["Period"] = (
            trend_df["Created_DT"]
            - pd.to_timedelta((trend_df["Created_DT"].dt.weekday - 4) % 7, unit="D")
        ).dt.normalize()
        period_format = "%d %b %Y"
    else:
        trend_df["Period"] = trend_df["Created_DT"].dt.to_period("M").dt.start_time
        period_format = "%b %Y"
    metric_columns = {
        "Delivery Rate": ("Is Delivered", "Delivery Rate (%)"),
        "TAT: Creation to Delivery": ("Creation_Delivery_TAT", "Average TAT (hrs)"),
        "TAT: Dispatch to Delivery": ("Shipping_TAT", "Average TAT (hrs)"),
        "TAT: Invoice to Dispatch": ("Invoice_Dispatch_TAT", "Average TAT (hrs)"),
    }
    value_column, y_axis_title = metric_columns[metric_label]
    trend = (
        trend_df.groupby("Period", as_index=False)[value_column]
        .mean()
        .rename(columns={value_column: "Value"})
        .sort_values("Period")
    )
    if metric_label == "Delivery Rate":
        trend["Value"] = trend["Value"] * 100
    if trend.empty:
        show_empty_chart("No data is available for the selected trend.")
        return
    fig = px.line(
        trend,
        x="Period",
        y="Value",
        markers=True,
        title=f"{metric_label} by Order Date ({date_granularity})",
        labels={"Period": "Order Date", "Value": y_axis_title},
    )
    fig.update_traces(
        line=dict(color=BRAND["blue"], width=3),
        marker=dict(color=BRAND["green"], size=8),
        hovertemplate=(
            f"Order Date: %{{x|{period_format}}}<br>"
            f"{y_axis_title}: %{{y:.1f}}<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False, height=390)
    st.plotly_chart(plotly_theme(fig), use_container_width=True)


# ============================================================================
# DATA LOADING
# ============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def load_data(path=DATA_PATH):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(path, headers=headers, timeout=(15, 180))
    response.raise_for_status()
    source = io.BytesIO(response.content)
    all_sheets = pd.read_excel(source, sheet_name=None)
    # Use the Shipment sheet for orders; fall back to first sheet if not found
    orders_sheet = next(
        (s for n, s in all_sheets.items() if "shipment" in str(n).lower()),
        None,
    )
    orders_df = orders_sheet if orders_sheet is not None else list(all_sheets.values())[0]
    fuel_sheet = next(
        (s for n, s in all_sheets.items() if str(n).strip().lower() == "fuel"),
        None,
    )
    assets_sheet = next(
        (s for n, s in all_sheets.items() if str(n).strip().lower() == "assets"),
        None,
    )
    asset_mapping_sheet = next(
        (s for n, s in all_sheets.items() if "asset mapping" in str(n).strip().lower()),
        None,
    )
    repairs_sheet = next(
        (s for n, s in all_sheets.items() if "repair" in str(n).lower() and "servic" in str(n).lower()),
        None,
    )
    access_sheet = next(
        (s for n, s in all_sheets.items() if "access" in str(n).lower() and "order" in str(n).lower()),
        None,
    )
    if access_sheet is not None and any(str(c).startswith("Unnamed") for c in access_sheet.columns):
        access_sheet = access_sheet.rename(
            columns=dict(zip(access_sheet.columns, access_sheet.iloc[0].astype(str).str.strip()))
        ).iloc[1:].reset_index(drop=True)
    return orders_df, fuel_sheet, assets_sheet, repairs_sheet, access_sheet, asset_mapping_sheet


# ============================================================================
# CUSTOM CSS
# ============================================================================
st.markdown(
    f"""
    <style>
        :root {{
            --ds-blue: {BRAND["blue"]};
            --ds-green: {BRAND["green"]};
            --ds-red: {BRAND["red"]};
            --ds-navy: {BRAND["navy"]};
            --ds-page: {THEME["page"]};
            --ds-surface: {THEME["surface"]};
            --ds-surface-2: {THEME["surface_2"]};
            --ds-text: {THEME["text"]};
            --ds-muted: {THEME["muted"]};
            --ds-border: {THEME["border"]};
            --ds-accent-soft: {THEME["accent_soft"]};
        }}
        .stApp {{
            background:
                radial-gradient(circle at 10% 0%, rgba(22,134,217,.06), transparent 28%),
                radial-gradient(circle at 90% 0%, rgba(16,185,129,.05), transparent 25%),
                var(--ds-page);
            color: var(--ds-text);
        }}
        [data-testid="stHeader"] {{ background: transparent !important; }}
        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }}
        h1, h2, h3, h4, h5, h6,
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        label {{ color: var(--ds-text) !important; }}
        h1 {{
            font-size: clamp(2rem, 3vw, 3rem) !important;
            letter-spacing: -1.5px !important;
            margin-bottom: .25rem !important;
        }}
        h2 {{ font-size: 1.55rem !important; letter-spacing: -.4px !important; }}
        h3 {{ font-size: 1.15rem !important; letter-spacing: -.2px !important; }}
        [data-testid="stCaptionContainer"] {{ color: var(--ds-muted) !important; }}
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #06182A 0%, #0A2339 100%) !important;
            border-right: 1px solid rgba(255,255,255,.08);
        }}
        section[data-testid="stSidebar"] * {{ color: #F1F7FC !important; }}
        section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
        section[data-testid="stSidebar"] .stButton button {{
            background: rgba(255,255,255,.08) !important;
            border: 1px solid rgba(255,255,255,.14) !important;
            border-radius: 10px !important;
        }}
        section[data-testid="stSidebar"] .stButton button {{
            width: 100%;
            font-weight: 700;
        }}
        section[data-testid="stSidebar"] .stButton button:hover {{
            border-color: var(--ds-blue) !important;
            background: rgba(22,134,217,.18) !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            display: flex;
            flex-direction: column;
        }}
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] > div {{
            flex: 1;
        }}
        .sidebar-footer {{
            margin-top: auto;
            padding: 12px 4px 2px 4px;
            border-top: 1px solid rgba(255,255,255,.12);
        }}
        .sidebar-user {{
            display: block;
            color: #9FB8CC !important;
            font-size: .76rem;
            margin: 4px 2px 10px 2px;
        }}
        .sidebar-footer .stButton button {{
            background: transparent !important;
            border: 1px solid rgba(255,255,255,.16) !important;
            border-radius: 9px !important;
            font-size: .82rem !important;
            font-weight: 600 !important;
            padding: .3rem .6rem !important;
            box-shadow: none !important;
            animation: none !important;
            transition: background .15s ease, border-color .15s ease;
        }}
        .sidebar-footer .stButton button:hover {{
            background: rgba(255,255,255,.10) !important;
            border-color: rgba(255,255,255,.3) !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] input {{ display: none; }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{ gap: 4px; }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
            display: flex;
            align-items: center;
            width: 100%;
            min-height: 44px;
            padding: 8px 14px !important;
            border-radius: 10px !important;
            background: transparent !important;
            border: none !important;
            cursor: pointer;
            transition: background .15s ease;
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
            background: rgba(255,255,255,.07) !important;
            border: none !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
            background: rgba(255,255,255,.13) !important;
            border: none !important;
            box-shadow: none !important;
            position: relative;
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked)::before {{
            content: "";
            position: absolute;
            left: 0;
            top: 22%;
            bottom: 22%;
            width: 3px;
            border-radius: 0 3px 3px 0;
            background: #6EC1F2;
        }}
        .sidebar-brand {{
            padding: 6px 0 18px 0;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,.12);
            margin-bottom: 16px;
        }}
        .sidebar-brand img {{
            width: 86%;
            max-height: 84px;
            object-fit: contain;
            margin-bottom: 8px;
        }}
        .sidebar-brand .brand-title {{
            font-size: .76rem;
            font-weight: 800;
            letter-spacing: .14em;
            color: #B9D7EE;
            text-transform: uppercase;
        }}
        .hero {{
            background: linear-gradient(135deg, rgba(22,134,217,.17), rgba(16,185,129,.10));
            border: 1px solid var(--ds-border);
            border-radius: 22px;
            padding: 24px 28px;
            margin-bottom: 18px;
            box-shadow: 0 12px 35px rgba(7,26,45,.08);
        }}
        .hero-top {{
            display: flex;
            align-items: center;
            gap: 18px;
        }}
        .hero-logo {{
            width: 76px;
            height: 76px;
            border-radius: 18px;
            object-fit: contain;
            background: rgba(255,255,255,.92);
            padding: 8px;
            box-shadow: 0 8px 20px rgba(7,26,45,.10);
        }}
        .eyebrow {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 999px;
            background: var(--ds-accent-soft);
            color: #1686D9 !important;
            font-size: .72rem;
            font-weight: 900;
            letter-spacing: .10em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .hero-title {{
            color: var(--ds-text) !important;
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 900;
            margin: 0;
        }}
        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 7px 11px;
            border-radius: 999px;
            background: rgba(16,185,129,.12);
            color: #10B981 !important;
            font-weight: 800;
            font-size: .76rem;
            margin-top: 12px;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10B981;
            box-shadow: 0 0 0 4px rgba(16,185,129,.12);
        }}
        .kpi-card {{
            position: relative;
            overflow: hidden;
            height: auto;
            min-height: 118px;
            box-sizing: border-box;
            background: var(--ds-surface);
            border: 1px solid var(--ds-border);
            border-radius: 17px;
            padding: 17px 18px 15px 18px;
            box-shadow: 0 8px 25px rgba(7,26,45,.07);
            transition: transform .18s ease, box-shadow .18s ease;
        }}
        .kpi-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 14px 32px rgba(7,26,45,.12);
        }}
        .kpi-card::before {{
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 5px;
            background: var(--kpi-accent);
        }}
        .kpi-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}
        .kpi-label {{
            color: var(--ds-muted) !important;
            font-size: .73rem;
            font-weight: 900;
            letter-spacing: .06em;
            text-transform: uppercase;
        }}
        .kpi-icon {{
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            background: var(--kpi-soft);
            font-size: 1rem;
        }}
        .kpi-value {{
            color: var(--ds-text) !important;
            font-size: clamp(1.35rem, 1.7vw, 1.72rem);
            font-weight: 900;
            line-height: 1.05;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-top: 11px;
        }}
        .kpi-weekly {{
            margin-top: 10px;
            border-top: 1px dashed var(--ds-border);
            padding-top: 7px;
        }}
        .kpi-weekly-row {{
            display: flex;
            justify-content: space-between;
            gap: 8px;
            color: var(--ds-muted) !important;
            font-size: .72rem;
            font-weight: 700;
        }}
        .kpi-delta {{
            font-size: .8rem;
            font-weight: 900;
            margin-top: 4px;
        }}
        .section-head {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin: 20px 0 8px 0;
        }}
        .section-title {{
            color: var(--ds-text) !important;
            font-size: 1.05rem;
            font-weight: 900;
            margin: 0;
        }}
        .comparison-legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            color: var(--ds-muted);
            font-size: .76rem;
            margin: 4px 0 12px 0;
        }}
        .comparison-legend span {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .comparison-legend i {{
            width: 11px;
            height: 11px;
            display: inline-block;
            border-radius: 2px;
        }}
        .legend-current {{ background: var(--ds-blue); }}
        .legend-previous {{ background: #587896; }}
        .legend-increase {{ background: var(--ds-green); }}
        .legend-decrease {{ background: var(--ds-red); }}
        .comparison-period {{
            margin: 14px 0 8px 0 !important;
            color: var(--ds-text) !important;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 12px;
        }}
        .comparison-card {{
            background: var(--ds-surface);
            border: 1px solid var(--ds-border);
            border-radius: 12px;
            padding: 14px;
        }}
        .comparison-title {{
            color: var(--ds-text);
            font-size: .78rem;
            font-weight: 800;
            min-height: 2.2em;
        }}
        .comparison-values {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 12px;
        }}
        .comparison-values div {{
            display: flex;
            flex-direction: column;
            gap: 3px;
        }}
        .comparison-label {{
            color: var(--ds-muted);
            font-size: .68rem;
        }}
        .comparison-values strong {{
            color: var(--ds-text);
            font-size: 1rem;
        }}
        .comparison-change {{
            font-size: .72rem;
            font-weight: 800;
            margin-top: 12px;
        }}
        .comparison-change.increase {{ color: var(--ds-green); }}
        .comparison-change.decrease {{ color: var(--ds-red); }}
        @media (max-width: 900px) {{
            .comparison-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}
        @media (max-width: 520px) {{
            .comparison-grid {{ grid-template-columns: 1fr; }}
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background: transparent;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: var(--ds-muted) !important;
            background: var(--ds-surface-2);
            border: 1px solid var(--ds-border);
            border-radius: 11px;
            padding: 9px 17px;
            font-weight: 800;
        }}
        .stTabs [aria-selected="true"] {{
            background: #1686D9 !important;
            color: #FFFFFF !important;
            border-color: #1686D9 !important;
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--ds-border);
            border-radius: 14px;
            overflow: hidden;
        }}
        /* Smaller fonts for the top filter bar only — the filter columns are the
           element container immediately after the marked Filters heading. */
        [data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] .filters-marker) + [data-testid="stElementContainer"] [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p {{
            font-size: .72rem !important;
        }}
        [data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] .filters-marker) + [data-testid="stElementContainer"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
            font-size: .78rem;
            min-height: 32px;
        }}
        [data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] .filters-marker) + [data-testid="stElementContainer"] [data-testid="stSelectbox"] div[data-baseweb="select"] span {{
            font-size: .78rem;
        }}
        [data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] .filters-marker) + [data-testid="stElementContainer"] .stButton button {{
            font-size: .74rem !important;
            padding: .3rem .5rem !important;
            min-height: 32px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# LOGIN SCREEN
# ============================================================================
configured_username, configured_password = get_login_credentials()
st.session_state.setdefault("dashboard_authenticated", False)

if not st.session_state["dashboard_authenticated"]:
    _login_bg_path = os.path.join(os.path.dirname(__file__), "login_bg.png")
    try:
        with open(_login_bg_path, "rb") as _bg_file:
            _login_bg_b64 = base64.b64encode(_bg_file.read()).decode("ascii")
    except OSError:
        _login_bg_b64 = ""
    if _login_bg_b64:
        st.markdown(
            f"""
            <style>
                .stApp {{
                    background-image: url("data:image/png;base64,{_login_bg_b64}");
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                }}
                [data-testid="stFormSubmitButton"] button,
                .stForm button[kind="primary"],
                .stForm button[kind="primary"]:hover {{
                    background-color: #1686D9 !important;
                    border-color: #1686D9 !important;
                    color: #FFFFFF !important;
                }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    st.markdown(
        "<div style='text-align:center;padding-top:7vh'>"
        "<div style='font-size:1.8rem;font-weight:700'>DrugStoc Logistics</div>"
        "<div style='color:#4A6178'>Dashboard sign in</div></div>",
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.image(COVER_LOGO_URL, width=190)
        if not configured_username or not configured_password:
            st.error(
                "Login is not configured. Set DASHBOARD_USERNAME and "
                "DASHBOARD_PASSWORD or add an [auth] section to Streamlit secrets."
            )
        else:
            with st.form("dashboard_login"):
                entered_username = st.text_input("Username", key="login_username")
                entered_password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Sign in", type="primary")
            if submitted:
                username_matches = hmac.compare_digest(entered_username, str(configured_username))
                password_matches = hmac.compare_digest(entered_password, str(configured_password))
                if username_matches and password_matches:
                    st.session_state["dashboard_authenticated"] = True
                    st.session_state["authenticated_user"] = entered_username
                    st.rerun()
                st.error("Incorrect username or password.")
    st.stop()


# ============================================================================
# SIDEBAR — HEADER & NAVIGATION
# ============================================================================
st.sidebar.markdown(
    f"""
    <div class="sidebar-brand">
        <img src="{COVER_LOGO_URL}" alt="DrugStoc logo"/>
        <div class="brand-title">Pharma Logistics Intelligence</div>
    </div>
    """,
    unsafe_allow_html=True,
)
PAGES = [
    ":material/insights: BI Summary",
    ":material/slides: Weekly meeting Presentation",
    ":material/local_shipping: Vehicles & Orders",
    ":material/oil_barrel: Fueling Cost",
    ":material/badge: Captain Efficiency",
    ":material/fact_check: Audit Data",
    ":material/receipt_long: Access Orders",
    ":material/handyman: Asset Management",
    ":material/savings: Cost Control",
    ":material/lightbulb: Recommendations",
]
selected_page = st.sidebar.radio("Dashboard pages", PAGES, label_visibility="collapsed")

with st.sidebar.container(key="sidebar_footer"):
    st.markdown(
        f"<span class='sidebar-user'>Signed in as "
        f"{st.session_state.get('authenticated_user', '')}</span>",
        unsafe_allow_html=True,
    )
    sign_out_col, refresh_col = st.columns(2, gap="small")
    with sign_out_col:
        if st.button("Sign out", key="dashboard_sign_out"):
            st.session_state["dashboard_authenticated"] = False
            st.session_state.pop("authenticated_user", None)
            st.rerun()
    with refresh_col:
        if st.button("Refresh data", key="dashboard_refresh"):
            st.cache_data.clear()
            st.rerun()


# ============================================================================
# DATA LOADING
# ============================================================================
try:
    with st.spinner("🔄 Refreshing live logistics data..."):
        df_raw, fuel_raw, assets_raw, repairs_raw, access_raw, asset_mapping_raw = load_data(DATA_PATH)
except Exception as exc:
    st.error("Unable to load the logistics workbook.")
    st.info("Verify the live link contains valid Excel tables.")
    with st.expander("Technical details"):
        st.code(str(exc))
    st.stop()


# ============================================================================
# DATA PROCESSING
# ============================================================================
df_raw = df_raw.copy()
df_raw.columns = [str(c).strip() for c in df_raw.columns]

# Column mapping
col_client = find_col(df_raw, ["Client Name", "Client", "Customer Name", "Pharmacy", "Hospital"])
col_so = find_col(df_raw, ["SO", "Sales Order", "SO Number"])
col_value = find_col(df_raw, ["Order Value", "Value", "Amount", "Sales Value", "Total Value"])
col_qty = find_col(df_raw, ["N0 OF CTN'S", "NO OF CTN'S", "Qty CTN", "Quantity", "CTN"])
col_date = find_col(df_raw, ["Date Column", "Date", "Created Date", "Creation Date", "Order Date"])
col_created_date = find_col(df_raw, ["Created Date", "Created At", "Creation Date", "Order Created At"])
col_create_time = find_col(df_raw, ["Created Time", "Creation Time", "Order Time"])
col_region = find_col(df_raw, ["Region", "Zone", "State", "Territory"])
col_status = find_col(df_raw, ["STATUS"], exact_only=True) or find_col(df_raw, ["STATUS"])
col_captain = find_col(df_raw, ["Captain", "Rider", "Driver", "Captain Name"])
col_vehicle = find_col(df_raw, ["Vehicle Plate No", "Plate Number", "Plate No", "Vehicle", "Vehicle Reg No", "Reg No", "Truck No", "Van Number", "Vehicle No"])
col_order_type = find_col(df_raw, ["Order Type", "Type", "Category"])
col_ship = find_col(df_raw, ["Ship Date", "Dispatch Date", "Pickup Date"])
col_dispatch_time = find_col(df_raw, ["Dispatch Time", "Ship Time", "Time Dispatched"])
col_invoice = find_col(df_raw, ["Invoice Date", "Invoiced Date", "INV Date"])
col_deliv = find_col(df_raw, ["Delivery Date", "Delivered Date"])
col_delivery_time = find_col(df_raw, ["Delivery Time", "Time Delivered"])

if not col_client:
    st.error("Unable to identify the Client column automatically in the dataset.")
    st.stop()

# Fallback columns
if not col_value:
    df_raw["__OrderValue"] = 0.0
    col_value = "__OrderValue"
if not col_qty:
    df_raw["__Quantity"] = 0.0
    col_qty = "__Quantity"
if not col_region:
    df_raw["__Region"] = "Unassigned"
    col_region = "__Region"

df = df_raw.copy()

# Date handling
if col_date and col_date in df.columns:
    df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
    _wk_num, _wk_start, _wk_year = fri_thu_week(df[col_date])
    df["Week"] = _wk_num.fillna(0).astype(int)
    df["Year"] = df[col_date].dt.year.fillna(0).astype(int)
    df["Month"] = df[col_date].dt.month.fillna(0).astype(int)
    df["Month Label"] = df[col_date].dt.strftime("%B %Y").fillna("Unassigned Date")
    df["Quarter Label"] = (
        df[col_date].dt.to_period("Q").astype(str)
        .str.replace(r"^(\d{4})Q(\d)$", r"Q\2 \1", regex=True)
        .fillna("Unassigned Date")
    )
    df["Week Label"] = week_label_with_span(df["Week"], _wk_year, _wk_start)
else:
    df["Month Label"] = "Unassigned Date"
    df["Week Label"] = "Unassigned Date"
    df["Quarter Label"] = "Unassigned Date"

df[col_value] = pd.to_numeric(df[col_value], errors="coerce").fillna(0)
df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(0)

# Timestamps
df["Created_DT"] = build_timestamp(df, col_created_date or col_date, col_create_time)
df["Delivery_DT"] = build_timestamp(df, col_deliv, col_delivery_time)
dispatch_date_col = col_ship if col_ship and col_ship in df.columns else col_date
df["Dispatch_DT"] = build_timestamp(df, dispatch_date_col, col_dispatch_time)
df["Invoice_DT"] = build_timestamp(df, col_invoice, None)

# TAT calculations
df["Creation_Delivery_TAT"] = ((df["Delivery_DT"] - df["Created_DT"]).dt.total_seconds() / 3600.0)
df["Creation_Delivery_TAT"] = df["Creation_Delivery_TAT"].apply(lambda x: x if pd.notna(x) and x >= 0 else np.nan)
df["Shipping_TAT"] = ((df["Delivery_DT"] - df["Dispatch_DT"]).dt.total_seconds() / 3600.0)
df["Shipping_TAT"] = df["Shipping_TAT"].apply(lambda x: x if pd.notna(x) and x >= 0 else np.nan)
df["Invoice_Dispatch_TAT"] = ((df["Dispatch_DT"] - df["Invoice_DT"]).dt.total_seconds() / 3600.0)
df["Invoice_Dispatch_TAT"] = df["Invoice_Dispatch_TAT"].apply(lambda x: x if pd.notna(x) and x >= 0 else np.nan)
df["Creation_Invoice_TAT"] = ((df["Invoice_DT"] - df["Created_DT"]).dt.total_seconds() / 3600.0)
df["Creation_Invoice_TAT"] = df["Creation_Invoice_TAT"].apply(lambda x: x if pd.notna(x) and x >= 0 else np.nan)
df["Invoice_Delivery_TAT"] = ((df["Delivery_DT"] - df["Invoice_DT"]).dt.total_seconds() / 3600.0)
df["Invoice_Delivery_TAT"] = df["Invoice_Delivery_TAT"].apply(lambda x: x if pd.notna(x) and x >= 0 else np.nan)

# Status mapping
if col_status and col_status in df.columns:
    df[col_status] = df[col_status].astype(str).str.strip().str.title()
    DELIVERED_LABELS = {"Delivered", "Complete", "Completed", "Successful"}
    df["Is Delivered"] = df[col_status].isin(DELIVERED_LABELS)
else:
    df[col_status] = "Unassigned"
    df["Is Delivered"] = False

# Year filter — keyed off the Fri-Thu week label year so no week appears
# under the previous year (e.g. W52 - 2025 for early-January shipments).
if col_date and col_date in df.columns:
    df = df.loc[_wk_year == FILTER_YEAR].copy()


# ============================================================================
# FUEL SHEET PROCESSING
# ============================================================================
fuel = None
col_fuel_date = None
col_fuel_cost = None
col_fuel_captain = None
col_fuel_plate = None
col_fuel_model = None

if fuel_raw is not None and not fuel_raw.empty:
    fuel = fuel_raw.copy()
    fuel.columns = [str(c).strip() for c in fuel.columns]
    col_fuel_date = find_col(fuel, ["DATE", "Date", "Fueling Date"])
    col_fuel_cost = find_col(fuel, ["Fueling/Ltr", "Fueling", "Fueling Cost", "Amount", "Cost"])
    col_fuel_captain = find_col(fuel, ["Captains Name", "Captain", "Captain Name", "Rider"])
    col_fuel_plate = find_col(fuel, ["PlateNumber", "Plate Number", "Plate No", "Vehicle Plate No"])
    col_fuel_model = find_col(fuel, ["Model", "Vehicle Model"])
    if col_fuel_date and col_fuel_date in fuel.columns:
        fuel[col_fuel_date] = pd.to_datetime(fuel[col_fuel_date], errors="coerce")
        fuel["Fuel Month Label"] = fuel[col_fuel_date].dt.strftime("%B %Y").fillna("Unassigned Date")
        fuel["Fuel Quarter Label"] = (
            fuel[col_fuel_date].dt.to_period("Q").astype(str)
            .str.replace(r"^(\d{4})Q(\d)$", r"Q\2 \1", regex=True)
            .fillna("Unassigned Date")
        )
        _fwk_num, _fwk_start, _fwk_year = fri_thu_week(fuel[col_fuel_date])
        fuel["Fuel Week"] = _fwk_num.fillna(0).astype(int)
        fuel["Fuel Year"] = _fwk_start.dt.year.fillna(0).astype(int)
        fuel["Fuel Week Label"] = week_label_with_span(fuel["Fuel Week"], _fwk_year, _fwk_start)
        fuel = fuel.loc[_fwk_year == FILTER_YEAR].copy()
    if col_fuel_cost and col_fuel_cost in fuel.columns:
        fuel[col_fuel_cost] = pd.to_numeric(fuel[col_fuel_cost], errors="coerce")


# ============================================================================
# ASSETS SHEET PROCESSING
# ============================================================================
plate_to_area = {}
assets_registry = None
col_assets_type = None
if assets_raw is not None and not assets_raw.empty:
    assets_df = assets_raw.copy()
    if assets_df.columns.astype(str).str.startswith("Unnamed").mean() > 0.5:
        assets_df.columns = [str(c).strip() for c in assets_df.iloc[0]]
        assets_df = assets_df.iloc[1:].reset_index(drop=True)
    else:
        assets_df.columns = [str(c).strip() for c in assets_df.columns]
    col_assets_plate = find_col(
        assets_df,
        ["PlateNumber", "Plate Number", "Plate No", "Vehicle Plate No", "Vehicle Reg No", "Reg No"],
    )
    col_assets_area = find_col(
        assets_df,
        ["Coverage Area", "Coverage", "Area", "Zone", "Region", "Territory", "Location"],
    )
    col_assets_type = find_col(
        assets_df,
        ["Asset Type", "Type", "Vehicle Type", "Vehicle Category", "Category", "Asset Category"],
    )
    if col_assets_plate and col_assets_area:
        pairs = (
            assets_df[[col_assets_plate, col_assets_area]]
            .dropna(subset=[col_assets_plate])
            .assign(_plate=lambda x: x[col_assets_plate].astype(str).str.strip().str.upper())
        )
        pairs = pairs[(pairs["_plate"] != "") & pairs[col_assets_area].notna()]
        plate_to_area = dict(zip(pairs["_plate"], pairs[col_assets_area].astype(str).str.strip()))
    assets_registry = assets_df


# ============================================================================
# REPAIRS AND SERVICING SHEET PROCESSING
# ============================================================================
repairs = None
col_repair_date = None
col_repair_cost = None
col_engine_cost = None
col_repair_desc = None
col_repair_plate = None
col_repair_area = None

if repairs_raw is not None and not repairs_raw.empty:
    repairs = repairs_raw.copy()
    repairs.columns = [str(c).strip() for c in repairs.columns]
    col_repair_date = find_col(repairs, ["Date", "DATE"])
    col_repair_plate = find_col(repairs, ["PLATENUMBER", "PlateNumber", "Plate Number", "Plate No"])
    col_repair_area = find_col(repairs, ["AREA COVERED", "Area Covered", "Coverage Area", "Coverage"])
    col_repair_cost = find_col(
        repairs,
        [
            "MAINTAINANCE & REPAIR", "Maintenance & Repair", "Maintenance and Repair",
            "Repair and Maintenance", "Repairs and Maintenance", "Maintainance",
            "Maintenance", "Repair",
        ],
    )
    col_engine_cost = find_col(
        repairs,
        ["Servicing", "Servcing", "Engine Servicing", "Engine Oil", "Cost of Engine Oil"],
    )
    col_repair_desc = find_col(
        repairs,
        ["DESCRIPTION", "Description", "REPAIRS", "Repairs", "WORK DONE", "Work Done",
         "ITEM", "Particulars", "Details"],
    )
    if col_repair_date and col_repair_date in repairs.columns:
        repairs[col_repair_date] = pd.to_datetime(repairs[col_repair_date], errors="coerce")
        repairs["Repair Month Label"] = repairs[col_repair_date].dt.strftime("%B %Y").fillna("Unassigned Date")
        repairs["Repair Quarter Label"] = (
            repairs[col_repair_date].dt.to_period("Q").astype(str)
            .str.replace(r"^(\d{4})Q(\d)$", r"Q\2 \1", regex=True)
            .fillna("Unassigned Date")
        )
        _rwk_num, _rwk_start, _rwk_year = fri_thu_week(repairs[col_repair_date])
        repairs["Repair Week"] = _rwk_num.fillna(0).astype(int)
        repairs["Repair Year"] = _rwk_start.dt.year.fillna(0).astype(int)
        repairs["Repair Week Label"] = week_label_with_span(repairs["Repair Week"], _rwk_year, _rwk_start)
        repairs = repairs.loc[_rwk_year == FILTER_YEAR].copy()
    for cost_col in (col_repair_cost, col_engine_cost):
        if cost_col and cost_col in repairs.columns:
            repairs[cost_col] = pd.to_numeric(repairs[cost_col], errors="coerce")
    # Coverage recheck: add plates from repairs tab that Assets sheet missed
    if col_repair_plate and col_repair_area:
        rpairs = (
            repairs[[col_repair_plate, col_repair_area]]
            .dropna(subset=[col_repair_plate])
            .assign(_plate=lambda x: x[col_repair_plate].astype(str).str.strip().str.upper())
        )
        rpairs = rpairs[(rpairs["_plate"] != "") & rpairs[col_repair_area].notna()]
        for plate, area in zip(rpairs["_plate"], rpairs[col_repair_area].astype(str).str.strip()):
            plate_to_area.setdefault(plate, area)


# ============================================================================
# ACCESS ORDERS (HMO last-mile deliveries)
# ============================================================================
ACCESS_COL_SO = "SALES ORDER [SO]"
access = None
if access_raw is not None and not access_raw.empty:
    access = access_raw.copy()
    access.columns = [str(c).strip() for c in access.columns]
    for expected in ("SALES ORDER [SO]", "DELIVERY STATUS", "DELIVERY DATE", "DELIVERY TIME", "TIME OUT", "PA CODE DATE"):
        if expected not in access.columns:
            access = None
            break

if access is not None:
    access["SO"] = access[ACCESS_COL_SO].fillna("").astype(str).str.strip()
    access = access[access["SO"] != ""].copy()
    access["Status"] = access["DELIVERY STATUS"].fillna("").astype(str).str.strip()
    access["HMO"] = access["HMO"].fillna("").astype(str).str.strip().replace({"": "Unassigned"})
    _reason = access["DISPATCH REMARKS"].fillna("").astype(str).str.strip()
    access["Return Reason"] = _reason.where(_reason != "")

    # TAT: dispatch (TIME OUT) to delivery, on the delivery date; deliveries past
    # midnight roll into the next day.
    access["Delivery_DT"] = build_timestamp(access, "DELIVERY DATE", "DELIVERY TIME")
    access["Dispatch_DT"] = build_timestamp(access, "DELIVERY DATE", "TIME OUT")
    past_midnight = access["Delivery_DT"] < access["Dispatch_DT"]
    access.loc[past_midnight, "Delivery_DT"] = access.loc[past_midnight, "Delivery_DT"] + pd.Timedelta(days=1)
    access["TAT_Hrs"] = (access["Delivery_DT"] - access["Dispatch_DT"]).dt.total_seconds() / 3600.0
    access["TAT_Hrs"] = access["TAT_Hrs"].apply(lambda x: x if pd.notna(x) and x >= 0 else np.nan)

    # Attempts: rows per SO ordered by delivery time (PA code date as fallback).
    access["_attempt_order"] = access["Delivery_DT"].fillna(
        pd.to_datetime(access.get("PA CODE DATE"), errors="coerce")
    )
    access = access.sort_values(["SO", "_attempt_order"], kind="mergesort")
    access["Attempt"] = access.groupby("SO").cumcount() + 1
    # A re-attempt is any trip after a failed (or still re-attempting) trip for
    # the same SO — bulk orders delivered in several scheduled trips only count
    # once a trip has actually failed.
    _prior_failures = access.groupby("SO")["Status"].transform(
        lambda statuses: statuses.isin({"Failed", "Re-attempting"}).cumsum().shift(fill_value=0)
    )
    access["Reattempt"] = _prior_failures.gt(0) & access["Attempt"].ge(2)
    _last_status = access.groupby("SO")["Status"].last()
    access["Returned_Order"] = access["SO"].isin(set(_last_status[_last_status == "Returned"].index))

    # Fri-Thu reporting weeks on delivery date (PA code date as fallback).
    _aw = access["_attempt_order"]
    _awk_num, _awk_start, _awk_year = fri_thu_week(_aw)
    access["Week"] = _awk_num.fillna(0).astype(int)
    access["Year"] = _awk_start.dt.year.fillna(0).astype(int)
    access["Week Label"] = week_label_with_span(access["Week"], _awk_year, _awk_start)
    access["Month Label"] = _aw.dt.strftime("%B %Y").fillna("Unassigned Date")
    access = access.loc[access["Year"] == FILTER_YEAR].copy()


# ============================================================================
# FILTER OPTIONS
# ============================================================================
month_labels = set(df["Month Label"].dropna().astype(str))
week_labels = set(df["Week Label"].dropna().astype(str))
quarter_labels = set(df["Quarter Label"].dropna().astype(str))
for date_view, month_label_col, week_label_col in (
    (fuel, "Fuel Month Label", "Fuel Week Label"),
    (repairs, "Repair Month Label", "Repair Week Label"),
):
    if date_view is not None:
        if month_label_col in date_view.columns:
            month_labels.update(date_view[month_label_col].dropna().astype(str))
        if week_label_col in date_view.columns:
            week_labels.update(date_view[week_label_col].dropna().astype(str))
        if "Fuel Quarter Label" in date_view.columns:
            quarter_labels.update(date_view["Fuel Quarter Label"].dropna().astype(str))
        if "Repair Quarter Label" in date_view.columns:
            quarter_labels.update(date_view["Repair Quarter Label"].dropna().astype(str))

month_options = ["All Months"] + sorted(
    month_labels,
    key=lambda label: pd.to_datetime(label, format="%B %Y", errors="coerce"),
    reverse=True,
)


def _quarter_sort_key(label):
    try:
        q, year = label.split()
        return pd.Period(f"{year}{q}", freq="Q")
    except (ValueError, TypeError):
        return pd.Period("1970Q1", freq="Q")


quarter_options = ["All Quarters"] + sorted(quarter_labels, key=_quarter_sort_key, reverse=True)
week_options = ["All Weeks"] + sorted(week_labels, reverse=True)
region_options = ["All Regions"] + sorted(df[col_region].dropna().astype(str).unique().tolist(), reverse=True)
status_options = ["All Statuses"] + sorted(df[col_status].dropna().unique().tolist(), reverse=True)
order_type_options = ["All Order Types"]
if col_order_type and col_order_type in df.columns:
    order_type_options += sorted(df[col_order_type].dropna().astype(str).str.strip().unique().tolist(), reverse=True)


def clear_filter_selections():
    st.session_state["filter_quarter"] = "All Quarters"
    st.session_state["filter_month"] = "All Months"
    st.session_state["filter_week"] = "All Weeks"
    st.session_state["filter_region"] = "All Regions"
    st.session_state["filter_status"] = "All Statuses"
    st.session_state["filter_order_type"] = "All Order Types"


# ============================================================================
# HERO HEADER
# ============================================================================
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-top">
            <img class="hero-logo" src="{COVER_LOGO_URL}" alt="DrugStoc logo"/>
            <div>
                <div class="eyebrow">Healthcare Supply Chain Monitor</div>
                <div class="hero-title">DrugStoc Pharma Logistics Dashboard</div>
                <div class="status-pill">
                    <span class="status-dot"></span>
                    Live operational view
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# TOP FILTER BAR
# ============================================================================
st.markdown(
    f"""
    <div class="section-head filters-marker" style="margin-top:0">
        <div class="section-title">🎛️ Filters</div>
    </div>
    """,
    unsafe_allow_html=True,
)
f_quarter, f_month, f_week, f_region, f_status, f_type, f_clear = st.columns([1, 1.1, 1.1, 1, 1.2, 1.1, 0.8])
with f_quarter:
    selected_quarter = st.selectbox("Quarter", quarter_options, key="filter_quarter")
with f_month:
    selected_month = st.selectbox("Month", month_options, key="filter_month")
with f_week:
    selected_week = st.selectbox("Week", week_options, key="filter_week")
with f_region:
    selected_region = st.selectbox("Region / Hub", region_options, key="filter_region")
with f_status:
    selected_status = st.selectbox("Delivery Status", status_options, key="filter_status")
with f_type:
    selected_order_type = st.selectbox("Order Type", order_type_options, key="filter_order_type")
with f_clear:
    st.button("Clear filters", on_click=clear_filter_selections, key="clear_filter_selections", type="primary")

# Apply filters
filtered = df.copy()
if selected_quarter != "All Quarters":
    filtered = filtered[filtered["Quarter Label"] == selected_quarter]
if selected_month != "All Months":
    filtered = filtered[filtered["Month Label"] == selected_month]
if selected_week != "All Weeks":
    filtered = filtered[filtered["Week Label"] == selected_week]
if selected_region != "All Regions":
    filtered = filtered[filtered[col_region].astype(str) == selected_region]
if selected_status != "All Statuses":
    filtered = filtered[filtered[col_status] == selected_status]
if selected_order_type != "All Order Types" and col_order_type:
    filtered = filtered[filtered[col_order_type].astype(str).str.strip() == selected_order_type]

# Comparison base (excludes Month/Week slicers)
comparison_base = df.copy()
if selected_region != "All Regions":
    comparison_base = comparison_base[comparison_base[col_region].astype(str) == selected_region]
if selected_status != "All Statuses":
    comparison_base = comparison_base[comparison_base[col_status] == selected_status]
if selected_order_type != "All Order Types" and col_order_type:
    comparison_base = comparison_base[comparison_base[col_order_type].astype(str).str.strip() == selected_order_type]

# Fuel view (respects Quarter/Month/Week only)
fuel_view = fuel.copy() if fuel is not None else None
if fuel_view is not None:
    if selected_quarter != "All Quarters" and "Fuel Quarter Label" in fuel_view.columns:
        fuel_view = fuel_view[fuel_view["Fuel Quarter Label"] == selected_quarter]
    if selected_month != "All Months" and "Fuel Month Label" in fuel_view.columns:
        fuel_view = fuel_view[fuel_view["Fuel Month Label"] == selected_month]
    if selected_week != "All Weeks" and "Fuel Week Label" in fuel_view.columns:
        fuel_view = fuel_view[fuel_view["Fuel Week Label"] == selected_week]


# ============================================================================
# PAGE ROUTING
# ============================================================================

# ---------------------------------------------------------------------------
# PAGE: WEEKLY MEETING PRESENTATION
# ---------------------------------------------------------------------------
if selected_page == ":material/slides: Weekly meeting Presentation":
    section_header("Weekly Meeting Presentation")

    _base = comparison_base
    _anchor = comparison_anchor(_base, col_date, selected_week, selected_month) if col_date else None
    if _anchor is None and col_date and col_date in _base.columns and _base[col_date].notna().any():
        _anchor = _base[col_date].max()
    if _anchor is None:
        st.info("No dated shipment records are available to build the weekly presentation.")
        st.stop()

    # Fri-Thu reporting weeks
    _ref = _anchor.normalize()
    _wk_start = _ref - pd.Timedelta(days=(_ref.weekday() - 4) % 7)
    _prev_start = _wk_start - pd.Timedelta(days=7)
    _wk_end = _wk_start + pd.Timedelta(days=6)
    _pwk_end = _prev_start + pd.Timedelta(days=6)
    _wk_num = int(_wk_start.isocalendar()[1])
    _pwk_num = int(_prev_start.isocalendar()[1])
    week_title = f"Week {_wk_num}: {_wk_start.day}\u2013{_wk_end.day} {_wk_end:%B %Y}"
    prev_title = f"Week {_pwk_num}: {_prev_start.day}\u2013{_pwk_end.day} {_pwk_end:%B %Y}"
    curr_col = f"W{_wk_num:02d} / {_wk_start.day}\u2013{_wk_end.day} {_wk_end:%b}"
    prev_col = f"W{_pwk_num:02d} / {_prev_start.day}\u2013{_pwk_end.day} {_pwk_end:%b}"

    def _in_week(frame, date_col, start):
        if frame is None or not date_col or date_col not in frame.columns:
            return frame.iloc[0:0]
        return frame[frame[date_col].ge(start) & frame[date_col].lt(start + pd.Timedelta(days=7))]

    _curr_orders = _in_week(_base, col_date, _wk_start)
    _prev_orders = _in_week(_base, col_date, _prev_start)

    def _tat_change(curr_v, prev_v):
        if curr_v is None or pd.isna(curr_v):
            return "No record"
        if prev_v is None or pd.isna(prev_v) or prev_v == 0:
            return "No comparison"
        pct = (curr_v - prev_v) / abs(prev_v) * 100
        if abs(pct) < 0.5:
            return "Broadly flat"
        return f"{abs(pct):.0f}% {'less' if pct < 0 else 'more'} time"

    def _hrs(value):
        return f"{value:.1f} hours" if value is not None and pd.notna(value) else "No record"

    # --- Slide 2 table: dispatch -> delivery TAT by programme ---------------
    if col_order_type and col_order_type in _base.columns:
        _progs = sorted(_base[col_order_type].dropna().astype(str).str.strip().unique())
    else:
        _progs = None
    programme_rows = []
    for prog in (_progs if _progs else ["All orders"]):
        if _progs:
            c_df = _curr_orders[_curr_orders[col_order_type].astype(str).str.strip() == prog]
            p_df = _prev_orders[_prev_orders[col_order_type].astype(str).str.strip() == prog]
        else:
            c_df, p_df = _curr_orders, _prev_orders
        c_tat = c_df["Shipping_TAT"].mean() if len(c_df) else None
        p_tat = p_df["Shipping_TAT"].mean() if len(p_df) else None
        c_n = int(c_df["Shipping_TAT"].notna().sum()) if len(c_df) else 0
        p_n = int(p_df["Shipping_TAT"].notna().sum()) if len(p_df) else 0
        programme_rows.append(
            {
                "Programme": prog,
                prev_col: _hrs(p_tat),
                curr_col: _hrs(c_tat),
                "Change in time": _tat_change(c_tat, p_tat),
                "Deliveries timed (prev / curr)": f"{p_n} / {c_n}",
            }
        )

    # --- Slide 3 table: stage turnaround ------------------------------------
    stage_defs = [
        ("Order to invoice", "Creation_Invoice_TAT"),
        ("Invoice to dispatch", "Invoice_Dispatch_TAT"),
        ("Dispatch to delivery", "Shipping_TAT"),
        ("Order to delivery", "Creation_Delivery_TAT"),
    ]
    stage_rows = []
    for step, col_tat in stage_defs:
        c_v = _curr_orders[col_tat].mean() if len(_curr_orders) else None
        p_v = _prev_orders[col_tat].mean() if len(_prev_orders) else None
        stage_rows.append(
            {
                "Step": step,
                prev_col: _hrs(p_v),
                curr_col: _hrs(c_v),
                "Change in time": _tat_change(c_v, p_v),
            }
        )
    stage_samples_curr = int(
        _curr_orders[[c for _, c in stage_defs]].notna().all(axis=1).sum()
    ) if len(_curr_orders) else 0
    stage_samples_prev = int(
        _prev_orders[[c for _, c in stage_defs]].notna().all(axis=1).sum()
    ) if len(_prev_orders) else 0

    # --- Slide 4: fuel -------------------------------------------------------
    def _fuel_week(start):
        if fuel is None or not col_fuel_date or not col_fuel_cost:
            return None
        return fuel[fuel[col_fuel_date].ge(start) & fuel[col_fuel_date].lt(start + pd.Timedelta(days=7))]

    _fuel_curr = _fuel_week(_wk_start)
    _fuel_prev = _fuel_week(_prev_start)
    fuel_total = float(_fuel_curr[col_fuel_cost].sum()) if _fuel_curr is not None and len(_fuel_curr) else 0.0
    fuel_prev_total = float(_fuel_prev[col_fuel_cost].sum()) if _fuel_prev is not None and len(_fuel_prev) else 0.0
    fuel_entries = int(_fuel_curr[col_fuel_cost].notna().sum()) if _fuel_curr is not None else 0
    fuel_vehicles = (
        int(_fuel_curr[col_fuel_plate].dropna().astype(str).str.strip().str.upper().nunique())
        if _fuel_curr is not None and col_fuel_plate else 0
    )
    fuel_pct = pct_change(fuel_total, fuel_prev_total) if fuel_prev_total else None
    fuel_top = []
    if _fuel_curr is not None and len(_fuel_curr) and col_fuel_cost and col_fuel_plate:
        _ft = (
            _fuel_curr.dropna(subset=[col_fuel_plate])
            .assign(_p=lambda x: x[col_fuel_plate].astype(str).str.strip().str.upper())
            .groupby("_p")[col_fuel_cost].sum()
            .sort_values(ascending=False)
            .head(10)
        )
        fuel_top = [(plate, float(amt)) for plate, amt in _ft.items() if amt > 0]

    # --- Slide 5: repairs ----------------------------------------------------
    repair_weekly = []
    _rp_prev = None
    for _off in (2, 1, 0):
        _start = _wk_start - pd.Timedelta(days=7 * _off)
        if repairs is None or not col_repair_date:
            _total = 0.0
        else:
            _sub = repairs[repairs[col_repair_date].ge(_start) & repairs[col_repair_date].lt(_start + pd.Timedelta(days=7))]
            _total = float(
                sum(
                    pd.to_numeric(_sub[c], errors="coerce").sum()
                    for c in (col_repair_cost, col_engine_cost)
                    if c and c in _sub.columns
                )
            )
        _wlab = f"W{int(_start.isocalendar()[1]):02d}"
        if _rp_prev is None:
            _chg = "\u2014"
        elif _rp_prev == 0:
            _chg = "No comparison"
        else:
            _p = (_total - _rp_prev) / _rp_prev * 100
            _chg = f"{abs(_p):.0f}% {'lower' if _p < 0 else 'higher'}"
        repair_weekly.append({"Period": _wlab, "Recorded cost": f"\u20a6{_total:,.0f}", "Weekly change": _chg})
        _rp_prev = _total

    repair_breakdown = []
    if repairs is not None and col_repair_date:
        _sub = repairs[repairs[col_repair_date].ge(_wk_start) & repairs[col_repair_date].lt(_wk_start + pd.Timedelta(days=7))]
        _group_col = col_repair_desc or col_repair_plate or col_repair_area
        if _group_col and _group_col in _sub.columns and len(_sub):
            _costs = pd.to_numeric(_sub[col_repair_cost], errors="coerce").fillna(0) if col_repair_cost and col_repair_cost in _sub.columns else 0
            if col_engine_cost and col_engine_cost in _sub.columns:
                _costs = _costs + pd.to_numeric(_sub[col_engine_cost], errors="coerce").fillna(0)
            _gb = (
                _sub.assign(_cost=_costs, _g=_sub[_group_col].astype(str).str.strip())
                .groupby("_g")["_cost"].sum()
                .sort_values(ascending=False)
                .head(10)
            )
            repair_breakdown = [
                {"Week work": g, "Recorded cost": f"\u20a6{v:,.0f}"}
                for g, v in _gb.items() if v > 0
            ]

    # --- Slide 6: actions ----------------------------------------------------
    _prep = _wk_end + pd.Timedelta(days=1)
    action_rows = [
        {"By when": f"{_prep:%d %b}", "Action": "Agree delivery promises for each service and route", "Proposed owner": "Quadri + operations"},
        {"By when": f"{_prep + pd.Timedelta(days=3):%d %b}", "Action": "Confirm the oil bill split and pending tyre; complete fuel records", "Proposed owner": "Quadri + Finance"},
        {"By when": f"{_prep + pd.Timedelta(days=4):%d %b}", "Action": "Review Abuja van repairs and long waits after invoicing", "Proposed owner": "Operations team"},
        {"By when": f"{_prep + pd.Timedelta(days=7):%d %b}", "Action": "Compare the next full week using the same measures", "Proposed owner": "Operations + analytics"},
    ]

    # ------------------------------------------------------------------
    # ON-PAGE RENDERING
    # ------------------------------------------------------------------
    st.caption(f"{week_title} \u2014 compared with {prev_title}")
    try:
        from pptx import Presentation as _PptxPresentation  # noqa: F401
        _pptx_ok = True
    except ImportError:
        _pptx_ok = False
    if not _pptx_ok:
        st.warning("python-pptx is not installed. Add it to requirements.txt to enable PowerPoint export.")

    _dl_col, _ = st.columns([1, 4])
    with _dl_col:
        _export_clicked = st.button("⬇️ Export to PowerPoint", disabled=not _pptx_ok, type="primary", key="weekly_export_btn")

    section_header("Delivery speed after dispatch")
    if programme_rows:
        st.dataframe(pd.DataFrame(programme_rows), hide_index=True, use_container_width=True)
    else:
        show_empty_chart("No programme delivery data available for the selected weeks.")

    section_header("Order stage turnaround")
    if stage_rows:
        st.dataframe(pd.DataFrame(stage_rows), hide_index=True, use_container_width=True)
        st.caption(f"Deliveries with every time available: {stage_samples_prev} last week; {stage_samples_curr} this week.")

    section_header("Fuel spend")
    fm1, fm2, fm3 = st.columns(3)
    fm1.metric(f"Fuel total \u00b7 W{_wk_num:02d}", f"\u20a6{fuel_total:,.0f}")
    fm2.metric("Fuel entries / vehicles", f"{fuel_entries} / {fuel_vehicles}")
    fm3.metric(f"vs W{_pwk_num:02d}", f"\u20a6{fuel_prev_total:,.0f}",
               delta=f"{fuel_pct:+.1f}%" if fuel_pct is not None else "No comparison")
    if fuel_top:
        _ft_df = pd.DataFrame(fuel_top, columns=["Vehicle plate", "Fuel amount (\u20a6)"])
        fig = px.bar(
            _ft_df.sort_values("Fuel amount (\u20a6)"),
            x="Fuel amount (\u20a6)",
            y="Vehicle plate",
            orientation="h",
            text="Fuel amount (\u20a6)",
            title=f"Highest recorded fuel amounts \u00b7 W{_wk_num:02d} (\u20a6)",
            color_discrete_sequence=[BRAND["green"]],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(showlegend=False, height=max(320, 60 + len(_ft_df) * 34), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(plotly_theme(fig), use_container_width=True)

    section_header("Repair costs")
    rc1, rc2 = st.columns(2)
    with rc1:
        st.dataframe(pd.DataFrame(repair_weekly), hide_index=True, use_container_width=True)
    with rc2:
        if repair_breakdown:
            st.dataframe(pd.DataFrame(repair_breakdown), hide_index=True, use_container_width=True)
        else:
            show_empty_chart("No repair records for the current week.")

    section_header("What needs to happen next")
    st.dataframe(pd.DataFrame(action_rows), hide_index=True, use_container_width=True)
    st.caption(f"Next report: {_wk_start + pd.Timedelta(days=7):%d %b} \u2013 {_wk_end + pd.Timedelta(days=7):%d %b %Y}.")

    # ------------------------------------------------------------------
    # POWERPOINT EXPORT
    # ------------------------------------------------------------------
    def _build_weekly_pptx():
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor

        HEADER = RGBColor(0x16, 0x86, 0xD9)
        WHITE = RGBColor(0xFF, 0xFF, 0xFF)
        DARK = RGBColor(0x0F, 0x23, 0x33)
        MUTED = RGBColor(0x4A, 0x61, 0x78)
        prs = Presentation()
        blank = prs.slide_layouts[6]

        def _add_text(slide, text, left, top, width, height, size=14, bold=False, color=DARK):
            box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
            tf = box.text_frame
            tf.word_wrap = True
            for i, line in enumerate(text.split("\n")):
                par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                run = par.add_run()
                run.text = line
                run.font.size = Pt(size)
                run.font.bold = bold
                run.font.color.rgb = color
            return box

        def _add_table(slide, headers, rows, top=1.6):
            data = [list(headers)] + [list(r) for r in rows]
            height = 0.4 * len(data)
            shape = slide.shapes.add_table(len(data), len(headers), Inches(0.5), Inches(top), Inches(9.0), Inches(height))
            tbl = shape.table
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    cell = tbl.cell(r, c)
                    cell.text = str(val)
                    for par in cell.text_frame.paragraphs:
                        for run in par.runs:
                            run.font.size = Pt(12)
                            run.font.color.rgb = WHITE if r == 0 else DARK
                            run.font.bold = r == 0
                    if r == 0:
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = HEADER
            return tbl

        # Slide 1: cover
        s = prs.slides.add_slide(blank)
        _add_text(s, "Delivery performance\nand vehicle costs", 0.8, 1.8, 8.5, 1.9, size=40, bold=True)
        _add_text(s, week_title, 0.8, 3.8, 8.5, 0.5, size=20)
        _add_text(s, f"Compared with {prev_title}", 0.8, 4.3, 8.5, 0.4, size=16, color=MUTED)
        _add_text(s, "What changed, what needs attention, and the next actions", 0.8, 4.8, 8.5, 0.4, size=14, color=MUTED)
        _add_text(s, f"Prepared {_prep:%d %B %Y}", 0.8, 5.6, 8.5, 0.4, size=12, color=MUTED)
        _add_text(s, f"Prepared by {st.session_state.get('authenticated_user', 'DrugStoc logistics')}", 0.8, 5.95, 8.5, 0.4, size=12, color=MUTED)

        # Slide 2: dispatch to delivery by programme
        s = prs.slides.add_slide(blank)
        _add_text(s, "B2B delivery was faster after dispatch", 0.5, 0.3, 9, 0.7, size=28, bold=True)
        _add_text(s, "Time shown is dispatch to delivery. Small samples need caution. On-time delivery needs an agreed delivery promise.", 0.5, 1.0, 9, 0.5, size=11, color=MUTED)
        if programme_rows:
            _keys = list(programme_rows[0].keys())
            _add_table(s, _keys, [[r[k] for k in _keys] for r in programme_rows])
        else:
            _add_text(s, "No programme delivery data available for the selected weeks.", 0.5, 1.8, 9, 0.4, size=14)

        # Slide 3: stage turnaround
        s = prs.slides.add_slide(blank)
        _add_text(s, "Most B2B time is spent before dispatch", 0.5, 0.3, 9, 0.7, size=28, bold=True)
        _add_text(s, "Hours include nights and weekends. Invoice time uses invoice creation; actual issue time may differ.", 0.5, 1.0, 9, 0.5, size=11, color=MUTED)
        if stage_rows:
            _keys = list(stage_rows[0].keys())
            _add_table(s, _keys, [[r[k] for k in _keys] for r in stage_rows])
        _add_text(s, f"Deliveries with every time available: {stage_samples_prev} last week; {stage_samples_curr} this week.", 0.5, 4.2, 9, 0.4, size=12, color=MUTED)

        # Slide 4: fuel
        s = prs.slides.add_slide(blank)
        _add_text(s, f"Week {_wk_num} fuel spend", 0.5, 0.3, 9, 0.7, size=28, bold=True)
        _add_text(s, "Figures assumed to be naira; confirm the source unit.", 0.5, 1.0, 9, 0.4, size=11, color=MUTED)
        _add_text(s, f"\u20a6{fuel_total:,.0f}", 0.5, 1.5, 4, 0.7, size=36, bold=True)
        _add_text(s, f"{fuel_entries} fuel entries\n{fuel_vehicles} vehicles", 0.5, 2.3, 4, 0.7, size=14, color=MUTED)
        if fuel_pct is not None:
            _add_text(s, f"{fuel_pct:+.1f}%", 4.5, 1.5, 4, 0.6, size=24, bold=True, color=MUTED)
            _add_text(s, f"versus \u20a6{fuel_prev_total:,.0f} last week", 4.5, 2.15, 4, 0.4, size=12, color=MUTED)
        if fuel_top:
            _add_text(s, "Highest recorded fuel amounts (\u20a6)", 0.5, 3.3, 9, 0.4, size=14, bold=True)
            _add_table(s, ["Vehicle plate", "Fuel amount (\u20a6)"], [[p, f"{a:,.0f}"] for p, a in fuel_top], top=3.8)
        else:
            _add_text(s, "No fuel records for the current week.", 0.5, 3.3, 9, 0.4, size=14)

        # Slide 5: repairs
        s = prs.slides.add_slide(blank)
        _add_text(s, "Recorded repair costs", 0.5, 0.3, 9, 0.7, size=28, bold=True)
        _add_text(s, "Uses the Maintenance & Repair and Servicing columns of the Repairs and Servicing tab.", 0.5, 1.0, 9, 0.4, size=11, color=MUTED)
        if repair_weekly:
            _keys = list(repair_weekly[0].keys())
            _add_table(s, _keys, [[r[k] for k in _keys] for r in repair_weekly], top=1.5)
        if repair_breakdown:
            _keys = list(repair_breakdown[0].keys())
            _add_table(s, _keys, [[r[k] for k in _keys] for r in repair_breakdown], top=3.6)

        # Slide 6: actions
        s = prs.slides.add_slide(blank)
        _add_text(s, "What needs to happen next", 0.5, 0.3, 9, 0.7, size=28, bold=True)
        _add_text(s, f"Proposed owners and dates. Next report: {_wk_start + pd.Timedelta(days=7):%d %b} \u2013 {_wk_end + pd.Timedelta(days=7):%d %b %Y}.", 0.5, 1.0, 9, 0.4, size=11, color=MUTED)
        _keys = list(action_rows[0].keys())
        _add_table(s, _keys, [[r[k] for k in _keys] for r in action_rows], top=1.6)
        _add_text(s, "Agree the owners today, then review the results next week.", 0.5, 4.6, 9, 0.4, size=12, color=MUTED)

        _buf = io.BytesIO()
        prs.save(_buf)
        return _buf.getvalue()

    if _export_clicked and _pptx_ok:
        try:
            _pptx_bytes = _build_weekly_pptx()
            st.download_button(
                "⬇️ Download PowerPoint",
                data=_pptx_bytes,
                file_name=f"DrugStoc_Weekly_Operations_W{_wk_num:02d}_{_wk_start:%Y%m%d}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key="weekly_export_download",
            )
            st.success("Presentation generated \u2014 use the download button above.")
        except Exception as exc:
            st.error("PowerPoint export failed.")
            with st.expander("Technical details"):
                st.code(str(exc))
# ---------------------------------------------------------------------------
# PAGE 3: VEHICLES & ORDER COUNT
# ---------------------------------------------------------------------------
elif selected_page == ":material/local_shipping: Vehicles & Orders":
    section_header("Vehicle Dispatch & Order Value Performance")
    if not col_vehicle:
        st.info(
            "No Vehicle Plate No field found in the dataset. Expected a column "
            "like 'Vehicle Plate No', 'Plate Number' or 'Vehicle Reg No'."
        )
    else:
        veh_df = filtered.dropna(subset=[col_vehicle]).copy()
        veh_df = veh_df[veh_df[col_vehicle].astype(str).str.strip() != ""]
        if veh_df.empty:
            st.info("No vehicle dispatch records available for the current filters.")
        else:
            veh_summary = (
                veh_df.assign(**{"Vehicle Plate No": veh_df[col_vehicle].astype(str).str.strip().str.upper()})
                .groupby("Vehicle Plate No", dropna=False)
                .agg(
                    Orders_Dispatched=(col_client, "count"),
                    Delivered_Orders=("Is Delivered", "sum"),
                    Total_Order_Value=(col_value, "sum"),
                )
                .reset_index()
                .sort_values("Orders_Dispatched", ascending=False)
            )
            veh_summary["Fulfillment_Rate"] = (veh_summary["Delivered_Orders"] / veh_summary["Orders_Dispatched"] * 100).round(1)
            veh_summary["Coverage Area"] = veh_summary["Vehicle Plate No"].map(
                lambda p: plate_to_area.get(str(p).strip().upper(), "Unassigned")
            )
            render_kpis(
                [
                    (
                        "Vehicles Deployed",
                        fmt_num(veh_summary["Vehicle Plate No"].nunique()),
                        "Unique vehicles with dispatch activity in the filtered view.",
                        "🚛",
                        BRAND["blue"],
                    ),
                    (
                        "Orders Dispatched",
                        fmt_num(veh_summary["Orders_Dispatched"].sum()),
                        "Total orders carried across all vehicles (filtered view).",
                        "📦",
                        BRAND["blue"],
                    ),
                    (
                        "Total Order Value",
                        money(veh_summary["Total_Order_Value"].sum()),
                        "Sum of Order Value across all dispatched orders.",
                        "💰",
                        BRAND["green"],
                    ),
                ]
            )
            display_veh = veh_summary.rename(
                columns={
                    "Orders_Dispatched": "Orders Dispatched",
                    "Delivered_Orders": "Delivered Orders",
                    "Total_Order_Value": "Total Order Value",
                    "Fulfillment_Rate": "Delivery Rate (%)",
                }
            )
            display_veh["Total Order Value"] = display_veh["Total Order Value"].apply(money)
            st.dataframe(display_veh, use_container_width=True, hide_index=True)

            chart_df = veh_summary.sort_values("Orders_Dispatched", ascending=True)
            fig = px.bar(
                chart_df,
                x="Orders_Dispatched",
                y="Vehicle Plate No",
                orientation="h",
                text="Orders_Dispatched",
                title="Orders Dispatched by Vehicle",
                color_discrete_sequence=[BRAND["blue"]],
                labels={"Orders_Dispatched": "Orders Dispatched", "Vehicle Plate No": "Vehicle Plate No"},
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                showlegend=False,
                height=max(360, min(650, 80 + len(chart_df) * 36)),
                xaxis_title="Orders Dispatched",
                yaxis_title=None,
            )
            st.plotly_chart(plotly_theme(fig), use_container_width=True)

            csv_veh = veh_summary.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Vehicle Summary CSV",
                data=csv_veh,
                file_name="drugstoc_vehicle_order_summary.csv",
                mime="text/csv",
            )


# ---------------------------------------------------------------------------
# PAGE 4: FUELING COST
# ---------------------------------------------------------------------------
elif selected_page == ":material/oil_barrel: Fueling Cost":
    section_header("Fueling Cost", "Fuel spend picked from the Fuel tab of the logistics_DB workbook.")
    if fuel is None or fuel.empty:
        st.info("No Fuel sheet found in the logistics workbook.")
    elif not col_fuel_cost:
        st.info("No fueling cost column (e.g. 'Fueling/Ltr') found in the Fuel sheet.")
    else:
        total_fuel_cost = fuel_view[col_fuel_cost].sum()
        fuel_events = int(fuel_view[col_fuel_cost].notna().sum())
        total_deliveries = int(filtered["Is Delivered"].sum())
        avg_cost_per_delivery = total_fuel_cost / total_deliveries if total_deliveries else 0

        section_header("Fueling KPIs")
        render_kpis(
            [
                (
                    "Total Fueling Cost",
                    money(total_fuel_cost),
                    "Sum of fuel spend recorded in the Fuel tab (filtered view).",
                    "⛽",
                    BRAND["green"],
                ),
                (
                    "Total Deliveries",
                    fmt_num(total_deliveries),
                    "Delivered orders in the filtered logistics view.",
                    "📦",
                    BRAND["blue"],
                ),
                (
                    "Fueling Events",
                    fmt_num(fuel_events),
                    "Number of fueling records logged in the Fuel tab.",
                    "🧾",
                    BRAND["amber"],
                ),
                (
                    "Avg Cost / Delivery",
                    money(avg_cost_per_delivery),
                    "Total fueling cost divided by total deliveries.",
                    "💸",
                    BRAND["teal"],
                ),
            ]
        )

        if col_fuel_date and fuel_view[col_fuel_date].notna().any():
            trend = (
                fuel_view.dropna(subset=[col_fuel_date])
                .assign(_month=lambda x: x[col_fuel_date].dt.to_period("M"))
                .groupby("_month", dropna=False)[col_fuel_cost]
                .sum()
                .reset_index()
                .sort_values("_month")
            )
            trend["Month"] = trend["_month"].dt.strftime("%b %Y")
            fig = px.bar(
                trend,
                x="Month",
                y=col_fuel_cost,
                text=col_fuel_cost,
                title="Monthly Fueling Spend",
                color_discrete_sequence=[BRAND["green"]],
                labels={col_fuel_cost: "Fueling Cost (₦)"},
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(showlegend=False, height=380, yaxis_title=None)
            st.plotly_chart(plotly_theme(fig), use_container_width=True)

        section_header("Fueling Records", f"{len(fuel_view):,} records from the Fuel tab.")
        table_cols = [
            c
            for c in [
                col_fuel_date,
                col_fuel_captain,
                col_fuel_plate,
                col_fuel_model,
                col_fuel_cost,
                "Fuel Week Label",
            ]
            if c and c in fuel_view.columns
        ]
        display_fuel = fuel_view[table_cols]
        if col_fuel_plate and col_fuel_plate in display_fuel.columns:
            display_fuel = display_fuel.assign(
                **{"Coverage Area": display_fuel[col_fuel_plate].map(
                    lambda p: plate_to_area.get(str(p).strip().upper(), "Unassigned")
                )}
            )
        if col_fuel_date and col_fuel_date in display_fuel.columns:
            display_fuel = display_fuel.sort_values(col_fuel_date, ascending=False)
        st.dataframe(display_fuel, use_container_width=True, hide_index=True, height=500)

        csv_fuel = fuel_view.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Fuel Data CSV",
            data=csv_fuel,
            file_name="drugstoc_fuel_data.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------------------------
# PAGE 5: CAPTAIN EFFICIENCY
# ---------------------------------------------------------------------------
elif selected_page == ":material/badge: Captain Efficiency":
    section_header("Rider & Captain Turnaround Performance")
    if not col_captain:
        st.info("No Captain field found in the dataset.")
    else:
        cap_df = filtered.dropna(subset=[col_captain]).copy()
        cap_df = cap_df[cap_df[col_captain].astype(str).str.strip() != ""]
        if cap_df.empty:
            st.info("No captain performance records available.")
        else:
            cap_summary = (
                cap_df.groupby(col_captain, dropna=False)
                .agg(
                    Total_Orders=(col_client, "count"),
                    Creation_to_Delivery_TAT=("Creation_Delivery_TAT", "mean"),
                    Shipping_TAT=("Shipping_TAT", "mean"),
                    Delivery_Rate=("Is Delivered", "mean"),
                )
                .reset_index()
            )
            cap_summary["Delivery_Rate"] = cap_summary["Delivery_Rate"].fillna(0) * 100
            display_cap = cap_summary.rename(
                columns={
                    col_captain: "Captain",
                    "Total_Orders": "Dispatches",
                    "Creation_to_Delivery_TAT": "Avg Creation→Delivery TAT (hrs)",
                    "Shipping_TAT": "Avg Shipping TAT (hrs)",
                    "Delivery_Rate": "Success Rate (%)",
                }
            )
            st.dataframe(
                display_cap.sort_values(["Success Rate (%)", "Dispatches"], ascending=[False, False]),
                use_container_width=True,
                hide_index=True,
            )


# ---------------------------------------------------------------------------
# PAGE 6: AUDIT DATA
# ---------------------------------------------------------------------------
elif selected_page == ":material/fact_check: Audit Data":
    section_header("Filtered Audit Logs", f"{len(filtered):,} records shown from {len(df):,} total records.")
    st.dataframe(filtered, use_container_width=True, hide_index=True, height=600)
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Filtered Audit CSV",
        data=csv,
        file_name="drugstoc_filtered_logistics_audit.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# PAGE: BI SUMMARY — Asset Mapping
# ---------------------------------------------------------------------------
elif selected_page == ":material/insights: BI Summary":
    # ------------------------------------------------------------------
    # OPERATIONAL TAT — first subheading on the BI Summary tab
    # ------------------------------------------------------------------
    section_header("Operational TAT")

    # Order -> Invoice is measured from 1 Oct 2026 onwards only
    ORDER_INVOICE_START = pd.Timestamp("2026-10-01")
    if "Created_DT" in filtered.columns:
        order_invoice_orders = filtered[filtered["Created_DT"].ge(ORDER_INVOICE_START)]
    else:
        order_invoice_orders = filtered

    _tat_periods = comparison_periods(filtered, col_date, selected_week, selected_month)
    if _tat_periods is not None:
        _curr_mask, _prev_mask = _tat_periods["WoW"][0], _tat_periods["WoW"][1]
    else:
        _curr_mask = _prev_mask = None

    def _weekly_payload(frame, tat_col):
        """Current-week and previous-week averages plus WoW delta (higher TAT = worse)."""
        cw = pw = delta = None
        if _curr_mask is not None and len(frame):
            cw_frame = frame.loc[frame.index.intersection(_curr_mask.index[_curr_mask])]
            pw_frame = frame.loc[frame.index.intersection(_prev_mask.index[_prev_mask])]
            cw = cw_frame[tat_col].mean() if len(cw_frame) else None
            pw = pw_frame[tat_col].mean() if len(pw_frame) else None
            if cw is not None and pd.notna(cw):
                cw = round(float(cw), 1)
            else:
                cw = None
            if pw is not None and pd.notna(pw):
                pw = round(float(pw), 1)
            else:
                pw = None
            if cw is not None and pw is not None and pw != 0:
                delta = (cw - pw) / abs(pw) * 100.0
        return {"cw": cw, "pw": pw, "delta": delta}

    def _hrs_or_na(value):
        return f"{value:.1f} hrs" if value is not None and pd.notna(value) else "N/A"

    tat_kpis = [
        (
            "TAT: Order → Invoice",
            order_invoice_orders,
            "Creation_Invoice_TAT",
            "🧾",
            BRAND["blue"],
        ),
        (
            "TAT: Invoice → Dispatch",
            filtered,
            "Invoice_Dispatch_TAT",
            "🚚",
            BRAND["amber"],
        ),
        (
            "TAT: Dispatch → Delivery",
            filtered,
            "Shipping_TAT",
            "⏱",
            BRAND["teal"],
        ),
        (
            "TAT: Invoice → Delivery",
            filtered,
            "Invoice_Delivery_TAT",
            "✅",
            BRAND["green"],
        ),
    ]
    render_kpis(
        [
            (
                label,
                _hrs_or_na(frame[tat_col].mean()),
                "",
                icon,
                accent,
                _weekly_payload(frame, tat_col),
            )
            for label, frame, tat_col, icon, accent in tat_kpis
        ]
    )

    # ------------------------------------------------------------------
    # LOGISTICS COSTS
    # ------------------------------------------------------------------
    repairs_view = repairs.copy() if repairs is not None else None
    if repairs_view is not None:
        if selected_quarter != "All Quarters" and "Repair Quarter Label" in repairs_view.columns:
            repairs_view = repairs_view[repairs_view["Repair Quarter Label"] == selected_quarter]
        if selected_month != "All Months" and "Repair Month Label" in repairs_view.columns:
            repairs_view = repairs_view[repairs_view["Repair Month Label"] == selected_month]
        if selected_week != "All Weeks" and "Repair Week Label" in repairs_view.columns:
            repairs_view = repairs_view[repairs_view["Repair Week Label"] == selected_week]

    bi_fuel_total = fuel_view[col_fuel_cost].sum() if (fuel_view is not None and col_fuel_cost) else 0.0
    bi_repair_total = repairs_view[col_repair_cost].sum() if (repairs_view is not None and col_repair_cost) else 0.0
    bi_engine_total = repairs_view[col_engine_cost].sum() if (repairs_view is not None and col_engine_cost) else 0.0
    bi_maintenance_total = bi_repair_total + bi_engine_total
    bi_logistics_total = bi_fuel_total + bi_maintenance_total

    _bi_delivered = filtered[filtered["Is Delivered"]]
    bi_deliveries = int(_bi_delivered[col_client].count()) if col_client else len(_bi_delivered)
    avg_logistics_cost = bi_logistics_total / bi_deliveries if bi_deliveries else None
    bi_revenue_total = filtered[col_value].sum()
    avg_revenue_per_delivery = bi_revenue_total / bi_deliveries if bi_deliveries else None

    section_header(
        "Logistics Costs",
        "Fuel spend from the Fuel tab and maintenance & repair spend from the Repairs and Servicing tab "
        "of the logistics_DB workbook (respects the Quarter/Month/Week filters).",
    )
    render_kpis(
        [
            (
                "Total Logistics Cost",
                money(bi_logistics_total),
                "Combined fuel, maintenance, repair and engine servicing spend for the selected period.",
                "💸",
                BRAND["navy"],
            ),
            (
                "Total Fuel Cost",
                money(bi_fuel_total),
                "Sum of the fueling cost column on the Fuel tab (filtered view).",
                "⛽",
                BRAND["green"],
            ),
            (
                "Maintenance and Repair Cost",
                money(bi_maintenance_total),
                "Sum of the Maintenance & Repair and Servicing columns on the Repairs and Servicing tab.",
                "🔧",
                BRAND["amber"],
            ),
            (
                "Average Logistic Cost",
                money(avg_logistics_cost) if avg_logistics_cost is not None else "N/A",
                "Total Logistics Cost divided by Total Deliveries.",
                "💸",
                BRAND["teal"],
            ),
            (
                "Average Revenue per Delivery",
                money(avg_revenue_per_delivery) if avg_revenue_per_delivery is not None else "N/A",
                "Total Order Value divided by Total Deliveries.",
                "💰",
                BRAND["green"],
            ),
        ]
    )

    # ------------------------------------------------------------------
    # LOGISTICS COST PER AREA
    # ------------------------------------------------------------------
    section_header(
        "Logistics Cost per Area",
        "Fuel and maintenance spend grouped by coverage area, using the plate-to-area "
        "mapping from the Assets and Repairs tabs (respects the Quarter/Month/Week filters).",
    )

    fuel_area = pd.Series(dtype=float)
    if fuel_view is not None and col_fuel_cost and col_fuel_plate and col_fuel_plate in fuel_view.columns:
        _f = fuel_view.dropna(subset=[col_fuel_plate]).copy()
        _f["_Area"] = _f[col_fuel_plate].map(
            lambda p: plate_to_area.get(str(p).strip().upper(), "Unassigned")
        )
        fuel_area = _f.groupby("_Area")[col_fuel_cost].sum()

    repair_area = pd.Series(dtype=float)
    if repairs_view is not None and (col_repair_cost or col_engine_cost):
        _r = repairs_view.copy()
        _r["_cost"] = 0.0
        for _c in (col_repair_cost, col_engine_cost):
            if _c and _c in _r.columns:
                _r["_cost"] = _r["_cost"] + pd.to_numeric(_r[_c], errors="coerce").fillna(0)
        if col_repair_area and col_repair_area in _r.columns:
            _r["_Area"] = (
                _r[col_repair_area].fillna("Unassigned").astype(str).str.strip().replace("", "Unassigned")
            )
        elif col_repair_plate and col_repair_plate in _r.columns:
            _r["_Area"] = _r[col_repair_plate].map(
                lambda p: plate_to_area.get(str(p).strip().upper(), "Unassigned")
            )
        else:
            _r["_Area"] = "Unassigned"
        repair_area = _r.groupby("_Area")["_cost"].sum()

    area_cost_df = pd.concat(
        {"Fuel Cost": fuel_area, "Maintenance Cost": repair_area}, axis=1
    ).fillna(0.0)
    area_cost_df["Total Cost"] = area_cost_df["Fuel Cost"] + area_cost_df["Maintenance Cost"]
    area_cost_df = area_cost_df[area_cost_df["Total Cost"] > 0].sort_values("Total Cost", ascending=False)

    if area_cost_df.empty:
        show_empty_chart("No fuel or maintenance cost records available for the selected period.")
    else:
        area_table = area_cost_df.reset_index().rename(columns={"_Area": "Area"})
        display_area = area_table.copy()
        for c in ("Fuel Cost", "Maintenance Cost", "Total Cost"):
            display_area[c] = display_area[c].apply(money)
        st.dataframe(display_area, use_container_width=True, hide_index=True)

        area_long = area_table.melt(
            id_vars="Area",
            value_vars=["Fuel Cost", "Maintenance Cost"],
            var_name="Cost Type",
            value_name="Amount",
        )
        fig = px.bar(
            area_long.sort_values("Amount", ascending=True),
            x="Amount",
            y="Area",
            color="Cost Type",
            orientation="h",
            barmode="stack",
            title="Logistics Cost per Area",
            color_discrete_map={"Fuel Cost": BRAND["green"], "Maintenance Cost": BRAND["amber"]},
            labels={"Amount": "Cost (₦)", "Area": "Coverage Area"},
            custom_data=["Cost Type"],
        )
        fig.update_traces(
            hovertemplate="%{y}<br>%{customdata[0]}: ₦%{x:,.0f}<extra></extra>"
        )
        fig.update_layout(
            showlegend=True,
            height=max(360, min(650, 120 + len(area_table) * 36)),
            xaxis_title=None,
            yaxis_title=None,
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.22, x=0.5, xanchor="center",
                font=dict(size=10, color=THEME["muted"]),
            ),
        )
        st.plotly_chart(plotly_theme(fig), use_container_width=True)

    section_header(
        "Asset Summary",
        "Operational assets and deliveries from the SHIPMENT DATA tab, plus asset mapping from the ASSET MAPPING tab of the logistics_DB workbook.",
    )

    # KPIs respect the top page filters (Quarter/Month/Week/Region/Status/Order Type)
    asset_summary_orders = filtered
    if col_vehicle and col_vehicle in asset_summary_orders.columns:
        _plates = asset_summary_orders[col_vehicle].dropna().astype(str).str.strip().str.upper()
        total_operational_assets = int(_plates[_plates != ""].nunique())
    else:
        total_operational_assets = 0
    _delivered_orders = asset_summary_orders[asset_summary_orders["Is Delivered"]]
    total_deliveries = int(_delivered_orders[col_client].count()) if col_client else len(_delivered_orders)

    render_kpis(
        [
            (
                "Total Operational Assets",
                fmt_num(total_operational_assets),
                "Distinct plate numbers on the SHIPMENT DATA tab within the selected dates.",
                "🚛",
                BRAND["blue"],
            ),
            (
                "Total Deliveries",
                fmt_num(total_deliveries),
                'Count of Client Name where Status = "Delivered" within the selected dates.',
                "📦",
                BRAND["green"],
            ),
        ]
    )
    ASSET_TYPE_COLORS = {
        "BIKE": BRAND["green"],
        "CARS": "#9AA3AF",
        "FUTON TRUCK": BRAND["blue"],
        "HIACE": "#1E3A8A",
        "SALON": "#F97316",
        "SALONPAS": "#F97316",
        "TRYCYCLE": "#7C3AED",
        "3PL": "#0D9488",
        "MSR": "#B45309",
    }
    if asset_mapping_raw is None or asset_mapping_raw.empty:
        st.info("No ASSET MAPPING tab found in the logistics_DB workbook.")
    else:
        am = asset_mapping_raw.copy()
        if am.columns.astype(str).str.startswith("Unnamed").mean() > 0.5:
            am.columns = [str(c).strip() for c in am.iloc[0]]
            am = am.iloc[1:].reset_index(drop=True)
        else:
            am.columns = [str(c).strip() for c in am.columns]
        col_am_date = find_col(am, ["DATE", "Date", "Month"])
        col_am_type = find_col(am, ["ASSET TYPE", "Asset Type", "Type"])
        col_am_qty = find_col(am, ["QUANTITY", "Quantity", "Qty"])
        meta_cols = {c for c in (col_am_date, col_am_type, col_am_qty) if c}
        area_cols = [c for c in am.columns if c not in meta_cols]

        today = pd.Timestamp.now()
        prev_month_start = (today.replace(day=1) - pd.Timedelta(days=1)).replace(day=1)
        prev_label = prev_month_start.strftime("%B %Y")
        if col_am_date:
            parsed_dates = pd.to_datetime(am[col_am_date], errors="coerce")
            prev = am[
                (parsed_dates.dt.year == prev_month_start.year)
                & (parsed_dates.dt.month == prev_month_start.month)
            ]
        else:
            prev = am
            st.caption("No DATE column found in the ASSET MAPPING tab — showing all records.")

        area_counts = pd.DataFrame(
            {
                "Business Area": area_cols,
                "Assets": [int(prev[c].count()) for c in area_cols],
            }
        )
        area_counts = area_counts[area_counts["Assets"] > 0]
        if col_am_type:
            t = prev[[col_am_type] + ([col_am_qty] if col_am_qty else [])].copy()
            t["_type"] = t[col_am_type].dropna().astype(str).str.strip().str.upper()
            t = t[t["_type"] != ""]
            if col_am_qty:
                t["_n"] = pd.to_numeric(t[col_am_qty], errors="coerce").fillna(0)
            else:
                t["_n"] = 1
            type_counts = t.groupby("_type")["_n"].sum().reset_index()
            type_counts.columns = ["Asset Type", "Assets"]
            type_counts = type_counts[type_counts["Assets"] > 0]
        else:
            type_counts = pd.DataFrame(columns=["Asset Type", "Assets"])
        top_type = str(type_counts.sort_values("Assets", ascending=False)["Asset Type"].iloc[0]) if not type_counts.empty else "—"

        render_kpis(
            [
                (
                    "Business Areas",
                    fmt_num(area_counts.shape[0]),
                    f"Distinct business areas with assets for {prev_label}.",
                    "📍",
                    BRAND["teal"],
                ),
                (
                    "Top Asset Type",
                    top_type,
                    f"Highest-quantity asset type for {prev_label}.",
                    "🏍",
                    BRAND["amber"],
                ),
            ]
        )

        col_bar, col_donut = st.columns(2)
        with col_bar:
            if area_counts.empty:
                show_empty_chart("No business area data available in the ASSET MAPPING tab.")
            else:
                fig = px.bar(
                    area_counts.sort_values("Assets", ascending=True),
                    x="Assets",
                    y="Business Area",
                    orientation="h",
                    text="Assets",
                    title=f"ASSETS PER BUSINESS AREA — {prev_label.upper()}",
                    color_discrete_sequence=["#6B7280"],
                )
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_layout(
                    showlegend=False,
                    height=max(360, min(650, 120 + len(area_counts) * 36)),
                    xaxis_title=None,
                    yaxis_title="BUSINESS AREA",
                )
                st.plotly_chart(plotly_theme(fig), use_container_width=True)
        with col_donut:
            if type_counts.empty:
                show_empty_chart("No asset type data found in the ASSET MAPPING tab.")
            else:
                fig = px.pie(
                    type_counts,
                    names="Asset Type",
                    values="Assets",
                    hole=0.6,
                    title=f"ASSET TYPE — {prev_label.upper()}",
                    color="Asset Type",
                    color_discrete_map=ASSET_TYPE_COLORS,
                    color_discrete_sequence=[BRAND["blue"], "#9AA3AF", "#1E3A8A", "#F97316", "#7C3AED", BRAND["green"]],
                )
                fig.update_traces(textinfo="value+percent")
                fig.update_layout(
                    height=420,
                    legend=dict(
                        orientation="v", yanchor="middle", y=0.5, x=1.02, xanchor="left",
                        font=dict(size=10, color=THEME["muted"]),
                    ),
                )
                st.plotly_chart(plotly_theme(fig), use_container_width=True)


# ---------------------------------------------------------------------------
# PAGE 7: ASSET MANAGEMENT
# ---------------------------------------------------------------------------
elif selected_page == ":material/handyman: Asset Management":
    st.subheader("🛠️ Asset Management")
    st.markdown(
        "Track and manage logistics assets — vehicles, cold-chain equipment, "
        "and pharmaceutical handling tools tied to distribution operations."
    )
    a1, a2, a3 = st.columns(3)
    a1.metric("Active Fleet Units", "—")
    a2.metric("Cold-Chain Assets", "—")
    a3.metric("Assets Due for Service", "—")
    st.info(
        "Asset registry integration is pending. Connect this module to your "
        "asset database to monitor utilization, maintenance schedules, and lifecycle status."
    )


# ---------------------------------------------------------------------------
# PAGE 8: COST CONTROL
# ---------------------------------------------------------------------------
elif selected_page == ":material/savings: Cost Control":
    st.subheader("💰 Cost Control")
    st.markdown(
        "Monitor logistics spend, cost per delivery, fuel efficiency, and "
        "operational budget variance across regions and order types."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Cost Per Delivery", "₦—")
    c2.metric("Fuel & Logistics Budget", "₦—")
    c3.metric("Budget Variance", "—%")
    st.info(
        "Cost data integration is pending. Link this module to your finance/ERP "
        "system to unlock cost-per-route, fuel trend analysis, and budget tracking."
    )


# ---------------------------------------------------------------------------
# PAGE 9: RECOMMENDATIONS
# ---------------------------------------------------------------------------
elif selected_page == ":material/lightbulb: Recommendations":
    section_header(
        "Month-on-Month Recommendations",
        "Latest month versus the previous month, using the selected Region, Status and Order Type.",
    )
    recommendation_periods = comparison_periods(comparison_base, col_date, selected_week, selected_month)
    if recommendation_periods is None:
        st.info("No dated orders are available to generate monthly recommendations.")
    else:
        current_mask, previous_mask, current_bounds, previous_bounds = recommendation_periods["MoM"]
        current_orders = comparison_base.loc[current_mask]
        previous_orders = comparison_base.loc[previous_mask]

        def order_metrics_for_period(frame):
            orders_count = len(frame)
            if not orders_count:
                return {
                    "Orders Dispensed": 0.0,
                    "Delivery Rate": None,
                    "Order-to-Delivery TAT": None,
                    "Dispatch-to-Delivery TAT": None,
                }
            order_tat = frame["Creation_Delivery_TAT"].mean()
            dispatch_tat = frame["Shipping_TAT"].mean()
            return {
                "Orders Dispensed": float(orders_count),
                "Delivery Rate": float(frame["Is Delivered"].mean() * 100),
                "Order-to-Delivery TAT": float(order_tat) if pd.notna(order_tat) else None,
                "Dispatch-to-Delivery TAT": float(dispatch_tat) if pd.notna(dispatch_tat) else None,
            }

        def costs_for_period(frame, date_column, cost_column, bounds):
            if frame is None or not date_column or not cost_column:
                return 0.0
            if date_column not in frame.columns or cost_column not in frame.columns:
                return 0.0
            start, end = bounds
            in_period = frame[date_column].ge(start) & frame[date_column].lt(end)
            return float(pd.to_numeric(frame.loc[in_period, cost_column], errors="coerce").sum())

        current_metrics = order_metrics_for_period(current_orders)
        previous_metrics = order_metrics_for_period(previous_orders)

        for period_metrics, period_bounds, period_orders in (
            (current_metrics, current_bounds, current_orders),
            (previous_metrics, previous_bounds, previous_orders),
        ):
            fuel_cost = costs_for_period(fuel, col_fuel_date, col_fuel_cost, period_bounds)
            repair_cost = costs_for_period(repairs, col_repair_date, col_repair_cost, period_bounds)
            service_cost = costs_for_period(repairs, col_repair_date, col_engine_cost, period_bounds)
            period_metrics["Fuel Cost"] = fuel_cost
            period_metrics["Repairs and Maintenance Cost"] = repair_cost
            period_metrics["Engine Servicing Cost"] = service_cost
            period_metrics["Average Cost per Order"] = (
                (fuel_cost + repair_cost + service_cost) / len(period_orders)
                if len(period_orders)
                else None
            )

        metric_rules = [
            (
                "Orders Dispensed", True, fmt_num,
                "Prepare inventory and dispatch capacity for the higher demand.",
                "Review client activity, order pipeline and service coverage.",
            ),
            (
                "Delivery Rate", True, lambda value: f"{value:.1f}%",
                "Maintain the practices supporting reliable fulfillment.",
                "Investigate stock availability, picking delays and failed deliveries.",
            ),
            (
                "Order-to-Delivery TAT", False, lambda value: f"{value:.1f} hrs",
                "Keep the faster handoffs and dispatch routines in place.",
                "Inspect order processing and delivery delays by route and facility.",
            ),
            (
                "Dispatch-to-Delivery TAT", False, lambda value: f"{value:.1f} hrs",
                "Sustain the route and dispatch practices reducing delivery time.",
                "Review late routes, dispatch timing and delivery exceptions.",
            ),
            (
                "Fuel Cost", False, money,
                "Check that lower spend did not come from fewer deliveries; sustain efficient routes.",
                "Review fuel outliers, route planning, idling and transaction records.",
            ),
            (
                "Repairs and Maintenance Cost", False, money,
                "Confirm preventive maintenance stayed on schedule despite lower spend.",
                "Investigate repeat repairs, high-cost vehicles and maintenance gaps.",
            ),
            (
                "Engine Servicing Cost", False, money,
                "Verify servicing intervals were met and no work was deferred.",
                "Review vehicle service history and engine-oil replacement intervals.",
            ),
            (
                "Average Cost per Order", False, money,
                "Maintain the operating changes that reduced cost per dispensed order.",
                "Identify the largest fuel or maintenance drivers per dispensed order.",
            ),
        ]

        def display_metric_value(value, formatter):
            return formatter(value) if value is not None else "N/A"

        recommendation_rows = []
        for metric, higher_is_better, formatter, improvement_advice, decline_advice in metric_rules:
            current_value = current_metrics[metric]
            previous_value = previous_metrics[metric]
            if current_value is None or previous_value is None:
                change_text = "N/A"
                advice = "Insufficient order data in one of the months for a meaningful comparison."
            elif previous_value == 0:
                change_text = "New baseline" if current_value else "0.0%"
                advice = (
                    "No prior-month baseline; monitor another month before setting a trend target."
                    if current_value
                    else "No activity in either month; verify the source data and operating schedule."
                )
            else:
                change_pct = pct_change(current_value, previous_value)
                change_text = f"{change_pct:+.1f}%" if change_pct is not None else "N/A"
                if change_pct is None or abs(change_pct) < 1:
                    advice = "Performance was broadly stable; maintain controls and continue monitoring."
                else:
                    improved = change_pct > 0 if higher_is_better else change_pct < 0
                    advice = improvement_advice if improved else decline_advice
            recommendation_rows.append(
                {
                    "Metric": metric,
                    "Current month": display_metric_value(current_value, formatter),
                    "Previous month": display_metric_value(previous_value, formatter),
                    "Change": change_text,
                    "Recommendation": advice,
                }
            )

        current_label = current_bounds[0].strftime("%B %Y")
        previous_label = previous_bounds[0].strftime("%B %Y")
        st.caption(f"{current_label} compared with {previous_label}")
        st.dataframe(pd.DataFrame(recommendation_rows), hide_index=True)


# ---------------------------------------------------------------------------
# PAGE 10: ACCESS ORDERS
# ---------------------------------------------------------------------------
elif selected_page == ":material/receipt_long: Access Orders":
    section_header(
        "Access Orders — HMO Delivery Performance",
        "Last-mile deliveries for HMO enrollees, fed from the Access Orders tab of the logistics workbook.",
    )
    if access is None or access.empty:
        st.info("No Access Orders data found in the logistics workbook.")
    else:
        month_options = sorted(
            access["Month Label"].unique(),
            key=lambda label: pd.to_datetime(label, errors="coerce"),
        )
        f1, f2 = st.columns(2)
        with f1:
            sel_access_months = st.multiselect("Month", month_options, default=month_options)
        with f2:
            hmo_options = sorted(access["HMO"].unique())
            sel_hmos = st.multiselect("HMO", hmo_options, default=hmo_options)

        av = access[access["Month Label"].isin(sel_access_months) & access["HMO"].isin(sel_hmos)].copy()

        def _hrs(value):
            return f"{value:.1f} hrs" if pd.notna(value) else "N/A"

        total_orders = av["SO"].nunique()
        dispatched = int(av["Dispatch_DT"].notna().sum())
        first_attempts = int((av["Attempt"] == 1).sum())
        first_attempt_deliveries = int(((av["Attempt"] == 1) & av["Status"].eq("Delivered")).sum())
        reattempts = int(av["Reattempt"].sum())
        returned_orders = int(av.loc[~av.duplicated("SO"), "Returned_Order"].sum())
        delivered_mask = av["Status"].eq("Delivered")
        tat = av["TAT_Hrs"]
        tat_valid = tat.notna().sum()
        avg_tat = tat.mean()
        sla_count = int((tat <= 4).sum())
        sla_pct = (sla_count / tat_valid * 100) if tat_valid else None
        avg_tat_reattempt = av.loc[av["Reattempt"], "TAT_Hrs"].mean()
        avg_tat_first = av.loc[(av["Attempt"] == 1) & delivered_mask, "TAT_Hrs"].mean()

        render_kpis(
            [
                ("Total Orders Processed", fmt_num(total_orders), "Distinct sales orders on the Access Orders tab.", "📦", BRAND["blue"]),
                ("Total Orders Dispatched", fmt_num(dispatched), "Delivery rows with a dispatch (TIME OUT) recorded.", "🚚", BRAND["amber"]),
                ("First Attempts", fmt_num(first_attempts), "First delivery trip for each sales order.", "✅", BRAND["green"]),
                ("Re-attempts", fmt_num(reattempts), "Trips after a failed delivery on the same order.", "🔁", BRAND["red"]),
                ("Returned Orders", fmt_num(returned_orders), "Orders whose latest status is Returned.", "↩️", BRAND["red"]),
                ("Average TAT", _hrs(avg_tat), "Mean dispatch-to-delivery turnaround.", "⏱", BRAND["blue"]),
                ("Deliveries within 4 hrs SLA", f"{sla_pct:.1f}%" if sla_pct is not None else "N/A", f"{sla_count:,} of {int(tat_valid):,} timed deliveries at or under 4 hours.", "🎯", BRAND["green"]),
                ("Avg TAT (Re-attempted)", _hrs(avg_tat_reattempt), "Mean turnaround on trips after a failed delivery.", "⏱", BRAND["amber"]),
            ]
        )

        section_header("Impact of Re-attempts on TAT", "Average dispatch-to-delivery time, first-trip deliveries versus re-attempts.")
        if pd.notna(avg_tat_first) and pd.notna(avg_tat_reattempt) and avg_tat_first:
            delta_h = avg_tat_reattempt - avg_tat_first
            delta_text = f"{delta_h:+.1f} hrs ({delta_h / avg_tat_first * 100:+.1f}%)"
            delta_note = (
                f"Re-attempted orders take {abs(delta_h):.1f} hrs longer on average — "
                "failed first trips add meaningful turnaround time."
                if delta_h > 0 else
                "Re-attempted orders currently show a lower average TAT than first attempts."
            )
        else:
            delta_text = "N/A"
            delta_note = "Insufficient delivered re-attempt data to measure the impact."
        render_kpis(
            [
                ("Avg TAT · First Attempt", _hrs(avg_tat_first), "Orders delivered on the first trip.", "🥇", BRAND["green"]),
                ("Avg TAT · Re-attempt", _hrs(avg_tat_reattempt), "Orders delivered on a second or later trip.", "🔁", BRAND["red"]),
                ("Re-attempt TAT Impact", delta_text, delta_note, "📊", BRAND["navy"]),
            ]
        )

        section_header("Week-on-Week Trend", "Fri-Thu reporting weeks, based on delivery date.")
        wow = (
            av.assign(
                FirstAttemptDeliveries=((av["Attempt"] == 1) & delivered_mask).astype(int),
                Reattempts=av["Reattempt"].astype(int),
            )
            .groupby(["Year", "Week", "Week Label"], as_index=False)[["FirstAttemptDeliveries", "Reattempts"]]
            .sum()
            .sort_values(["Year", "Week"])
        )
        if wow.empty:
            st.info("No dated access orders for the selected filters.")
        else:
            wow_long = wow.melt(
                id_vars="Week Label",
                value_vars=["FirstAttemptDeliveries", "Reattempts"],
                var_name="Metric",
                value_name="Orders",
            )
            wow_long["Metric"] = wow_long["Metric"].map(
                {"FirstAttemptDeliveries": "First Attempt deliveries", "Reattempts": "Re-attempts"}
            )
            fig = px.line(wow_long, x="Week Label", y="Orders", color="Metric", markers=True,
                          color_discrete_map={"First Attempt deliveries": BRAND["green"], "Re-attempts": BRAND["red"]})
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        section_header("Delivery Performance per HMO")
        hmo_rows = []
        for hmo, group in av.groupby("HMO"):
            group_tat = group["TAT_Hrs"]
            group_tat_valid = group_tat.notna().sum()
            hmo_rows.append(
                {
                    "HMO": hmo,
                    "Volume (Orders)": group["SO"].nunique(),
                    "Delivered": int(group["Status"].eq("Delivered").sum()),
                    "First Attempts": int((group["Attempt"] == 1).sum()),
                    "First Attempt Deliveries": int(((group["Attempt"] == 1) & group["Status"].eq("Delivered")).sum()),
                    "Re-attempts": int(group["Reattempt"].sum()),
                    "Avg TAT (hrs)": round(float(group_tat.mean()), 1) if group_tat_valid else None,
                    "≤ 4 hrs Deliveries (%)": round((group_tat <= 4).sum() / group_tat_valid * 100, 1) if group_tat_valid else None,
                }
            )
        hmo_df = pd.DataFrame(hmo_rows).sort_values("Volume (Orders)", ascending=False)
        st.dataframe(hmo_df, use_container_width=True, hide_index=True)

        section_header("Return Reasons", "Dispatch remarks on orders not delivered (Failed, Returned, Re-attempting, Dropped).")
        not_delivered = av[~delivered_mask & av["Return Reason"].notna()]
        if not_delivered.empty:
            st.info("No return reasons recorded for the selected filters.")
        else:
            reason_summary = not_delivered["Return Reason"].value_counts().reset_index()
            reason_summary.columns = ["Return Reason", "Count"]
            reason_summary["% of Non-Delivered"] = (
                reason_summary["Count"] / len(not_delivered) * 100
            ).round(1)
            reason_summary["% of All Orders"] = (
                reason_summary["Count"] / max(len(av), 1) * 100
            ).round(1)
            st.dataframe(reason_summary, use_container_width=True, hide_index=True)

        section_header("Access Orders Data", f"{len(av):,} delivery rows for the selected filters.")
        access_columns = [
            col for col in ["SO", "HMO", "CLIENT NAME", "Type", "CAPTAIN NAME",
                            "Attempt", "Reattempt", "Status", "Dispatch_DT", "Delivery_DT", "TAT_Hrs",
                            "Return Reason", "Week Label"]
            if col in av.columns
        ]
        st.dataframe(av[access_columns], use_container_width=True, hide_index=True, height=420)
        access_csv = av[access_columns].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Access Orders CSV",
            data=access_csv,
            file_name="drugstoc_access_orders.csv",
            mime="text/csv",
        )
