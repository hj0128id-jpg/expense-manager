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
# SUPABASE AUTH (이미 st.secrets에 세팅되어 있어야 함)
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
# 업로드 헬퍼 (간단 안정형)
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
# SAVE RECORD (추가)
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
        df_all = pd.concat([old, new_data], ignore_index=True)
    else:
        df_all = new_data
    df_all.to_excel(excel_file, index=False)
    st.success("✅ Record saved successfully (Supabase Synced)!")
    time.sleep(0.4)
    st.rerun()

# ====================================================
# DISPLAY / DATA 로드
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
    if st.button("🔄 Reset Filters"):
        month_filter = "All"
        cat_filter = "All"

view_df = df.copy()
if month_filter != "All":
    view_df = view_df[view_df["Month"] == month_filter]
if cat_filter != "All":
    view_df = view_df[view_df["Category"] == cat_filter]

asc_flag = True if st.session_state.sort_order == "asc" else False
view_df = view_df.sort_values("Date", ascending=asc_flag)
view_df_reset = view_df.reset_index()

# ====================================================
# SAVED RECORDS
# ====================================================
st.markdown("### 📋 Saved Records")

header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

categories_list = ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"]

for i, row in view_df_reset.iterrows():
    original_idx = int(row["index"])
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(row['Amount']):,}")
    cols[5].markdown(f"[🔗 View]({row['Receipt']})" if str(row["Receipt"]).startswith("http") else row["Receipt"], unsafe_allow_html=True)

    with cols[6]:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🧾", key=f"view_{original_idx}"):
                st.session_state.active_row = original_idx
                st.session_state.active_mode = "view"
                st.rerun()
        with c2:
            if st.button("✏️", key=f"edit_{original_idx}"):
                st.session_state.active_row = original_idx
                st.session_state.active_mode = "edit"
                st.rerun()
        with c3:
            if st.button("🗑️", key=f"del_{original_idx}"):
                df = df.drop(index=original_idx)
                df.to_excel(excel_file, index=False)
                st.success("🗑️ Deleted!")
                time.sleep(0.4)
                st.rerun()

    if st.session_state.active_row == original_idx:
        st.markdown("---")
        if st.session_state.active_mode == "view":
            st.subheader("🧾 Receipt Preview")
            receipt_link = df.at[original_idx, "Receipt"] if original_idx in df.index else row["Receipt"]
            if str(receipt_link).startswith("http"):
                if receipt_link.lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(receipt_link, width=500)
                elif receipt_link.lower().endswith(".pdf"):
                    st.markdown(f"[📄 Open PDF]({receipt_link})", unsafe_allow_html=True)
                else:
                    st.markdown(f"[🔗 Open File]({receipt_link})", unsafe_allow_html=True)
            else:
                st.warning("⚠️ No valid receipt link found.")
            if st.button("Close", key=f"close_view_{original_idx}"):
                st.session_state.active_row = None
                st.session_state.active_mode = None
                st.rerun()

        elif st.session_state.active_mode == "edit":
            st.subheader("✏️ Edit Record")
            cur_row = df.loc[original_idx]
            cur_date = cur_row["Date"] if pd.notna(cur_row["Date"]) else datetime.today()
            new_date = st.date_input("Date", value=cur_date, key=f"date_{original_idx}")
            try:
                default_cat_idx = categories_list.index(cur_row["Category"])
            except Exception:
                default_cat_idx = 0
            new_cat = st.selectbox("Category", categories_list, index=default_cat_idx, key=f"cat_{original_idx}")
            new_desc = st.text_input("Description", value=cur_row["Description"], key=f"desc_{original_idx}")
            new_vendor = st.text_input("Vendor", value=cur_row["Vendor"], key=f"ven_{original_idx}")
            new_amt = st.number_input("Amount (Rp)", value=float(cur_row["Amount"]), key=f"amt_{original_idx}")

            c4, c5 = st.columns(2)
            with c4:
                if st.button("💾 Save", key=f"save_{original_idx}"):
                    df.at[original_idx, "Date"] = pd.to_datetime(new_date)
                    df.at[original_idx, "Category"] = new_cat
                    df.at[original_idx, "Description"] = new_desc
                    df.at[original_idx, "Vendor"] = new_vendor
                    df.at[original_idx, "Amount"] = new_amt
                    df.to_excel(excel_file, index=False)
                    st.success("✅ Updated!")
                    st.session_state.active_row = None
                    st.session_state.active_mode = None
                    time.sleep(0.4)
                    st.rerun()
            with c5:
                if st.button("Cancel", key=f"cancel_{original_idx}"):
                    st.session_state.active_row = None
                    st.session_state.active_mode = None
                    st.rerun()

# ====================================================
# SUMMARY SECTION
# ====================================================
st.markdown("---")
st.markdown("### 📊 Monthly / Category Summary")

summary_col1, summary_col2 = st.columns([1.5, 2])
with summary_col1:
    month_default = month_filter if month_filter != "All" else (months[0] if months else None)
    month_select = st.selectbox(
        "📆 Select Month",
        ["All"] + list(months),
        index=0 if month_default is None or month_default == "All"
        else (["All"]+list(months)).index(month_default)
    )
with summary_col2:
    cat_select = st.selectbox("📁 Select Category", ["All"] + sorted(df["Category"].unique()))

summary_df = df.copy()
if month_select != "All":
    summary_df = summary_df[summary_df["Month"] == month_select]
if cat_select != "All":
    summary_df = summary_df[summary_df["Category"] == cat_select]

if summary_df.empty:
    st.info("No records for this selection.")
else:
    total_amount = summary_df["Amount"].sum()
    st.success(f"💸 Total Spending: Rp {int(total_amount):,}")
    grouped = summary_df.groupby("Category", as_index=False)["Amount"].sum()
    grouped["Amount"] = grouped["Amount"].apply(lambda x: f"Rp {int(x):,}")
    st.markdown("**Detailed Breakdown:**")
    st.dataframe(grouped, use_container_width=True)

# ====================================================
# 📥 DOWNLOAD FILTERED EXCEL (업그레이드 버전)
# ====================================================
st.markdown("---")
st.subheader("📥 Download Filtered Excel")

if os.path.exists(excel_file):
    # 다운로드 옵션 선택
    st.write("원하는 기간의 데이터를 선택 후 다운로드하세요 👇")

    download_col1, download_col2 = st.columns([1.5, 2])
    with download_col1:
        month_opt = st.selectbox("📅 Select Month", ["All"] + list(months))
    with download_col2:
        st.write(" ")  # 여백용

    # 선택한 월에 따라 데이터 필터링
    if month_opt == "All":
        export_df = df.copy()
        label = "📤 Download All Records (.xlsx)"
        fname = f"expenses_all_{datetime.today().strftime('%Y-%m-%d')}.xlsx"
    else:
        export_df = df[df["Month"] == month_opt].copy()
        label = f"📤 Download {month_opt}.xlsx"
        fname = f"expenses_{month_opt}.xlsx"

    # 다운로드 준비
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Expenses")

    # 다운로드 버튼 표시
    st.download_button(
        label=label,
        data=buf.getvalue(),
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("⚠️ No expenses.xlsx file found to download.")


