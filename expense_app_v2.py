import streamlit as st
import pandas as pd
import json
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile
from datetime import datetime

# ==========================
# 🔐 GOOGLE AUTH (Secrets 기반)
# ==========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

try:
    service_account_info = json.loads(st.secrets["google"]["service_account"])
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    gc = gspread.authorize(credentials)
    drive_service = build("drive", "v3", credentials=credentials)
except Exception as e:
    st.error(f"🚨 Google 인증 실패: {e}")
    st.stop()

# ==========================
# 📊 Google Sheets / Drive 설정
# ==========================
SPREADSHEET_NAME = "Expense Records"   # ✅ 시트 이름 정확히 반영
RECEIPT_FOLDER_ID = "1LrpOrq1GWnH-PweYuC8Bk6wKogiTesD_"

# 시트 열기 시 예외 처리
try:
    sheet = gc.open(SPREADSHEET_NAME).sheet1
except Exception as e:
    st.error(f"🚨 Google Sheets 접근 실패: '{SPREADSHEET_NAME}' 시트를 찾을 수 없습니다.")
    st.info("""
    👉 확인하세요:
    1. Google Sheets 이름이 정확히 "Expense Records" 인가요?
    2. 서비스 계정 이메일(`streamlit-expense@ducksanexpensemanage.iam.gserviceaccount.com`)을
       편집자 권한으로 공유했나요?
    3. Streamlit Secrets의 서비스 계정 JSON이 올바른가요?
    """)
    st.stop()

# ==========================
# 🌈 Streamlit 기본 UI
# ==========================
st.set_page_config(page_title="지출결의서 v43.4", layout="wide")
st.title("💰 지출결의서 v43.4 (Google Sheets + Drive 안정버전)")

# ==========================
# 📥 데이터 불러오기
# ==========================
try:
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
except Exception as e:
    st.error("🚨 시트 데이터 로딩 실패. 시트 구조나 권한을 확인하세요.")
    st.stop()

if not df.empty:
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# ==========================
# 🔍 필터
# ==========================
st.sidebar.header("🔎 필터")
if not df.empty:
    months = ["전체"] + sorted(df["Date"].dt.to_period("M").astype(str).unique().tolist())
    categories = ["전체"] + sorted(df["Category"].dropna().unique().tolist())
else:
    months, categories = ["전체"], ["전체"]

selected_month = st.sidebar.selectbox("월 선택", months)
selected_category = st.sidebar.selectbox("카테고리 선택", categories)

filtered_df = df.copy()
if selected_month != "전체":
    filtered_df = filtered_df[filtered_df["Date"].dt.to_period("M").astype(str) == selected_month]
if selected_category != "전체":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

# ==========================
# 🧾 새 결의서 입력
# ==========================
with st.expander("➕ 새 결의서 추가", expanded=True):
    with st.form("expense_form"):
        date = st.date_input("날짜", value=datetime.today())
        category = st.text_input("카테고리")
        description = st.text_input("내용")
        amount = st.number_input("금액 (Rp)", min_value=0)
        receipt = st.file_uploader("영수증 업로드 (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "pdf"])
        submitted = st.form_submit_button("저장")

    if submitted:
        receipt_url = ""
        try:
            if receipt:
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(receipt.read())
                    tmp.flush()
                    file_metadata = {
                        "name": f"{date}_{receipt.name}",
                        "parents": [RECEIPT_FOLDER_ID]
                    }
                    media = MediaFileUpload(tmp.name, mimetype=receipt.type)
                    uploaded = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields="id"
                    ).execute()
                    file_id = uploaded.get("id")
                    receipt_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

            new_row = [str(date), category, description, amount, receipt_url]
            sheet.append_row(new_row)
            st.success("✅ Google Sheets & Drive 저장 완료!")
            st.balloons()
            st.experimental_rerun()

        except Exception as e:
            st.error(f"🚨 저장 중 오류 발생: {e}")

# ==========================
# 🗂 수정 / 삭제
# ==========================
st.subheader("📋 저장된 결의서 내역 (수정/삭제 가능)")

if not filtered_df.empty:
    for i, row in filtered_df.iterrows():
        with st.expander(f"{row['Date'].date()} | {row['Category']} | {row['Amount']:,}"):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                new_cat = st.text_input(f"카테고리_{i}", value=row["Category"])
                new_desc = st.text_input(f"내용_{i}", value=row["Description"])
            with c2:
                new_amt = st.number_input(f"금액_{i}", value=row["Amount"], step=1000)
                new_date = st.date_input(f"날짜_{i}", value=row["Date"].date())
            with c3:
                if st.button(f"💾 수정", key=f"edit_{i}"):
                    try:
                        sheet.update_cell(i + 2, 1, str(new_date))
                        sheet.update_cell(i + 2, 2, new_cat)
                        sheet.update_cell(i + 2, 3, new_desc)
                        sheet.update_cell(i + 2, 4, new_amt)
                        st.success("수정 완료 ✅")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"수정 실패: {e}")

                if st.button(f"🗑 삭제", key=f"del_{i}"):
                    try:
                        sheet.delete_rows(i + 2)
                        st.warning("삭제 완료 🗑")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"삭제 실패: {e}")
else:
    st.info("필터에 맞는 데이터가 없습니다.")

# ==========================
# 📊 요약
# ==========================
st.markdown("---")
st.subheader("📈 월별 / 카테고리별 요약")

if not df.empty:
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    monthly_summary = df.groupby("Month")["Amount"].sum().reset_index()
    category_summary = df.groupby("Category")["Amount"].sum().reset_index()

    col1, col2 = st.columns(2)
    with col1:
        st.write("**월별 합계 (Rp)**")
        st.dataframe(monthly_summary, use_container_width=True)
    with col2:
        st.write("**카테고리별 합계 (Rp)**")
        st.dataframe(category_summary, use_container_width=True)
else:
    st.warning("시트에 데이터가 없습니다.")
