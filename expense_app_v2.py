import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
import time
import tempfile
import mimetypes
import re
import uuid
from supabase import create_client

# ====================================================
# PAGE CONFIG
# ====================================================
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ====================================================
# SUPABASE AUTH
# ====================================================
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ====================================================
# STATE
# ====================================================
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"
if "active_row" not in st.session_state:
    st.session_state.active_row = None
if "active_mode" not in st.session_state:
    st.session_state.active_mode = None

excel_file = "expenses.xlsx"
os.makedirs("receipts", exist_ok=True)

# ====================================================
# FILE UPLOAD HELPER
# ====================================================
def upload_to_supabase(bucket_name: str, file_name: str, file_path: str):
    mime_type, _ = mimetypes.guess_type(file_name)
    if mime_type is None:
        mime_type = "application/octet-stream"

    try:
        with open(file_path, "rb") as f:
            res = supabase.storage.from_(bucket_name).upload(
                file_name,
                f,
                {"cache-control": "3600", "upsert": "true", "content-type": mime_type}
            )
        st.toast("✅ Uploaded to Supabase")
        return res
    except Exception as e:
        st.error(f"🚨 업로드 중 오류: {e}")
        return None

# ====================================================
# HEADER
# ====================================================
if os.path.exists("unnamed.png"):
    st.image(Image.open("unnamed.png"), width=240)
st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Manager</h1>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================
# INPUT FORM
# ====================================================
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("Date", datetime.today())
with col2:
    category = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"])
with col3:
    amount = st.number_input("Amount (Rp)", min_value=0, step=1000)

description = st.text_input("Description")
vendor = st.text_input("Vendor")
receipt_file = st.file_uploader("Upload Receipt", type=["png", "jpg", "jpeg", "pdf"])

receipt_name, receipt_url = "-", ""
if receipt_file is not None:
    safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', receipt_file.name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(receipt_file.read())
        tmp.flush()
        res = upload_to_supabase("receipts", unique_name, tmp.name)
        if res:
            receipt_url = f"{SUPABASE_URL}/storage/v1/object/public/receipts/{unique_name}"
    receipt_name = unique_name

if st.button("💾 Save Record"):
    new_data = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description if description else "-"],
        "Vendor": [vendor if vendor else "-"],
        "Amount": [amount],
        "Receipt": [receipt_url if receipt_url else receipt_name]
    })
    if os.path.exists(excel_file):
        old = pd.read_excel(excel_file)
        df = pd.concat([old, new_data], ignore_index=True)
    else:
        df = new_data
    df.to_excel(excel_file, index=False)
    st.success("✅ Record saved successfully (Supabase Synced)!")
    time.sleep(0.5)
    st.rerun()

# ====================================================
# DISPLAY SECTION
# ====================================================
if not os.path.exists(excel_file):
    st.info("No records yet.")
    st.stop()

df = pd.read_excel(excel_file).fillna("-")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Month"] = df["Date"].dt.strftime("%Y-%m")

months = sorted(df["Month"].dropna().unique(), reverse=True)
f1, f2, f3 = st.columns([1.5, 1.5, 1])
with f1:
    month_filter = st.selectbox("📅 Filter by Month", ["All"] + list(months))
with f2:
    cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["Category"].unique()))
with f3:
    reset = st.button("🔄 Reset Filters")

view_df = df.copy()
if month_filter != "All":
    view_df = view_df[view_df["Month"] == month_filter]
if cat_filter != "All":
    view_df = view_df[view_df["Category"] == cat_filter]
if reset:
    view_df = df.copy()

asc_flag = True if st.session_state.sort_order == "asc" else False
view_df = view_df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

# ====================================================
# SAVED RECORDS SECTION (with Header)
# ====================================================
st.markdown("### 📋 Saved Records")

# === 테이블 헤더 표시 ===
header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

# === 데이터 행 표시 ===
for i, row in view_df.iterrows():
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(row['Amount']):,}")
    cols[5].markdown(f"[🔗 View]({row['Receipt']})" if str(row["Receipt"]).startswith("http") else row["Receipt"], unsafe_allow_html=True)

    with cols[6]:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🧾", key=f"view_{i}"):
                st.session_state.active_row, st.session_state.active_mode = i, "view"
                st.rerun()
        with c2:
            if st.button("✏️", key=f"edit_{i}"):
                st.session_state.active_row, st.session_state.active_mode = i, "edit"
                st.rerun()
        with c3:
            if st.button("🗑️", key=f"del_{i}"):
                df = df.drop(view_df.index[i])
                df.to_excel(excel_file, index=False)
                st.success("🗑️ Deleted!")
                time.sleep(0.5)
                st.rerun()

# ====================================================
# SUMMARY SECTION (MONTH & CATEGORY)
# ====================================================
st.markdown("---")
st.markdown("### 📊 Monthly / Category Summary")

summary_col1, summary_col2 = st.columns([1.5, 2])
with summary_col1:
    month_select = st.selectbox("📆 Select Month", list(months))
with summary_col2:
    cat_select = st.selectbox("📁 Select Category", ["All"] + sorted(df["Category"].unique()))

summary_df = df[df["Month"] == month_select]
if cat_select != "All":
    summary_df = summary_df[summary_df["Category"] == cat_select]

if summary_df.empty:
    st.info("No records for this selection.")
else:
    total_amount = summary_df["Amount"].sum()
    st.success(f"💸 Total Spending: Rp {int(total_amount):,}")

    grouped = summary_df.groupby("Category", as_index=False)["Amount"].sum()
    grouped["Amount"] = grouped["Amount"].apply(lambda x: f"Rp {int(x):,}")
    st.markdown("**Detailed Breakdown:**")
    st.dataframe(grouped, use_container_width=True)
