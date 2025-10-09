import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
import time

st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# -----------------------------
# STATE
# -----------------------------
if "expanded_row" not in st.session_state:
    st.session_state.expanded_row = None
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"

excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# -----------------------------
# STYLE
# -----------------------------
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  background-color: white;
  border-radius: 8px;
}
th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
  font-size: 14px;
}
th {
  background: linear-gradient(90deg, #2b5876, #4e4376);
  color: white;
}
tr:hover { background-color: #f9f9f9; }
button {
  border: none;
  background: none;
  color: #007bff;
  cursor: pointer;
}
button:hover { text-decoration: underline; }
@media (prefers-color-scheme: dark) {
  table { background-color: #1e1e1e; color: #fff; }
  th { background: linear-gradient(90deg, #3b7dd8, #4e4376); }
  td { border-color: #444; }
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# HEADER
# -----------------------------
if os.path.exists("unnamed.png"):
    st.image(Image.open("unnamed.png"), width=240)
st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Manager</h1>", unsafe_allow_html=True)
st.markdown("---")

# -----------------------------
# INPUT FORM
# -----------------------------
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("Date", datetime.today())
with col2:
    category = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"])
with col3:
    amount = st.number_input("Amount (Rp)", min_value=0, step=1000)
description = st.text_input("Description")
vendor = st.text_input("Vendor")
receipt_file = st.file_uploader("Upload Receipt", type=["png","jpg","jpeg","pdf"])

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
    st.success("✅ Saved!")
    time.sleep(0.5)
    st.rerun()

# -----------------------------
# DISPLAY SECTION
# -----------------------------
if os.path.exists(excel_file):
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

    # 정렬
    asc_flag = True if st.session_state.sort_order == "asc" else False
    view_df = view_df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

    # 헤더 + 다운로드 버튼
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(f"### 📋 Saved Records ({'⬆️ Asc' if asc_flag else '⬇️ Desc'})")
    with h2:
        with st.popover("📥 Download"):
            month_opt = st.selectbox("Export Month", ["All"] + list(months))
            export_df = df if month_opt == "All" else df[df["Month"] == month_opt]
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                export_df.to_excel(writer, index=False)
            st.download_button(
                label=f"📤 Download {month_opt}",
                data=buf.getvalue(),
                file_name=f"DuckSan_Expense_{month_opt}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    if st.button("🔁 Toggle Sort"):
        st.session_state.sort_order = "asc" if st.session_state.sort_order == "desc" else "desc"
        st.rerun()

    # 표 출력
    st.markdown("<table><tr><th>Date</th><th>Category</th><th>Description</th><th>Vendor</th><th>Amount</th><th>Action</th></tr>", unsafe_allow_html=True)
    for idx, r in view_df.iterrows():
        st.markdown(
            f"""
            <tr>
                <td>{r['Date'].strftime('%Y-%m-%d') if pd.notna(r['Date']) else '-'}</td>
                <td>{r['Category']}</td>
                <td>{r['Description']}</td>
                <td>{r['Vendor']}</td>
                <td>Rp {int(r['Amount']):,}</td>
                <td>
                    <form action="?action={idx}" method="get">
                        <input type="hidden" name="row" value="{idx}">
                    </form>
                </td>
            </tr>
            """,
            unsafe_allow_html=True
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🧾 View", key=f"v_{idx}"):
                st.session_state.expanded_row = ("view", idx)
                st.rerun()
        with c2:
            if st.button("✏️ Edit", key=f"e_{idx}"):
                st.session_state.expanded_row = ("edit", idx)
                st.rerun()
        with c3:
            if st.button("🗑️ Delete", key=f"d_{idx}"):
                df = df.drop(view_df.index[idx])
                df.to_excel(excel_file, index=False)
                st.success("🗑️ Deleted!")
                time.sleep(0.5)
                st.rerun()

        # 확장 보기
        if st.session_state.expanded_row and st.session_state.expanded_row[1] == idx:
            mode = st.session_state.expanded_row[0]
            st.markdown("---")
            if mode == "view":
                st.subheader("🧾 Receipt Preview")
                path = os.path.join(receipt_folder, str(r["Receipt"]))
                if os.path.exists(path):
                    if path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(path, width=500)
                    elif path.lower().endswith(".pdf"):
                        st.markdown(f"📄 [Open PDF]({path})", unsafe_allow_html=True)
                else:
                    st.warning("⚠️ File not found.")
                if st.button("Close", key=f"cv_{idx}"):
                    st.session_state.expanded_row = None
                    st.rerun()

            elif mode == "edit":
                st.subheader("✏️ Edit Record")
                new_date = st.date_input("Date", value=r["Date"], key=f"d_{idx}")
                new_cat = st.selectbox("Category",
                    ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                    index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(r["Category"]),
                    key=f"c_{idx}"
                )
                new_desc = st.text_input("Description", value=r["Description"], key=f"desc_{idx}")
                new_vendor = st.text_input("Vendor", value=r["Vendor"], key=f"v_{idx}")
                new_amt = st.number_input("Amount (Rp)", value=float(r["Amount"]), key=f"a_{idx}")
                c4, c5 = st.columns(2)
                with c4:
                    if st.button("💾 Save", key=f"s_{idx}"):
                        df.loc[view_df.index[idx], "Date"] = new_date
                        df.loc[view_df.index[idx], "Category"] = new_cat
                        df.loc[view_df.index[idx], "Description"] = new_desc
                        df.loc[view_df.index[idx], "Vendor"] = new_vendor
                        df.loc[view_df.index[idx], "Amount"] = new_amt
                        df.to_excel(excel_file, index=False)
                        st.success("✅ Updated!")
                        st.session_state.expanded_row = None
                        time.sleep(0.5)
                        st.rerun()
                with c5:
                    if st.button("Cancel", key=f"cc_{idx}"):
                        st.session_state.expanded_row = None
                        st.rerun()

    st.markdown("</table>", unsafe_allow_html=True)

    # 요약
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
