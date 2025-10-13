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
    """앱이 inactive → 다시 켜질 때도 자동 재연결"""
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
    st.session_state.sort_order = "desc"  # 기본 최신순

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
# LOAD & ENSURE IDs
# ====================================================
def load_and_ensure_ids(excel_path):
    base_cols = ["id", "Date", "Category", "Description", "Vendor", "Amount", "Receipt_url"]
    if not os.path.exists(excel_path):
        return pd.DataFrame(columns=base_cols)
    df = pd.read_excel(excel_path).fillna("-")
    if "Receipt" in df.columns and "Receipt_url" not in df.columns:
        df = df.rename(columns={"Receipt": "Receipt_url"})
    for c in base_cols:
        if c not in df.columns:
            df[c] = "-"
    for i in df.index:
        if not df.loc[i, "id"] or df.loc[i, "id"] in ["-", "None", "nan"]:
            df.loc[i, "id"] = str(uuid.uuid4())
    df.to_excel(excel_path, index=False)
    return df

# ====================================================
# SYNC FUNCTIONS
# ====================================================
def sync_supabase_to_excel(excel_path):
    try:
        res = supabase.table("expense-data").select("*").execute()
        data = json.loads(res.json())
        supa_data = pd.DataFrame(data if data else [])
        if supa_data.empty:
            return
        if "Date" in supa_data.columns:
            supa_data["Date"] = pd.to_datetime(supa_data["Date"], errors="coerce")
        if os.path.exists(excel_path):
            local_df = pd.read_excel(excel_path).fillna("-")
        else:
            local_df = pd.DataFrame(columns=supa_data.columns)
        if "Receipt" in local_df.columns and "Receipt_url" not in local_df.columns:
            local_df = local_df.rename(columns={"Receipt": "Receipt_url"})
        if "id" not in local_df.columns:
            local_df["id"] = "-"
        merged = pd.concat([local_df, supa_data]).drop_duplicates(subset=["id"], keep="last")
        merged.to_excel(excel_path, index=False)
    except Exception:
        pass

def sync_excel_to_supabase(df):
    try:
        df = df.copy()
        if "Date" in df.columns:
            df["Date"] = df["Date"].apply(lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else str(x))
        df = df[[c for c in df.columns if c not in ["Month", "_orig_index", "index"]]]
        res = supabase.table("expense-data").select("id").execute()
        existing_ids = [r["id"] for r in getattr(res, "data", []) if isinstance(r, dict)]
        new_records = df[~df["id"].isin(existing_ids)]
        if not new_records.empty:
            supabase.table("expense-data").upsert(new_records.to_dict(orient="records")).execute()
    except Exception:
        pass

# ====================================================
# FORCE RELOAD ON APP START (after inactive)
# ====================================================
if "reloaded" not in st.session_state:
    st.session_state.reloaded = True
    try:
        st.info("🔄 Reconnecting to Supabase and loading latest data...")
        supabase = get_supabase()
        sync_supabase_to_excel("expenses.xlsx")
        st.success("✅ Latest data loaded from Supabase!")
        time.sleep(0.4)
        st.rerun()
    except Exception as e:
        st.error(f"❌ Auto reload failed: {e}")

# ====================================================
# LOAD + SYNC BOTH + AUTO CLEANUP
# ====================================================
df = load_and_ensure_ids(excel_file)
sync_supabase_to_excel(excel_file)
sync_excel_to_supabase(df)
