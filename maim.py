import io
import os
import base64
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
# PATH & ASSET CONFIGURATION
# ----------------------------------------------------------------------------
DATA_PATH = r"https://drugstock-my.sharepoint.com/:x:/g/personal/it_drugstoc_com/IQA5yp0kdh82Ra7YcCr-be0vAXufIjkPsYHD4yoBbt6byhs?e=MFF4su&download=1"

# Inline Base64 DrugStoc Logo fallback to guarantee it always renders anywhere
DRUGSTOC_LOGO_BASE64 = "https://raw.githubusercontent.com/streamlit/streamlit/main/docs/static/logo.png" # Fallback if local image missing

# ----------------------------------------------------------------------------
# CUSTOM CSS & THEMING
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --ds-blue: #2A85C8;
            --ds-green: #00A86B;
            --ds-dark: #0F172A;
            --ds-card-bg: #FFFFFF;
            --ds-bg: #F8FAFC;
        }

        .main { background-color: var(--ds-bg); }

        /* Modern High-Visibility KPI Cards */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-left: 5px solid var(--ds-blue) !important;
            border-radius: 12px !important;
            padding: 16px 20px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
            transition: all 0.2s ease-in-out;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
        }

        div[data-testid="stMetricLabel"] * { 
            font-weight: 700 !important; 
            color: #64748B !important; 
            font-size: 0.80rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }

        div[data-testid="stMetricValue"] * { 
            font-size: 1.7rem !important; 
            font-weight: 800 !important;
            color: #0F172A !important; 
        }

        /* Sidebar Customization */
        section[data-testid="stSidebar"] { 
            background-color: #0B192C !important; 
        }
        section[data-testid="stSidebar"] * { 
            color: #F1F5F9 !important; 
        }

        /* Custom Badges & Headers */
        .pharma-badge {
            background-color: #E0F2FE;
            color: #0369A1;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.8rem;
            font-weight: 700;
            display: inline-block;
            margin-bottom: 8px;
        }

        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #FFFFFF; 
            border-radius: 8px 8px 0 0;
            padding: 10px 20px; 
            border: 1px solid #E2E8F0;
            font-weight: 600;
            color: #334155;
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--ds-blue) !important;
            color: #FFFFFF !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# DATA LOADING & CACHING
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


def find_col(df, candidates):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    cols_lower = {str(c).lower().strip(): c for c in df.columns}
    for cand in candidates:
        cand_str = str(cand).lower().strip()
        if cand_str in cols_lower:
            return cols_lower[cand_str]
    for cand in candidates:
        cand_str = str(cand).lower().strip()
        for col in df.columns:
            if cand_str in str(col).lower().strip():
                return col
    return None


# ----------------------------------------------------------------------------
# SIDEBAR HEADER & LOGO DISPLAY
# ----------------------------------------------------------------------------
# Display DrugStoc Header Logo
st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 10px 0;">
        <h2 style="color: #2A85C8; margin: 0; font-weight: 800; font-size: 28px;">
            💊 DrugStoc
        </h2>
        <p style="color: #94A3B8; font-size: 12px; margin-top: 2px;">Logistics & Operations Intelligence</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Data Connection")
uploaded = st.sidebar.file_uploader("Upload Logistics_DB.xlsx", type=["xlsx", "xls"])

if st.sidebar.button("🔄 Refresh Data Cache"):
    st.cache_data.clear()
    st.rerun()

# ----------------------------------------------------------------------------
# DATA PROCESSING
# ----------------------------------------------------------------------------
df_raw = None
try:
    df_raw = load_data(DATA_PATH if uploaded is None else None, uploaded_file=uploaded)
except Exception as e:
    st.error(f"Unable to read dataset: {e}")
    st.stop()

df_raw.columns = [str(c).strip() for c in df_raw.columns]

