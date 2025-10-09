import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time
from io import BytesIO
import streamlit.components.v1 as components

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ----------------------------------------
# STATE 초기화
# ----------------------------------------
if "selected_receipt" not in st.session_state:
    st.session_state.selected_receipt = None

# ----------------------------------------
# CSS
# ----------------------------------------
table_css = """
<style>
body {
    font-family: 'Segoe UI', sans-serif;
    color: inherit;
    background-color: transparent;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    font-size: 14px;
    border-radius: 10px;
    overflow: hidden;
    background-color: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
thead {
    background: linear-gradient(90deg, #2b5876, #4e4376);
    color: white;
}
th, td {
    text-align: left;
    padding: 10px 14px;
    color: #222;
}
tbody tr:nth-child(even) {
    background-color: #f8f9fa;
}
tbody tr:hover {
    background-color: #eef4ff;
    transition: 0.2s;
}
button.receipt-btn {
    background: none;
    border: none;
    color: #007bff;
    font-weight: 600;
    cursor: pointer;
}
button.receipt-btn:hover {
    text-decoration: underline;
}
.action-icons {
    font-size: 16px;
    color: #2b5876;
}
</style>
"""

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
receipt_file = st.file_uploader("Upload Receipt", type=["png", "jpg", "jpeg", "pdf"])

receipt_name = None
if receipt_file is not None:
    receipt_bytes = receipt_file.read()
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_bytes)
    st.success(f"📎 Uploaded: {receipt_name}")

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
        df_old = pd.read_excel(excel_file)
        df = pd.concat([df_old, new], ignore_index=True)
    else:
        df = new
    df.to_excel(excel_file, index=False)
    st.success("✅ Saved successfully!")
    time.sleep(0.4)
    st.rerun()

# ----------------------------------------
# DISPLAY SECTION
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    c1, c2 = st.columns([4, 1])
    with c1:
        st.subheader("📋 Saved Records")
    with c2:
        months = sorted(df["Month"].unique(), reverse=True)
        with st.popover("📥 Download Excel"):
            sel_month = st.selectbox("Select month", months)
            filt = df[df["Month"] == sel_month]
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                filt.to_excel(writer, index=False, sheet_name=sel_month)
            st.download_button(
                f"📤 Download {sel_month}.xlsx",
                data=buf.getvalue(),
                file_name=f"DuckSan_Expense_{sel_month}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Filters
    f1, f2, f3 = st.columns([1.5, 1.5, 1])
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

    # HTML table (rendered via components)
    html = table_css + """
    <table>
        <thead>
            <tr>
                <th>Date</th><th>Category</th><th>Description</th>
                <th>Vendor</th><th>Amount</th><th>Receipt</th><th>Action</th>
            </tr>
        </thead>
        <tbody>
    """

    # Generate rows
    for idx, r in view_df.iterrows():
        receipt_btn_html = f"<form><button class='receipt-btn' name='view' value='{idx}' formmethod='post'>View</button></form>" \
            if pd.notna(r["Receipt"]) else "-"
        html += f"""
        <tr>
            <td>{r['Date'].strftime('%Y-%m-%d')}</td>
            <td>{r['Category']}</td>
            <td>{r['Description']}</td>
            <td>{r['Vendor']}</td>
            <td>Rp {int(r['Amount']):,}</td>
            <td>{receipt_btn_html}</td>
            <td class='action-icons'>✏️ 🗑️</td>
        </tr>
        """

    html += "</tbody></table>"

    components.html(html, height=450, scrolling=True)

    # Modal handler
    if st.session_state.selected_receipt:
        with st.modal("🧾 Receipt Preview"):
            file_path = st.session_state.selected_receipt
            if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                st.image(file_path, use_container_width=True)
            elif file_path.lower().endswith(".pdf"):
                st.markdown(f"📄 [Open PDF Receipt]({file_path})")
            if st.button("Close"):
                st.session_state.selected_receipt = None
                st.rerun()

else:
    st.info("No records yet.")
