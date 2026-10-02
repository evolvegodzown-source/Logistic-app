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
    """Week number and week-start (Sunday) for a datetime Series.

    Weeks run Sunday-Saturday; numbering follows strftime %U so labels like
    'W40 - 2026' round-trip through week_start_from_label().
    """
    week_start = dates - pd.to_timedelta((dates.dt.weekday + 1) % 7, unit="D")
    week_num = pd.to_numeric(week_start.dt.strftime("%U"), errors="coerce")
    return week_num, week_start

def week_start_from_label(year, week):
    """Sunday start date of a Sun-Sat 'Www - yyyy' week label."""
    jan1 = pd.Timestamp(year=int(year), month=1, day=1)
    first_sunday = jan1 + pd.Timedelta(days=(6 - jan1.weekday()) % 7)
    return first_sunday + pd.Timedelta(days=(int(week) - 1) * 7)

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

# ----------------------------------------------------------------------------
# KPI PERIOD-COMPARISON HELPERS (WoW / MoM)
# ----------------------------------------------------------------------------
COMPARE_KPIS = [
    "Order Volume",
    "Fulfilment Rate",
    "TAT: Order to Delivery",
    "TAT: Dispatch to Delivery",
    "Fuel Cost",
]

def fuel_cost_between(start, end_exclusive):
    """Total fuel cost within a date window from the Fuel tab (year-filtered)."""
    if fuel is None or not col_fuel_date or not col_fuel_cost:
        return 0.0
    mask = (fuel[col_fuel_date] >= start) & (fuel[col_fuel_date] < end_exclusive)
    return float(fuel.loc[mask, col_fuel_cost].sum())

def compute_period_kpis(frame):
    """Compute the core operational KPIs for a given dataframe slice."""
    orders = int(frame[col_client].count()) if col_client and col_client in frame.columns else len(frame)
    delivered = int(frame["Is Delivered"].sum()) if orders else 0
    fulfil = (delivered / orders * 100.0) if orders else 0.0
    tat_order = frame["Creation_Delivery_TAT"].mean()
    tat_dispatch = frame["Shipping_TAT"].mean()
    return {
        "Order Volume": float(orders),
        "Fulfilment Rate": float(fulfil),
        "TAT: Order to Delivery": float(tat_order) if pd.notna(tat_order) else 0.0,
        "TAT: Dispatch to Delivery": float(tat_dispatch) if pd.notna(tat_dispatch) else 0.0,
    }

def pct_change(current, previous):
    """Percentage change between two values; None if not computable."""
    if previous is None or pd.isna(previous) or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100.0

def format_kpi_value(kpi_name, value):
    """Human-readable formatting per KPI type."""
    if kpi_name == "Order Volume":
        return fmt_num(value)
    if kpi_name == "Fulfilment Rate":
        return f"{value:.1f}%"
    if kpi_name == "Fuel Cost":
        return money(value)
    return f"{value:.1f} hrs"

