import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
import time

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide", initial_sidebar_state="collapsed")

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
# STYLE (모바일 반응형)
# ----------------------------------------
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }
.responsive-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  background-color: white;
  border-radius: 10px;
  overflow: hidden;
}
.responsive-table th, .responsive-table td {
  border: 1px solid #ddd;
  padding: 10px 8px;
  text-align: left;
  font-size: 15px;
}
.responsive-table th {
  background: linear-gradient(90deg, #2b5876, #4e4376);
  color: white;
}
tr:hover { background-color: #f9f9f9; }
.action-btn {
  text-decoration: none;
  color: #007bff;
  font-weight: bold;
  margin-right: 10px;
  cursor: pointer;
}
.action-btn:hover { text-decoration: underline; }

/* 📱 모바일 */
@media (max-width: 768px) {
  .responsive-table thead { display: none; }
  .responsive-table, .responsive-table tbody, .responsive-table tr, .responsive-table td {
    display: block;
    width: 100%;
  }
  .responsive-table tr { margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; padding: 10px; background: white; }
  .responsive-table td {
    text-align: right;
    padding-left: 50%;
    position: relative;
  }
  .responsive-table td::before {
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

    asc_flag = True if st.session_state.sort_order == "asc" else False
    df = df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

    st.markdown(f"### 📋 Saved Records ({'⬆️ Ascending' if asc_flag else '⬇️ Descending'})")
    if st.button("🔁 Toggle Sort Order"):
        st.session_state.sort_order = "asc" if st.session_state.sort_order == "desc" else "desc"
        st.rerun()

    html = """<table class='responsive-table'><thead><tr>
              <th>Date</th><th>Category</th><th>Description</th><th>Vendor</th><th>Amount</th><th>Actions</th></tr></thead><tbody>"""

    for idx, r in df.iterrows():
        actions = f"""
        <a class='action-btn' href='?view={idx}'>View</a>
        <a class='action-btn' href='?edit={idx}'>Edit</a>
        <a class='action-btn' href='?delete={idx}'>Delete</a>
        """
        html += f"""
        <tr>
          <td data-label='Date'>{r.Date.strftime('%Y-%m-%d')}</td>
          <td data-label='Category'>{r.Category}</td>
          <td data-label='Description'>{r.Description}</td>
          <td data-label='Vendor'>{r.Vendor}</td>
          <td data-label='Amount'>Rp {int(r.Amount):,}</td>
          <td data-label='Actions'>{actions}</td>
        </tr>"""
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

    # ✅ Summary Section 복원
    st.markdown("---")
    st.subheader("📊 Summary")

    cat_sum = df.groupby("Category", as_index=False)["Amount"].sum()
    cat_sum["Amount"] = cat_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")

    mon_sum = df.groupby("Month", as_index=False)["Amount"].sum()
    mon_sum["Amount"] = mon_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")

    col1, col2 = st.columns(2)
    with col1:
        st.write("**By Category**")
        st.table(cat_sum)
    with col2:
        st.write("**By Month**")
        st.table(mon_sum)

else:
    st.info("No data yet.")