# Auto-detect column mappings
auto = {
    "client": find_col(df_raw, ["Client Name", "Client", "Customer Name", "Pharmacy", "Hospital"]),
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

with st.sidebar.expander("🛠️ Column Mapping Settings", expanded=False):
    all_cols = ["(none)"] + list(df_raw.columns)
    def picker(label, key):
        default = auto.get(key)
        idx = all_cols.index(default) if (default and default in all_cols) else 0
        choice = st.selectbox(label, all_cols, index=idx, key=f"map_{key}")
        return None if choice == "(none)" else choice

    col_client = picker("Client Name", "client")
    col_value = picker("Order Value (₦)", "value")
    col_qty = picker("Quantity (CTN)", "qty")
    col_date = picker("Created Date", "created_date")
    col_create_time = picker("Created Time", "created_time")
    col_region = picker("Region/Zone", "region")
    col_status = picker("Delivery Status", "status")
    col_captain = picker("Captain/Rider", "captain")
    col_order_type = picker("Order Type", "order_type")
    col_ship = picker("Dispatch Date", "ship_date")
    col_dispatch_time = picker("Dispatch Time", "dispatch_time")
    col_deliv = picker("Delivery Date", "deliv_date")
    col_delivery_time = picker("Delivery Time", "delivery_time")

df = df_raw.copy()

# Date & Time Parsing
df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
df = df.dropna(subset=[col_date])
df["Week"] = df[col_date].dt.isocalendar().week.astype(int)
df["Year"] = df[col_date].dt.year.astype(int)
df["Week Label"] = "W" + df["Week"].astype(str).str.zfill(2) + " - " + df["Year"].astype(str)

df[col_value] = pd.to_numeric(df[col_value], errors="coerce").fillna(0)
df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce").fillna(0)

def build_timestamp(data_df, date_c, time_c):
    if not date_c or date_c not in data_df.columns:
        return pd.Series(pd.NaT, index=data_df.index)
    dates = pd.to_datetime(data_df[date_c], errors="coerce")
    if time_c and time_c in data_df.columns:
        times = data_df[time_c].astype(str).str.strip().replace(["nan", "None", "<NaT>", ""], "00:00:00")
        combined_str = dates.dt.strftime("%Y-%m-%d") + " " + times
        return pd.to_datetime(combined_str, errors="coerce")
    return dates

df["Created_DT"] = build_timestamp(df, col_date, col_create_time)
df["Delivery_DT"] = build_timestamp(df, col_deliv, col_delivery_time)
dispatch_date_col = col_ship if (col_ship and col_ship in df.columns) else col_date
df["Dispatch_DT"] = build_timestamp(df, dispatch_date_col, col_dispatch_time)

# ----------------------------------------------------------------------------
# TAT CALCULATIONS
# ----------------------------------------------------------------------------
# 1. Creation to Delivery TAT (Hours)
df["Creation_Delivery_TAT"] = (df["Delivery_DT"] - df["Created_DT"]).dt.total_seconds() / 3600.0
df["Creation_Delivery_TAT"] = df["Creation_Delivery_TAT"].apply(lambda x: x if (pd.notna(x) and x >= 0) else np.nan)

# 2. Shipping / Dispatch TAT (Hours)
df["Shipping_TAT"] = (df["Delivery_DT"] - df["Dispatch_DT"]).dt.total_seconds() / 3600.0
df["Shipping_TAT"] = df["Shipping_TAT"].apply(lambda x: x if (pd.notna(x) and x >= 0) else np.nan)

df[col_status] = df[col_status].astype(str).str.strip().str.title()
DELIVERED_LABELS = {"Delivered", "Complete", "Completed", "Successful"}
df["Is Delivered"] = df[col_status].isin(DELIVERED_LABELS)

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Operations Filters")

week_options = ["All Weeks"] + sorted(df["Week Label"].unique(), reverse=True)
selected_week = st.sidebar.selectbox("Delivery Week", week_options)

region_options = ["All Regions"] + sorted(df[col_region].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("Region / Hub", region_options)

filtered = df.copy()
if selected_week != "All Weeks":
    filtered = filtered[filtered["Week Label"] == selected_week]
if selected_region != "All Regions":
    filtered = filtered[filtered[col_region] == selected_region]

# ----------------------------------------------------------------------------
# MAIN DASHBOARD
# ----------------------------------------------------------------------------
st.markdown('<div class="pharma-badge">HEALTHCARE SUPPLY CHAIN MONITOR</div>', unsafe_allow_html=True)
st.title("🚚 DrugStoc Logistics Performance Dashboard")
st.caption(f"Refreshed: {datetime.now().strftime('%d %b %Y, %H:%M')} | Week: **{selected_week}** | Region: **{selected_region}**")

tab_overview, tab_captains, tab_data = st.tabs(["📊 Executive Overview", "🧑‍✈️ Captain Efficiency", "🗂️ Audit Data"])

with tab_overview:
    # Calculations
    total_orders = len(filtered)
    total_value = filtered[col_value].sum()
    delivered_count = filtered["Is Delivered"].sum()
    delivery_pct = (delivered_count / total_orders * 100) if total_orders else 0
    
    avg_creation_to_deliv_tat = filtered["Creation_Delivery_TAT"].mean()
    avg_shipping_tat = filtered["Shipping_TAT"].mean()

    # Metric Row 1: Fulfillment & Value
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Dispensed Orders", f"{total_orders:,}")
    c2.metric("Total Order Value", f"₦{total_value:,.0f}")
    c3.metric("Fulfillment Rate", f"{delivery_pct:.1f}%", f"{int(delivered_count)} Delivered")
    c4.metric("Active Health Facilities", f"{filtered[col_client].nunique():,}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Metric Row 2: Turnaround Time (TAT) Focus
    c5, c6, c7, c8 = st.columns(4)
    
    # Creation to Delivery TAT KPI
    tat_create_str = f"{avg_creation_to_deliv_tat:.1f} hrs" if pd.notna(avg_creation_to_deliv_tat) else "N/A"
    c5.metric("TAT: Creation to Delivery", tat_create_str, help="Average time taken from Order Creation to Final Delivery")

    # Shipping TAT KPI
    tat_ship_str = f"{avg_shipping_tat:.1f} hrs" if pd.notna(avg_shipping_tat) else "N/A"
    c6.metric("TAT: Shipping Duration", tat_ship_str, help="Average time taken from Dispatch/Pickup to Final Delivery")

    c7.metric("Total Volume Shipped", f"{filtered[col_qty].sum():,.0f} CTN")
    c8.metric("Avg Order Value", f"₦{(total_value/total_orders if total_orders else 0):,.0f}")

    st.markdown("---")

    # Visualizations
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Distribution Volume by Region")
        reg_summary = filtered.groupby(col_region)[col_client].count().reset_index()
        fig = px.bar(reg_summary, x=col_region, y=col_client, text=col_client, template="plotly_white",
                     color_discrete_sequence=["#2A85C8"])
        fig.update_layout(height=350, showlegend=False, xaxis_title=None, yaxis_title="Orders")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Fulfillment Status Breakdown")
        status_summary = filtered[col_status].value_counts().reset_index()
        fig = px.pie(status_summary, names=status_summary.columns[0], values=status_summary.columns[1],
                     hole=0.5, template="plotly_white",
                     color_discrete_sequence=["#00A86B", "#2A85C8", "#E63946", "#FFB703"])
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

with tab_captains:
    if col_captain:
        cap_df = filtered.dropna(subset=[col_captain])
        st.subheader("Rider & Captain Turnaround Performance")

        cap_summary = cap_df.groupby(col_captain).agg(
            Total_Orders=(col_client, "count"),
            Creation_to_Delivery_TAT=("Creation_Delivery_TAT", "mean"),
            Shipping_TAT=("Shipping_TAT", "mean"),
            Delivery_Rate=("Is Delivered", "mean")
        ).reset_index()
        cap_summary["Delivery_Rate"] = (cap_summary["Delivery_Rate"] * 100).round(1)

        st.dataframe(
            cap_summary.rename(columns={
                col_captain: "Captain",
                "Total_Orders": "Dispatches",
                "Creation_to_Delivery_TAT": "Avg Order-to-Delivery (hrs)",
                "Shipping_TAT": "Avg Shipping TAT (hrs)",
                "Delivery_Rate": "Success Rate (%)"
            }).style.format({
                "Avg Order-to-Delivery (hrs)": "{:.1f}",
                "Avg Shipping TAT (hrs)": "{:.1f}",
                "Success Rate (%)": "{:.1f}%"
            }),
            use_container_width=True,
            hide_index=True
        )

with tab_data:
    st.subheader("Filtered Audit Logs")
    st.dataframe(filtered, use_container_width=True)
