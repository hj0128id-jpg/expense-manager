import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

# ----------------------------------------
# Basic Config
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .ag-theme-streamlit {
        --ag-header-background-color: #2b5876;
        --ag-header-foreground-color: white;
        --ag-row-hover-color: #e3f2fd;
        --ag-odd-row-background-color: #fafafa;
        --ag-font-size: 15px;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------
# Header
# ----------------------------------------
if os.path.exists("unnamed.png"):
    logo = Image.open("unnamed.png")
    st.image(logo, width=280)
else:
    st.warning("⚠️ Please upload your logo file (unnamed.png) in the same folder.")

st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Management System</h1>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# Input Section
#
