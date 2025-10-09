import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ----------------------------------------
# CSS STYLE
# ----------------------------------------
st.markdown("""
    <style>
    .record-row {
        display: grid;
        grid-template-columns: 140px 160px 250px 160px 120px 100px;
        padding: 6px 0;
        border-bottom: 1px solid #ccc;
        align-items: center;
    }
    .record-row div {
        padding-left: 6px;
    }
    .record-header {
        display: grid;
        grid-template-columns: 140px 160px 250px 160px 120px 100px;
        font-weight: bold;
        background-color: #2b5876;
        color: white;
        padding: 8px 0;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }
    .filter-box {
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------
# HEADER
# ----------------------------------------
if os.path.exists("unnamed.png"):
    logo = Image.open("unnamed.png")
    st.image(logo, width=280)
else:
    st.warning("⚠️ Please upload your logo file (unnamed.png) in the same folder.")

st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Management System</h1>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# PATHS
# ----------------------------------------
excel_file = "expenses.xlsx"
receipt_folder = "receipts"
if not
