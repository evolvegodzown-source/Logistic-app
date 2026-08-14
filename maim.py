import io
import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ----------------------------------------------------------------------------
# PATH CONFIGURATION
# ----------------------------------------------------------------------------
DATA_PATH = r"https://drugstock-my.sharepoint.com/:x:/g/personal/it_drugstoc_com/IQA5yp0kdh82Ra7YcCr-be0vAXufIjkPsYHD4yoBbt6byhs?e=MFF4su&download=1"
IMAGE_PATH = r"C:\Users\IT\OneDrive - DrugStoc\OPERATIONS\LOGISTICS DASH\images (1).png"
CLOUD_IMAGE_PATH = "images (1).png"  # Fallback for Streamlit Cloud deployment

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="DrugStoc | Logistics Control Tower",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# CUSTOM CSS WITH HIGH-VISIBILITY KPI CARDS (DARK MODE COMPATIBLE)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --ds-navy: #071A2B;
            --ds-navy-2: #0D2942;
            --ds-teal: #00A878;
            --ds-teal-soft: #E8F8F2;
            --ds-green: #16A34A;
            --ds-amber: #F59E0B;
            --ds-red: #DC2626;
            --ds-bg: #F5F8FA;
            --ds-border: #D9E2EA;
            --ds-text: #102A43;
            --ds-muted: #627D98;
        }

        .stApp {
            background:
                radial-gradient(circle at 92% 2%, rgba(0,168,120,.08), transparent 22rem),
                linear-gradient(180deg, #F8FBFC 0%, #F3F7F9 100%);
        }

        .block-container {
            max-width: 1500px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            color: var(--ds-navy) !important;
            font-weight: 800 !important;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #061827 0%, #0B243A 100%) !important;
            border-right: 1px solid rgba(255,255,255,.08);
        }

        section[data-testid="stSidebar"] * {
            color: #F4F8FB !important;
        }

        .ds-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 1.15rem 1.35rem;
            margin: .2rem 0 1.2rem 0;
            border-radius: 18px;
            background: linear-gradient(135deg, #071A2B 0%, #0E3554 68%, #006D57 100%);
            box-shadow: 0 10px 30px rgba(7,26,43,.16);
            color: white;
        }

        .ds-header-title {
            font-size: 1.65rem;
            font-weight: 850;
            line-height: 1.1;
        }

        .ds-header-subtitle {
            margin-top: .35rem;
            color: rgba(255,255,255,.78);
            font-size: .9rem;
        }

        .ds-header-chip {
            padding: .45rem .8rem;
            border: 1px solid rgba(255,255,255,.22);
            border-radius: 999px;
            background: rgba(255,255,255,.09);
            color: #fff;
            font-size: .76rem;
            font-weight: 750;
            white-space: nowrap;
        }

        div[data-testid="stMetric"] {
            background: rgba(255,255,255,.96) !important;
            border: 1px solid var(--ds-border) !important;
            border-top: 4px solid var(--ds-teal) !important;
            border-radius: 15px !important;
            padding: 1rem 1.05rem !important;
            min-height: 116px;
            box-shadow: 0 7px 20px rgba(16,42,67,.07) !important;
            transition: all .2s ease;
        }

        div[data-testid="stMetric"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 28px rgba(16,42,67,.12) !important;
        }

        div[data-testid="stMetric"] * {
            color: var(--ds-text) !important;
        }

        div[data-testid="stMetricLabel"] *,
        div[data-testid="stMetricLabel"] label,
        div[data-testid="stMetricLabel"] p {
            font-weight: 750 !important;
            color: var(--ds-muted) !important;
            font-size: .76rem !important;
            text-transform: uppercase !important;
            letter-spacing: .55px !important;
        }

        div[data-testid="stMetricValue"] * {
            font-size: 1.55rem !important;
            font-weight: 850 !important;
            color: var(--ds-navy) !important;
        }

        .ds-filter-summary {
            padding: .7rem .9rem;
            border-radius: 12px;
            background: rgba(0,168,120,.08);
            border: 1px solid rgba(0,168,120,.15);
            color: #0B5D49;
            font-size: .82rem;
            margin: .4rem 0 1rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 7px;
            padding: .25rem;
            background: #EAF0F4;
            border-radius: 12px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 9px;
            padding: .6rem 1rem;
            font-weight: 750;
            color: #38536B;
        }

        .stTabs [aria-selected="true"] {
            background: #FFFFFF !important;
            color: var(--ds-teal) !important;
            box-shadow: 0 3px 10px rgba(16,42,67,.08);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--ds-border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 5px 16px rgba(16,42,67,.05);
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 9px !important;
            font-weight: 750 !important;
        }

        .stDownloadButton > button {
            background: var(--ds-navy) !important;
            color: white !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 12px;
        }

        @media (max-width: 900px) {
            .ds-header {
                align-items: flex-start;
                flex-direction: column;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# DATA LOADING WITH HTTP HEADERS & CACHE (ttl=300)
# ----------------------------------------------------------------------------
@st.cache_data(
    ttl=300, show_spinner="Fetching live logistics data from SharePoint..."
)
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


def find_col(df, candidates):
    """Safely match column headers even if Excel contains numbers/dates in headers."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None

    cols_lower = {str(c).lower().strip(): c for c in df.columns}

    # 1. Exact match pass
    for cand in candidates:
        cand_str = str(cand).lower().strip()
        if cand_str in cols_lower:
            return cols_lower[cand_str]

    # 2. Substring match pass
    for cand in candidates:
        cand_str = str(cand).lower().strip()
        for col in df.columns:
            if cand_str in str(col).lower().strip():
                return col

    return None


# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# VISUAL HELPERS
# ----------------------------------------------------------------------------
def polish_plot(fig, height=380):
    """Apply a consistent DrugStoc visual language to Plotly charts."""
    fig.update_layout(
        height=height,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Inter, Arial, sans-serif", color="#102A43"),
        margin=dict(t=35, b=45, l=20, r=20),
        hoverlabel=dict(bgcolor="#071A2B", font_color="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#D9E2EA", zeroline=False)
    fig.update_yaxes(gridcolor="#E8EEF2", linecolor="#D9E2EA", zeroline=False)
    return fig


def status_color(status):
    status = str(status).strip().lower()
    if status in {"delivered", "complete", "completed", "successful"}:
        return "#16A34A"
    if status in {"pending", "processing", "in transit", "out for delivery"}:
        return "#F59E0B"
    if status in {"failed", "cancelled", "canceled", "returned", "rejected"}:
        return "#DC2626"
    return "#64748B"


def style_scorecard(dataframe):
    """Conditional formatting: green = better, red = slower/lower."""
    styler = dataframe.style

    if "Delivery Rate %" in dataframe.columns:
        styler = styler.background_gradient(
            subset=["Delivery Rate %"], cmap="RdYlGn", vmin=0, vmax=100
        )

    if "Avg Dispatch Duration (Hrs)" in dataframe.columns:
        styler = styler.background_gradient(
            subset=["Avg Dispatch Duration (Hrs)"], cmap="RdYlGn_r"
        )

    if "Avg Creation-Delivery TAT (Hrs)" in dataframe.columns:
        styler = styler.background_gradient(
            subset=["Avg Creation-Delivery TAT (Hrs)"], cmap="RdYlGn_r"
        )

    return styler


# SIDEBAR HEADER & FILE UPLOADER
# ----------------------------------------------------------------------------
if os.path.exists(IMAGE_PATH):
    st.sidebar.image(IMAGE_PATH, use_container_width=True)
elif os.path.exists(CLOUD_IMAGE_PATH):
    st.sidebar.image(CLOUD_IMAGE_PATH, use_container_width=True)
else:
    st.sidebar.markdown(
        """
        <div style="text-align:center;padding:.6rem 0 1rem;">
            <div style="font-size:2.4rem;">💊</div>
            <div style="font-size:1.25rem;font-weight:850;">DrugStoc</div>
            <div style="font-size:.75rem;opacity:.75;">LOGISTICS CONTROL TOWER</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    """
    <div style="
        padding:.65rem .8rem;
        border:1px solid rgba(255,255,255,.12);
        border-radius:10px;
        background:rgba(255,255,255,.05);
        font-size:.76rem;
        line-height:1.45;">
        <b>Rx Supply Chain</b><br>
        Cold-chain • Distribution • Delivery
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Data Source")
uploaded = st.sidebar.file_uploader(
    "Upload Logistics_DB.xlsx manually", type=["xlsx", "xls"]
)

if st.sidebar.button("🔄 Refresh Data Cache"):
    st.cache_data.clear()
    st.rerun()

# ----------------------------------------------------------------------------
# LOAD RAW DATA & SAFE COLUMN DETECT
# ----------------------------------------------------------------------------
df_raw = None
load_error = None
try:
    df_raw = load_data(
        DATA_PATH if uploaded is None else None, uploaded_file=uploaded
    )
except Exception as e:
    load_error = e

if df_raw is None or not isinstance(df_raw, pd.DataFrame):
    st.error(
        f"Unable to read the dataset from SharePoint.\n\n"
        f"**Details:** {load_error}\n\n"
        "**Quick Fix:** Use the file uploader in the sidebar to select `Logistics_DB.xlsx` from your computer."
    )
    st.stop()

# Clean raw column names to string
df_raw.columns = [str(c).strip() for c in df_raw.columns]

# Auto-detect column headers
auto = {
    "client": find_col(
        df_raw,
        [
            "Client Name",
            "Client",
            "Customer Name",
            "Customer",
            "Pharmacy",
            "Hospital",
        ],
    ),
    "value": find_col(
        df_raw,
        ["Order Value", "Value", "Amount", "Sales Value", "Total Value"],
    ),
    "qty": find_col(
        df_raw,
        [
            "N0 OF CTN'S",
            "NO OF CTN'S",
            "N0 OF CTNS",
            "NO OF CTNS",
            "NO. OF CTNS",
            "Qty CTN",
            "Quantity CTN",
            "Qty (CTN)",
            "Quantity",
            "Qty",
            "Cartons",
            "Carton",
            "CTN",
        ],
    ),
    "created_date": find_col(
        df_raw,
        [
            "Created Date",
            "Creation Date",
            "Order Date",
            "Date Created",
            "Date",
            "Dispatch Date",
        ],
    ),
    "created_time": find_col(
        df_raw,
        [
            "Created Time",
            "Creation Time",
            "Order Time",
            "Time Created",
            "Create Time",
        ],
    ),
    "region": find_col(df_raw, ["Region", "Zone", "State", "Territory"]),
    "status": find_col(df_raw, ["Delivery Status", "Status"]),
    "captain": find_col(
        df_raw,
        ["Captain", "Rider", "Driver", "Captain Name", "Dispatcher"],
    ),
    "order_type": find_col(
        df_raw, ["Order Type", "Type", "Category", "Channel", "Order_Type"]
    ),
    "ship_date": find_col(
        df_raw, ["Ship Date", "Dispatch Date", "Pickup Date"]
    ),
    "dispatch_time": find_col(
        df_raw,
        [
            "Dispatch Time",
            "Ship Time",
            "Time Dispatched",
            "Departure Time",
            "Time Out",
        ],
    ),
    "deliv_date": find_col(
        df_raw, ["Delivery Date", "Delivered Date", "Date Delivered"]
    ),
    "delivery_time": find_col(
        df_raw, ["Delivery Time", "Time Delivered", "Arrival Time", "Time In"]
    ),
}

# ----------------------------------------------------------------------------
# SIDEBAR COLUMN MAPPING PICKER UI
# ----------------------------------------------------------------------------
st.sidebar.markdown("---")
with st.sidebar.expander("🛠️ Data Column Mapping", expanded=False):
    all_cols = ["(none)"] + list(df_raw.columns)

    def picker(label, key):
        default = auto.get(key)
        idx = (
            all_cols.index(default)
            if (default and default in all_cols)
            else 0
        )
        choice = st.selectbox(label, all_cols, index=idx, key=f"map_{key}")
        return None if choice == "(none)" else choice

    col_client = picker("Facility/Client Name", "client")
    col_value = picker("Order Value (₦)", "value")
    col_qty = picker("Quantity (CTN)", "qty")
    col_date = picker("Created Date / Order Date", "created_date")
    col_create_time = picker("Creation Time (Optional)", "created_time")
    col_region = picker("Delivery Zone/Region", "region")
    col_status = picker("Delivery Status", "status")
    col_captain = picker("Logistics Captain", "captain")
    col_order_type = picker("Order Type", "order_type")
    col_ship = picker("Dispatch Date", "ship_date")
    col_dispatch_time = picker("Dispatch Time", "dispatch_time")
    col_deliv = picker("Delivery Date", "deliv_date")
    col_delivery_time = picker("Delivery Time", "delivery_time")

required_missing = [
    n
    for n, v in [
        ("Client Name", col_client),
        ("Order Value", col_value),
        ("Qty CTN", col_qty),
        ("Created/Order Date", col_date),
        ("Region", col_region),
        ("Delivery Status", col_status),
    ]
    if v is None
]

if required_missing:
    st.error(
        f"Missing required mapping for: **{', '.join(required_missing)}**. "
        "Please assign them under 'Data Column Mapping' in the sidebar."
    )
    st.stop()

df = df_raw.copy()

# ----------------------------------------------------------------------------
# DATA CLEANING & TIMESTAMP PARSING
# ----------------------------------------------------------------------------
df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
df = df.dropna(subset=[col_date])
df["Week"] = df[col_date].dt.isocalendar().week.astype(int)
df["Year"] = df[col_date].dt.year.astype(int)
df["Week Label"] = (
    "W" + df["Week"].astype(str).str.zfill(2) + " - " + df["Year"].astype(str)
)

df[col_value] = pd.to_numeric(df[col_value], errors="coerce").fillna(0)
df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(0)


def build_timestamp(data_df, date_c, time_c):
    """Combines a date column and an optional time column into a single datetime pandas Series."""
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
        combined_str = dates.dt.strftime("%Y-%m-%d") + " " + times
        return pd.to_datetime(combined_str, errors="coerce")
    return dates


# Construct full Timestamps
df["Created_DT"] = build_timestamp(df, col_date, col_create_time)
df["Delivery_DT"] = build_timestamp(df, col_deliv, col_delivery_time)

dispatch_date_col = (
    col_ship if (col_ship and col_ship in df.columns) else col_date
)
df["Dispatch_DT"] = build_timestamp(df, dispatch_date_col, col_dispatch_time)

# ----------------------------------------------------------------------------
# TAT & DURATION CALCULATIONS (Created_DT to Delivery_DT)
# ----------------------------------------------------------------------------
if col_deliv and col_deliv in df.columns:
    # Creation to Delivery TAT in hours
    tat_hrs = (df["Delivery_DT"] - df["Created_DT"]).dt.total_seconds() / 3600.0
    df["Creation_Delivery_TAT"] = tat_hrs.apply(
        lambda x: x if (pd.notna(x) and x >= 0) else np.nan
    )

    # Dispatch to Delivery Duration in hours
    duration_hrs = (
        df["Delivery_DT"] - df["Dispatch_DT"]
    ).dt.total_seconds() / 3600.0
    df["Dispatch Duration (hrs)"] = duration_hrs.apply(
        lambda x: x if (pd.notna(x) and x >= 0) else np.nan
    )
else:
    df["Creation_Delivery_TAT"] = np.nan
    df["Dispatch Duration (hrs)"] = np.nan

df[col_status] = df[col_status].astype(str).str.strip().str.title()
DELIVERED_LABELS = {"Delivered", "Complete", "Completed", "Successful"}
df["Is Delivered"] = df[col_status].isin(DELIVERED_LABELS)

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Operations Filters")

week_options = ["All Weeks"] + sorted(
    df["Week Label"].unique(),
    key=lambda w: (w.split(" - ")[1], w.split(" - ")[0]),
    reverse=True,
)
selected_week = st.sidebar.selectbox("Filter by Delivery Week", week_options)

region_options = ["All Regions"] + sorted(
    df[col_region].dropna().unique().tolist()
)
selected_region = st.sidebar.selectbox("Filter by Region / Hub", region_options)

if col_order_type and col_order_type in df.columns:
    order_type_options = ["All Order Types"] + sorted(
        df[col_order_type].dropna().astype(str).unique().tolist()
    )
else:
    order_type_options = ["All Order Types"]
selected_order_type = st.sidebar.selectbox(
    "Filter by Order Type", order_type_options
)

status_options = ["All Statuses"] + sorted(
    df[col_status].dropna().unique().tolist()
)
selected_status = st.sidebar.selectbox("Filter by Order Status", status_options)

filtered = df.copy()

if selected_week != "All Weeks":
    filtered = filtered[filtered["Week Label"] == selected_week]

if selected_region != "All Regions":
    filtered = filtered[filtered[col_region] == selected_region]

if (
    selected_order_type != "All Order Types"
    and col_order_type
    and col_order_type in filtered.columns
):
    filtered = filtered[
        filtered[col_order_type].astype(str) == selected_order_type
    ]

if selected_status != "All Statuses":
    filtered = filtered[filtered[col_status] == selected_status]

if filtered.empty:
    st.warning(
        "No pharmaceutical delivery records match the current filter criteria."
    )
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(
    f"📦 Total Records: **{len(df):,}** | Filtered Result: **{len(filtered):,}**"
)

# ----------------------------------------------------------------------------
# MAIN DASHBOARD HEADER
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="ds-header">
        <div>
            <div class="ds-header-title">🚚 DrugStoc Logistics Control Tower</div>
            <div class="ds-header-subtitle">
                Live pharmaceutical distribution & fulfillment performance
            </div>
        </div>
        <div class="ds-header-chip">
            LIVE • {datetime.now().strftime('%d %b %Y, %H:%M')}
        </div>
    </div>
    <div class="ds-filter-summary">
        <b>Active view:</b>
        Week: {selected_week} &nbsp;•&nbsp;
        Region: {selected_region} &nbsp;•&nbsp;
        Order Type: {selected_order_type} &nbsp;•&nbsp;
        Status: {selected_status}
    </div>
    """,
    unsafe_allow_html=True,
)

tab_overview, tab_captains, tab_data = st.tabs(
    [
        "📊 Executive Overview",
        "🧑‍✈️ Captain & Rider Efficiency",
        "🗂️ Audit & Raw Data",
    ]
)

# ============================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ============================================================================
with tab_overview:
    total_orders = filtered[col_client].count()
    total_value = filtered[col_value].sum()
    avg_duration_hrs = filtered["Dispatch Duration (hrs)"].mean()
    total_qty = filtered[col_qty].sum()
    delivered_count = filtered["Is Delivered"].sum()
    delivery_pct = (
        (delivered_count / total_orders * 100) if total_orders else 0
    )
    avg_order_value = total_value / total_orders if total_orders else 0
    unique_clients = filtered[col_client].nunique()

    # Calculate Creation-to-Delivery TAT KPI
    avg_tat_hrs = filtered["Creation_Delivery_TAT"].mean()
    if pd.notna(avg_tat_hrs):
        tat_str = f"{avg_tat_hrs:.1f} hrs"
    else:
        tat_str = "N/A"

    if pd.notna(avg_duration_hrs):
        if avg_duration_hrs < 24:
            duration_str = f"{avg_duration_hrs:.1f} hrs"
        else:
            days = avg_duration_hrs / 24.0
            duration_str = f"{avg_duration_hrs:.1f} hrs ({days:.1f}d)"
    else:
        duration_str = "N/A"

    # Row 1: Primary Order & Delivery KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Dispensed Orders", f"{total_orders:,}")
    c2.metric("Total Order Value", f"₦{total_value:,.0f}")
    c3.metric(
        "Fulfillment Rate",
        f"{delivery_pct:.1f}%",
        f"{int(delivered_count)}/{int(total_orders)} Delivered",
    )
    c4.metric("Avg Creation-Delivery TAT", tat_str)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 2: Secondary Performance & Volume Metrics
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Avg Dispatch Duration", duration_str)
    c6.metric("Total Volume Shipped", f"{total_qty:,.0f} CTN")
    c7.metric("Avg Order Value", f"₦{avg_order_value:,.0f}")
    c8.metric("Active Health Facilities", f"{unique_clients:,}")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Distribution Volume by Region")
        region_summary = (
            filtered.groupby(col_region)
            .agg(Orders=(col_client, "count"), Value=(col_value, "sum"))
            .reset_index()
            .sort_values("Orders", ascending=False)
        )

        fig = px.bar(
            region_summary,
            x=col_region,
            y="Orders",
            color=col_region,
            text="Orders",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Dark2,
        )
        fig.update_layout(
            showlegend=False, height=380, margin=dict(t=20, b=20, l=10, r=10)
        )
        fig = polish_plot(fig, 380)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Fulfillment Status Breakdown")
        status_summary = filtered[col_status].value_counts().reset_index()
        status_summary.columns = ["Status", "Count"]

        fig = px.pie(
            status_summary,
            names="Status",
            values="Count",
            hole=0.5,
            template="plotly_white",
            color_discrete_sequence=[
                "#00A86B",
                "#1E3E62",
                "#E63946",
                "#FFB703",
            ],
        )
        fig.update_layout(height=380, margin=dict(t=20, b=20, l=10, r=10))
        fig = polish_plot(fig, 380)
        st.plotly_chart(fig, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Weekly Distribution Value Trend")
        week_summary = (
            filtered.groupby(["Year", "Week", "Week Label"])
            .agg(Value=(col_value, "sum"), Orders=(col_client, "count"))
            .reset_index()
            .sort_values(["Year", "Week"])
        )

        fig = px.line(
            week_summary,
            x="Week Label",
            y="Value",
            markers=True,
            template="plotly_white",
            line_shape="spline",
        )
        fig.update_traces(line_color="#00A86B", line_width=3)
        fig.update_layout(
            height=380, xaxis_title="Week", yaxis_title="Value (₦)"
        )
        fig = polish_plot(fig, 380)
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.subheader("Weekly Carton Volume (CTN)")
        qty_week = (
            filtered.groupby("Week Label")[col_qty].sum().reset_index()
        )

        fig2 = px.area(
            qty_week, x="Week Label", y=col_qty, template="plotly_white"
        )
        fig2.update_traces(
            fillcolor="rgba(0, 168, 107, 0.25)", line_color="#00A86B"
        )
        fig2.update_layout(
            height=380, xaxis_title="Week", yaxis_title="Quantity (Cartons)"
        )
        fig2 = polish_plot(fig2, 380)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top 10 Health Facilities / Accounts by Value")
    top_clients = (
        filtered.groupby(col_client)
        .agg(Orders=(col_client, "count"), Value=(col_value, "sum"))
        .reset_index()
        .sort_values("Value", ascending=False)
        .head(10)
    )

    fig = px.bar(
        top_clients,
        x="Value",
        y=col_client,
        orientation="h",
        text="Orders",
        template="plotly_white",
        color="Value",
        color_continuous_scale="Tealgrn",
    )
    fig.update_layout(
        height=420,
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
    )
    fig = polish_plot(fig, 420)
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 2: CAPTAIN PERFORMANCE
# ============================================================================
with tab_captains:
    if col_captain is None:
        st.info(
            "No Delivery Captain/Rider column mapped. Select your rider column in sidebar settings."
        )
    else:
        cap_df = filtered.dropna(subset=[col_captain])
        st.subheader("Rider & Captain Performance Metrics")

        cap_summary = (
            cap_df.groupby(col_captain)
            .agg(
                Total_Orders=(col_client, "count"),
                Total_Value=(col_value, "sum"),
                Total_Qty=(col_qty, "sum"),
                Avg_Duration_Hrs=("Dispatch Duration (hrs)", "mean"),
                Avg_TAT_Hrs=("Creation_Delivery_TAT", "mean"),
                Delivered=("Is Delivered", "sum"),
            )
            .reset_index()
        )
        cap_summary["Delivery Rate %"] = (
            cap_summary["Delivered"] / cap_summary["Total_Orders"] * 100
        ).round(1)
        cap_summary = cap_summary.sort_values("Total_Orders", ascending=False)

        best_captain = (
            cap_summary.iloc[0][col_captain] if not cap_summary.empty else "N/A"
        )
        best_delivery = cap_summary.sort_values(
            "Delivery Rate %", ascending=False
        ).iloc[0]
        fastest = cap_summary.sort_values(
            "Avg_TAT_Hrs", ascending=True
        ).iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Active Fleet Captains", f"{cap_summary.shape[0]:,}")
        m2.metric("Highest Dispatch Captain", str(best_captain))
        m3.metric(
            "Top Reliability Score",
            f"{best_delivery[col_captain]}",
            f"{best_delivery['Delivery Rate %']:.1f}%",
        )
        m4.metric(
            "Fastest Creation-Delivery TAT",
            f"{fastest[col_captain]}",
            (
                f"{fastest['Avg_TAT_Hrs']:.1f} hrs"
                if pd.notna(fastest["Avg_TAT_Hrs"])
                else "N/A"
            ),
        )

        st.markdown("### ")
        col_e, col_f = st.columns(2)

        with col_e:
            st.subheader("Total Orders Handled per Captain")
            fig = px.bar(
                cap_summary,
                x=col_captain,
                y="Total_Orders",
                text="Total_Orders",
                color="Total_Orders",
                template="plotly_white",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(
                height=400, coloraxis_showscale=False, xaxis_tickangle=-30
            )
            fig = polish_plot(fig, 400)
            st.plotly_chart(fig, use_container_width=True)

        with col_f:
            st.subheader("Successful Delivery Rate (%)")
            fig = px.bar(
                cap_summary.sort_values("Delivery Rate %"),
                x="Delivery Rate %",
                y=col_captain,
                orientation="h",
                text="Delivery Rate %",
                template="plotly_white",
                color="Delivery Rate %",
                color_continuous_scale="Emrld",
            )
            fig.update_layout(height=400, coloraxis_showscale=False)
            fig = polish_plot(fig, 400)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Comprehensive Captain Scorecard")
        display_cap = cap_summary.rename(
            columns={
                col_captain: "Captain / Rider",
                "Total_Orders": "Total Dispatches",
                "Total_Value": "Order Value",
                "Total_Qty": "Volume (CTN)",
                "Avg_Duration_Hrs": "Avg Dispatch Duration (Hrs)",
                "Avg_TAT_Hrs": "Avg Creation-Delivery TAT (Hrs)",
                "Delivered": "Completed Deliveries",
            }
        )
        scorecard_style = style_scorecard(display_cap).format(
            {
                "Order Value": "₦{:,.0f}",
                "Volume (CTN)": "{:,.0f}",
                "Avg Dispatch Duration (Hrs)": "{:.1f}",
                "Avg Creation-Delivery TAT (Hrs)": "{:.1f}",
                "Delivery Rate %": "{:.1f}%",
            }
        )

        st.dataframe(
            scorecard_style,
            use_container_width=True,
            hide_index=True,
        )

# ============================================================================
# TAB 3: AUDIT & RAW DATA
# ============================================================================
with tab_data:
    st.subheader("Filtered Delivery Logs")

    def highlight_status(row):
        styles = [""] * len(row)
        try:
            idx = list(row.index).index(col_status)
            color = status_color(row[col_status])
            styles[idx] = (
                f"color: {color}; font-weight: 800; "
                f"background-color: {color}18;"
            )
        except ValueError:
            pass
        return styles

    st.dataframe(
        filtered.style.apply(highlight_status, axis=1),
        use_container_width=True,
        height=540,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download Filtered Audit Report (CSV)",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"DrugStoc_Logistics_Export_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )


# ----------------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div style="
        margin-top:2rem;
        padding:1rem 0;
        border-top:1px solid #D9E2EA;
        text-align:center;
        color:#627D98;
        font-size:.74rem;">
        <b style="color:#0B243A;">DrugStoc Logistics Control Tower</b>
        &nbsp;•&nbsp; Pharmaceutical Supply Chain Analytics
        &nbsp;•&nbsp; Built for Operations
    </div>
    """,
    unsafe_allow_html=True,
)
