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
# SAVE NEW RECORD
# ====================================================
if st.button("💾 Save Record"):
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
    except Exception:
        pass

    time.sleep(0.4)
    st.rerun()

# ====================================================
# LOAD + SYNC BOTH + AUTO CLEANUP
# ====================================================
df = load_and_ensure_ids(excel_file)
sync_supabase_to_excel(excel_file)
sync_excel_to_supabase(df)

# ✅ 완벽 자동 클린업 (Amount 0이고 다른 필드 모두 비었을 때만 삭제)
try:
    temp_df = pd.read_excel(excel_file)
    temp_df = temp_df.replace("Rp 0", 0).replace("-", None)
    temp_df["Amount"] = pd.to_numeric(temp_df["Amount"], errors="coerce").fillna(0)
    temp_df = temp_df.dropna(how="all")

    # Amount=0 이면서 다른 필드도 모두 비었을 때만 제거
    temp_df = temp_df[~(
        (temp_df["Amount"] == 0) &
        (temp_df["Date"].isna() | (temp_df["Date"].astype(str).isin(["", "None", "NaT", "nan"]))) &
        (temp_df["Category"].isna() | temp_df["Category"].astype(str).isin(["", "None", "nan"])) &
        (temp_df["Description"].isna() | temp_df["Description"].astype(str).isin(["", "None", "nan"])) &
        (temp_df["Vendor"].isna() | temp_df["Vendor"].astype(str).isin(["", "None", "nan"]))
    )]
    temp_df.to_excel(excel_file, index=False)
except Exception as e:
    st.warning(f"⚠️ Clean-up skipped: {e}")

# ====================================================
# RELOAD CLEANED DATA
# ====================================================
df = pd.read_excel(excel_file).fillna("-")
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Month"] = df["Date"].dt.strftime("%Y-%m")

# ====================================================
# FILTERS
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
# SAVED RECORDS (정렬버튼 포함)
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

ascending_flag = True if st.session_state.sort_order == "asc" else False
view_df = view_df.sort_values("Date", ascending=ascending_flag).reset_index(drop=True)

# ====================================================
# RECORD DISPLAY
# ====================================================
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
                try:
                    df = df[df["id"].astype(str) != row_id]
                    df.to_excel(excel_file, index=False)
                    supabase.table("expense-data").delete().eq("id", row_id).execute()
                except:
                    pass
                st.session_state.active_row, st.session_state.active_mode = None, None
                st.success("🗑️ Deleted!")
                time.sleep(0.4)
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
                st.session_state.active_row, st.session_state.active_mode = None, None
                st.rerun()

        elif st.session_state.active_mode == "edit":
            st.subheader("✏️ Edit Record")
            new_date = st.date_input("Date", value=row["Date"], key=f"date_{row_id}")
            new_cat = st.selectbox("Category",
                ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(row["Category"]),
                key=f"cat_{row_id}"
            )
            new_desc = st.text_input("Description", value=row["Description"], key=f"desc_{row_id}")
            new_vendor = st.text_input("Vendor", value=row["Vendor"], key=f"ven_{row_id}")
            new_amt = st.number_input("Amount (Rp)", value=float(row["Amount"]), key=f"amt_{row_id}")

            c4, c5 = st.columns(2)
            with c4:
                if st.button("💾 Save", key=f"save_{row_id}"):
                    df.loc[df["id"] == row_id, ["Date", "Category", "Description", "Vendor", "Amount"]] = [
                        str(new_date), new_cat, new_desc, new_vendor, int(new_amt)
                    ]
                    df.to_excel(excel_file, index=False)
                    try:
                        supabase.table("expense-data").update({
                            "Date": str(new_date),
                            "Category": new_cat,
                            "Description": new_desc,
                            "Vendor": new_vendor,
                            "Amount": int(new_amt)
                        }).eq("id", row_id).execute()
                    except:
                        pass
                    st.session_state.active_row, st.session_state.active_mode = None, None
                    st.success("✅ Updated!")
                    time.sleep(0.4)
                    st.rerun()
            with c5:
                if st.button("Cancel", key=f"cancel_{row_id}"):
                    st.session_state.active_row, st.session_state.active_mode = None, None
                    st.rerun()

# ====================================================
# SUMMARY
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
    st.success(
        f"📌 {month_summary if month_summary!='All' else 'All months'} | "
        f"{cat_summary if cat_summary!='All' else 'All categories'} → "
        f"{count} transactions, Rp {int(total):,}"
    )

    display_df = summary_df[["Date", "Category", "Description", "Vendor", "Amount", "Receipt_url"]].copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df["Amount"] = display_df["Amount"].apply(lambda x: f"Rp {int(x):,}")
    st.dataframe(display_df, use_container_width=True)
