import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time
import tempfile
import mimetypes
import re
import uuid
import json
from supabase import create_client

# ====================================================
# PAGE CONFIG
# ====================================================
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ====================================================
# SUPABASE CONNECTION
# ====================================================
@st.cache_resource(ttl=0, show_spinner=False)
def get_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase()

# ====================================================
# SESSION STATE
# ====================================================
if "active_row" not in st.session_state:
    st.session_state.active_row = None
if "active_mode" not in st.session_state:
    st.session_state.active_mode = None
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

excel_file = "expenses.xlsx"
os.makedirs("receipts", exist_ok=True)

# ====================================================
# 업로드 헬퍼
# ====================================================
def upload_to_supabase(bucket_name: str, file_name: str, file_path: str):
    mime_type, _ = mimetypes.guess_type(file_name)
    if mime_type is None:
        mime_type = "application/octet-stream"
    try:
        with open(file_path, "rb") as f:
            supabase.storage.from_(bucket_name).upload(
                file_name, f,
                {"cache-control": "3600", "upsert": "true", "content-type": mime_type}
            )
        return True
    except Exception as e:
        st.error(f"🚨 Upload error: {e}")
        return False

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
        if upload_to_supabase("receipts", unique_name, tmp.name):
            receipt_url = f"{st.secrets['supabase']['url']}/storage/v1/object/public/receipts/{unique_name}"
    receipt_name = unique_name

# ====================================================
# SAVE NEW RECORD
# ====================================================
if st.button("💾 Save Record", use_container_width=True):
    record_id = str(uuid.uuid4())
    new_data = {
        "id": record_id,
        "Date": str(date),
        "Category": category,
        "Description": description or "-",
        "Vendor": vendor or "-",
        "Amount": int(amount),
        "Receipt_url": receipt_url or receipt_name
    }

    new_df = pd.DataFrame([new_data])
    if os.path.exists(excel_file):
        old_df = pd.read_excel(excel_file).fillna("-")
        df_all = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df_all = new_df

    df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")
    df_all = df_all.sort_values("Date", ascending=False)
    df_all.to_excel(excel_file, index=False)

    try:
        supabase.table("expense-data").upsert(new_data).execute()
    except Exception as e:
        st.warning(f"Supabase insert failed: {e}")

    st.session_state.df = df_all
    st.success("✅ Record Saved!")
    time.sleep(0.5)
    st.rerun()

# ====================================================
# LOAD & CLEANUP
# ====================================================
def load_and_ensure_ids(excel_path):
    base_cols = ["id", "Date", "Category", "Description", "Vendor", "Amount", "Receipt_url"]
    if not os.path.exists(excel_path):
        return pd.DataFrame(columns=base_cols)
    df = pd.read_excel(excel_path).fillna("-")
    for c in base_cols:
        if c not in df.columns:
            df[c] = "-"
    for i in df.index:
        if not df.loc[i, "id"] or df.loc[i, "id"] in ["-", "None", "nan"]:
            df.loc[i, "id"] = str(uuid.uuid4())
    df.to_excel(excel_path, index=False)
    return df

def sync_supabase_to_excel(excel_path):
    try:
        res = supabase.table("expense-data").select("*").execute()
        data = getattr(res, "data", None)
        supa_data = pd.DataFrame(data if data else [])
        if supa_data.empty:
            return
        if "Date" in supa_data.columns:
            supa_data["Date"] = pd.to_datetime(supa_data["Date"], errors="coerce")
        if os.path.exists(excel_path):
            local_df = pd.read_excel(excel_path).fillna("-")
        else:
            local_df = pd.DataFrame(columns=supa_data.columns)
        merged = pd.concat([local_df, supa_data]).drop_duplicates(subset=["id"], keep="last")
        merged.to_excel(excel_path, index=False)
        st.session_state.df = merged
    except Exception:
        pass

df = load_and_ensure_ids(excel_file)
sync_supabase_to_excel(excel_file)

df = df.dropna(how="all").replace("-", None)
df = df[df["Date"].notna()]
df = df.fillna("-")
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Month"] = df["Date"].dt.strftime("%Y-%m")

# ====================================================
# FILTER
# ====================================================
months = sorted(df["Month"].dropna().unique(), reverse=True)
f1, f2 = st.columns(2)
with f1:
    month_filter = st.selectbox("📅 Filter by Month", ["All"] + list(months))
with f2:
    cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["Category"].unique()))

view_df = df.copy()
if month_filter != "All":
    view_df = view_df[view_df["Month"] == month_filter]
if cat_filter != "All":
    view_df = view_df[view_df["Category"] == cat_filter]

# ====================================================
# SAVED RECORDS
# ====================================================
st.markdown("### 📋 Saved Records")

header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
with header_cols[0]:
    sort_icon = "⬇️" if st.session_state.sort_order == "desc" else "⬆️"
    if st.button(f"📅 Date {sort_icon}"):
        st.session_state.sort_order = "asc" if st.session_state.sort_order == "desc" else "desc"
        st.rerun()
