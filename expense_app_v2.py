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
if "view_receipt" not in st.session_state:
    st.session_state.view_receipt = None

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
    amount = st.number_input("Amount (Rp)", min_value=0, step=1000)

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
            )

    # Filters
    f1, f2, f3 = st.columns([1.5, 1.5, 1])
    with f1:
        month_filter = st.selectbox("📅 Filter by Month", ["All"] + months)
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

    st.markdown("### 💾 Expense Records")

    # ✅ 헤더 줄 추가
    header_cols = st.columns([1.1, 1.2, 2, 1.3, 1, 0.8])
    headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt"]
    for i, h in enumerate(headers):
        header_cols[i].markdown(f"<div class='header-cell'>{h}</div>", unsafe_allow_html=True)

    # ✅ 데이터 줄 렌더링
    for idx, row in view_df.iterrows():
        cols = st.columns([1.1, 1.2, 2, 1.3, 1, 0.8])
        cols[0].write(row["Date"].strftime("%Y-%m-%d"))
        cols[1].write(row["Category"])
        cols[2].write(row["Description"])
        cols[3].write(row["Vendor"])
        cols[4].write(f"Rp {int(row['Amount']):,}")
        with cols[5]:
            if pd.notna(row["Receipt"]):
                if st.button("View", key=f"view_{idx}"):
                    st.session_state.view_receipt = os.path.join(receipt_folder, row["Receipt"])
                    st.rerun()
            else:
                st.write("-")

    # ✅ 팝업
    if st.session_state.view_receipt:
        with st.modal("🧾 Receipt Preview"):
            path = st.session_state.view_receipt
            if path.lower().endswith((".png", ".jpg", ".jpeg")):
                st.image(path, use_container_width=True)
            elif path.lower().endswith(".pdf"):
                st.markdown(f"📄 [Open PDF Receipt]({path})")
            if st.button("Close"):
                st.session_state.view_receipt = None
                st.rerun()

    # ✅ Summary
    st.markdown("---")
    st.subheader("📊 Summary (Filtered Data)")
    c1, c2 = st.columns(2)
    with c1:
        cat_sum = view_df.groupby("Category")["Amount"].sum().reset_index()
        st.dataframe(cat_sum, use_container_width=True)
    with c2:
        mon_sum = view_df.groupby("Month")["Amount"].sum().reset_index()
        st.dataframe(mon_sum, use_container_width=True)

else:
    st.info("No records yet.")
