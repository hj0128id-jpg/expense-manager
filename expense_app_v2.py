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
# LOAD & ENSURE IDS / COLUMNS
# ====================================================
def load_and_ensure_ids(excel_path):
    base_columns = ["id", "Date", "Category", "Description", "Vendor", "Amount", "Receipt_url"]
    if not os.path.exists(excel_path):
        return pd.DataFrame(columns=base_columns)

    df = pd.read_excel(excel_path).fillna("-")

    # ✅ Receipt → Receipt_url 변환 (이전 버전 호환)
    if "Receipt" in df.columns and "Receipt_url" not in df.columns:
        df = df.rename(columns={"Receipt": "Receipt_url"})

    # ✅ 누락된 컬럼 자동 추가
    for col in base_columns:
        if col not in df.columns:
            df[col] = "-"

    # ✅ 누락된 id 자동 생성
    for idx in df.index:
        if not df.loc[idx, "id"] or df.loc[idx, "id"] in ["-", "None", "nan"]:
            df.loc[idx, "id"] = str(uuid.uuid4())

    # ✅ 저장
    df.to_excel(excel_path, index=False)
    return df

# ====================================================
# SYNC EXCEL → SUPABASE
# ====================================================
def sync_excel_to_supabase(df):
    try:
        df = df.copy()

        # ✅ Supabase는 datetime을 JSON으로 못 보내므로 문자열로 변환
        if "Date" in df.columns:
            df["Date"] = df["Date"].apply(
                lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else str(x)
            )

        res = supabase.table("expense-data").select("id").execute()
        existing_ids = [r["id"] for r in res.data] if hasattr(res, "data") and res.data else []
        new_records = df[~df["id"].isin(existing_ids)]

        if not new_records.empty:
            supabase.table("expense-data").upsert(new_records.to_dict(orient="records")).execute()
            st.success(f"📤 Synced {len(new_records)} old records to Supabase!")
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

view_df = view_df.sort_values("Date", ascending=False).reset_index(drop=True)

# ====================================================
# TABLE DISPLAY
# ====================================================
st.markdown("### 📋 Saved Records")

header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt_url", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

for _, row in view_df.iterrows():
    row_id = str(row["id"])
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(float(row['Amount'])):,}")
    cols[5].markdown(f"[🔗 View]({row['Receipt_url']})" if str(row["Receipt_url"]).startswith("http") else "-", unsafe_allow_html=True)
