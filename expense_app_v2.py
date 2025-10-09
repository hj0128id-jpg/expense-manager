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
# CSS STYLING
# ----------------------------------------
st.markdown("""
    <style>
    /* 전체 폰트와 컬러 */
    html, body, [class*="st"] {
        font-family: "Segoe UI", sans-serif;
        color: #333333;
    }

    /* 표 스타일 */
    .expense-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 13.5px;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }

    .expense-table thead {
        background: linear-gradient(90deg, #2b5876, #4e4376);
        color: #fff;
    }

    .expense-table th, .expense-table td {
        text-align: left;
        padding: 10px 14px;
    }

    .expense-table tbody tr:nth-child(even) {
        background-color: #f8f9fa;
    }

    .expense-table tbody tr:hover {
        background-color: #e9f3ff;
        transition: 0.2s ease;
    }

    .icon-btn {
        border: none;
        background: none;
        cursor: pointer;
        font-size: 16px;
        color: #2b5876;
        margin-right: 4px;
    }

    .icon-btn:hover {
        color: #1b3f5d;
    }

    .receipt-btn {
        border: none;
        background: none;
        cursor: pointer;
        color: #007bff;
        font-weight: 600;
    }

    .receipt-btn:hover {
        text-decoration: underline;
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
    category = st.selectbox(
        "Category",
        ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"]
    )
with col3:
    amount = st.number_input("Amount (Rp)", min_value=0, step=1000)

description = st.text_input("Description")
vendor = st.text_input("Vendor")
receipt_file = st.file_uploader("Upload Receipt", type=["png","jpg","jpeg","pdf"])

receipt_name = None
if receipt_file is not None:
    receipt_bytes = receipt_file.read()
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_bytes)
    st.success(f"📎 Uploaded: {receipt_name}")

# ----------------------------------------
# SAVE
# ----------------------------------------
if st.button("💾 Save Record"):
    new_data = pd.DataFrame({
        "Date":[date],
        "Category":[category],
        "Description":[description],
        "Vendor":[vendor],
        "Amount":[amount],
        "Receipt":[receipt_name]
    })

    if os.path.exists(excel_file):
        df_old = pd.read_excel(excel_file)
        df = pd.concat([df_old, new_data], ignore_index=True)
    else:
        df = new_data
    df.to_excel(excel_file, index=False)
    st.success("✅ Saved Successfully!")
    time.sleep(0.3)
    st.rerun()

# ----------------------------------------
# DISPLAY SECTION
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    # Title + Download
    title_col1, title_col2 = st.columns([4,1])
    with title_col1:
        st.subheader("📋 Saved Records")
    with title_col2:
        with st.popover("📥 Download Excel"):
            months = sorted(df["Month"].unique(), reverse=True)
            sel_month = st.selectbox("Select month", months)
            filtered = df[df["Month"] == sel_month]
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                filtered.to_excel(writer, index=False, sheet_name=sel_month)
            st.download_button(
                label=f"📤 Download {sel_month}.xlsx",
                data=buffer.getvalue(),
                file_name=f"DuckSan_Expense_{sel_month}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Filter
    f1, f2, f3 = st.columns([1.5,1.5,1])
    with f1:
        month_filter = st.selectbox("📅 Month Filter", ["All"] + months)
    with f2:
        cat_filter = st.selectbox("📂 Category Filter", ["All"] + sorted(df["Category"].unique()))
    with f3:
        reset = st.button("🔄 Reset")

    view_df = df.copy()
    if month_filter != "All":
        view_df = view_df[view_df["Month"] == month_filter]
    if cat_filter != "All":
        view_df = view_df[view_df["Category"] == cat_filter]
    if reset:
        view_df = df.copy()

    # --- Table Rendering ---
    html = """
    <table class='expense-table'>
        <thead>
            <tr>
                <th>Date</th><th>Category</th><th>Description</th>
                <th>Vendor</th><th>Amount</th><th>Receipt</th><th>Action</th>
            </tr>
        </thead><tbody>
    """

    for idx, r in view_df.iterrows():
        receipt_link = "-"
        if pd.notna(r["Receipt"]) and os.path.exists(os.path.join(receipt_folder, r["Receipt"])):
            receipt_link = f"<button class='receipt-btn' id='r_{idx}'>View</button>"

        html += f"""
        <tr>
            <td>{r['Date'].strftime('%Y-%m-%d')}</td>
            <td>{r['Category']}</td>
            <td>{r['Description']}</td>
            <td>{r['Vendor']}</td>
            <td>Rp {int(r['Amount']):,}</td>
            <td>{receipt_link}</td>
            <td>✏️ 🗑️</td>
        </tr>
        """

    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

    # Summary
    st.markdown("---")
    st.subheader("📊 Summary (Filtered Data)")
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(view_df.groupby("Category")["Amount"].sum().reset_index(), use_container_width=True)
    with c2:
        st.dataframe(view_df.groupby("Month")["Amount"].sum().reset_index(), use_container_width=True)
else:
    st.info("No records yet.")
