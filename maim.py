import io
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

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

BRAND = {
    "blue": "#1686D9",
    "blue_dark": "#0B5FA5",
    "green": "#10B981",
    "navy": "#071A2D",
    "teal": "#14B8A6",
    "amber": "#F59E0B",
    "red": "#EF4444",
}

# ----------------------------------------------------------------------------
# THEME
# ----------------------------------------------------------------------------
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "Light"

ui_theme = st.sidebar.selectbox(
    "🎨 Dashboard Theme",
    ["Light", "Dark"],
    index=["Light", "Dark"].index(st.session_state.ui_theme),
    key="ui_theme_picker",
)
st.session_state.ui_theme = ui_theme

DARK = True  # Permanently dark theme

THEME = {
    "page": "#071421" if DARK else "#F4F8FC",
    "surface": "#0E2236" if DARK else "#FFFFFF",
    "surface_2": "#132B42" if DARK else "#F8FBFF",
    "text": "#F4F8FC" if DARK else "#102337",
    "muted": "#A9BCD0" if DARK else "#61758A",
    "border": "rgba(255,255,255,.10)" if DARK else "#DCE6EF",
    "grid": "rgba(255,255,255,.10)" if DARK else "#E5EDF4",
    "plot_bg": "#0E2236" if DARK else "#FFFFFF",
    "accent_soft": "rgba(22,134,217,.18)" if DARK else "#EAF5FF",
}

