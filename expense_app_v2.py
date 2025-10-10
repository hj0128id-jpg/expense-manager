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
            supabase.storage.from_(bucket_name).upload(
                file_name,
                f,
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
        ok = upload_to_supabase("receipts", unique_name, tmp.name)
        if ok:
            receipt_url = f"{SUPABASE_URL}/storage/v1/object/public/receipts/{unique_name}"
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
# Supabase → Excel (역방향 동기화)
# ====================================================
def sync_supabase_to_excel(excel_path):
    """Supabase 데이터를 읽어와 Excel과 병합"""
    try:
        res = supabase.table("expense-data").select("*").execute()
        supa_data = pd.DataFrame(res.data if res.data else [])

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
        st.success(f"🔄 Synced {len(supa_data)} records from Supabase to Excel!")
    except Exception as e:
        st.warning(f"⚠️ Supabase → Excel sync failed: {e}")

# ====================================================
# Excel → Supabase (정방향 동기화)
# ====================================================
def sync_excel_to_supabase(df):
    try:
        df = df.copy()
        if "Date" in df.columns:
            df["Date"] = df["Date"].apply(lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else str(x))
        df = df[[c for c in df.columns if c not in ["Month", "_orig_index", "_index", "index"]]]

        res = supabase.table("expense-data").select("id").execute()
        existing_ids = [r["id"] for r in getattr(res, "data", []) if isinstance(r, dict)]
        new_records = df[~df["id"].isin(existing_ids)]

        if not new_records.empty:
            supabase.table("expense-data").upsert(new_records.to_dict(orient="records")).execute()
            st.success(f"📤 Synced {len(new_records)} missing records to Supabase!")
    except Exception:
        st.warning("⚠️ Some records couldn't sync (non-critical).")

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
    except Exception:
        st.warning("⚠️ Supabase sync failed (non-critical).")

    time.sleep(0.4)
    st.rerun()

# ====================================================
# DISPLAY SECTION
# ====================================================
df = load_and_ensure_ids(excel_file)
sync_supabase_to_excel(excel_file)
sync_excel_to_supabase(df)

df = pd.read_excel(excel_file).fillna("-")
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Month"] = df["Date"].dt.strftime("%Y-%m")

if df.empty:
    st.info("No records yet.")
    st.stop()

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
# RECORD TABLE
# ====================================================
st.markdown("### 📋 Saved Records")

header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt_url", "Actions"]
for c, h in zip(header_cols, headers):
    c.markdown(f"**{h}**")

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
                df = df[df["id"].astype(str) != row_id]
                df.to_excel(excel_file, index=False)
                try:
                    supabase.table("expense-data").delete().eq("id", row_id).execute()
                except:
                    pass
                st.success("🗑️ Deleted!")
                time.sleep(0.4)
                st.rerun()

# ====================================================
# SUMMARY SECTION
# ====================================================
st.markdown("---")
st.subheader("📊 Monthly & Category Summary")

col1, col2 = st.columns(2)
with col1:
    month_summary = st.selectbox("📅 Select Month", ["All"] + list(months))
with col2:
    cat_summary = st.selectbox("📁 Select Category", ["All"] + sorted(df["Category"].unique()))

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
    st.success(f"📌 {month_summary if month_summary != 'All' else 'All months'} | {cat_summary if cat_summary != 'All' else 'All categories'} → {count} transactions, Rp {int(total):,}")
    grouped = summary_df.groupby(["Category", "Vendor"], as_index=False)["Amount"].sum()
    grouped["Amount"] = grouped["Amount"].apply(lambda x: f"Rp {int(x):,}")
    st.dataframe(grouped, use_container_width=True)

# ==============================================
# ⚙️ Supabase → Excel 강제 동기화 (이번만 실행용)
# ==============================================
import pandas as pd
from supabase import create_client

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    res = supabase.table("expense-data").select("*").execute()
    supa_data = pd.DataFrame(res.data if res.data else [])
    if not supa_data.empty:
        supa_data.to_excel("expenses.xlsx", index=False)
        st.success(f"✅ Synced {len(supa_data)} records from Supabase → Streamlit Excel!")
    else:
        st.info("ℹ️ Supabase에 데이터가 없습니다.")
except Exception as e:
    st.error(f"⚠️ Sync failed: {e}")


