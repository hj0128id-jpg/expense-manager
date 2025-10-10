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
# HELPER: load dataframe and ensure 'id' exists
# ====================================================
def load_and_ensure_ids(excel_path):
    if not os.path.exists(excel_path):
        return pd.DataFrame(columns=["id", "Date", "Category", "Description", "Vendor", "Amount", "Receipt"])
    df = pd.read_excel(excel_path)
    # fill NaN with '-'
    df = df.fillna("-")
    # ensure columns exist
    for c in ["id", "Date", "Category", "Description", "Vendor", "Amount", "Receipt"]:
        if c not in df.columns:
            df[c] = "-"
    # If some rows missing id, generate and try to upsert to supabase
    if df["id"].isnull().any() or (df["id"] == "-").any():
        changed = False
        for idx in df.index:
            if df.loc[idx, "id"] == "-" or pd.isna(df.loc[idx, "id"]):
                new_id = str(uuid.uuid4())
                df.loc[idx, "id"] = new_id
                changed = True
        if changed:
            # save back to excel
            df.to_excel(excel_path, index=False)
            # try upsert to supabase (best-effort)
            try:
                # prepare payload: convert dates to strings
                payload = []
                for _, r in df.iterrows():
                    payload.append({
                        "id": str(r["id"]),
                        "Date": str(r["Date"]) if not pd.isna(r["Date"]) else None,
                        "Category": r["Category"],
                        "Description": r["Description"],
                        "Vendor": r["Vendor"],
                        "Amount": float(r["Amount"]) if r["Amount"] != "-" else 0,
                        "Receipt": r["Receipt"]
                    })
                # upsert will insert new rows or update by primary key if exists
                supabase.table("expense-data").upsert(payload).execute()
            except Exception:
                # 실패해도 진행 (네트워크/권한 문제 가능)
                pass
    return df

# ====================================================
# SAVE RECORD (엑셀 + Supabase 자동 업로드)
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
        "Receipt": receipt_url if receipt_url else receipt_name
    }

    # 1️⃣ 엑셀에 저장
    new_df = pd.DataFrame([new_data])
    if os.path.exists(excel_file):
        old_df = pd.read_excel(excel_file).fillna("-")
        df_all = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df_all = new_df
    df_all.to_excel(excel_file, index=False)

    # 2️⃣ Supabase DB에 업로드 (insert)
    try:
        res = supabase.table("expense-data").insert(new_data).execute()
        # supabase-py returns a dict-like; check for error
        if hasattr(res, "status_code") and res.status_code >= 400:
            st.warning(f"⚠️ Supabase insert failed: {res}")
        else:
            st.success("✅ Record saved and synced to Supabase!")
    except Exception as e:
        st.warning(f"⚠️ Supabase upload error: {e}")

    time.sleep(0.4)
    st.experimental_rerun()

# ====================================================
# DISPLAY SECTION
# ====================================================
# load dataframe and ensure ids
df = load_and_ensure_ids(excel_file)
if df.empty:
    st.info("No records yet.")
    st.stop()

# normalize Date column to datetime where possible
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Month"] = df["Date"].dt.strftime("%Y-%m")

# preserve original index for exact row reference
df = df.reset_index().rename(columns={"index": "_orig_index"})

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
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

categories_list = ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"]

