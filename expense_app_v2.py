import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO
from supabase import create_client
import tempfile
import time

# ----------------------------------------
# SUPABASE CONFIG
# ----------------------------------------
SUPABASE_URL = "https://wopkkfxfhvfodovieptg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcGtrZnhmaHZmb2RvdmllcHRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAwNjE3NjcsImV4cCI6MjA3NTYzNzc2N30.NY9EMZtqBmRBO0S4xNwk9M7Vj7ON_gCrC3u-S_-J9_Q"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TABLE_NAME = "expense-data"
BUCKET_NAME = "receipts"

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

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

# ----------------------------------------
# SAVE BUTTON
# ----------------------------------------
if st.button("💾 Save Record"):
    receipt_url = None

    # --- 1. 영수증 업로드 ---
    if receipt_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(receipt_file.getvalue())
            tmp_path = tmp.name
        try:
            # ✅ 수정된 부분 — file 인자 중복 제거
            res = supabase.storage.from_(BUCKET_NAME).upload(
                receipt_file.name,
                tmp_path,
                {"upsert": True}
            )
            if hasattr(res, "error") and res.error:
                st.error(f"🚨 Upload failed: {res.error}")
            else:
                receipt_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{receipt_file.name}"
        except Exception as e:
            st.error(f"🚨 Supabase upload failed: {str(e)}")

    # --- 2. DB 저장 ---
    data = {
        "date": str(date),
        "category": category,
        "description": description,
        "vendor": vendor,
        "amount": amount,
        "receipt_url": receipt_url
    }

    res = supabase.table(TABLE_NAME).insert(data).execute()
    if hasattr(res, "error") and res.error:
        st.error(f"🚨 Database insert failed: {res.error}")
    else:
        st.success("✅ Record saved successfully!")
        time.sleep(0.5)
        st.rerun()

# ----------------------------------------
# LOAD DATA
# ----------------------------------------
try:
    df = pd.DataFrame(supabase.table(TABLE_NAME).select("*").execute().data)
except Exception:
    st.info("No records found yet.")
    st.stop()

if df.empty:
    st.info("No records yet.")
    st.stop()

# ----------------------------------------
# FILTERS
# ----------------------------------------
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["Month"] = df["date"].dt.strftime("%Y-%m")

months = sorted(df["Month"].dropna().unique(), reverse=True)
f1, f2, f3 = st.columns([1.5, 1.5, 1])
with f1:
    month_filter = st.selectbox("📅 Filter by Month", ["All"] + list(months))
with f2:
    cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["category"].unique()))
with f3:
    reset = st.button("🔄 Reset Filters")

view_df = df.copy()
if month_filter != "All":
    view_df = view_df[view_df["Month"] == month_filter]
if cat_filter != "All":
    view_df = view_df[view_df["category"] == cat_filter]
if reset:
    view_df = df.copy()

# ----------------------------------------
# DISPLAY TABLE
# ----------------------------------------
st.markdown("---")
st.subheader("📋 Saved Records")

header_cols = st.columns([1, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

for i, row in view_df.iterrows():
    cols = st.columns([1, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
    cols[0].write(row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "-")
    cols[1].write(row["category"])
    cols[2].write(row["description"])
    cols[3].write(row["vendor"])
    cols[4].write(f"Rp {int(row['amount']):,}")
    if row["receipt_url"]:
        cols[5].markdown(f"[🧾 View]({row['receipt_url']})", unsafe_allow_html=True)
    else:
        cols[5].write("-")

    with cols[6]:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✏️", key=f"edit_{i}"):
                st.session_state.active_row = i
                st.session_state.mode = "edit"
                st.rerun()
        with c3:
            if st.button("🗑️", key=f"del_{i}"):
                supabase.table(TABLE_NAME).delete().eq("id", row["id"]).execute()
                st.success("🗑️ Deleted!")
                time.sleep(0.5)
                st.rerun()

    if "active_row" in st.session_state and st.session_state.active_row == i:
        st.markdown("---")
        st.subheader("✏️ Edit Record")

        new_date = st.date_input("Date", value=row["date"], key=f"date_{i}")
        new_cat = st.selectbox("Category",
            ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
            index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(row["category"]),
            key=f"cat_{i}"
        )
        new_desc = st.text_input("Description", value=row["description"], key=f"desc_{i}")
        new_vendor = st.text_input("Vendor", value=row["vendor"], key=f"ven_{i}")
        new_amt = st.number_input("Amount (Rp)", value=float(row["amount"]), key=f"amt_{i}")

        c4, c5 = st.columns(2)
        with c4:
            if st.button("💾 Save", key=f"save_{i}"):
                supabase.table(TABLE_NAME).update({
                    "date": str(new_date),
                    "category": new_cat,
                    "description": new_desc,
                    "vendor": new_vendor,
                    "amount": new_amt
                }).eq("id", row["id"]).execute()
                st.success("✅ Updated!")
                time.sleep(0.5)
                del st.session_state["active_row"]
                st.rerun()
        with c5:
            if st.button("Cancel", key=f"cancel_{i}"):
                del st.session_state["active_row"]
                st.rerun()

# ----------------------------------------
# SUMMARY
# ----------------------------------------
st.markdown("---")
st.subheader("📊 Summary (Filtered Data)")

cat_sum = view_df.groupby("category", as_index=False)["amount"].sum()
cat_sum["amount"] = cat_sum["amount"].apply(lambda x: f"Rp {int(x):,}")

mon_sum = view_df.groupby("Month", as_index=False)["amount"].sum()
mon_sum["amount"] = mon_sum["amount"].apply(lambda x: f"Rp {int(x):,}")

c1, c2 = st.columns(2)
with c1:
    st.write("**By Category**")
    st.dataframe(cat_sum, use_container_width=True)
with c2:
    st.write("**By Month**")
    st.dataframe(mon_sum, use_container_width=True)
