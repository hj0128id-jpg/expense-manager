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
# CUSTOM STYLE
# ----------------------------------------
table_css = """
<style>
body {
    font-family: 'Segoe UI', sans-serif;
    color: inherit; /* ✅ 시스템 테마 따라감 */
    background-color: transparent; /* ✅ 시스템 배경 유지 */
}

/* ✅ 테이블은 항상 화이트 카드형 */
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

/* 헤더 스타일 */
thead {
    background: linear-gradient(90deg, #2b5876, #4e4376);
    color: white;
}

/* 기본 셀 */
th, td {
    text-align: left;
    padding: 10px 14px;
    color: #222; /* ✅ 항상 선명한 글씨 */
}

/* 짝수행 */
tbody tr:nth-child(even) {
    background-color: #f8f9fa;
}

/* hover 강조 */
tbody tr:hover {
    background-color: #eef4ff;
    transition: 0.2s;
}

/* 링크 버튼 */
a.receipt-btn {
    color: #007bff;
    text-decoration: none;
    font-weight: 600;
}
a.receipt-btn:hover {
    text-decoration: underline;
}

/* 액션 아이콘 */
.action-icons {
    font-size: 16px;
    color: #2b5876;
}

/* Streamlit 다크모드 강제 표색 고정 */
html[data-theme="dark"] table {
    background-color: #ffffff !important;
}
html[data-theme="dark"] th,
html[data-theme="dark"] td {
    color: #222 !important;
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
# FILES
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

    # HTML table
    html = table_css + """
    <table>
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
            receipt_link = f"<a href='?view={idx}' class='receipt-btn'>View</a>"

        html += f"""
        <tr>
            <td>{r['Date'].strftime('%Y-%m-%d')}</td>
            <td>{r['Category']}</td>
            <td>{r['Description']}</td>
            <td>{r['Vendor']}</td>
            <td>Rp {int(r['Amount']):,}</td>
            <td>{receipt_link}</td>
            <td class='action-icons'>✏️ 🗑️</td>
        </tr>
        """

    html += "</tbody></table>"

    # ✅ Use components.html instead of st.markdown
    components.html(html, height=450, scrolling=True)

    # Modal for receipt preview
    params = st.query_params
    if "view" in params:
        try:
            idx = int(params["view"])
            record = view_df.iloc[idx]
            file_path = os.path.join(receipt_folder, record["Receipt"])
            if os.path.exists(file_path):
                with st.modal("🧾 Receipt Preview", key="modal_view"):
                    if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(file_path, use_container_width=True)
                    elif file_path.lower().endswith(".pdf"):
                        st.markdown(f"📄 [Open PDF Receipt]({file_path})")
                    st.button("Close", on_click=lambda: st.query_params.clear())
        except Exception:
            pass

    # Summary
    st.markdown("---")
    st.subheader("📊 Summary (Filtered Data)")
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(view_df.groupby("Category")["Amount"].sum().reset_index(), use_container_width=True)
    with col2:
        st.dataframe(view_df.groupby("Month")["Amount"].sum().reset_index(), use_container_width=True)
else:
    st.info("No records yet.")