for c, h in zip(header_cols[1:], ["Category", "Description", "Vendor", "Amount", "Receipt_url", "Actions"]):
    c.markdown(f"**{h}**")

ascending_flag = st.session_state.sort_order == "asc"
view_df = view_df.sort_values("Date", ascending=ascending_flag).reset_index(drop=True)

df["id"] = df["id"].astype(str)
for _, row in view_df.iterrows():
    row_id = str(row["id"])
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
    date_display = row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-"
    cols[0].write(date_display)
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(float(row['Amount'])):,}")
    link = row.get("Receipt_url", "-")
    cols[5].markdown(f"[🔗 View]({link})" if str(link).startswith("http") else "-", unsafe_allow_html=True)
    with cols[6]:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🧾", key=f"view_{row_id}"):
                st.session_state.active_row, st.session_state.active_mode = row_id, "view"
                st.rerun()
        with c2:
            if st.button("✏️", key=f"edit_{row_id}"):
                st.session_state.active_row, st.session_state.active_mode = row_id, "edit"
                st.rerun()
        with c3:
            if st.button("🗑️", key=f"del_{row_id}"):
                df = df[df["id"] != row_id]
                df.to_excel(excel_file, index=False)
                supabase.table("expense-data").delete().eq("id", row_id).execute()
                st.session_state.df = df
                st.success("🗑️ Deleted!")
                time.sleep(0.3)
                st.rerun()

    if st.session_state.active_row == row_id:
        st.markdown("---")
        if st.session_state.active_mode == "view":
            st.subheader("🧾 Receipt Preview")
            if link.startswith("http"):
                if link.lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(link, width=500)
                elif link.lower().endswith(".pdf"):
                    st.markdown(f"[📄 Open PDF]({link})", unsafe_allow_html=True)
            if st.button("Close", key=f"close_{row_id}"):
                st.session_state.active_row = None
                st.session_state.active_mode = None
                st.rerun()

        elif st.session_state.active_mode == "edit":
            st.subheader("✏️ Edit Record")
            new_date = st.date_input("Date", value=row["Date"], key=f"date_{row_id}")
            new_cat = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"], key=f"cat_{row_id}")
            new_desc = st.text_input("Description", value=row["Description"], key=f"desc_{row_id}")
            new_vendor = st.text_input("Vendor", value=row["Vendor"], key=f"ven_{row_id}")
            new_amt = st.number_input("Amount (Rp)", value=float(row["Amount"]), key=f"amt_{row_id}")
            c4, c5 = st.columns(2)
            with c4:
                if st.button("💾 Save", key=f"save_{row_id}"):
                    df.loc[df["id"] == row_id, ["Date", "Category", "Description", "Vendor", "Amount"]] = [str(new_date), new_cat, new_desc, new_vendor, int(new_amt)]
                    df.to_excel(excel_file, index=False)
                    supabase.table("expense-data").update({
                        "Date": str(new_date),
                        "Category": new_cat,
                        "Description": new_desc,
                        "Vendor": new_vendor,
                        "Amount": int(new_amt)
                    }).eq("id", row_id).execute()
                    st.session_state.df = df
                    st.success("✅ Updated!")
                    time.sleep(0.3)
                    st.rerun()
            with c5:
                if st.button("Cancel", key=f"cancel_{row_id}"):
                    st.session_state.active_row = None
                    st.session_state.active_mode = None
                    st.rerun()

# ====================================================
# SUMMARY (접히는 버전)
# ====================================================
st.markdown("---")
with st.expander("📊 Monthly & Category Summary", expanded=False):
    st.subheader("📈 Summary Overview")
    col1, col2 = st.columns(2)
    with col1:
        month_summary = st.selectbox("📅 Select Month", ["All"] + list(months), key="summary_month")
    with col2:
        cat_summary = st.selectbox("📁 Select Category", ["All"] + sorted(df["Category"].unique()), key="summary_cat")
    summary_df = df.copy()
    if month_summary != "All":
        summary_df = summary_df[summary_df["Month"] == month_summary]
    if cat_summary != "All":
        summary_df = summary_df[summary_df["Category"] == cat_summary]
    if summary_df.empty:
        st.info("No data for this selection.")
    else:
        count = len(summary_df)
        total = summary_df["Amount"].sum()
        st.success(f"📌 {month_summary if month_summary!='All' else 'All months'} | {cat_summary if cat_summary!='All' else 'All categories'} → {count} transactions, Rp {int(total):,}")
        display_df = summary_df[["Date", "Category", "Description", "Vendor", "Amount", "Receipt_url"]].copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
        display_df["Amount"] = display_df["Amount"].apply(lambda x: f"Rp {int(x):,}")
        st.dataframe(display_df, use_container_width=True)
