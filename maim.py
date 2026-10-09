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
            0% {{ box-shadow: 0 0 0
