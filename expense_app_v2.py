import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide", initial_sidebar_state="collapsed")

# ----------------------------------------
# STATE
# ----------------------------------------
if "sort_order" not in st.session_state:
    st.session_state.sort_order = "desc"
if "view_index" not in st.session_state:
    st.session_state.view_index = None
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

# ----------------------------------------
# FILE PATHS
# ----------------------------------------
excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# ----------------------------------------
# STYLE
# ----------------------------------------
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }
.container-box {
    background-color: white;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 10px;
    border: 1px solid #ddd;
}
.container-box:hover {
    background-color: #f9f9f9;
}
.dark-mode .container-box {
    background-color: #1e1e1e !important;
    border-color: #444 !important;
}
.dark-mode .stButton > button {
    color: #fff !important;
}
@media (prefers-color-scheme: dark) {
    .stApp {
        background-color: #0e0e0e !important;
        color: #fff !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# HEADER
# ----------------------------------------
if os.path.exists("unnamed.png"):
    st.image(Image.open("unnamed.png"), width=240)
st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Manager</h1>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# INPUT SECTION
# ----------------------------------------
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

receipt_name = None
if receipt_file is not None:
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_file.read())

if st.button("💾 Save Record"):
    new = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description],
        "Vendor": [vendor],
        "Amount": [amount],
        "Receipt": [receipt_name]
    })
    if os.path.exists(excel_file):
        old = pd.read_excel(excel_file)
        df = pd.concat([old, new], ignore_index=True)
    else:
        df = new
    df.to_excel(excel_file, index=False)
    st.success("✅ Record saved successfully!")
    time.sleep(0.5)
    st.rerun()

# ----------------------------------------
# DISPLAY SECTION
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    # 필터링
    months = sorted(df["Month"].unique(), reverse=True)
    f1, f2, f3 = st.columns([1.5, 1.5, 1])
    with f1:
        month_filter = st.selectbox("📅 Filter by Month", ["All"] + months)
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

    # 정렬
    asc_flag = True if st.session_state.sort_order == "asc" else False
    view_df = view_df.sort_values("Date", ascending=asc_flag).reset_index(drop=True)

    st.markdown(f"### 📋 Saved Records ({'⬆️ Ascending' if asc_flag else '⬇️ Descending'})")
    if st.button("🔁 Toggle Sort Order"):
        st.session_state.sort_order = "asc" if st.session_state.sort_order == "desc" else "desc"
        st.rerun()

    # 행 렌더링
    for idx, row in view_df.iterrows():
        with st.container():
            st.markdown(f"<div class='container-box'>", unsafe_allow_html=True)
            st.write(f"**📅 {row['Date'].strftime('%Y-%m-%d')} | {row['Category']}**")
            st.write(f"💬 {row['Description']}")
            st.write(f"🏢 {row['Vendor']}")
            st.write(f"💰 Rp {int(row['Amount']):,}")

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🧾 View", key=f"view_{idx}"):
                    st.session_state.view_index = idx
                    st.session_state.edit_index = None
                    st.rerun()
            with c2:
                if st.button("✏️ Edit", key=f"edit_{idx}"):
                    st.session_state.edit_index = idx
                    st.session_state.view_index = None
                    st.rerun()
            with c3:
                if st.button("🗑️ Delete", key=f"del_{idx}"):
                    df = df.drop(view_df.index[idx])
                    df.to_excel(excel_file, index=False)
                    st.success("🗑️ Record deleted!")
                    time.sleep(0.5)
                    st.rerun()

            # View 모드
            if st.session_state.view_index == idx:
                st.markdown("---")
                st.subheader("🧾 Receipt Preview")
                file_path = os.path.join(receipt_folder, str(row["Receipt"]))
                if os.path.exists(file_path):
                    if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(file_path, width=500)  # ✅ 적당한 사이즈
                    elif file_path.lower().endswith(".pdf"):
                        st.markdown(f"📄 [Open PDF]({file_path})", unsafe_allow_html=True)
                else:
                    st.warning("⚠️ File not found.")
                if st.button("Close Preview", key=f"close_{idx}"):
                    st.session_state.view_index = None
                    st.rerun()

            # Edit 모드
            if st.session_state.edit_index == idx:
                st.markdown("---")
                st.subheader("✏️ Edit Record")
                new_date = st.date_input("Date", value=row["Date"], key=f"date_{idx}")
                new_cat = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                                       index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(row["Category"]),
                                       key=f"cat_{idx}")
                new_desc = st.text_input("Description", value=row["Description"], key=f"desc_{idx}")
                new_vendor = st.text_input("Vendor", value=row["Vendor"], key=f"vendor_{idx}")
                new_amount = st.number_input("Amount (Rp)", value=float(row["Amount"]), key=f"amt_{idx}")

                c4, c5 = st.columns(2)
                with c4:
                    if st.button("💾 Save", key=f"save_{idx}"):
                        df.loc[view_df.index[idx], "Date"] = new_date
                        df.loc[view_df.index[idx], "Category"] = new_cat
                        df.loc[view_df.index[idx], "Description"] = new_desc
                        df.loc[view_df.index[idx], "Vendor"] = new_vendor
                        df.loc[view_df.index[idx], "Amount"] = new_amount
                        df.to_excel(excel_file, index=False)
                        st.success("✅ Record updated!")
                        st.session_state.edit_index = None
                        time.sleep(0.5)
                        st.rerun()
                with c5:
                    if st.button("Cancel", key=f"cancel_{idx}"):
                        st.session_state.edit_index = None
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 요약
    st.markdown("---")
    st.subheader("📊 Summary (Filtered Data)")
    cat_sum = view_df.groupby("Category", as_index=False)["Amount"].sum()
    cat_sum["Amount"] = cat_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")
    mon_sum = view_df.groupby("Month", as_index=False)["Amount"].sum()
    mon_sum["Amount"] = mon_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")

    c1, c2 = st.columns(2)
    with c1:
        st.write("**By Category**")
        st.table(cat_sum)
    with c2:
        st.write("**By Month**")
        st.table(mon_sum)

else:
    st.info("No records yet.")