def comparison_pie(kpi_name, current_val, previous_val, current_label, previous_label):
    """
    Build a donut pie chart comparing the current period against the previous
    period for a single KPI. Slice size = share of the combined total.
    """
    curr = max(float(current_val), 0.0)
    prev = max(float(previous_val), 0.0)
    delta = pct_change(curr, prev)

    # For TAT metrics a decrease is an improvement; for volume/rate an increase is.
    lower_is_better = kpi_name.startswith("TAT")
    if delta is None:
        delta_color = THEME["muted"]
        delta_text = "Δ N/A (no baseline)"
    else:
        improved = (delta < 0) if lower_is_better else (delta > 0)
        delta_color = BRAND["green"] if improved else BRAND["red"]
        arrow = "▲" if delta >= 0 else "▼"
        delta_text = f"{arrow} {abs(delta):.1f}% WoW" if "W" in current_label else f"{arrow} {abs(delta):.1f}% MoM"

    fig = go.Figure(
        data=[
            go.Pie(
                labels=[
                    f"Current · {current_label}",
                    f"Previous · {previous_label}",
                ],
                values=[curr, prev],
                hole=0.58,
                sort=False,
                direction="clockwise",
                marker=dict(colors=[BRAND["blue"], "#4C6A86"]),
                textinfo="label+percent",
                textfont=dict(color=THEME["text"], size=11),
                customdata=[
                    format_kpi_value(kpi_name, curr),
                    format_kpi_value(kpi_name, prev),
                ],
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
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            x=0.5,
            xanchor="center",
            font=dict(size=10, color=THEME["muted"]),
        ),
        height=330,
        margin=dict(l=10, r=10, t=92, b=10),
    )
    return fig

# ----------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_data(path=DATA_PATH):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(path, headers=headers, timeout=25)
    response.raise_for_status()
    source = io.BytesIO(response.content)

    all_sheets = pd.read_excel(source, sheet_name=None)
    combined_df = pd.concat(all_sheets.values(), ignore_index=True)
    fuel_sheet = next(
        (s for n, s in all_sheets.items() if str(n).strip().lower() == "fuel"),
        None,
    )
    assets_sheet = next(
        (s for n, s in all_sheets.items() if str(n).strip().lower() == "assets"),
        None,
    )
    repairs_sheet = next(
        (s for n, s in all_sheets.items() if "repair" in str(n).lower() and "servic" in str(n).lower()),
        None,
    )
    # The orders pipeline must use the shipment sheet alone: concatenating the
    # other sheets lets their columns (e.g. the Repairs sheet's "Date") shadow
    # the shipment columns during automatic column mapping.
    orders_sheet = next(
        (s for n, s in all_sheets.items() if "shipment" in str(n).lower()),
        None,
    )
    orders_df = orders_sheet if orders_sheet is not None else combined_df
    return combined_df, fuel_sheet, assets_sheet, repairs_sheet, orders_df

# ----------------------------------------------------------------------------
# SIDEBAR HEADER & REFRESH BUTTON
# ----------------------------------------------------------------------------
st.sidebar.markdown(
    f"""
    <div class="sidebar-brand">
        <img src="{COVER_LOGO_URL}" alt="DrugStoc logo"/>
        <div class="brand-title">Pharma Logistics Intelligence</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.caption(f"Signed in as {st.session_state.get('authenticated_user', '')}")
if st.sidebar.button("Sign out", key="dashboard_sign_out"):
    st.session_state["dashboard_authenticated"] = False
    st.session_state.pop("authenticated_user", None)
    st.rerun()

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ----------------------------------------------------------------------------
# DATA PROCESSING
# ----------------------------------------------------------------------------
try:
    with st.spinner("🔄 Refreshing live logistics data..."):
        _combined, fuel_raw, assets_raw, repairs_raw, df_raw = load_data(DATA_PATH)
except Exception as exc:
    st.error("Unable to load the logistics workbook.")
    st.info("Verify the live link contains valid Excel tables.")
    with st.expander("Technical details"):
        st.code(str(exc))
    st.stop()

df_raw = df_raw.copy()
df_raw.columns = [str(c).strip() for c in df_raw.columns]

# AUTOMATIC COLUMN MAPPING
col_client = find_col(df_raw, ["Client Name", "Client", "Customer Name", "Pharmacy", "Hospital"])
col_so = find_col(df_raw, ["SO", "Sales Order", "SO Number"])
col_value = find_col(df_raw, ["Order Value", "Value", "Amount", "Sales Value", "Total Value"])
col_qty = find_col(df_raw, ["N0 OF CTN'S", "NO OF CTN'S", "Qty CTN", "Quantity", "CTN"])
col_date = find_col(df_raw, ["Date Column", "Date", "Created Date", "Creation Date", "Order Date"])
col_created_date = find_col(df_raw, ["Created Date", "Created At", "Creation Date", "Order Created At"])
col_create_time = find_col(df_raw, ["Created Time", "Creation Time", "Order Time"])
col_region = find_col(df_raw, ["Region", "Zone", "State", "Territory"])
col_status = find_col(df_raw, ["STATUS"], exact_caps_only=True) or find_col(df_raw, ["STATUS"])
col_captain = find_col(df_raw, ["Captain", "Rider", "Driver", "Captain Name"])
col_vehicle = find_col(df_raw, ["Vehicle Plate No", "Plate Number", "Plate No", "Vehicle", "Vehicle Reg No", "Reg No", "Truck No", "Van Number", "Vehicle No"])
col_order_type = find_col(df_raw, ["Order Type", "Type", "Category"])
col_ship = find_col(df_raw, ["Ship Date", "Dispatch Date", "Pickup Date"])
col_dispatch_time = find_col(df_raw, ["Dispatch Time", "Ship Time", "Time Dispatched"])
col_deliv = find_col(df_raw, ["Delivery Date", "Delivered Date"])
col_delivery_time = find_col(df_raw, ["Delivery Time", "Time Delivered"])

if not col_client:
    st.error("Unable to identify the Client column automatically in the dataset.")
    st.stop()

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
    _wk_num, _wk_start = sun_sat_week(df[col_date])
    df["Week"] = _wk_num.fillna(0).astype(int)
    df["Year"] = df[col_date].dt.year.fillna(0).astype(int)
    df["Month"] = df[col_date].dt.month.fillna(0).astype(int)
    df["Month Label"] = df[col_date].dt.strftime("%B %Y").fillna("Unassigned Date")
    df["Week Label"] = (
        "W" + df["Week"].astype(str).str.zfill(2)
        + " - " + _wk_start.dt.year.fillna(0).astype(int).astype(str)
    )
else:
    df["Month Label"] = "Unassigned Date"
    df["Week Label"] = "Unassigned Date"

df[col_value] = pd.to_numeric(df[col_value], errors="coerce").fillna(0)
df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(0)
df["Created_DT"] = build_timestamp(df, col_created_date or col_date, col_create_time)
df["Delivery_DT"] = build_timestamp(df, col_deliv, col_delivery_time)
dispatch_date_col = col_ship if col_ship and col_ship in df.columns else col_date
df["Dispatch_DT"] = build_timestamp(df, dispatch_date_col, col_dispatch_time)

df["Creation_Delivery_TAT"] = (
    (df["Delivery_DT"] - df["Created_DT"]).dt.total_seconds() / 3600.0
)
df["Creation_Delivery_TAT"] = df["Creation_Delivery_TAT"].apply(
    lambda x: x if pd.notna(x) and x >= 0 else np.nan
)
df["Shipping_TAT"] = (
    (df["Delivery_DT"] - df["Dispatch_DT"]).dt.total_seconds() / 3600.0
)
df["Shipping_TAT"] = df["Shipping_TAT"].apply(
    lambda x: x if pd.notna(x) and x >= 0 else np.nan
)

# Status mapping strictly tied to the STATUS column
if col_status and col_status in df.columns:
    df[col_status] = df[col_status].astype(str).str.strip().str.title()
    DELIVERED_LABELS = {"Delivered", "Complete", "Completed", "Successful"}
    df["Is Delivered"] = df[col_status].isin(DELIVERED_LABELS)
else:
    df[col_status] = "Unassigned"
    df["Is Delivered"] = False

if col_date and col_date in df.columns:
    df = df.loc[df[col_date].dt.year == FILTER_YEAR].copy()

# ----------------------------------------------------------------------------
# FUEL SHEET PROCESSING (Fueling Cost tab)
# ----------------------------------------------------------------------------
fuel = None
col_fuel_date = None
col_fuel_cost = None
if fuel_raw is not None and not fuel_raw.empty:
    fuel = fuel_raw.copy()
    fuel.columns = [str(c).strip() for c in fuel.columns]
    col_fuel_date = find_col(fuel, ["DATE", "Date", "Fueling Date"])
    # NOTE: the sheet column is labelled "Fueling/Ltr" but the values are
    # fueling spend in naira (e.g. 40000), not litres.
    col_fuel_cost = find_col(fuel, ["Fueling/Ltr", "Fueling", "Fueling Cost", "Amount", "Cost"])
    col_fuel_captain = find_col(fuel, ["Captains Name", "Captain", "Captain Name", "Rider"])
    col_fuel_plate = find_col(fuel, ["PlateNumber", "Plate Number", "Plate No", "Vehicle Plate No"])
    col_fuel_model = find_col(fuel, ["Model", "Vehicle Model"])

    if col_fuel_date and col_fuel_date in fuel.columns:
        fuel[col_fuel_date] = pd.to_datetime(fuel[col_fuel_date], errors="coerce")
        fuel["Fuel Month Label"] = fuel[col_fuel_date].dt.strftime("%B %Y").fillna("Unassigned Date")
        _fwk_num, _fwk_start = sun_sat_week(fuel[col_fuel_date])
        fuel["Fuel Week"] = _fwk_num.fillna(0).astype(int)
        fuel["Fuel Year"] = _fwk_start.dt.year.fillna(0).astype(int)
        fuel["Fuel Week Label"] = (
            "W" + fuel["Fuel Week"].astype(str).str.zfill(2) + " - " + fuel["Fuel Year"].astype(str)
        )
        fuel = fuel.loc[fuel[col_fuel_date].dt.year == FILTER_YEAR].copy()
    if col_fuel_cost and col_fuel_cost in fuel.columns:
        fuel[col_fuel_cost] = pd.to_numeric(fuel[col_fuel_cost], errors="coerce")

# ----------------------------------------------------------------------------
# ASSETS SHEET PROCESSING (plate number -> coverage area mapping)
# ----------------------------------------------------------------------------
plate_to_area = {}
if assets_raw is not None and not assets_raw.empty:
    assets_df = assets_raw.copy()
    # The Assets sheet ships with its real header on the first data row
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
    if col_assets_plate and col_assets_area:
        pairs = (
            assets_df[[col_assets_plate, col_assets_area]]
            .dropna(subset=[col_assets_plate])
            .assign(_plate=lambda x: x[col_assets_plate].astype(str).str.strip().str.upper())
        )
        pairs = pairs[(pairs["_plate"] != "") & pairs[col_assets_area].notna()]
        plate_to_area = dict(zip(pairs["_plate"], pairs[col_assets_area].astype(str).str.strip()))

# ----------------------------------------------------------------------------
# REPAIRS AND SERVICING SHEET PROCESSING (coverage recheck + cost KPIs)
# ----------------------------------------------------------------------------
repairs = None
col_repair_date = None
col_repair_cost = None
col_engine_cost = None
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

    if col_repair_date and col_repair_date in repairs.columns:
        repairs[col_repair_date] = pd.to_datetime(repairs[col_repair_date], errors="coerce")
        repairs["Repair Month Label"] = repairs[col_repair_date].dt.strftime("%B %Y").fillna("Unassigned Date")
        _rwk_num, _rwk_start = sun_sat_week(repairs[col_repair_date])
        repairs["Repair Week"] = _rwk_num.fillna(0).astype(int)
        repairs["Repair Year"] = _rwk_start.dt.year.fillna(0).astype(int)
        repairs["Repair Week Label"] = (
            "W" + repairs["Repair Week"].astype(str).str.zfill(2) + " - " + repairs["Repair Year"].astype(str)
        )
        repairs = repairs.loc[repairs[col_repair_date].dt.year == FILTER_YEAR].copy()
    for cost_col in (col_repair_cost, col_engine_cost):
        if cost_col and cost_col in repairs.columns:
            repairs[cost_col] = pd.to_numeric(repairs[cost_col], errors="coerce")

    # Coverage recheck: add plates from this tab that the Assets sheet missed
    if col_repair_plate and col_repair_area:
        rpairs = (
            repairs[[col_repair_plate, col_repair_area]]
            .dropna(subset=[col_repair_plate])
            .assign(_plate=lambda x: x[col_repair_plate].astype(str).str.strip().str.upper())
        )
        rpairs = rpairs[(rpairs["_plate"] != "") & rpairs[col_repair_area].notna()]
        for plate, area in zip(rpairs["_plate"], rpairs[col_repair_area].astype(str).str.strip()):
            plate_to_area.setdefault(plate, area)

# ----------------------------------------------------------------------------
# FILTER OPTIONS (rendered as a top filter bar below the hero)
# ----------------------------------------------------------------------------
month_labels = set(df["Month Label"].dropna().astype(str))
week_labels = set(df["Week Label"].dropna().astype(str))
for date_view, month_label_col, week_label_col in (
    (fuel, "Fuel Month Label", "Fuel Week Label"),
    (repairs, "Repair Month Label", "Repair Week Label"),
):
    if date_view is not None:
        if month_label_col in date_view.columns:
            month_labels.update(date_view[month_label_col].dropna().astype(str))
        if week_label_col in date_view.columns:
            week_labels.update(date_view[week_label_col].dropna().astype(str))

month_options = ["All Months"] + sorted(
    month_labels,
    key=lambda label: pd.to_datetime(label, format="%B %Y", errors="coerce"),
    reverse=True,
)
week_options = ["All Weeks"] + sorted(week_labels, reverse=True)
region_options = ["All Regions"] + sorted(df[col_region].dropna().astype(str).unique().tolist(), reverse=True)
status_options = ["All Statuses"] + sorted(df[col_status].dropna().unique().tolist(), reverse=True)
order_type_options = ["All Order Types"]
if col_order_type and col_order_type in df.columns:
    order_type_options += sorted(df[col_order_type].dropna().astype(str).str.strip().unique().tolist(), reverse=True)

def clear_filter_selections():
    st.session_state["filter_month"] = "All Months"
    st.session_state["filter_week"] = "All Weeks"
    st.session_state["filter_region"] = "All Regions"
    st.session_state["filter_status"] = "All Statuses"
    st.session_state["filter_order_type"] = "All Order Types"

# ----------------------------------------------------------------------------
# HERO HEADER
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-top">
            <img class="hero-logo" src="{COVER_LOGO_URL}" alt="DrugStoc logo"/>
            <div>
                <div class="eyebrow">Healthcare Supply Chain Monitor</div>
                <div class="hero-title">DrugStoc Pharma Logistics Dashboard</div>
                <div class="hero-subtitle">
                    Executive visibility across order fulfillment, delivery turnaround,
                    shipment volume and field-captain performance.
                </div>
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

# ----------------------------------------------------------------------------
# TOP FILTER BAR (slicers shared across all tabs)
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="section-head" style="margin-top:0">
        <div class="section-title">🎛️ Filters</div>
        <div class="section-note">Slicers apply to every page below</div>
    </div>
    """,
    unsafe_allow_html=True,
)
f_month, f_week, f_region, f_status, f_type, f_clear = st.columns([1.1, 1.1, 1, 1.2, 1.1, 0.9])
with f_month:
    selected_month = st.selectbox("Month", month_options, key="filter_month")
with f_week:
    selected_week = st.selectbox("Week", week_options, key="filter_week")
with f_region:
    selected_region = st.selectbox("Region / Hub", region_options, key="filter_region")
with f_status:
    selected_status = st.selectbox("Delivery Status (STATUS)", status_options, key="filter_status")
with f_type:
    selected_order_type = st.selectbox("Order Type", order_type_options, key="filter_order_type")
with f_clear:
    st.button(
        "Clear filters",
        on_click=clear_filter_selections,
        key="clear_filter_selections",
        type="primary",
    )

filtered = df.copy()
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

comparison_base = df.copy()
if selected_region != "All Regions":
    comparison_base = comparison_base[comparison_base[col_region].astype(str) == selected_region]
if selected_status != "All Statuses":
    comparison_base = comparison_base[comparison_base[col_status] == selected_status]
if selected_order_type != "All Order Types" and col_order_type:
    comparison_base = comparison_base[comparison_base[col_order_type].astype(str).str.strip() == selected_order_type]

# Fuel rows filtered by the Month/Week slicers (shared by the overview KPI and
# the Fueling Cost page; fuel carries its own DATE so Region/Status don't apply)
fuel_view = fuel.copy() if fuel is not None else None
if fuel_view is not None:
    if selected_month != "All Months" and "Fuel Month Label" in fuel_view.columns:
        fuel_view = fuel_view[fuel_view["Fuel Month Label"] == selected_month]
    if selected_week != "All Weeks" and "Fuel Week Label" in fuel_view.columns:
        fuel_view = fuel_view[fuel_view["Fuel Week Label"] == selected_week]

# ----------------------------------------------------------------------------
# SIDEBAR PAGE NAVIGATION
# ----------------------------------------------------------------------------
PAGES = [
    "📊 Executive Overview",
    "📈 WoW / MoM Comparison",
    "🚛 Vehicles & Order Count",
    "⛽ Fueling Cost",
    "🧑‍✈️ Captain Efficiency",
    "🗂️ Audit Data",
    "🛠️ Asset Management",
    "💰 Cost Control",
    "💡 Recommendations",
]

selected_page = st.sidebar.radio(
    "Dashboard pages",
    PAGES,
    label_visibility="collapsed",
)

# ============================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ============================================================================
if selected_page == "📊 Executive Overview":
    total_orders = int(filtered[col_client].count()) if col_client else len(filtered)
    total_value = filtered[col_value].sum()
    delivered_count = int(filtered["Is Delivered"].sum())
    delivery_pct = (delivered_count / total_orders * 100) if total_orders else 0
    avg_creation_to_deliv_tat = filtered["Creation_Delivery_TAT"].mean()
    avg_shipping_tat = filtered["Shipping_TAT"].mean()

    # Contract: order-to-delivery TAT must be within 24 hrs
    CONTRACT_TAT_HOURS = 24.0
    if pd.notna(avg_creation_to_deliv_tat):
        tat_within_contract = avg_creation_to_deliv_tat <= CONTRACT_TAT_HOURS
        tat_diff = avg_creation_to_deliv_tat - CONTRACT_TAT_HOURS
        tat_status_color = BRAND["green"] if tat_within_contract else BRAND["red"]
        tat_contract_accent = tat_status_color
        tat_contract_desc = (
            f"Contract: {CONTRACT_TAT_HOURS:.0f} hrs · "
            f"<strong style='color:{tat_status_color}'>"
            f"{'Under' if tat_within_contract else 'Exceeded'} by {abs(tat_diff):.1f} hrs"
            f"</strong>"
        )
    else:
        tat_contract_accent = BRAND["amber"]
        tat_contract_desc = "Average time from order creation to delivery."
    total_ctns = filtered[col_qty].sum()
    avg_order_value = total_value / total_orders if total_orders else 0
    facilities = filtered[col_client].nunique()

    # Fuel KPIs (from the Fuel tab; respects the Month/Week slicers)
    fuel_cost_total = fuel_view[col_fuel_cost].sum() if (fuel_view is not None and col_fuel_cost) else 0
    top_plate = None
    top_plate_cost = 0
    if fuel_view is not None and col_fuel_cost and col_fuel_plate:
        plate_totals = (
            fuel_view.dropna(subset=[col_fuel_plate])
            .assign(_plate=lambda x: x[col_fuel_plate].astype(str).str.strip().str.upper())
            .groupby("_plate")[col_fuel_cost]
            .sum()
        )
        if len(plate_totals):
            top_plate = plate_totals.idxmax()
            top_plate_cost = plate_totals.max()

    # Total assets = distinct plate numbers across dispatch records and the Fuel tab
    asset_plates = set()
    if col_vehicle:
        asset_plates |= set(
            filtered[col_vehicle].dropna().astype(str).str.strip().str.upper().unique()
        )
    if fuel_view is not None and col_fuel_plate:
        asset_plates |= set(
            fuel_view[col_fuel_plate].dropna().astype(str).str.strip().str.upper().unique()
        )
    total_assets = len(asset_plates)

    # Repairs & servicing totals (respect the Month/Week slicers)
    repairs_view = repairs.copy() if repairs is not None else None
    if repairs_view is not None:
        if selected_month != "All Months" and "Repair Month Label" in repairs_view.columns:
            repairs_view = repairs_view[repairs_view["Repair Month Label"] == selected_month]
        if selected_week != "All Weeks" and "Repair Week Label" in repairs_view.columns:
            repairs_view = repairs_view[repairs_view["Repair Week Label"] == selected_week]
    repair_maint_total = (
        repairs_view[col_repair_cost].sum() if (repairs_view is not None and col_repair_cost) else 0.0
    )
    engine_service_total = (
        repairs_view[col_engine_cost].sum() if (repairs_view is not None and col_engine_cost) else 0.0
    )
    total_operational_cost = fuel_cost_total + repair_maint_total + engine_service_total
    avg_operational_cost_per_order = (
        total_operational_cost / total_orders if total_orders else None
    )

    section_header("Order and Operations KPIs")
    render_kpis(
        [
            (
                "Total Dispensed Orders",
                fmt_num(total_orders),
                "Count of Count Client Name (All records including duplicates).",
                "📦",
                BRAND["blue"],
            ),
            (
                "Total Order Value",
                money(total_value),
                "Sum of Order Value across all filtered orders.",
                "💰",
                BRAND["green"],
            ),
            (
                "Active Health Facilities",
                fmt_num(facilities),
                "Unique pharmacies, hospitals or facilities served.",
                "🏥",
                BRAND["blue"],
            ),
            (
                "Order → Delivery TAT",
                f"{avg_creation_to_deliv_tat:.1f} hrs" if pd.notna(avg_creation_to_deliv_tat) else "N/A",
                tat_contract_desc,
                "⏱",
                tat_contract_accent,
            ),
            (
                "Dispatch → Delivery TAT",
                f"{avg_shipping_tat:.1f} hrs" if pd.notna(avg_shipping_tat) else "N/A",
                "Average time from dispatch to successful delivery.",
                "🚚",
                BRAND["amber"],
            ),
            (
                "Total Volume Shipped",
                f"{total_ctns:,.0f} CTN",
                "Total cartons recorded across filtered orders.",
                "📦",
                BRAND["blue"],
            ),
            (
                "Total Operational Assets (Vehicle)",
                fmt_num(total_assets),
                "Distinct plate numbers across dispatch records and the Fuel tab.",
                "🚛",
                BRAND["blue"],
            ),
        ]
    )

    section_header("Operational Cost KPIs", "Fuel, repairs and servicing costs use the selected Month/Week filters.")
    render_kpis(
        [
            (
                "Total Fueling Cost",
                money(fuel_cost_total),
                (
                    f"Highest consumption: {top_plate} · {money(top_plate_cost)}"
                    if top_plate
                    else "No fuel records match the current Month/Week filters."
                ),
                "⛽",
                BRAND["green"],
            ),
            (
                "Repairs and Maintenance Cost",
                money(repair_maint_total),
                "Sum of the Maintenance & Repair column on the Repairs and Servicing tab.",
                "🔧",
                BRAND["amber"],
            ),
            (
                "Engine Servicing Cost",
                money(engine_service_total),
                "Sum of the Engine Oil / Servicing column on the Repairs and Servicing tab.",
                "🛢",
                BRAND["amber"],
            ),
            (
                "Average Cost per Order",
                money(avg_operational_cost_per_order) if avg_operational_cost_per_order is not None else "N/A",
                "Fuel, repairs and engine servicing costs divided by total dispensed orders.",
                "💸",
                BRAND["teal"],
            ),
        ]
    )

    section_header(
        "Week-on-Week & Month-on-Month Performance",
        "Green indicates improvement, red indicates decline. For TAT metrics the colours are reversed — a decrease in turnaround time is green.",
    )
    # WoW/MoM anchored to the selected week/month (or the latest week when
    # filters are cleared); previous periods resolve against comparison_base
    render_comparison_section(comparison_base)

    section_header("Performance Trend", "Track fulfillment and delivery turnaround over time.")
    render_performance_trend(filtered)

    section_header("Network Performance")
    col_a, col_b = st.columns(2)
    with col_a:
        reg_summary = (
            filtered.groupby(col_region, dropna=False)[col_client]
            .count()
            .reset_index(name="Orders")
            .sort_values("Orders", ascending=False)
        )
        reg_summary[col_region] = reg_summary[col_region].fillna("Unassigned").astype(str)
        if reg_summary.empty:
            show_empty_chart("No regional data is available.")
        else:
            fig = px.bar(
                reg_summary,
                x="Orders",
                y=col_region,
                orientation="h",
                text="Orders",
                title="Orders by Region / Hub",
                color_discrete_sequence=[BRAND["blue"]],
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                showlegend=False,
                height=max(360, min(650, 80 + len(reg_summary) * 36)),
                xaxis_title="Orders",
                yaxis_title=None,
            )
            st.plotly_chart(plotly_theme(fig), use_container_width=True)

    with col_b:
        status_summary = filtered[col_status].fillna("Unknown").astype(str).value_counts().reset_index()
        status_summary.columns = ["Status", "Orders"]
        if status_summary.empty:
            show_empty_chart("No status data available.")
        else:
            fig = px.pie(
                status_summary,
                names="Status",
                values="Orders",
                hole=0.56,
                title="Fulfillment Status Mix (STATUS)",
                color_discrete_sequence=[
                    BRAND["green"],
                    BRAND["blue"],
                    BRAND["amber"],
                    BRAND["red"],
                    "#8B5CF6",
                ],
            )
            st.plotly_chart(plotly_theme(fig), use_container_width=True)

    section_header(
        "Coverage Area Analysis",
        "Order count and fuel cost grouped by vehicle coverage area (from the Assets tab).",
    )
    if col_vehicle:
        order_area = (
            filtered.dropna(subset=[col_vehicle])
            .assign(_area=lambda x: x[col_vehicle].map(
                lambda p: plate_to_area.get(str(p).strip().upper(), "Unassigned")
            ))
            .groupby("_area")[col_client]
            .count()
            .reset_index(name="Orders")
        )
    else:
        order_area = pd.DataFrame({"_area": ["Unassigned"], "Orders": [len(filtered)]})

    if fuel_view is not None and col_fuel_cost and col_fuel_plate:
        fuel_area = (
            fuel_view.dropna(subset=[col_fuel_plate])
            .assign(_area=lambda x: x[col_fuel_plate].map(
                lambda p: plate_to_area.get(str(p).strip().upper(), "Unassigned")
            ))
            .groupby("_area")[col_fuel_cost]
            .sum()
            .reset_index(name="Fuel Cost")
        )
    else:
        fuel_area = pd.DataFrame(columns=["_area", "Fuel Cost"])

    area_analysis = pd.merge(order_area, fuel_area, on="_area", how="outer").fillna(0)
    area_analysis = area_analysis.rename(columns={"_area": "Coverage Area"}).sort_values(
        "Orders", ascending=False
    )

    if area_analysis.empty:
        show_empty_chart("No coverage area data available.")
    else:
        fig = go.Figure()
        fig.add_bar(
            x=area_analysis["Coverage Area"],
            y=area_analysis["Orders"],
            name="Order Count",
            marker_color=BRAND["blue"],
        )
        fig.add_bar(
            x=area_analysis["Coverage Area"],
            y=area_analysis["Fuel Cost"],
            name="Fuel Cost (₦)",
            marker_color=BRAND["green"],
            yaxis="y2",
        )
        fig.update_layout(
            barmode="group",
            height=420,
            yaxis=dict(title="Order Count"),
            yaxis2=dict(
                title=dict(text="Fuel Cost (₦)", font=dict(color=BRAND["green"])),
                overlaying="y",
                side="right",
                tickfont=dict(color=BRAND["green"]),
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"),
        )
        st.plotly_chart(plotly_theme(fig), use_container_width=True)

# ============================================================================
# TAB 2: WoW / MoM KPI COMPARISON
# ============================================================================
if selected_page == "📈 WoW / MoM Comparison":
    section_header(
        "Week-on-Week & Month-on-Month Performance",
        "Pie-chart share comparison across the core operational KPIs plus fuel cost",
    )

    # Comparison base respects Region/Status/Order Type slicers; the period
    # anchor comes from the selected Week/Month so the previous period
    # (which falls outside the selection) still has data to compare against.
    comp_df = comparison_base.copy()

    # Reference date: selected week > latest date of selected month > latest data
    anchor = comparison_anchor(comp_df)
    if anchor is not None:
        ref_date = anchor
    elif col_date and col_date in comp_df.columns and comp_df[col_date].notna().any():
        ref_date = comp_df[col_date].max()
    else:
        ref_date = pd.Timestamp.today()

    # ------------------------- WEEK BOUNDARIES -------------------------
    week_start = ref_date - pd.Timedelta(days=(int(ref_date.weekday()) + 1) % 7)
    prev_week_start = week_start - pd.Timedelta(days=7)
    prev_week_end = week_start - pd.Timedelta(days=1)

    curr_week_df = comp_df[(comp_df[col_date] >= week_start) & (comp_df[col_date] <= ref_date)]
    prev_week_df = comp_df[(comp_df[col_date] >= prev_week_start) & (comp_df[col_date] <= prev_week_end)]

    curr_week_label = f"W{int(week_start.strftime('%U')):02d}"
    prev_week_label = f"W{int(prev_week_start.strftime('%U')):02d}"

    # ------------------------- MONTH BOUNDARIES ------------------------
    month_start = ref_date.replace(day=1)
    prev_month_end = month_start - pd.Timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    curr_month_df = comp_df[(comp_df[col_date] >= month_start) & (comp_df[col_date] <= ref_date)]
    prev_month_df = comp_df[(comp_df[col_date] >= prev_month_start) & (comp_df[col_date] <= prev_month_end)]

    curr_month_label = month_start.strftime("%b %Y")
    prev_month_label = prev_month_start.strftime("%b %Y")

    # --------------------------- WEEK-ON-WEEK --------------------------
    st.markdown(
        f"**📅 Week-on-Week** — {curr_week_label} vs {prev_week_label} &nbsp;|&nbsp; "
        f"<span style='color:{THEME['muted']};font-size:.8rem'>"
        f"{week_start:%d %b} – {ref_date:%d %b %Y} vs {prev_week_start:%d %b} – {prev_week_end:%d %b %Y}</span>",
        unsafe_allow_html=True,
    )
    wow_curr = compute_period_kpis(curr_week_df)
    wow_prev = compute_period_kpis(prev_week_df)
    wow_curr["Fuel Cost"] = fuel_cost_between(week_start, ref_date + pd.Timedelta(days=1))
    wow_prev["Fuel Cost"] = fuel_cost_between(prev_week_start, week_start)

    wow_cols = st.columns(len(COMPARE_KPIS))
    for col, kpi in zip(wow_cols, COMPARE_KPIS):
        with col:
            st.plotly_chart(
                comparison_pie(kpi, wow_curr[kpi], wow_prev[kpi], curr_week_label, prev_week_label),
                use_container_width=True,
            )

    st.markdown("---")

    # -------------------------- MONTH-ON-MONTH -------------------------
    st.markdown(
        f"**🗓️ Month-on-Month** — {curr_month_label} vs {prev_month_label} &nbsp;|&nbsp; "
        f"<span style='color:{THEME['muted']};font-size:.8rem'>"
        f"{month_start:%d %b} – {ref_date:%d %b %Y} vs {prev_month_start:%d %b} – {prev_month_end:%d %b %Y}</span>",
        unsafe_allow_html=True,
    )
    mom_curr = compute_period_kpis(curr_month_df)
    mom_prev = compute_period_kpis(prev_month_df)
    mom_curr["Fuel Cost"] = fuel_cost_between(month_start, ref_date + pd.Timedelta(days=1))
    mom_prev["Fuel Cost"] = fuel_cost_between(prev_month_start, month_start)

    mom_cols = st.columns(len(COMPARE_KPIS))
    for col, kpi in zip(mom_cols, COMPARE_KPIS):
        with col:
            st.plotly_chart(
                comparison_pie(kpi, mom_curr[kpi], mom_prev[kpi], curr_month_label, prev_month_label),
                use_container_width=True,
            )

    st.markdown("---")
    st.caption(
        "ℹ️ Slice size represents each period's share of the combined total. "
        "TAT deltas are colour-coded green when turnaround improves (decreases). "
        "Fuel Cost deltas follow the volume rule (increase = green). "
        "Comparison respects the sidebar slicers (Month, Week, Region, Status, Order Type)."
    )

# ============================================================================
# TAB 3: MONTH-ON-MONTH RECOMMENDATIONS
# ============================================================================
if selected_page == "💡 Recommendations":
    section_header(
        "Month-on-Month Recommendations",
        "Latest month versus the previous month, using the selected Region, Status and Order Type.",
    )
    recommendation_periods = comparison_periods(comparison_base)
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
                    "Fulfillment Rate": None,
                    "Order-to-Delivery TAT": None,
                    "Dispatch-to-Delivery TAT": None,
                }
            order_tat = frame["Creation_Delivery_TAT"].mean()
            dispatch_tat = frame["Shipping_TAT"].mean()
            return {
                "Orders Dispensed": float(orders_count),
                "Fulfillment Rate": float(frame["Is Delivered"].mean() * 100),
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
            repair_cost = costs_for_period(
                repairs, col_repair_date, col_repair_cost, period_bounds
            )
            service_cost = costs_for_period(
                repairs, col_repair_date, col_engine_cost, period_bounds
            )
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
                "Fulfillment Rate", True, lambda value: f"{value:.1f}%",
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

# ============================================================================
# TAB 4: VEHICLES & ORDER COUNT
# ============================================================================
if selected_page == "🚛 Vehicles & Order Count":
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
                veh_df.assign(**{
                    "Vehicle Plate No": veh_df[col_vehicle].astype(str).str.strip().str.upper()
                })
                .groupby("Vehicle Plate No", dropna=False)
                .agg(
                    Orders_Dispatched=(col_client, "count"),
                    Delivered_Orders=("Is Delivered", "sum"),
                    Total_Order_Value=(col_value, "sum"),
                )
                .reset_index()
                .sort_values("Orders_Dispatched", ascending=False)
            )
            veh_summary["Fulfillment_Rate"] = (
                veh_summary["Delivered_Orders"] / veh_summary["Orders_Dispatched"] * 100
            ).round(1)
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
                    "Fulfillment_Rate": "Fulfillment Rate (%)",
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

# ============================================================================
# TAB 4: FUELING COST
# ============================================================================
if selected_page == "⛽ Fueling Cost":
    section_header(
        "Fueling Cost",
        "Fuel spend picked from the Fuel tab of the logistics_DB workbook.",
    )

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

# ============================================================================
# TAB 5: CAPTAIN PERFORMANCE
# ============================================================================
if selected_page == "🧑‍✈️ Captain Efficiency":
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

# ============================================================================
# TAB 6: AUDIT DATA
# ============================================================================
if selected_page == "🗂️ Audit Data":
    section_header("Filtered Audit Logs", f"{len(filtered):,} records shown from {len(df):,} total records.")
    st.dataframe(filtered, use_container_width=True, hide_index=True, height=600)
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Filtered Audit CSV",
        data=csv,
        file_name="drugstoc_filtered_logistics_audit.csv",
        mime="text/csv",
    )

# ============================================================================
# TAB 7: ASSET MANAGEMENT
# ============================================================================
if selected_page == "🛠️ Asset Management":
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

# ============================================================================
# TAB 8: COST CONTROL
# ============================================================================
if selected_page == "💰 Cost Control":
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
