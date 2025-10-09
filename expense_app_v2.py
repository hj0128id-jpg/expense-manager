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
# CSS STYLE
# ----------------------------------------
st.markdown("""
    <style>
    .expense-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }
    .expense-table th {
        background-color: #2b5876;
        color: white;
        text-align: left;
        padding: 8px;
    }
    .expense-table td {
        border-bottom: 1px solid #ddd;
        padding: 6px 8px;
        vertical-align: middle;
    }
    .receipt-btn {
        background: none;
        border: none;
        color: #2b5876;
        cursor: pointer;
        font-weight: bold;
    }
    .receipt-btn:hover {
        text-decoration: underline;
    }
    .small-btn {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 15px;
        margin-right: 5px;
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
if not os.path.exists(receipt_folder):
    os.makedirs(receipt_folder)

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
if st.button("💾 Save"):
    new_data = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description],
        "Vendor": [vendor],
        "Amount": [amount],
        "Receipt": [receipt_name]
    })

    if os.path.exists(excel_file):
        old_data = pd.read_excel(excel_file)
        df = pd.concat([old_data, new_data], ignore_index=True)
    else:
        df = new_data

    df.to_excel(excel_file, index=False)
    st.success("✅ Data saved successfully!")
    time.sleep(0.5)
    st.rerun()

# ----------------------------------------
# DISPLAY + EDIT / DELETE
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    # Title + Download
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("📋 Saved Records")
    with col2:
        with st.popover("📥 Download Excel"):
            selected_month = st.selectbox(
                "Select month to download:",
                sorted(df["Date"].dt.strftime("%Y-%m").unique(), reverse=True)
            )
            filtered_month = df[df["Date"].dt.strftime("%Y-%m") == selected_month]
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                filtered_month.to_excel(writer, index=False, sheet_name=f"{selected_month}")
            st.download_button(
                label=f"📤 Download {selected_month}.xlsx",
                data=buffer.getvalue(),
                file_name=f"DuckSan_Expense_{selected_month}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Filters
    f1, f2, f3 = st.columns([1.5, 1.5, 1])
    with f1:
        month_filter = st.selectbox("📅 Filter by Month", ["All"] + sorted(df["Month"].unique(), reverse=True))
    with f2:
        cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["Category"].unique()))
    with f3:
        reset = st.button("🔄 Reset Filters")

    filtered_df = df.copy()
    if month_filter != "All":
        filtered_df = filtered_df[filtered_df["Month"] == month_filter]
    if cat_filter != "All":
        filtered_df = filtered_df[filtered_df["Category"] == cat_filter]
    if reset:
        filtered_df = df.copy()

    # Table Header
    st.markdown("""
        <table class='expense-table'>
        <tr>
            <th>Date</th>
            <th>Category</th>
            <th>Description</th>
            <th>Vendor</th>
            <th>Amount</th>
            <th>Receipt</th>
            <th>Action</th>
        </tr>
    """, unsafe_allow_html=True)

    # Table Rows
    for idx, row in filtered_df.iterrows():
        receipt_html = "-"
        if pd.notna(row["Receipt"]) and os.path.exists(os.path.join(receipt_folder, row["Receipt"])):
            receipt_html = f"<button class='receipt-btn' id='btn_{idx}'>🔍 View</button>"

        st.markdown(
            f"""
            <tr>
                <td>{row['Date'].strftime('%Y-%m-%d')}</td>
                <td>{row['Category']}</td>
                <td>{row['Description']}</td>
                <td>{row['Vendor']}</td>
                <td>Rp {int(row['Amount']):,}</td>
                <td>{receipt_html}</td>
                <td>✏️ 🗑️</td>
            </tr>
            """,
            unsafe_allow_html=True
        )

    st.markdown("</table>", unsafe_allow_html=True)

    # Summary
    st.markdown("---")
    st.subheader("📊 Summary (Filtered Data)")
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(filtered_df.groupby("Category")["Amount"].sum().reset_index())
    with c2:
        st.dataframe(filtered_df.groupby("Month")["Amount"].sum().reset_index())

else:
    st.info("No data saved yet.")
