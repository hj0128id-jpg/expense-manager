import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
import time
import tempfile
import json
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ====================================================
# PAGE CONFIG
# ====================================================
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ====================================================
# GOOGLE AUTH
# ====================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"  # ✅ 전체 Drive 권한
]

service_account_info = json.loads(st.secrets["google"]["service_account"])
credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
gc = gspread.authorize(credentials)
drive_service = build("drive", "v3", credentials=credentials)

SPREADSHEET_ID = "12AuEDjFKAha32dXVres3EYasYC6TiLrEx0zTHfufJKc"

# ====================================================
# GOOGLE DRIVE FOLDER 자동 생성 (서비스 계정 소유)
# ====================================================
folder_name = "Expense_Receipts_Service"
query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
results = drive_service.files().list(q=query, fields="files(id)").execute()
folders = results.get("files", [])

if folders:
    RECEIPT_FOLDER_ID = folders[0]["id"]
else:
    metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    folder = drive_service.files().create(body=metadata, fields="id").execute()
    RECEIPT_FOLDER_ID = folder["id"]
    st.success(f"📁 Created new folder: {folder_name}")

# ====================================================
# GLOBAL STATE
# ====================================================
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"
if "active_row" not in st.session_state:
    st.session_state.active_row = None
if "active_mode" not in st.session_state:
    st.session_state.active_mode = None

excel_file = "expenses.xlsx"   # local backup
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# ====================================================
# CSS (원본 유지)
# ====================================================
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }
table, .summary-table {
  width: 100%; border-collapse: collapse; margin-top: 10px;
  background-color: white !important; border-radius: 8px; border: 1px solid #ccc;
}
th, td, .summary-table th, .summary-table td {
  border: 1px solid #ccc; padding: 8px 10px; text-align: left; font-size: 14px;
  vertical-align: middle; color: black;
}
tr:nth-child(even), .summary-table tr:nth-child(even) { background-color: #fafafa; }
tr:hover, .summary-table tr:hover { background-color: #eef3ff; }
</style>
""", unsafe_allow_html=True)

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
    receipt_name = receipt_file.name
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(receipt_file.read())
        tmp.flush()
        file_metadata = {"name": os.path.basename(receipt_file.name)
        media = MediaFileUpload(tmp.name, resumable=True)
        uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        receipt_url = f"https://drive.google.com/file/d/{uploaded.get('id')}/view?usp=sharing"

# ====================================================
# SAVE BUTTON
# ====================================================
if st.button("💾 Save Record"):
    new_row = [str(date), category, description or "-", vendor or "-", amount, receipt_url or receipt_name]
    try:
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        sheet.append_row(new_row)
    except Exception as e:
        st.warning(f"⚠️ Google Sheets 저장 실패: {e}")

    new_data = pd.DataFrame({
        "Date": [date], "Category": [category], "Description": [description or "-"],
        "Vendor": [vendor or "-"], "Amount": [amount],
        "Receipt": [receipt_url or receipt_name]
    })
    if os.path.exists(excel_file):
        old = pd.read_excel(excel_file)
        df = pd.concat([old, new_data], ignore_index=True)
    else:
        df = new_data
    df.to_excel(excel_file, index=False)

    st.success("✅ Record saved successfully (AutoFolder Google Drive Synced)!")
    time.sleep(0.5)
    st.rerun()

# ====================================================
# LOAD DATA FROM GOOGLE SHEETS (안정형)
# ====================================================
try:
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    raw_values = sheet.get_all_values()
    if not raw_values:
        st.info("No records yet.")
        st.stop()
    header = raw_values[0]
    rows = raw_values[1:]
    df = pd.DataFrame(rows, columns=header)
    for col in ["Date", "Category", "Description", "Vendor", "Amount", "Receipt"]:
        if col not in df.columns:
            df[col] = None
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
except Exception as e:
    st.error(f"🚨 Google Sheets 데이터 로드 실패: {e}")
    if os.path.exists(excel_file):
        df = pd.read_excel(excel_file)
    else:
        st.stop()

# ====================================================
# FILTERS + TABLE (원본 그대로)
# ====================================================
df["Month"] = df["Date"].dt.strftime("%Y-%m")
months = sorted(df["Month"].dropna().unique(), reverse=True)
f1, f2, f3 = st.columns([1.5, 1.5, 1])
with f1:
    month_filter = st.selectbox("📅 Filter by Month", ["All"] + list(months))
with f2:
    cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["Category"].unique()))
with f3:
    reset = st.button("🔄 Reset Filters")

view_df = df.copy()
if month_filter != "All":
    view_df = view_df[view_df["Month"] == month_filter]
if cat_filter != "All":
    view_df = view_df[view_df["Category"] == cat_filter]
if reset:
    view_df = df.copy()

asc_flag = st.session_state.sort_order == "asc"
view_df = view_df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

st.markdown("#### Expense Table")
header_cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.2, 1.5])
headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt", "Actions"]
for col, name in zip(header_cols, headers):
    col.markdown(f"**{name}**")

for i, row in view_df.iterrows():
    cols = st.columns([1.2, 1.3, 2, 1.2, 1.2, 1.2, 1.5])
    cols[0].write(row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "-")
    cols[1].write(row["Category"])
    cols[2].write(row["Description"])
    cols[3].write(row["Vendor"])
    cols[4].write(f"Rp {int(row['Amount']):,}")
    if str(row["Receipt"]).startswith("http"):
        cols[5].markdown(f"[Open]({row['Receipt']})", unsafe_allow_html=True)
    else:
        cols[5].write(row["Receipt"])

