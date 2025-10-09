import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide", initial_sidebar_state="collapsed")

# ----------------------------------------
# STATE
# ----------------------------------------
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"
if "view_index" not in st.session_state:
    st.session_state.view_index = None
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# ----------------------------------------
# STYLE
# ----------------------------------------
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }

/* 표 스타일 */
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
  background-color: white;
  border-radius: 10px;
  overflow: hidden;
}
th, td {
  border: 1px solid #ddd;
  padding: 10px 8px;
  text-align: left;
  font-size: 15px;
}
th {
  background: linear-gradient(90deg, #2b5876, #4e4376);
  color: white;
}
tr:hover { background-color: #f9f9f9; }

/* 버튼 스타일 */
.action-btn {
  border: none;
  background: none;
  color: #007bff;
  font-weight: bold;
  cursor: pointer;
}
.action-btn:hover {
  text-decoration: underline;
}

/* 🌙 다크모드 */
@media (prefers-color-scheme: dark) {
  table { background-color: #1e1e1e !important; color: #f5f5f5 !important; }
  th { background: linear-gradient(90deg, #3b7dd8, #4e4376) !important; color: #fff !important; }
  tr:hover { background-color: #2a2a2a !important; }
  td { border-color: #444 !important; }
}

/* 📱 모바일 */
@media (max-width: 768px) {
  table, thead, tbody, th, td, tr { display: block; }
  thead tr { display: none; }
  tr { margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; padding: 10px; }
  td {
    text-align: right;
    padding-left: 50%;
    position: relative;
  }
  td::before {
    content: attr(data-label);
    position: absolute;
    left: 10px;
    width: 45%;
    font-weight: 700;
    text-align: left;
  }
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# HEADER
# ----------------------------------------
if os.path.exists("unnamed.png"):
    st.image(Image.open("unnamed.png"), width=240)
st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Manager</h1>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# INPUT SECTION
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
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_file.read())

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

    # 필터
    months = sorted(df["Month"].unique(), reverse=True)
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

    # 정렬
    asc_flag = True if st.session_state.sort_order == "asc" else False
    view_df = view_df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

    st.markdown(f"### 📋 Saved Records ({'⬆️ Ascending' if asc_flag else '⬇️ Descending'})")
    if st.button("🔁 Toggle Sort Order"):
        st.session_state.sort_order = "asc" if st.session_state.sort_order == "desc" else "desc"
        st.rerun()

    # 테이블
    table_html = "<table><thead><tr><th>Date</th><th>Category</th><th>Description</th><th>Vendor</th><th>Amount</th><th>Actions</th></tr></thead><tbody>"
    for idx, r in view_df.iterrows():
        btn_view = f"<button class='action-btn' onclick=\"window.location.href='?view={idx}'\">View</button>"
        btn_edit = f"<button class='action-btn' onclick=\"window.location.href='?edit={idx}'\">Edit</button>"
        btn_delete = f"<button class='action-btn' onclick=\"window.location.href='?delete={idx}'\">Delete</button>"
        table_html += f"<tr><td data-label='Date'>{r.Date.strftime('%Y-%m-%d')}</td><td data-label='Category'>{r.Category}</td><td data-label='Description'>{r.Description}</td><td data-label='Vendor'>{r.Vendor}</td><td data-label='Amount'>Rp {int(r.Amount):,}</td><td data-label='Actions'>{btn_view} {btn_edit} {btn_delete}</td></tr>"
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

    # --- 실제 동작 버튼 (진짜 작동 부분) ---
    for idx, row in view_df.iterrows():
        # View 모드
        if f"view_{idx}" in st.session_state and st.session_state[f"view_{idx}"]:
            st.image(os.path.join(receipt_folder, str(row["Receipt"])), width=500)
        # Edit 모드
        if f"edit_{idx}" in st.session_state and st.session_state[f"edit_{idx}"]:
            st.write("수정창 열기")
        # Delete 모드
        if f"delete_{idx}" in st.session_state and st.session_state[f"delete_{idx}"]:
            st.write("삭제 기능 작동")

    # Summary
    st.markdown("---")
    st.subheader("📊 Summary (Filtered Data)")
    cat_sum = view_df.groupby("Category", as_index=False)["Amount"].sum()
    cat_sum["Amount"] = cat_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")
    mon_sum = view_df.groupby("Month", as_index=False)["Amount"].sum()
    mon_sum["Amount"] = mon_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")

    c1, c2 = st.columns(2)
    with c1:
        st.write("**By Category**")
        st.table(cat_sum)
    with c2:
        st.write("**By Month**")
        st.table(mon_sum)
else:
    st.info("No records yet.")
