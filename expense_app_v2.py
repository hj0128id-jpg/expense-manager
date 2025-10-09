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

# ----------------------------------------
# STATE INIT
# ----------------------------------------
if "view_index" not in st.session_state:
    st.session_state.view_index = None
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"

excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# ----------------------------------------
# STYLE
# ----------------------------------------
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }

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
  vertical-align: top;
}
th {
  background: linear-gradient(90deg, #2b5876, #4e4376);
  color: white;
}
tr:hover { background-color: #f9f9f9; }

@media (prefers-color-scheme: dark) {
  table { background-color: #1e1e1e !important; color: #f5f5f5 !important; }
  th { background: linear-gradient(90deg, #3b7dd8, #4e4376) !important; color: #fff !important; }
  tr:hover { background-color: #2a2a2a !important; }
  td { border-color: #444 !important; }
}

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

receipt_name = "-"
if receipt_file is not None:
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_file.read())

if st.button("💾 Save Record"):
    new = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description if description else "-"],
        "Vendor": [vendor if vendor else "-"],
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
    df = pd.read_excel(excel_file).fillna("-")
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    # 필터
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

    # 정렬
    asc_flag = True if st.session_state.sort_order == "asc" else False
    view_df = view_df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

    # Header + Download
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(f"### 📋 Saved Records ({'⬆️ Ascending' if asc_flag else '⬇️ Descending'})")
    with h2:
        with st.popover("📥 Download Excel"):
            month_opt = st.selectbox("Select month to export", ["All"] + list(months))
            export_df = df if month_opt == "All" else df[df["Month"] == month_opt]
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                export_df.to_excel(writer, index=False, sheet_name="Expenses")
            st.download_button(
                label=f"📤 Download {month_opt}.xlsx",
                data=buffer.getvalue(),
                file_name=f"DuckSan_Expense_{month_opt}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    if st.button("🔁 Toggle Sort Order"):
        st.session_state.sort_order = "asc" if st.session_state.sort_order == "desc" else "desc"
        st.rerun()

    # --- 표 렌더링 ---
    for idx, r in view_df.iterrows():
        with st.container(border=True):
            st.markdown(
                f"""
                <table>
                    <tr>
                        <td><b>Date</b></td><td>{r['Date'].strftime('%Y-%m-%d') if pd.notna(r['Date']) else '-'}</td>
                    </tr>
                    <tr>
                        <td><b>Category</b></td><td>{r['Category']}</td>
                    </tr>
                    <tr>
                        <td><b>Description</b></td><td>{r['Description']}</td>
                    </tr>
                    <tr>
                        <td><b>Vendor</b></td><td>{r['Vendor']}</td>
                    </tr>
                    <tr>
                        <td><b>Amount</b></td><td>Rp {int(r['Amount']):,}</td>
                    </tr>
                </table>
                """,
                unsafe_allow_html=True
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🧾 View", key=f"view_{idx}"):
                    st.session_state.view_index = idx
                    st.session_state.edit_index = None
                    st.rerun()
            with c2:
                if st.button("✏️ Edit", key=f"edit_{idx}"):
                    st.session_state.edit_index = idx
                    st.session_state.view_index = None
                    st.rerun()
            with c3:
                if st.button("🗑️ Delete", key=f"del_{idx}"):
                    df = df.drop(view_df.index[idx])
                    df.to_excel(excel_file, index=False)
                    st.success("🗑️ Record deleted!")
                    time.sleep(0.5)
                    st.rerun()

            # View
            if st.session_state.view_index == idx:
                st.markdown("---")
                st.subheader("🧾 Receipt Preview")
                file_path = os.path.join(receipt_folder, str(r["Receipt"]))
                if os.path.exists(file_path):
                    if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(file_path, width=500)
                    elif file_path.lower().endswith(".pdf"):
                        st.markdown(f"📄 [Open PDF]({file_path})", unsafe_allow_html=True)
                else:
                    st.warning("⚠️ File not found.")
                if st.button("Close", key=f"close_{idx}"):
                    st.session_state.view_index = None
                    st.rerun()

            # Edit
            if st.session_state.edit_index == idx:
                st.markdown("---")
                st.subheader("✏️ Edit Record")
                new_date = st.date_input("Date", value=r["Date"], key=f"date_{idx}")
                new_cat = st.selectbox("Category",
                    ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                    index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(r["Category"]),
                    key=f"cat_{idx}"
                )
                new_desc = st.text_input("Description", value=r["Description"], key=f"desc_{idx}")
                new_vendor = st.text_input("Vendor", value=r["Vendor"], key=f"vendor_{idx}")
                new_amount = st.number_input("Amount (Rp)", value=float(r["Amount"]), key=f"amt_{idx}")

                c4, c5 = st.columns(2)
                with c4:
                    if st.button("💾 Save", key=f"save_{idx}"):
                        df.loc[view_df.index[idx], "Date"] = new_date
                        df.loc[view_df.index[idx], "Category"] = new_cat
                        df.loc[view_df.index[idx], "Description"] = new_desc
                        df.loc[view_df.index[idx], "Vendor"] = new_vendor
                        df.loc[view_df.index[idx], "Amount"] = new_amount
                        df.to_excel(excel_file, index=False)
                        st.success("✅ Record updated!")
                        st.session_state.edit_index = None
                        time.sleep(0.5)
                        st.rerun()
                with c5:
                    if st.button("Cancel", key=f"cancel_{idx}"):
                        st.session_state.edit_index = None
                        st.rerun()

    # --- Summary
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
