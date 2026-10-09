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

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="DrugStoc Pharma Logistics Dashboard",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# ASSET CONFIGURATION
# ----------------------------------------------------------------------------
DATA_PATH = r"https://drugstock-my.sharepoint.com/:x:/g/personal/it_drugstoc_com/IQA5yp0kdh82Ra7YcCr-be0vAXufIjkPsYHD4yoBbt6byhs?e=MFF4su&download=1"
COVER_LOGO_URL = r"https://drugstock-my.sharepoint.com/:i:/g/personal/it_drugstoc_com/IQCURjcRKFhMQ4HunFjm4IxrAfQqHn3s3TDz3jUrWgzgw5g?e=dNiGIh&download=1"
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

def get_login_credentials():
    try:
        auth_settings = st.secrets.get("auth", {})
    except StreamlitSecretNotFoundError:
        auth_settings = {}
    username = os.getenv("DASHBOARD_USERNAME") or auth_settings.get("username")
    password = os.getenv("DASHBOARD_PASSWORD") or auth_settings.get("password")
    return username, password

# ----------------------------------------------------------------------------
# THEME (PERMANENT LIGHT MODE)
# ----------------------------------------------------------------------------
DARK = False
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
        [data-testid="stHeader"] {{
            background: transparent !important;
        }}
        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }}
        h1, h2, h3, h4, h5, h6,
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        label {{
            color: var(--ds-text) !important;
        }}
        h1 {{
            font-size: clamp(2rem, 3vw, 3rem) !important;
            letter-spacing: -1.5px !important;
            margin-bottom: .25rem !important;
        }}
        h2 {{
            font-size: 1.55rem !important;
            letter-spacing: -.4px !important;
        }}
        h3 {{
            font-size: 1.15rem !important;
            letter-spacing: -.2px !important;
        }}
        [data-testid="stCaptionContainer"] {{
            color: var(--ds-muted) !important;
        }}
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #06182A 0%, #0A2339 100%) !important;
            border-right: 1px solid rgba(255,255,255,.08);
        }}
        section[data-testid="stSidebar"] * {{
            color: #F1F7FC !important;
        }}
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
        @keyframes ds-pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(22,134,217,.45); }}
            70% {{ box-shadow: 0 0 0 12px rgba(22,134,217,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(22,134,217,0); }}
        }}
        @keyframes ds-spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}
        section[data-testid="stSidebar"] .stButton button {{
            animation: ds-pulse 2.4s infinite;
        }}
        section[data-testid="stSidebar"] .stButton button:active {{
            animation: ds-spin .45s linear;
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] input {{
            display: none;
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{
            gap: 7px;
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
            display: flex;
            width: 100%;
            padding: 10px 14px !important;
            border-radius: 11px !important;
            background: rgba(255,255,255,.08) !important;
            border: 1px solid rgba(255,255,255,.14) !important;
            cursor: pointer;
            transition: background .15s ease, border-color .15s ease, transform .15s ease;
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
            background: rgba(22,134,217,.18) !important;
            border-color: var(--ds-blue) !important;
            transform: translateX(3px);
        }}
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
            background: #1686D9 !important;
            border-color: #1686D9 !important;
            box-shadow: 0 6px 16px rgba(22,134,217,.35);
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
        .hero-subtitle {{
            color: var(--ds-muted) !important;
            margin: 6px 0 0 0;
            font-size: .95rem;
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
            height: 154px;
            min-height: 154px;
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
        .kpi-description {{
            color: var(--ds-muted) !important;
            font-size: .75rem;
            line-height: 1.32;
            margin-top: 7px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
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
        .section-note {{
            color: var(--ds-muted) !important;
            font-size: .76rem;
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
        .legend-decrease {{ background: var(--ds-red, #EF4444); }}
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
        .comparison-change.decrease {{ color: var(--ds-red, #EF4444); }}
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
    </style>
    """,
    unsafe_allow_html=True,
)

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
                [data-testid="stFormSubmitButton"] button:hover,
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
                entered_password = st.text_input(
                    "Password", type="password", key="login_password"
                )
                submitted = st.form_submit_button(
                    "Sign in", type="primary", width="stretch"
                )
            if submitted:
                username_matches = hmac.compare_digest(
                    entered_username, str(configured_username)
                )
                password_matches = hmac.compare_digest(
                    entered_password, str(configured_password)
                )
                if username_matches and password_matches:
                    st.session_state["dashboard_authenticated"] = True
                    st.session_state["authenticated_user"] = entered_username
                    st.rerun()
                st.error("Incorrect username or password.")
    st.stop()

# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
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

def sun_sat_week(dates):
    """Week number, week-start (Sunday) and label-year for a datetime Series.

    Weeks run Sunday-Saturday and are numbered by the ISO week of the week's
    Thursday, so the week containing 1 Oct 2026 is 'W40 - 2026' and early
    January 2026 dates are never labelled as 2025. Round-trips through
    week_start_from_label().
    """
    week_start = dates - pd.to_timedelta((dates.dt.weekday + 1) % 7, unit="D")
    thursday = week_start + pd.Timedelta(days=4)
    iso = thursday.dt.isocalendar()
    return iso["week"], week_start, iso["year"]

def week_start_from_label(year, week):
    """Sunday start of the Sun-Sat week numbered (year, week) by its Thursday."""
    iso_monday = pd.Timestamp.fromisocalendar(int(year), int(week), 1)
    thursday = iso_monday + pd.Timedelta(days=3)
    return thursday - pd.Timedelta(days=(int(thursday.weekday()) + 1) % 7)

def comparison_anchor(data_df):
    """Anchor date for WoW/MoM: selected week > selected month > latest date.

    Uses col_date (the same column the Week/Month slicer labels derive from)
    so the comparison windows line up with the KPI/filter logic.
    """
    date_col = col_date if col_date and col_date in data_df.columns else None
    if selected_week != "All Weeks":
        try:
            _wk = int(selected_week[1:3])
            _yr = int(selected_week.split("-")[-1])
            return week_start_from_label(_yr, _wk)
        except (ValueError, TypeError):
            pass
    if selected_month != "All Months" and "Month Label" in data_df.columns and date_col:
        month_dates = data_df.loc[data_df["Month Label"] == selected_month, date_col].dropna()
        if not month_dates.empty:
            return month_dates.max()
    if date_col:
        dated = data_df[date_col].dropna()
        return dated.max() if not dated.empty else None
    return None

def comparison_periods(data_df):
    # Week/month windows are cut on col_date — the same column behind the
    # slicer Week/Month labels and the Executive KPIs.
    date_col = col_date if col_date and col_date in data_df.columns else None
    if date_col is None:
        return None
    dated = data_df[date_col].dropna()
    if dated.empty:
        return None

    anchor = comparison_anchor(data_df)
    if anchor is None:
        return None
    latest_date = anchor.normalize()
    current_week_start = latest_date - pd.Timedelta(days=(latest_date.weekday() + 1) % 7)
    current_month_start = latest_date.replace(day=1)
    previous_month_end = current_month_start - pd.Timedelta(days=1)
    return {
        "WoW": (
            data_df[date_col].ge(current_week_start)
            & data_df[date_col].lt(current_week_start + pd.Timedelta(days=7)),
            data_df[date_col].ge(current_week_start - pd.Timedelta(days=7))
            & data_df[date_col].lt(current_week_start),
            (current_week_start, current_week_start + pd.Timedelta(days=7)),
            (current_week_start - pd.Timedelta(days=7), current_week_start),
        ),
        "MoM": (
            data_df[date_col].ge(current_month_start)
            & data_df[date_col].lt(current_month_start + pd.offsets.MonthBegin(1)),
            data_df[date_col].ge(previous_month_end.replace(day=1))
            & data_df[date_col].lt(current_month_start),
            (current_month_start, current_month_start + pd.offsets.MonthBegin(1)),
            (previous_month_end.replace(day=1), current_month_start),
        ),
    }

def comparison_metrics(data_df, mask, fuel_bounds=None):
    period = data_df.loc[mask]
    orders = int(period[col_client].count()) if col_client and col_client in period.columns else len(period)
    fuel_cost = 0.0
    if fuel_bounds and fuel is not None and col_fuel_date and col_fuel_cost:
        f_start, f_end = fuel_bounds
        f_mask = (fuel[col_fuel_date] >= f_start) & (fuel[col_fuel_date] < f_end)
        fuel_cost = float(fuel.loc[f_mask, col_fuel_cost].sum())
    return {
        "Order Volume": float(orders),
        "Fulfillment Rate": float(period["Is Delivered"].mean() * 100) if orders else 0.0,
        "TAT: Order to Delivery": float(period["Creation_Delivery_TAT"].mean()) if orders else 0.0,
        "TAT: Dispatch to Delivery": float(period["Shipping_TAT"].mean()) if orders else 0.0,
        "Fuel Cost": fuel_cost,
    }

def comparison_value(metric, value):
    if metric == "Order Volume":
        return f"{value:,.0f}"
    if metric == "Fulfillment Rate":
        return f"{value:.1f}%"
    if metric == "Fuel Cost":
        return money(value)
    return f"{value:.1f} hrs"

def render_comparison_section(data_df):
    periods = comparison_periods(data_df)
    if periods is None:
        show_empty_chart("No dated records are available for WoW/MoM comparison.")
        return

    st.markdown(
        "<div class='comparison-legend'>"
        "<span><i class='legend-current'></i>Current period</span>"
        "<span><i class='legend-previous'></i>Previous period</span>"
        "<span><i class='legend-increase'></i>Improvement (green)</span>"
        "<span><i class='legend-decrease'></i>Decline (red) — for TAT metrics the colours are reversed: faster is green</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    metric_order = [
        "Order Volume",
        "Fulfillment Rate",
        "TAT: Order to Delivery",
        "TAT: Dispatch to Delivery",
        "Fuel Cost",
    ]
    lower_is_better = ("TAT: Order to Delivery", "TAT: Dispatch to Delivery")
    for comparison_name, (current_mask, previous_mask, curr_bounds, prev_bounds) in periods.items():
        current = comparison_metrics(data_df, current_mask, curr_bounds)
        previous = comparison_metrics(data_df, previous_mask, prev_bounds)
        cards = []
        for metric in metric_order:
            current_value = current[metric]
            previous_value = previous[metric]
            change = current_value - previous_value
            change_pct = (change / previous_value * 100) if previous_value else 0.0
            if change == 0:
                change_class, change_color = "", THEME["muted"]
            else:
                improved = (change < 0) if metric in lower_is_better else (change > 0)
                change_class = "increase" if improved else "decrease"
                change_color = BRAND["green"] if improved else BRAND["red"]
            change_symbol = "▲" if change >= 0 else "▼"
            cards.append(
                textwrap.dedent(
                    f"""
                    <div class='comparison-card'>
                        <div class='comparison-title'>{metric}</div>
                        <div class='comparison-values'>
                            <div><span class='comparison-label'>Current</span><strong>{comparison_value(metric, current_value)}</strong></div>
                            <div><span class='comparison-label'>Previous</span><strong>{comparison_value(metric, previous_value)}</strong></div>
                        </div>
                        <div class='comparison-change {change_class}' style='color: {change_color} !important;'>{change_symbol} {abs(change_pct):.1f}% vs previous</div>
                    </div>
                    """
                ).strip()
            )
        st.markdown(f"<h3 class='comparison-period'>{comparison_name}</h3>", unsafe_allow_html=True)
        st.markdown("<div class='comparison-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)

def kpi_card(label, value, description, icon="•", accent=None):
    accent = accent or BRAND["blue"]
    soft = "rgba(22,134,217,.12)" if accent == BRAND["blue"] else ("rgba(16,185,129,.12)" if accent == BRAND["green"] else ("rgba(245,158,11,.13)" if accent == BRAND["amber"] else "rgba(239,68,68,.12)"))
    return f"""
        <div class="kpi-card" style="--kpi-accent:{accent};--kpi-soft:{soft};">
            <div class="kpi-top">
                <div class="kpi-label">{label}</div>
                <div class="kpi-icon">{icon}</div>
            </div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-description">{description}</div>
        </div>
    """

def render_kpis(cards):
    for row_start in range(0, len(cards), 4):
        row = cards[row_start:row_start + 4]
        cols = st.columns(4)
        for col, card in zip(cols, row):
            label, value, description, icon, accent = card
            with col:
                st.markdown(
                    kpi_card(
                        label=label,
                        value=value,
                        description=description,
                        icon=icon,
                        accent=accent,
                    ),
                    unsafe_allow_html=True,
                )

def plotly_theme(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=THEME["plot_bg"],
        plot_bgcolor=THEME["plot_bg"],
        font=dict(color=THEME["text"]),
        margin=dict(l=24, r=24, t=60, b=28),
        hoverlabel=dict(
            bgcolor=THEME["surface"],
            font_color=THEME["text"],
        ),
        autosize=True,
    )
    fig.update_xaxes(
        showgrid=False,
        color=THEME["muted"],
        tickfont=dict(color=THEME["muted"]),
    )
    fig.update_yaxes(
        gridcolor=THEME["grid"],
        color=THEME["muted"],
        tickfont=dict(color=THEME["muted"]),
    )
    return fig

def show_empty_chart(message):
    st.info(message)

def section_header(title, note=""):
    st.markdown(
        f"""
        <div class="section-head">
            <div class="section-title">{title}</div>
            <div class="section-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_performance_trend(data_df):
    trend_df = data_df.dropna(subset=["Created_DT"]).copy()
    if trend_df.empty:
        show_empty_chart("No dated records are available for the performance trend.")
        return

    control_date, control_metric = st.columns(2)
    with control_date:
        date_granularity = st.selectbox(
            "Order Date",
            ["Week", "Month"],
            key="performance_trend_date",
        )
    with control_metric:
        metric_label = st.selectbox(
            "Metric",
            [
                "Fulfillment",
                "TAT: Creation to Delivery",
                "TAT: Dispatch to Delivery",
            ],
            key="performance_trend_metric",
        )

    if date_granularity == "Week":
        trend_df["Period"] = (
            trend_df["Created_DT"]
            - pd.to_timedelta((trend_df["Created_DT"].dt.weekday + 1) % 7, unit="D")
        ).dt.normalize()
        period_format = "%d %b %Y"
    else:
        trend_df["Period"] = trend_df["Created_DT"].dt.to_period("M").dt.start_time
        period_format = "%b %Y"

    metric_columns = {
        "Fulfillment": ("Is Delivered", "Fulfillment Rate (%)"),
        "TAT: Creation to Delivery": ("Creation_Delivery_TAT", "Average TAT (hrs)"),
        "TAT: Dispatch to Delivery": ("Shipping_TAT", "Average TAT (hrs)"),
    }
    value_column, y_axis_title = metric_columns[metric_label]
    trend = (
        trend_df.groupby("Period", as_index=False)[value_column]
        .mean()
        .rename(columns={value_column: "Value"})
        .sort_values("Period")
    )
    if metric_label == "Fulfillment":
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

def find_col(df, candidates, exact_caps_only=False):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    if exact_caps_only:
        for cand in candidates:
            if cand in df.columns:
                return cand

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

def build_timestamp(data_df, date_c, time_c):
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

# ------------
