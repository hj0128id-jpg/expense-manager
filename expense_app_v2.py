import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time
from io import BytesIO

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ----------------------------------------
# STATE
# ----------------------------------------
if "view_index" not in st.session_state:
    st.session_state.view_index = None
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

# ----------------------------------------
# STYLES
# ----------------------------------------
st.markdown("""
<style>
.stButton > button {
    border: none;
    background-color: transparent;
    color: #007bff;
    font-weight: 600;
    cursor: pointer;
}
.stButton > button:hover {
    text-decoration: underline;
}
.dataframe tbody tr:hover {
    background-color: #eef4ff !important;
}
.header-cell {
    font-weight: 700;
    color: white;
    background: linear-gradient(90deg, #2b5876, #4e4376);
    padding: 8px 10px;
    border-radius: 6px 6px 0 0;
    text-align: left;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# HEADER
# ----------------------------------------
if os.path.exists("unnamed.png"):
    logo = Image.open("unnamed.png")
    st.image(logo, width=240)

st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Management System</h1>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# FILE PATHS
# ----------------------------------------
excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# ----------------------------------------
# INPUT FORM
# ----------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("Date", datetime.today())
with col2:
    category = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"])
with col3:
    amount_str = st.text_input("Amount (Rp)", value="", placeholder="e.g. 1,000,000")
    if amount_str:
        clean_amount = amount_str.replace(",", "").strip()
        amount = int(clean_amount) if clean_amount.isdigit() else 0
    else:
        amount = 0

description = st.text_input("Description")
vendor = st.text_input("Vendor")
receipt_file = st.file_uploader("Upload Receipt", type=["png", "jpg", "jpeg", "pdf"])

receipt_name = None
if receipt_file is not None:
    receipt_bytes = receipt_file.read()
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_bytes)
    st.success(f"📎 Uploaded: {receipt_name}")

# ----------------------------------------
# SAVE RECORD
# ----------------------------------------
if st.button("💾 Save Record"):
    new = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description],
        "Vendor": [vendor],
        "Amount": [amount],
        "Receipt": [receipt_name]
    })
    if os.path.exists(excel_file):
        old = pd.read_excel(excel_file)
        df = pd.concat([old, new], ignore_index=True)
    else:
        df = new
    df.to_excel(excel_file, index=False)
    st.success("✅ Record saved successfully!")
    time.sleep(0.5)
    st.rerun()

# ----------------------------------------
# DISPLAY SECTION
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    left, right = st.columns([4, 1])
    with left:
        st.subheader("📋 Saved Records")
    with right:
        months = sorted(df["Month"].unique(), reverse=True)
        with st.popover("📥 Download Excel"):
            sel = st.selectbox("Select month", months)
            filtered = df[df["Month"] == sel]
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                filtered.to_excel(writer, index=False, sheet_name=sel)
           st.download_button(
    label=f"📤 Download {sel}.xlsx",
    data=buf.getvalue(),
    file_name=f"DuckSan_Expense_{sel}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