for i, row in view_df.iterrows():
    # row contains '_orig_index' which maps to df._orig_index
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.8, 1.5])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(row['Amount']):,}" if row["Amount"] not in [None, "-", ""] else "Rp 0")
    cols[5].markdown(f"[🔗 View]({row['Receipt']})" if str(row["Receipt"]).startswith("http") else row["Receipt"], unsafe_allow_html=True)

    orig_idx = int(row["_orig_index"])
    row_id = str(row["id"])

    with cols[6]:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🧾", key=f"view_{i}"):
                st.session_state.active_row, st.session_state.active_mode = i, "view"
                st.session_state._current_view_row = {"i": i, "orig_idx": orig_idx, "row_id": row_id}
                st.experimental_rerun()
        with c2:
            if st.button("✏️", key=f"edit_{i}"):
                st.session_state.active_row, st.session_state.active_mode = i, "edit"
                st.session_state._current_edit_row = {"i": i, "orig_idx": orig_idx, "row_id": row_id}
                st.experimental_rerun()
        with c3:
            if st.button("🗑️", key=f"del_{i}"):
                # remove from local df
                try:
                    # drop by _orig_index in original file
                    # reload actual excel to avoid index mismatch
                    real_df = pd.read_excel(excel_file).fillna("-")
                    # find row by id
                    real_df = real_df.reset_index().rename(columns={"index":"_orig_index"})
                    mask = real_df["id"] == row_id
                    if mask.any():
                        real_df = real_df[~mask]
                        real_df.to_excel(excel_file, index=False)
                    else:
                        # fallback: drop by orig_idx
                        real_df = real_df[real_df["_orig_index"] != orig_idx]
                        real_df.to_excel(excel_file, index=False)
                except Exception as e:
                    st.warning(f"⚠️ 로컬 삭제 중 오류: {e}")

                # Supabase에도 삭제 요청 (best-effort)
                try:
                    supabase.table("expense-data").delete().eq("id", row_id).execute()
                except Exception as e:
                    st.warning(f"⚠️ Supabase delete failed: {e}")

                st.success("🗑️ Deleted!")
                time.sleep(0.4)
                st.experimental_rerun()

    # ACTIVE ROW: view or edit (works with view_df index i)
    if st.session_state.active_row == i:
        st.markdown("---")
        if st.session_state.active_mode == "view":
            st.subheader("🧾 Receipt Preview")
            link = row["Receipt"]
            if str(link).startswith("http"):
                if link.lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(link, width=500)
                elif link.lower().endswith(".pdf"):
                    st.markdown(f"[📄 Open PDF]({link})", unsafe_allow_html=True)
                else:
                    st.markdown(f"[🔗 Open]({link})", unsafe_allow_html=True)
            else:
                st.warning("⚠️ File not found.")
            if st.button("Close", key=f"close_{i}"):
                st.session_state.active_row, st.session_state.active_mode = None, None
                st.experimental_rerun()

        elif st.session_state.active_mode == "edit":
            st.subheader("✏️ Edit Record")
            # use current values as defaults
            new_date = st.date_input("Date", value=row["Date"] if pd.notna(row["Date"]) else datetime.today(), key=f"date_{i}")
            # ensure category exists in list
            init_cat_index = 0
            if row["Category"] in categories_list:
                init_cat_index = categories_list.index(row["Category"])
            else:
                categories_list.append(row["Category"])
                init_cat_index = categories_list.index(row["Category"])
            new_cat = st.selectbox("Category", categories_list, index=init_cat_index, key=f"cat_{i}")
            new_desc = st.text_input("Description", value=row["Description"], key=f"desc_{i}")
            new_vendor = st.text_input("Vendor", value=row["Vendor"], key=f"ven_{i}")
            try:
                new_amt = st.number_input("Amount (Rp)", value=float(row["Amount"]) if row["Amount"] not in [None, "-", ""] else 0.0, key=f"amt_{i}")
            except Exception:
                new_amt = st.number_input("Amount (Rp)", value=0.0, key=f"amt_{i}")

            c4, c5 = st.columns(2)
            with c4:
                if st.button("💾 Save", key=f"save_{i}"):
                    # update local excel by id
                    try:
                        real_df = pd.read_excel(excel_file).fillna("-")
                        # find by id
                        mask = real_df["id"] == row_id
                        if mask.any():
                            idxs = real_df[mask].index
                            for ridx in idxs:
                                real_df.loc[ridx, ["Date", "Category", "Description", "Vendor", "Amount"]] = [
                                    str(new_date), new_cat, new_desc, new_vendor, int(new_amt)
                                ]
                            real_df.to_excel(excel_file, index=False)
                        else:
                            # fallback - try using _orig_index
                            real_df = real_df.reset_index().rename(columns={"index":"_orig_index"})
                            real_df.loc[real_df["_orig_index"] == orig_idx, ["Date", "Category", "Description", "Vendor", "Amount"]] = [
                                str(new_date), new_cat, new_desc, new_vendor, int(new_amt)
                            ]
                            # drop helper col then save
                            real_df = real_df.drop(columns=["_orig_index"])
                            real_df.to_excel(excel_file, index=False)
                    except Exception as e:
                        st.warning(f"⚠️ 로컬 업데이트 중 오류: {e}")

                    # Supabase 반영
                    try:
                        supabase.table("expense-data").update({
                            "Date": str(new_date),
                            "Category": new_cat,
                            "Description": new_desc,
                            "Vendor": new_vendor,
                            "Amount": int(new_amt)
                        }).eq("id", row_id).execute()
                    except Exception as e:
                        st.warning(f"⚠️ Supabase update failed: {e}")

                    st.success("✅ Updated!")
                    st.session_state.active_row, st.session_state.active_mode = None, None
                    time.sleep(0.4)
                    st.experimental_rerun()
            with c5:
                if st.button("Cancel", key=f"cancel_{i}"):
                    st.session_state.active_row, st.session_state.active_mode = None, None
                    st.experimental_rerun()

# ====================================================
# SUMMARY SECTION
# ====================================================
st.markdown("---")
st.markdown("### 📊 Monthly / Category Summary")

summary_col1, summary_col2 = st.columns([1.5, 2])
with summary_col1:
    month_select = st.selectbox("📆 Select Month", ["All"] + list(months))
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
    total = summary_df["Amount"].replace("-", 0).astype(float).sum()
    st.success(f"💸 Total Spending: Rp {int(total):,}")
    grouped = summary_df.groupby("Category", as_index=False)["Amount"].sum()
    grouped["Amount"] = grouped["Amount"].apply(lambda x: f"Rp {int(x):,}")
    st.dataframe(grouped, use_container_width=True)

# ====================================================
# 📥 DOWNLOAD FILTERED EXCEL
# ====================================================
st.markdown("---")
st.subheader("📥 Download Filtered Excel")

if os.path.exists(excel_file):
    month_opt = st.selectbox("📅 Select Month to Download", ["All"] + list(months))
    if month_opt == "All":
        export_df = pd.read_excel(excel_file).fillna("-")
        fname = f"expenses_all_{datetime.today().strftime('%Y-%m-%d')}.xlsx"
    else:
        temp_df = pd.read_excel(excel_file).fillna("-")
        temp_df["Date"] = pd.to_datetime(temp_df["Date"], errors="coerce")
        temp_df["Month"] = temp_df["Date"].dt.strftime("%Y-%m")
        export_df = temp_df[temp_df["Month"] == month_opt]
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
