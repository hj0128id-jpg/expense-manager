import streamlit as st
from supabase import create_client
import pandas as pd
import os  # ✅ 이 줄 추가!

# ======================================
# 기존 Excel 파일 로드
# ======================================
EXCEL_FILE = "expenses.xlsx"

st.title("📦 Expense Data → Supabase Migration Tool")
st.markdown("이 도구는 기존 엑셀 데이터를 Supabase DB(`expense-data`)로 이전합니다.")
st.markdown("---")

if not os.path.exists(EXCEL_FILE):
    st.error("❌ expenses.xlsx 파일이 없습니다. 기존 코드 실행 폴더에 있는지 확인하세요.")
    st.stop()

df = pd.read_excel(EXCEL_FILE).fillna("-")
st.success(f"✅ Loaded {len(df)} records from {EXCEL_FILE}")

# ======================================
# Supabase 연결
# ======================================
SUPABASE_URL = "https://wopkkfxfhvfodovieptg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcGtrZnhmaHZmb2RvdmllcHRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAwNjE3NjcsImV4cCI6MjA3NTYzNzc2N30.NY9EMZtqBmRBO0S4xNwk9M7Vj7ON_gCrC3u-S_-J9_Q"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================================
# 업로드 함수
# ======================================
def upload_to_supabase(df):
    success_count = 0
    fail_count = 0

    for i, r in df.iterrows():
        try:
            res = supabase.table("expense-data").insert({
                "date": str(r["Date"]),
                "category": str(r["Category"]),
                "description": str(r["Description"]),
                "vendor": str(r["Vendor"]),
                "amount": float(r["Amount"]),
                "receipt_url": str(r["Receipt"]),
            }).execute()
            if hasattr(res, "error") and res.error:
                fail_count += 1
            else:
                success_count += 1
        except Exception as e:
            st.warning(f"⚠️ Row {i} upload failed: {e}")
            fail_count += 1

    return success_count, fail_count

# ======================================
# 실행 버튼
# ======================================
if st.button("🚀 Upload All to Supabase"):
    with st.spinner("데이터를 Supabase로 업로드 중입니다..."):
        success, fail = upload_to_supabase(df)
    st.success(f"✅ 업로드 완료: {success}개 성공 / {fail}개 실패")
    st.info("이제 Supabase에 데이터가 저장되었습니다. 이후부터는 Excel 파일이 필요 없습니다!")

