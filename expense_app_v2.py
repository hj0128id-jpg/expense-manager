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
# 업로드 헬퍼
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
# LOAD & ENSURE IDS
# ====================================================
def load_and_ensure_ids(excel_path):
    if not os.path.exists(excel_path):
        return pd.DataFrame(columns=["id", "Date", "Category", "Description", "Vendor", "Amount", "Receipt_url"])
    df = pd.read_excel(excel_path).fillna("-")
    if "id" not in df.columns:
        df["id"] = "-"
    # 누락된 id 자동 생성
    for idx in df.index:
        if not df.loc[idx, "id"] or df.loc[idx, "id"] in ["-", "None", "nan"]:
            df.loc[idx, "id"] = str(uuid.uuid4())
    df.to_excel(excel_path, index=False)
    return df

# ====================================================
# SYNC EXCEL → SUPABASE
# ====================================================
def sync_excel_to_supabase(df):
    try:
        res = supabase.table("expense-data").select("id").execute()
        existing_ids = [r["id"] for r in res.data] if hasattr(res, "data") and res.data else []
        new_records = df[~df["id"].isin(existing_ids)]
        if not new_records.empty:
            supabase.table("expense-data").upsert(new_records.to_dict(orient="records")).execute()
            st.success(f"📤 Synced {len(new_records)} missing records to Supabase!")
    except Exception as e:
        st.warning(f"⚠️ Sync error: {e}")

# ====================================================
# SAVE NEW RECORD
# ====================================================
if st.button("💾 Save Record"):
    record_id = str(uuid.uuid4())
    new_data = {
        "id": record_id,
        "Date": str(date),
        "Category": category,
        "Description": description if description else "-",
        "Vendor": vendor if vendor else "-",
        "Amount": int(amount),
        "Receipt_url": receipt_url if receipt_url else receipt_name
    }

    new_df = pd.DataFrame([new_data])
    if os.path.exists(excel_file):
        old_df = pd.read_excel(excel_file).fillna("-")
        df_all = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df_all = new_df
    df_all.to_excel(excel_file, index=False)

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
sync_excel_to_supabase(df)
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

if df.empty:
    st.info("No records yet.")
    st.stop()

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Month"] = df["Date"].dt.strftime("%Y-%m")

months = sorted(df["Month"].dropna().unique(), reverse=True)
f1, f2, f3 = st.columns([1.5, 1.5, 1])
with f1:
    month_filter = st.selectbox("📅 Filter by Month", ["All"] + list(months))
with f2:
    cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["Category"].unique()))
with f3:
    if st.button("🔄 Reset Filters"):
        month_filter = "All"
        cat_filter = "All"

view_df = df.copy()
if month_filter != "All":
    view_df = view_df[view_df["Month"] == month_filter]
if cat_filter != "All":
    view_df = view_df[view_df["Category"] == cat_filter]

asc_flag = True if st.session_state.sort_order == "asc" else False
view_df = view_df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

# ====================================================
# SAVED RECORDS TABLE
# ====================================================
st.markdown("### 📋 Saved Records")

header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt_url", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

categories_list = ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"]

for _, row in view_df.iterrows():
    row_id = str(row["id"])
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(float(row['Amount'])):,}")
    cols[5].markdown(f"[🔗 View]({row['Receipt_url']})" if str(row["Receipt_url"]).startswith("http") else "-", unsafe_allow_html=True)

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
                try:
                    real_df = pd.read_excel(excel_file).fillna("-")
                    real_df = real_df[real_df["id"].astype(str) != row_id]
                    real_df.to_excel(excel_file, index=False)
                    supabase.table("expense-data").delete().eq("id", row_id).execute()
                    st.success("🗑️ Deleted!")
                except Exception as e:
                    st.warning(f"⚠️ Delete failed: {e}")
                time.sleep(0.4)
                st.rerun()

    # ====================================================
    # ACTIVE ROW (VIEW / EDIT)
    # ====================================================
    if st.session_state.active_row == row_id:
        st.markdown("---")
        if st.session_state.active_mode == "view":
            st.subheader("🧾 Receipt Preview")
            link = row["Receipt_url"]
            if str(link).startswith("http"):
                if link.lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(link, width=500)
                elif link.lower().endswith(".pdf"):
                    st.markdown(f"[📄 Open PDF]({link})", unsafe_allow_html=True)
            if st.button("Close", key=f"close_{row_id}"):
                st.session_state.active_row, st.session_state.active_mode = None, None
                st.rerun()

        elif st.session_state.active_mode == "edit":
            st.subheader("✏️ Edit Record")
            new_date = st.date_input("Date", value=row["Date"], key=f"date_{row_id}")
            new_cat = st.selectbox("Category", categories_list, index=categories_list.index(row["Category"]), key=f"cat_{row_id}")
            new_desc = st.text_input("Description", value=row["Description"], key=f"desc_{row_id}")
            new_vendor = st.text_input("Vendor", value=row["Vendor"], key=f"ven_{row_id}")
            new_amt = st.number_input("Amount (Rp)", value=float(row["Amount"]), key=f"amt_{row_id}")

            c4, c5 = st.columns(2)
            with c4:
                if st.button("💾 Save", key=f"save_{row_id}"):
                    try:
                        real_df = pd.read_excel(excel_file).fillna("-")
                        mask = real_df["id"].astype(str) == row_id
                        if mask.any():
                            real_df.loc[mask, ["Date", "Category", "Description", "Vendor", "Amount"]] = [
                                str(new_date), new_cat, new_desc, new_vendor, int(new_amt)
                            ]
                            real_df.to_excel(excel_file, index=False)
                        supabase.table("expense-data").update({
                            "Date": str(new_date),
                            "Category": new_cat,
                            "Description": new_desc,
                            "Vendor": new_vendor,
                            "Amount": int(new_amt)
                        }).eq("id", row_id).execute()
                        st.success("✅ Updated!")
                    except Exception as e:
                        st.warning(f"⚠️ Update failed: {e}")
                    st.session_state.active_row, st.session_state.active_mode = None, None
                    time.sleep(0.4)
                    st.rerun()
            with c5:
                if st.button("Cancel", key=f"cancel_{row_id}"):
                    st.session_state.active_row, st.session_state.active_mode = None, None
                    st.rerun()
