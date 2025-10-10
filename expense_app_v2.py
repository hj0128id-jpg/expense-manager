import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
import time
import tempfile
import mimetypes
import re
import uuid
from supabase import create_client

# ====================================================
# PAGE CONFIG
# ====================================================
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ====================================================
# SUPABASE CONNECTION
# ====================================================
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ====================================================
# STATE 초기화
# ====================================================
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"
if "active_row" not in st.session_state:
    st.session_state.active_row = None
if "active_mode" not in st.session_state:
    st.session_state.active_mode = None

excel_file = "expenses.xlsx"
os.makedirs("receipts", exist_ok=True)

# ====================================================
# 업로드 헬퍼 (Supabase Storage)
# ====================================================
def upload_to_supabase(bucket_name: str, file_name: str, file_path: str):
    mime_type, _ = mimetypes.guess_type(file_name)
    if mime_type is None:
        mime_type = "application/octet-stream"
    try:
        with open(file_path, "rb") as f:
            res = supabase.storage.from_(bucket_name).upload(
                file_name,
                f,
                {"cache-control": "3600", "upsert": "true", "content-type": mime_type}
            )
        return res
    except Exception as e:
        st.error(f"🚨 업로드 중 오류: {e}")
        return None

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
    safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', receipt_file.name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(receipt_file.read())
        tmp.flush()
        res = upload_to_supabase("receipts", unique_name, tmp.name)
        if res:
            receipt_url = f"{SUPABASE_URL}/storage/v1/object/public/receipts/{unique_name}"
    receipt_name = unique_name

# ====================================================
# LOAD & ENSURE ID
# ====================================================
def load_and_ensure_ids(excel_path):
    if not os.path.exists(excel_path):
        return pd.DataFrame(columns=["id", "date", "category", "description", "vendor", "amount", "receipt_url"])
    df = pd.read_excel(excel_path).fillna("-")
    if "id" not in df.columns:
        df["id"] = "-"
    for idx in df.index:
        if df.loc[idx, "id"] == "-" or pd.isna(df.loc[idx, "id"]):
            df.loc[idx, "id"] = str(uuid.uuid4())
    df.to_excel(excel_path, index=False)
    return df

# ====================================================
# SAVE RECORD
# ====================================================
if st.button("💾 Save Record"):
    record_id = str(uuid.uuid4())
    new_data = {
        "id": record_id,
        "date": str(date),
        "category": category,
        "description": description if description else "-",
        "vendor": vendor if vendor else "-",
        "amount": int(amount),
        "receipt_url": receipt_url if receipt_url else receipt_name
    }

    # Excel 저장
    new_df = pd.DataFrame([new_data])
    if os.path.exists(excel_file):
        old_df = pd.read_excel(excel_file).fillna("-")
        df_all = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df_all = new_df
    df_all.to_excel(excel_file, index=False)

    # ✅ Supabase 동기화 (Upsert)
    try:
        supabase.table("expense-data").upsert(new_data).execute()
        st.success("✅ Record saved and synced to Supabase!")
    except Exception as e:
        st.warning(f"⚠️ Supabase upsert failed: {e}")

    time.sleep(0.4)
    st.rerun()

# ====================================================
# DISPLAY SECTION
# ====================================================
df = load_and_ensure_ids(excel_file)
if df.empty:
    st.info("No records yet.")
    st.stop()

# Date parsing
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["Month"] = df["date"].dt.strftime("%Y-%m")

months = sorted(df["Month"].dropna().unique(), reverse=True)
f1, f2, f3 = st.columns([1.5, 1.5, 1])
with f1:
    month_filter = st.selectbox("📅 Filter by Month", ["All"] + list(months))
with f2:
    cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["category"].unique()))
with f3:
    if st.button("🔄 Reset Filters"):
        month_filter = "All"
        cat_filter = "All"

view_df = df.copy()
if month_filter != "All":
    view_df = view_df[view_df["Month"] == month_filter]
if cat_filter != "All":
    view_df = view_df[view_df["category"] == cat_filter]

asc_flag = True if st.session_state.sort_order == "asc" else False
view_df = view_df.sort_values("date", ascending=asc_flag).reset_index(drop=True)

# ====================================================
# SAVED RECORDS TABLE
# ====================================================
st.markdown("### 📋 Saved Records")

header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

categories_list = ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"]

