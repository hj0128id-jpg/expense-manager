import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time
from io import BytesIO

st.set_page_config(page_title="Duck San Expense Manager", layout="wide", initial_sidebar_state="collapsed")

if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"

excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# ✅ CSS
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
tr:hover { background-color: #f1f1f1; }

/* 📱 모바일용 */
@media (max-width: 768px) {
  .responsive-table thead { display: none; }
  .responsive-table, .responsive-table tbody, .responsive-table tr, .responsive-table td {
    display: block;
    width: 100%;
  }
  .responsive-table tr { margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; padding: 10px; }
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

# ✅ 로고
if os.path.exists("unnamed.png"):
    st.image(Image.open("unnamed.png"), width=240)
st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Manager</h1>", unsafe_allow_html=True)
st.markdown("---")

# ✅ 입력 영역
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("Date", datetime.today())
with col2:
    category = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"])
with col3:
    amount = st.number_input("Amount (Rp)", min_value=0, step=1000)

description = st.text_input("Description")
vendor = st.text_input("Vendor")
receipt = st.file_uploader("Upload Receipt", type=["png", "jpg", "jpeg", "pdf"])

receipt_name = None
if receipt:
    receipt_name = receipt.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt.read())

if st.button("💾 Save"):
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
    st.success("✅ Saved!")
    st.rerun()

# ✅ 데이터 표시
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])

    if st.button("⬆️ Ascending" if st.session_state.sort_order == "desc" else "⬇️ Descending"):
        st.session_state.sort_order = "asc" if st.session_state.sort_order == "desc" else "desc"
        st.rerun()

    asc_flag = True if st.session_state.sort_order == "asc" else False
    df = df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

    html = """<table class='responsive-table'><thead><tr>
              <th>Date</th><th>Category</th><th>Description</th><th>Vendor</th><th>Amount</th><th>Receipt</th></tr></thead><tbody>"""
    for _, r in df.iterrows():
        view_btn = f"<a href='/app?view={r.Receipt}' target='_blank'>View</a>" if pd.notna(r.Receipt) else "-"
        html += f"""
        <tr>
          <td data-label='Date'>{r.Date.strftime('%Y-%m-%d')}</td>
          <td data-label='Category'>{r.Category}</td>
          <td data-label='Description'>{r.Description}</td>
          <td data-label='Vendor'>{r.Vendor}</td>
          <td data-label='Amount'>Rp {int(r.Amount):,}</td>
          <td data-label='Receipt'>{view_btn}</td>
        </tr>"""
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("No data yet.")
