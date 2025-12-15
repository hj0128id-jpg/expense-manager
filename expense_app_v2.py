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
# PAGE CONFIG (화이트 테마 강제)
# ====================================================
st.set_page_config(
    page_title="Duck San Expense Manager",
    layout="wide",
    initial_sidebar_state="auto"
)

# 강제로 밝은 테마(화이트) 고정
st.markdown("""
    <style>
    /* 전체 배경 흰색 고정 */
    body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* 사이드바도 흰색 계열로 */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
        color: #000000 !important;
    }

    /* 테이블, 버튼 등 다크모드 색상 방지 */
    div[data-testid="stDataFrame"], .stButton>button, .stTextInput>div>div>input {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* 링크 색상 수정 (어두운 배경 대비용) */
    a, a:visited {
        color: #2b5876 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ====================================================
# 글씨 색상 명확히 (입력창, 셀렉트박스, 업로더, 버튼 등)
# ====================================================
st.markdown("""
    <style>
    /* 입력창, 선택창, 업로더 내부 글씨 검정색 */
    input, textarea, select, div[data-baseweb="input"] input {
        color: #000000 !important;
        background-color: #ffffff !important;
    }

    /* 드롭다운 내부 옵션 글씨 */
    div[role="listbox"] div {
        color: #000000 !important;
        background-color: #ffffff !important;
    }

    /* 파일 업로더 라벨, 안내문 글씨 */
    .stFileUploader label, .stFileUploader div {
        color: #000000 !important;
    }

    /* 버튼 텍스트 및 색상 */
    .stButton>button {
        color: #000000 !important;
        background-color: #f3f3f3 !important;
        border: 1px solid #cccccc !important;
    }

    /* selectbox, number input 테두리 명확하게 */
    .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        border: 1px solid #d0d0d0 !important;
    }

    /* 라벨(필드명)도 검정색 */
    label, .stTextInput label, .stSelectbox label, .stNumberInput label {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* selectbox(카테고리) 완전 화이트 강제 */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #d0d0d0 !important;
    }

    /* select 내부 옵션도 하얗게 */
    div[data-baseweb="popover"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* number input (Amount) 내부 버튼 영역 포함 전체 하얗게 */
    div[data-baseweb="input"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* number input의 + / - 버튼 영역 색상 통일 */
    div[data-testid="stNumberInput"] button {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #cccccc !important;
    }
    </style>
""", unsafe_allow_html=True)

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
                file_name,
                f,
                {
                    "cache-control": "3600",
                    "upsert": "true",
                    "content-type": mime_type,
                },
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
st.markdown("<h1 style='color:#2b5876;'> Duck San Expense Manager</h1>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================
# INPUT FORM
# ====================================================
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("Date", datetime.today())
with col2:
    category = st.selectbox("Category", ["Transportation", "Meals", "Sales", "Hotel", "Office", "Office Supply", "ETC"])
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
# SAVE NEW RECORD (Supabase auto ID)
# ====================================================
if st.button("💾 Save Record", use_container_width=True):
    new_data = {
        "Date": str(date),
        "Category": category,
        "Description": description or "-",
        "Vendor": vendor or "-",
        "Amount": int(amount),
        "Receipt_url": receipt_url or receipt_name,
        "created_at": datetime.utcnow().isoformat(),
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
        supabase.table("expense-data").insert([new_data]).execute()
        st.success("✅ Record Saved to Supabase!")
    except Exception as e:
        st.warning(f"Supabase insert failed: {e}")

    time.sleep(0.5)
    st.rerun()

# ====================================================
# LOAD DATA
# ====================================================
def load_data():
    res = supabase.table("expense-data").select("*").order("id", desc=True).execute()
    data = getattr(res, "data", [])
    if not data:
        return pd.DataFrame(columns=["id", "Date", "Category", "Description", "Vendor", "Amount", "Receipt_url"])
    df = pd.DataFrame(data)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    return df

df = load_data()

# ====================================================
# FILTER
# ====================================================
months = sorted(df["Month"].dropna().unique(), reverse=True)

# 현재 월 문자열 (예: "2025-12")
current_month = datetime.today().strftime("%Y-%m")

# 옵션 목록: All + (months에 이미 없으면 current_month 포함) + 기존 months
months_options = ["All"] + list(months)
if current_month not in months_options:
    # current_month가 months에 없으면 All 다음에 삽입해서 기본 선택 가능하게 만듦
    months_options.insert(1, current_month)

f1, f2 = st.columns(2)
with f1:
    # 기본값 인덱스: current_month가 목록에 있으면 그 인덱스로, 아니면 0(All)
    default_index = months_options.index(current_month) if current_month in months_options else 0
    month_filter = st.selectbox(
        "📅 Filter by Month",
        months_options,
        index=default_index
    )

with f2:
    cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["Category"].unique()))

# === Apply filtering ===
view_df = df.copy()

if month_filter != "All":
    view_df = view_df[view_df["Month"] == month_filter]

if cat_filter != "All":
    view_df = view_df[view_df["Category"] == cat_filter]

# === If empty, show message ===
if view_df.empty:
    # month_filter가 현재달이지만 데이터가 없다면 빈 테이블과 안내문을 보여줌
    st.info(f"📭 '{month_filter}' 기간에 해당되는 데이터가 없습니다.")

# ✅ 필터된 결과 다운로드 버튼 (화이트 스타일)
if not view_df.empty:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_xlsx:
        view_df.to_excel(tmp_xlsx.name, index=False)
        tmp_xlsx.seek(0)

        st.markdown("""
            <style>
            .white-download-btn > button {
                background-color: #ffffff !important;
                color: #000000 !important;
                border: 1px solid #cccccc !important;
                border-radius: 8px !important;
                font-weight: 500 !important;
                padding: 0.6em 1em !important;
            }
            .white-download-btn > button:hover {
                background-color: #f3f3f3 !important;
            }
            </style>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="white-download-btn">', unsafe_allow_html=True)
            st.download_button(
                label="⬇️ Download Filtered Data (Excel)",
                data=tmp_xlsx.read(),
                file_name=f"filtered_expense_{month_filter}_{cat_filter}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("No data to download for the selected filters.")

# ====================================================
# SAVED RECORDS
# ====================================================
st.markdown("### 📋 Saved Records")

header_cols = st.columns([1.3, 1.3, 2, 1.3, 1.2, 1.5, 1])
for c, h in zip(header_cols, ["Date", "Category", "Description", "Vendor", "Amount", "Receipt_url", "Actions"]):
    c.markdown(f"**{h}**")

view_df = view_df.sort_values("Date", ascending=False).reset_index(drop=True)
for _, row in view_df.iterrows():
    row_id = row["id"]
    cols = st.columns([1.3, 1.3, 2, 1.3, 1.2, 1.5, 1])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
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
                supabase.table("expense-data").delete().eq("id", row_id).execute()
                st.success("🗑️ Deleted!")
                time.sleep(0.3)
                st.rerun()

    # === View Mode ===
    if st.session_state.active_row == row_id and st.session_state.active_mode == "view":
        st.markdown("---")
        st.subheader("🧾 Receipt Preview")
        if link.startswith("http"):
            if link.lower().endswith((".png", ".jpg", ".jpeg")):
                st.image(link, width=500)
            elif link.lower().endswith(".pdf"):
                st.markdown(f"[📄 Open PDF]({link})", unsafe_allow_html=True)
        if st.button("Close", key=f"close_{row_id}"):
            st.session_state.active_row, st.session_state.active_mode = None, None
            st.rerun()

    # === Edit Mode ===
    if st.session_state.active_row == row_id and st.session_state.active_mode == "edit":
        st.markdown("---")
        st.subheader("✏️ Edit Record")
        new_date = st.date_input("Date", value=row["Date"], key=f"date_{row_id}")
        new_cat = st.selectbox("Category", ["Transportation", "Meals", "Sales", "Hotel", "Office", "Office Supply", "ETC"], index=["Transportation", "Meals", "Sales", "Hotel", "Office", "Office Supply", "ETC"].index(row["Category"]), key=f"cat_{row_id}")
        new_desc = st.text_input("Description", value=row["Description"], key=f"desc_{row_id}")
        new_vendor = st.text_input("Vendor", value=row["Vendor"], key=f"ven_{row_id}")
        new_amt = st.number_input("Amount (Rp)", value=float(row["Amount"]), key=f"amt_{row_id}")

        c4, c5 = st.columns(2)
        with c4:
            if st.button("💾 Save", key=f"save_{row_id}"):
                supabase.table("expense-data").update({
                    "Date": str(new_date),
                    "Category": new_cat,
                    "Description": new_desc,
                    "Vendor": new_vendor,
                    "Amount": int(new_amt),
                }).eq("id", row_id).execute()
                st.success("✅ Updated!")
                time.sleep(0.3)
                st.rerun()
        with c5:
            if st.button("Cancel", key=f"cancel_{row_id}"):
                st.session_state.active_row, st.session_state.active_mode = None, None
                st.rerun()

# ====================================================
# SUMMARY (접힘)
# ====================================================
st.markdown("---")
with st.expander("📊 Monthly & Category Summary", expanded=False):
    st.subheader("📈 Summary Overview")

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
        total = summary_df["Amount"].sum()
        st.success(f"📌 {month_summary if month_summary!='All' else 'All months'} | {cat_summary if cat_summary!='All' else 'All categories'} → Rp {int(total):,}")
        summary_df_display = summary_df[["Date", "Category", "Description", "Vendor", "Amount", "Receipt_url"]].copy()
        summary_df_display["Date"] = summary_df_display["Date"].dt.strftime("%Y-%m-%d")
        summary_df_display["Amount"] = summary_df_display["Amount"].apply(lambda x: f"Rp {int(x):,}")
        st.dataframe(summary_df_display, use_container_width=True)