for i, row in view_df.iterrows():
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
    cols[0].write(row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "-")
    cols[1].write(row["category"])
    cols[2].write(row["description"])
    cols[3].write(row["vendor"])
    cols[4].write(f"Rp {int(row['amount']):,}")
    cols[5].markdown(f"[🔗 View]({row['receipt_url']})" if str(row["receipt_url"]).startswith("http") else "-", unsafe_allow_html=True)

    row_id = str(row["id"])

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
                df = df.drop(i)
                df.to_excel(excel_file, index=False)
                try:
                    supabase.table("expense-data").delete().eq("id", row_id).execute()
                except Exception as e:
                    st.warning(f"⚠️ Supabase delete failed: {e}")
                st.success("🗑️ Deleted on Supabase!")
                time.sleep(0.4)
                st.rerun()

    # View or Edit active row
    if st.session_state.active_row == i:
        st.markdown("---")
        if st.session_state.active_mode == "view":
            st.subheader("🧾 Receipt Preview")
            link = row["receipt_url"]
            if str(link).startswith("http"):
                if link.lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(link, width=500)
                elif link.lower().endswith(".pdf"):
                    st.markdown(f"[📄 Open PDF]({link})", unsafe_allow_html=True)
            if st.button("Close", key=f"close_{i}"):
                st.session_state.active_row, st.session_state.active_mode = None, None
                st.rerun()

        elif st.session_state.active_mode == "edit":
            st.subheader("✏️ Edit Record")
            new_date = st.date_input("Date", value=row["date"], key=f"date_{i}")
            new_cat = st.selectbox("Category", categories_list, index=categories_list.index(row["category"]), key=f"cat_{i}")
            new_desc = st.text_input("Description", value=row["description"], key=f"desc_{i}")
            new_vendor = st.text_input("Vendor", value=row["vendor"], key=f"ven_{i}")
            new_amt = st.number_input("Amount (Rp)", value=float(row["amount"]), key=f"amt_{i}")

            c4, c5 = st.columns(2)
            with c4:
                if st.button("💾 Save", key=f"save_{i}"):
                    df.loc[i, ["date", "category", "description", "vendor", "amount"]] = [
                        new_date, new_cat, new_desc, new_vendor, new_amt
                    ]
                    df.to_excel(excel_file, index=False)

                    # ✅ Supabase 업데이트
                    try:
                        supabase.table("expense-data").update({
                            "date": str(new_date),
                            "category": new_cat,
                            "description": new_desc,
                            "vendor": new_vendor,
                            "amount": int(new_amt)
                        }).eq("id", row_id).execute()
                        st.success("✅ Updated on Supabase!")
                    except Exception as e:
                        st.warning(f"⚠️ Supabase update failed: {e}")

                    st.session_state.active_row, st.session_state.active_mode = None, None
                    time.sleep(0.4)
                    st.rerun()
            with c5:
                if st.button("Cancel", key=f"cancel_{i}"):
                    st.session_state.active_row, st.session_state.active_mode = None, None
                    st.rerun()

# ====================================================
# SUMMARY SECTION
# ====================================================
st.markdown("---")
st.markdown("### 📊 Monthly / Category Summary")

summary_col1, summary_col2 = st.columns([1.5, 2])
with summary_col1:
    month_select = st.selectbox("📆 Select Month", ["All"] + list(months))
with summary_col2:
    cat_select = st.selectbox("📁 Select Category", ["All"] + sorted(df["category"].unique()))

summary_df = df.copy()
if month_select != "All":
    summary_df = summary_df[summary_df["Month"] == month_select]
if cat_select != "All":
    summary_df = summary_df[summary_df["category"] == cat_select]

if summary_df.empty:
    st.info("No records for this selection.")
else:
    total = summary_df["amount"].sum()
    st.success(f"💸 Total Spending: Rp {int(total):,}")
    grouped = summary_df.groupby("category", as_index=False)["amount"].sum()
    grouped["amount"] = grouped["amount"].apply(lambda x: f"Rp {int(x):,}")
    st.dataframe(grouped, use_container_width=True)

# ====================================================
# DOWNLOAD
# ====================================================
st.markdown("---")
st.subheader("📥 Download Filtered Excel")

if os.path.exists(excel_file):
    month_opt = st.selectbox("📅 Select Month to Download", ["All"] + list(months))
    if month_opt == "All":
        export_df = df
        fname = f"expenses_all_{datetime.today().strftime('%Y-%m-%d')}.xlsx"
    else:
        export_df = df[df["Month"] == month_opt]
        fname = f"expenses_{month_opt}.xlsx"

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Expenses")

    st.download_button(
        label=f"📤 Download {month_opt}.xlsx",
        data=buf.getvalue(),
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("⚠️ No expenses.xlsx file found to download.")