st.markdown(
    f"""
    <style>
        :root {{
            --ds-blue: {BRAND["blue"]};
            --ds-green: {BRAND["green"]};
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
                radial-gradient(circle at 10% 0%, rgba(22,134,217,.10), transparent 28%),
                radial-gradient(circle at 90% 0%, rgba(16,185,129,.08), transparent 25%),
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

        /* Global typography / header visibility */
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

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #06182A 0%, #0A2339 100%) !important;
            border-right: 1px solid rgba(255,255,255,.08);
        }}

        section[data-testid="stSidebar"] * {{
            color: #F1F7FC !important;
        }}

        section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
        section[data-testid="stSidebar"] .stFileUploader,
        section[data-testid="stSidebar"] .stButton button {{
            background: rgba(255,255,255,.08) !important;
            border: 1px solid rgba(255,255,255,.14) !important;
            border-radius: 10px !important;
        }}

        section[data-testid="stSidebar"] .stButton button:hover {{
            border-color: var(--ds-blue) !important;
            background: rgba(22,134,217,.18) !important;
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

        /* Hero */
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

        /* KPI cards */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(220px, 1fr));
            gap: 14px;
            margin: 10px 0 8px 0;
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

        /* Tabs */
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

        [data-testid="stExpander"] {{
            background: var(--ds-surface) !important;
            border: 1px solid var(--ds-border) !important;
            border-radius: 14px !important;
        }}

        .stButton button {{
            border-radius: 10px !important;
            font-weight: 800 !important;
        }}

        @media (max-width: 1100px) {{
            .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}

        @media (max-width: 650px) {{
            .kpi-grid {{ grid-template-columns: 1fr; }}
            .hero-top {{ align-items: flex-start; }}
            .hero-logo {{ width: 60px; height: 60px; }}
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# DEPENDENCY NOTE
# ----------------------------------------------------------------------------
# Captain table uses Streamlit column_config instead of pandas Styler
# background_gradient(), so Matplotlib is NOT required.

# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def money(value):
    return f"₦{value:,.0f}"

def fmt_num(value):
    return f"{value:,.0f}"

def kpi_card(label, value, description, icon="•", accent=None):
    accent = accent or BRAND["blue"]
    soft = (
        "rgba(22,134,217,.12)"
        if accent == BRAND["blue"]
        else (
            "rgba(16,185,129,.12)"
            if accent == BRAND["green"]
            else (
                "rgba(245,158,11,.13)"
                if accent == BRAND["amber"]
                else "rgba(239,68,68,.12)"
            )
        )
    )
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
    # Use native Streamlit columns for predictable KPI alignment.
    # Four cards per row on desktop; the CSS card styling handles the visuals.
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
    # Keep Plotly styling centralized so every chart behaves consistently
    # in both themes and does not depend on Streamlit internals.
    fig.update_layout(
        template="plotly_dark",
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

def find_col(df, candidates):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
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
# DATA LOADING
# ----------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Fetching live logistics data...")
def load_data(path=None, uploaded_file=None):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(path, headers=headers, timeout=25)
    response.raise_for_status()
    return pd.read_excel(io.BytesIO(response.content))

# ----------------------------------------------------------------------------
# SIDEBAR
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

st.sidebar.markdown("### 📂 Data Connection")
uploaded = st.sidebar.file_uploader(
    "Upload Logistics_DB.xlsx",
    type=["xlsx", "xls"],
    help="Upload a current logistics workbook to replace the live SharePoint dataset.",
)

# ----------------------------------------------------------------------------
# DATA PROCESSING
# ----------------------------------------------------------------------------
try:
    df_raw = load_data(
        None if uploaded is not None else DATA_PATH,
        uploaded_file=uploaded,
    )
except Exception as exc:
    st.error("Unable to load the logistics workbook.")
    st.info(
        "If this is running on Streamlit Cloud, verify that the SharePoint "
        "download link is still valid and that it returns the Excel file directly."
    )
    with st.expander("Technical details"):
        st.code(str(exc))
    st.stop()

df_raw = df_raw.copy()
df_raw.columns = [str(c).strip() for c in df_raw.columns]

auto = {
    "client": find_col(df_raw, ["Client Name", "Client", "Customer Name", "Pharmacy", "Hospital"]),
    "so_extract": find_col(df_raw, ["SO Extract", "SO_Extract", "SOExtract"]),
    "value": find_col(df_raw, ["Order Value", "Value", "Amount", "Sales Value", "Total Value"]),
    "qty": find_col(df_raw, ["N0 OF CTN'S", "NO OF CTN'S", "Qty CTN", "Quantity", "CTN"]),
    "created_date": find_col(df_raw, ["Created Date", "Creation Date", "Order Date", "Date Created"]),
    "created_time": find_col(df_raw, ["Created Time", "Creation Time", "Order Time"]),
    "region": find_col(df_raw, ["Region", "Zone", "State", "Territory"]),
    "status": find_col(df_raw, ["Delivery Status", "Status"]),
    "captain": find_col(df_raw, ["Captain", "Rider", "Driver", "Captain Name"]),
    "order_type": find_col(df_raw, ["Order Type", "Type", "Category"]),
    "ship_date": find_col(df_raw, ["Ship Date", "Dispatch Date", "Pickup Date"]),
    "dispatch_time": find_col(df_raw, ["Dispatch Time", "Ship Time", "Time Dispatched"]),
    "deliv_date": find_col(df_raw, ["Delivery Date", "Delivered Date"]),
    "delivery_time": find_col(df_raw, ["Delivery Time", "Time Delivered"]),
}

with st.sidebar.expander("🛠️ Column Mapping", expanded=False):
    all_cols = ["(none)"] + list(df_raw.columns)

    def picker(label, key):
        default = auto.get(key)
        idx = all_cols.index(default) if default in all_cols else 0
        choice = st.selectbox(label, all_cols, index=idx, key=f"map_{key}")
        return None if choice == "(none)" else choice

    col_client = picker("Client / Facility", "client")
    col_so_extract = picker("SO Extract", "so_extract")
    col_value = picker("Order Value (₦)", "value")
    col_qty = picker("Quantity (CTN)", "qty")
    col_date = picker("Created Date", "created_date")
    col_create_time = picker("Created Time", "created_time")
    col_region = picker("Region / Hub", "region")
    col_status = picker("Delivery Status", "status")
    col_captain = picker("Captain / Rider", "captain")
    col_order_type = picker("Order Type", "order_type")
    col_ship = picker("Dispatch Date", "ship_date")
    col_dispatch_time = picker("Dispatch Time", "dispatch_time")
    col_deliv = picker("Delivery Date", "deliv_date")
    col_delivery_time = picker("Delivery Time", "delivery_time")

required = {
    "Client / Facility": col_client,
    "Created Date": col_date,
    "Delivery Status": col_status,
}
missing = [name for name, value in required.items() if not value]
if missing:
    st.error(
        "Please map the following required fields in **🛠️ Column Mapping**: "
        + ", ".join(missing)
    )
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

df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
df = df.dropna(subset=[col_date]).copy()
df["Week"] = df[col_date].dt.isocalendar().week.astype(int)
df["Year"] = df[col_date].dt.year.astype(int)
df["Month"] = df[col_date].dt.month.astype(int)
df["Month Label"] = df[col_date].dt.strftime("%B %Y")
df["Week Label"] = "W" + df["Week"].astype(str).str.zfill(2) + " - " + df["Year"].astype(str)

df[col_value] = pd.to_numeric(df[col_value], errors="coerce").fillna(0)
df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(0)

df["Created_DT"] = build_timestamp(df, col_date, col_create_time)
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

df[col_status] = df[col_status].astype(str).str.strip().str.title()
DELIVERED_LABELS = {"Delivered", "Complete", "Completed", "Successful"}
df["Is Delivered"] = df[col_status].isin(DELIVERED_LABELS)

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Operations Filters")

month_options = ["All Months"] + sorted(
    df["Month Label"].dropna().unique().tolist(),
    key=lambda x: pd.to_datetime(x, format="%B %Y"),
    reverse=True,
)
selected_month = st.sidebar.selectbox("Delivery Month", month_options)

week_options = ["All Weeks"] + sorted(df["Week Label"].unique(), reverse=True)
selected_week = st.sidebar.selectbox("Delivery Week", week_options)

region_options = ["All Regions"] + sorted(
    df[col_region].dropna().astype(str).unique().tolist()
)
selected_region = st.sidebar.selectbox("Region / Hub", region_options)

status_options = ["All Statuses"] + sorted(df[col_status].dropna().unique().tolist())
selected_status = st.sidebar.selectbox("Delivery Status", status_options)

filtered = df.copy()

if selected_month != "All Months":
    filtered = filtered[filtered["Month Label"] == selected_month]

if selected_week != "All Weeks":
    filtered = filtered[filtered["Week Label"] == selected_week]

if selected_region != "All Regions":
    filtered = filtered[filtered[col_region].astype(str) == selected_region]

if selected_status != "All Statuses":
    filtered = filtered[filtered[col_status] == selected_status]

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

st.caption(
    f"Last refreshed: {datetime.now().strftime('%d %b %Y, %H:%M')}  •  "
    f"Month: **{selected_month}**  •  Week: **{selected_week}**  •  Region: **{selected_region}**  •  "
    f"Status: **{selected_status}**"
)

tab_overview, tab_captains, tab_data = st.tabs(
    ["📊 Executive Overview", "🧑‍✈️ Captain Efficiency", "🗂️ Audit Data"]
)

# ============================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ============================================================================
with tab_overview:
    # Count of SO Extract (COUNT, not DISTINCT COUNT): each non-blank SO Extract row is counted.
    total_orders = int(filtered[col_so_extract].notna().sum()) if col_so_extract else len(filtered)
    total_value = filtered[col_value].sum()
    delivered_count = int(filtered["Is Delivered"].sum())
    delivery_pct = (delivered_count / total_orders * 100) if total_orders else 0
    avg_creation_to_deliv_tat = filtered["Creation_Delivery_TAT"].mean()
    avg_shipping_tat = filtered["Shipping_TAT"].mean()
    total_ctns = filtered[col_qty].sum()
    avg_order_value = total_value / total_orders if total_orders else 0
    facilities = filtered[col_client].nunique()

    section_header(
        "Operational KPIs",
        "Descriptions are intentionally visible so every metric is self-explanatory.",
    )

    render_kpis(
        [
            (
                "Total Dispensed Orders",
                fmt_num(total_orders),
                "Count of SO Extract values in the selected filters.",
                "📦",
                BRAND["blue"],
            ),
            (
                "Total Order Value",
                money(total_value),
                "Gross order value represented by the filtered records.",
                "₦",
                BRAND["green"],
            ),
            (
                "Fulfillment Rate",
                f"{delivery_pct:.1f}%",
                f"{delivered_count:,} orders currently marked delivered.",
                "✓",
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
                f"{avg_creation_to_deliv_tat:.1f} hrs"
                if pd.notna(avg_creation_to_deliv_tat)
                else "N/A",
                "Average time from order creation to delivery.",
                "⏱",
                BRAND["amber"],
            ),
            (
                "Dispatch → Delivery TAT",
                f"{avg_shipping_tat:.1f} hrs"
                if pd.notna(avg_shipping_tat)
                else "N/A",
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
                "Average Order Value",
                money(avg_order_value),
                "Average monetary value per order.",
                "₦",
                BRAND["green"],
            ),
        ]
    )

    section_header(
        "Network Performance",
        "Use the visuals to spot concentration, exceptions and delivery mix.",
    )

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
            show_empty_chart("No regional data is available for the selected filters.")
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
            st.plotly_chart(
                plotly_theme(fig),
                use_container_width=True,
                config={"displaylogo": False, "responsive": True},
            )

    with col_b:
        status_summary = filtered[col_status].fillna("Unknown").astype(str).value_counts().reset_index()
        status_summary.columns = ["Status", "Orders"]

        if status_summary.empty:
            show_empty_chart("No fulfillment-status data is available for the selected filters.")
        else:
            fig = px.pie(
                status_summary,
                names="Status",
                values="Orders",
                hole=0.56,
                title="Fulfillment Status Mix",
                color_discrete_sequence=[
                    BRAND["green"],
                    BRAND["blue"],
                    BRAND["amber"],
                    BRAND["red"],
                    "#8B5CF6",
                ],
            )
            fig.update_layout(
                height=380,
                legend_title_text="",
                margin=dict(l=20, r=20, t=60, b=20),
            )
            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>Orders: %{value:,}<br>Share: %{percent}<extra></extra>",
            )
            st.plotly_chart(
                plotly_theme(fig),
                use_container_width=True,
                config={"displaylogo": False, "responsive": True},
            )

    section_header(
        "Weekly Order Trend",
        "Order count by ISO week within the current dataset.",
    )

    trend = (
        filtered.groupby(["Year", "Week"], as_index=False)
        .size()
        .rename(columns={"size": "Orders"})
        .sort_values(["Year", "Week"])
    )
    trend["Week Label"] = (
        "W" + trend["Week"].astype(str).str.zfill(2)
        + " • " + trend["Year"].astype(str)
    )

    if trend.empty:
        show_empty_chart("No weekly order data is available for the selected filters.")
    else:
        fig = px.line(
            trend,
            x="Week Label",
            y="Orders",
            markers=True,
            title="Dispensed Orders Over Time",
        )
        fig.update_traces(
            line_width=3,
            marker_size=8,
            hovertemplate="Week: %{x}<br>Orders: %{y:,}<extra></extra>",
        )
        fig.update_layout(height=340, yaxis_title="Orders", xaxis_title="Week")
        st.plotly_chart(
            plotly_theme(fig),
            use_container_width=True,
            config={"displaylogo": False, "responsive": True},
        )

# ============================================================================
# TAB 2: CAPTAIN PERFORMANCE
# ============================================================================
with tab_captains:
    section_header(
        "Rider & Captain Turnaround Performance",
        "Native Streamlit formatting — no Matplotlib dependency required.",
    )

    if not col_captain:
        st.info("Map the **Captain / Rider** field in the sidebar to activate this view.")
    else:
        cap_df = filtered.dropna(subset=[col_captain]).copy()
        cap_df = cap_df[cap_df[col_captain].astype(str).str.strip() != ""]

        if cap_df.empty:
            st.info("No captain performance records are available for the selected filters.")
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

            cap_summary["Delivery_Rate"] = (
                cap_summary["Delivery_Rate"].fillna(0) * 100
            )

            display_cap = cap_summary.rename(
                columns={
                    col_captain: "Captain",
                    "Total_Orders": "Dispatches",
                    "Creation_to_Delivery_TAT": "Avg Creation→Delivery TAT (hrs)",
                    "Shipping_TAT": "Avg Shipping TAT (hrs)",
                    "Delivery_Rate": "Success Rate (%)",
                }
            )

            # Clean invalid/infinite values before sending data to Streamlit.
            numeric_cols = [
                "Dispatches",
                "Avg Creation→Delivery TAT (hrs)",
                "Avg Shipping TAT (hrs)",
                "Success Rate (%)",
            ]
            for numeric_col in numeric_cols:
                display_cap[numeric_col] = pd.to_numeric(
                    display_cap[numeric_col], errors="coerce"
                )

            display_cap["Success Rate (%)"] = (
                display_cap["Success Rate (%)"].fillna(0).clip(0, 100)
            )

            # Native Streamlit column configuration.
            # IMPORTANT: Do not use pandas Styler.background_gradient here;
            # that requires matplotlib and caused the Streamlit Cloud ImportError.
            st.dataframe(
                display_cap.sort_values(
                    ["Success Rate (%)", "Dispatches"],
                    ascending=[False, False],
                ),
                use_container_width=True,
                hide_index=True,
                height=min(650, 120 + len(display_cap) * 38),
                column_config={
                    "Captain": st.column_config.TextColumn(
                        "Captain",
                        help="Assigned field captain / rider.",
                    ),
                    "Dispatches": st.column_config.NumberColumn(
                        "Dispatches",
                        help="Number of filtered orders assigned to the captain.",
                        format="%d",
                    ),
                    "Avg Creation→Delivery TAT (hrs)": st.column_config.NumberColumn(
                        "Avg Creation→Delivery TAT (hrs)",
                        help="Average elapsed time from order creation to delivery.",
                        format="%.1f",
                    ),
                    "Avg Shipping TAT (hrs)": st.column_config.NumberColumn(
                        "Avg Shipping TAT (hrs)",
                        help="Average elapsed time from dispatch to delivery.",
                        format="%.1f",
                    ),
                    "Success Rate (%)": st.column_config.ProgressColumn(
                        "Success Rate (%)",
                        help="Percentage of the captain's filtered orders marked as delivered.",
                        min_value=0,
                        max_value=100,
                        format="%.1f%%",
                    ),
                },
            )

            st.markdown("")

            # Captain ranking chart.
            rank_df = (
                display_cap.sort_values(
                    ["Success Rate (%)", "Dispatches"],
                    ascending=[False, False],
                )
                .head(12)
                .sort_values("Success Rate (%)")
            )

            if rank_df.empty:
                st.info("Not enough captain data to draw the performance chart.")
            else:
                fig = px.bar(
                    rank_df,
                    x="Success Rate (%)",
                    y="Captain",
                    orientation="h",
                    text="Success Rate (%)",
                    title="Top Captain Delivery Success Rates",
                    color_discrete_sequence=[BRAND["green"]],
                )
                fig.update_traces(
                    texttemplate="%{text:.1f}%",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Success Rate: %{x:.1f}%<extra></extra>"
                    ),
                )
                fig.update_xaxes(range=[0, 100], ticksuffix="%")
                fig.update_layout(
                    height=max(360, min(650, 100 + len(rank_df) * 38)),
                    xaxis_title="Successful Deliveries (%)",
                    yaxis_title=None,
                )

                st.plotly_chart(
                    plotly_theme(fig),
                    use_container_width=True,
                    config={"displaylogo": False, "responsive": True},
                )

            # Operational interpretation cards.
            best_captain = display_cap.sort_values(
                ["Success Rate (%)", "Dispatches"],
                ascending=[False, False],
            ).iloc[0]

            valid_tat = display_cap[
                display_cap["Avg Shipping TAT (hrs)"].notna()
            ].copy()

            if not valid_tat.empty:
                fastest = valid_tat.sort_values(
                    "Avg Shipping TAT (hrs)"
                ).iloc[0]
                fastest_text = (
                    f"{fastest['Captain']} • "
                    f"{fastest['Avg Shipping TAT (hrs)']:.1f} hrs"
                )
            else:
                fastest_text = "N/A"

            st.markdown(
                f"""
                <div class="kpi-grid" style="margin-top:10px;">
                    {kpi_card(
                        "Top Success Rate",
                        f"{best_captain['Success Rate (%)']:.1f}%",
                        f"Highest delivery success rate: {best_captain['Captain']}.",
                        "🏆",
                        BRAND["green"],
                    )}
                    {kpi_card(
                        "Fastest Shipping TAT",
                        fastest_text,
                        "Lowest average dispatch-to-delivery turnaround among captains with valid TAT.",
                        "⚡",
                        BRAND["blue"],
                    )}
                </div>
                """,
                unsafe_allow_html=True,
            )
# ============================================================================
# TAB 3: AUDIT DATA
# ============================================================================
with tab_data:
    section_header(
        "Filtered Audit Logs",
        f"{len(filtered):,} records shown from {len(df):,} total records.",
    )
    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        height=600,
    )

    csv = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download Filtered Audit CSV",
        data=csv,
        file_name="drugstoc_filtered_logistics_audit.csv",
        mime="text/csv",
    )

# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div style="
        margin-top:28px;
        padding-top:14px;
        border-top:1px solid var(--ds-border);
        color:var(--ds-muted);
        font-size:.72rem;
        text-align:center;">
        DrugStoc • Pharma Logistics Intelligence • Operational dashboard
    </div>
    """,
    unsafe_allow_html=True,
)
