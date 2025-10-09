import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
import time

# ----------------------------------------
# CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"
if "active_row" not in st.session_state:
    st.session_state.active_row = None
if "active_mode" not in st.session_state:
    st.session_state.active_mode = None

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

receipt_name = "-"
if receipt_file is not None:
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_file.read())

if st.button("💾 Save Record"):
    new_data = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description if description else "-"],
        "Vendor": [vendor if vendor else "-"],
        "Amount": [amount],
        "Receipt": [receipt_name]
    })
    if os.path.exists(excel_file):
        old = pd.read_excel(excel_file)
        df = pd.concat([old, new_data], ignore_index=True)
    else:
        df = new_data
    df.to_excel(excel_file, index=False)
    st.success("✅ Record saved successfully!")
    time.sleep(0.5)
    st.rerun()

# ----------------------------------------
# DISPLAY SECTION
# ----------------------------------------
if not os.path.exists(excel_file):
    st.info("No records yet.")
    st.stop()

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

asc_flag = True if st.session_state.sort_order == "asc" else False
view_df = view_df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

# 헤더 + 다운로드
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown(f"### 📋 Saved Records ({'⬆️ Ascending' if asc_flag else '⬇️ Descending'})")
with h2:
    with st.popover("📥 Download Excel"):
        month_opt = st.selectbox("Select month to export", ["All"] + list(months))
        export_df = df if month_opt == "All" else df[df["Month"] == month_opt]
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Expenses")
        st.download_button(
            label=f"📤 Download {month_opt}.xlsx",
            data=buf.getvalue(),
            file_name=f"DuckSan_Expense_{month_opt}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if st.button("🔁 Toggle Sort Order"):
    st.session_state.sort_order = "asc" if st.session_state.sort_order == "desc" else "desc"
    st.rerun()

# ----------------------------------------
# TABLE (Streamlit Grid Style)
# ----------------------------------------
st.markdown("#### Expense Table")
header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.2, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

for i, row in view_df.iterrows():
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.2, 1.5])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(row['Amount']):,}")
    cols[5].write(row["Receipt"])

    with cols[6]:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🧾", key=f"view_{i}"):
                st.session_state.active_row, st.session_state.active_mode = i, "view"
                st.rerun()
        with c2:
            if st.button("✏️", key=f"edit_{i}"):
                st.session_state.active_row, st.session_state.active_mode = i, "edit"
                st.rerun()
        with c3:
            if st.button("🗑️", key=f"del_{i}"):
                df = df.drop(view_df.index[i])
                df.to_excel(excel_file, index=False)
                st.success("🗑️ Deleted!")
                time.sleep(0.5)
                st.rerun()

    # 확장 영역
    if st.session_state.active_row == i:
        st.markdown("---")
        if st.session_state.active_mode == "view":
            st.subheader("🧾 Receipt Preview")
            path = os.path.join(receipt_folder, str(row["Receipt"]))
            if os.path.exists(path):
                if path.lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(path, width=500)
                elif path.lower().endswith(".pdf"):
                    st.markdown(f"📄 [Open PDF]({path})", unsafe_allow_html=True)
            else:
                st.warning("⚠️ File not found.")
            if st.button("Close", key=f"close_{i}"):
                st.session_state.active_row = None
                st.rerun()

        elif st.session_state.active_mode == "edit":
            st.subheader("✏️ Edit Record")
            new_date = st.date_input("Date", value=row["Date"], key=f"date_{i}")
            new_cat = st.selectbox("Category",
                ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(row["Category"]),
                key=f"cat_{i}"
            )
            new_desc = st.text_input("Description", value=row["Description"], key=f"desc_{i}")
            new_vendor = st.text_input("Vendor", value=row["Vendor"], key=f"ven_{i}")
            new_amt = st.number_input("Amount (Rp)", value=float(row["Amount"]), key=f"amt_{i}")

            c4, c5 = st.columns(2)
            with c4:
                if st.button("💾 Save", key=f"save_{i}"):
                    df.loc[view_df.index[i], ["Date","Category","Description","Vendor","Amount"]] = [
                        new_date, new_cat, new_desc, new_vendor, new_amt
                    ]
                    df.to_excel(excel_file, index=False)
                    st.success("✅ Updated!")
                    st.session_state.active_row = None
                    time.sleep(0.5)
                    st.rerun()
            with c5:
                if st.button("Cancel", key=f"cancel_{i}"):
                    st.session_state.active_row = None
                    st.rerun()

# ----------------------------------------
# SUMMARY
# ----------------------------------------
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
