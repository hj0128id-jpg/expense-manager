import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
import time
import tempfile
from supabase import create_client
from storage3.utils import FileOptions  # ✅ 필수 추가

# ====================================================
# PAGE CONFIG
# ====================================================
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ====================================================
# SUPABASE AUTH
# ====================================================
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ====================================================
# GLOBAL SETTINGS
# ====================================================
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"
excel_file = "expenses.xlsx"
os.makedirs("receipts", exist_ok=True)

# ====================================================
# HEADER
# ====================================================
if os.path.exists("unnamed.png"):
    st.image(Image.open("unnamed.png"), width=240)
st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Manager</h1>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================
# INPUT FORM
# ====================================================
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

receipt_name, receipt_url = "-", ""
if receipt_file is not None:
    receipt_name = receipt_file.name
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(receipt_file.read())
        tmp.flush()

        try:
            # ✅ Supabase 업로드 (정상 문법)
            res = supabase.storage.from_("receipts").upload(
                receipt_name,
                tmp.name,
                file_options=FileOptions(upsert=True)
            )

            if res.status_code in (200, 201):
                receipt_url = f"{SUPABASE_URL}/storage/v1/object/public/receipts/{receipt_name}"
            else:
                st.warning(f"⚠️ Supabase 업로드 실패 (코드 {res.status_code})")

        except Exception as e:
            st.error(f"🚨 업로드 중 오류 발생: {e}")

# ====================================================
# SAVE RECORD
# ====================================================
if st.button("💾 Save Record"):
    new_data = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description if description else "-"],
        "Vendor": [vendor if vendor else "-"],
        "Amount": [amount],
        "Receipt": [receipt_url if receipt_url else receipt_name]
    })

    if os.path.exists(excel_file):
        old = pd.read_excel(excel_file)
        df = pd.concat([old, new_data], ignore_index=True)
    else:
        df = new_data

    df.to_excel(excel_file, index=False)
    st.success("✅ Record saved successfully (Supabase Synced)!")
    time.sleep(0.5)
    st.rerun()

# ====================================================
# DISPLAY SECTION
# ====================================================
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

# ====================================================
# TABLE
# ====================================================
st.markdown("#### Expense Table")
for i, row in view_df.iterrows():
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 2])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(row['Amount']):,}")
    if row["Receipt"].startswith("http"):
        cols[5].markdown(f"[🔗 View Receipt]({row['Receipt']})", unsafe_allow_html=True)
    else:
        cols[5].write(row["Receipt"])

# ====================================================
# SUMMARY
# ====================================================
st.markdown("---")
st.subheader("📊 Summary (Filtered Data)")
cat_sum = view_df.groupby("Category", as_index=False)["Amount"].sum()
cat_sum["Amount"] = cat_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")
mon_sum = view_df.groupby("Month", as_index=False)["Amount"].sum()
mon_sum["Amount"] = mon_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")

c1, c2 = st.columns(2)
with c1:
    st.write("**By Category**")
    st.dataframe(cat_sum)
with c2:
    st.write("**By Month**")
    st.dataframe(mon_sum)
