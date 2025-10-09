import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image

st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ---------------- 헤더바 ----------------
col1, col2 = st.columns([1, 4])
with col1:
    logo_path = "unnamed.png"  # 로고 파일명 (같은 폴더에 두세요)
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        st.image(logo, width=180)
with col2:
    st.markdown(
        """
        <div style='text-align:right; padding-top:25px;'>
            <h2 style='margin:0; color:#004C92;'>DUCK SAN EXPENSE MANAGER</h2>
            <p style='margin:0; color:gray;'>지출결의서 관리 시스템</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------------- 기본 설정 ----------------
st.subheader("🧾 지출 입력")

month_now = datetime.today().strftime("%Y-%m")
FILE_PATH = f"expenses_{month_now}.xlsx"

if os.path.exists(FILE_PATH):
    df = pd.read_excel(FILE_PATH)
else:
    df = pd.DataFrame(columns=["날짜", "카테고리", "내용", "거래처", "결제방법", "금액", "영수증"])

# ---------------- 입력 폼 ----------------
with st.form("expense_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("날짜", datetime.today())
        category = st.selectbox("카테고리", ["식대", "교통비", "사무용품", "접대비", "기타"])
        payment = st.selectbox("결제방법", ["법인카드", "현금", "계좌이체", "기타"])
    with col2:
        description = st.text_input("내용", placeholder="예: 회식비, 출장비 등")
        vendor = st.text_input("거래처", placeholder="예: 식당 A, 택시 등")
        amount = st.number_input("금액", min_value=0, step=1000)
    receipt = st.file_uploader("영수증 파일 업로드 (선택)", type=["jpg", "jpeg", "png", "pdf"])

    submitted = st.form_submit_button("💾 저장")

    if submitted:
        new_data = {
            "날짜": date,
            "카테고리": category,
            "내용": description,
            "거래처": vendor,
            "결제방법": payment,
            "금액": amount,
            "영수증": receipt.name if receipt else ""
        }

        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        df.to_excel(FILE_PATH, index=False)
        st.success(f"✅ 저장 완료! ({FILE_PATH})")

st.divider()
st.subheader("📊 지출 내역 보기")

# ---------------- 필터 ----------------
col1, col2 = st.columns(2)
with col1:
    category_filter = st.selectbox("카테고리 필터", ["전체"] + list(df["카테고리"].unique()))
with col2:
    month_filter = st.selectbox("월별 필터", ["전체"] + sorted(df["날짜"].astype(str).str[:7].unique()))

filtered_df = df.copy()
if category_filter != "전체":
    filtered_df = filtered_df[filtered_df["카테고리"] == category_filter]
if month_filter != "전체":
    filtered_df = filtered_df[filtered_df["날짜"].astype(str).str.startswith(month_filter)]

# ---------------- 합계 + 데이터 표시 ----------------
total = filtered_df["금액"].sum()
st.metric("💰 총 지출 합계", f"{total:,.0f} 원")

st.dataframe(filtered_df, use_container_width=True)
