import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ----------------------------------------
# CSS STYLE
# ----------------------------------------
st.markdown("""
    <style>
    .record-row {
        display: grid;
        grid-template-columns: 140px 160px 250px 160px 120px 100px;
        padding: 6px 0;
        border-bottom: 1px solid #ccc;
        align-items: center;
    }
    .record-row div {
        padding-left: 6px;
    }
    .record-header {
        display: grid;
        grid-template-columns: 140px 160px 250px 160px 120px 100px;
        font-weight: bold;
        background-color: #2b5876;
        color: white;
        padding: 8px 0;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }
    .filter-box {
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------
# HEADER
# ----------------------------------------
if os.path.exists("unnamed.png"):
    logo = Image.open("unnamed.png")
    st.image(logo, width=280)
else:
    st.warning("⚠️ Please upload your logo file (unnamed.png) in the same folder.")

st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Management System</h1>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# PATHS
# ----------------------------------------
excel_file = "expenses.xlsx"
receipt_folder = "receipts"
if not os.path.exists(receipt_folder):
    os.makedirs(receipt_folder)

# ----------------------------------------
# INPUT FORM
# ----------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("Date", datetime.today())
with col2:
    category = st.selectbox(
        "Category",
        ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"]
    )
with col3:
    amount = st.number_input("Amount (Rp)", min_value=0, step=1000)

description = st.text_input("Description")
vendor = st.text_input("Vendor")
receipt_file = st.file_uploader("Upload Receipt", type=["png", "jpg", "jpeg", "pdf"])

receipt_name = None
if receipt_file is not None:
    receipt_bytes = receipt_file.read()
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_bytes)
    st.success(f"📎 Uploaded: {receipt_name}")

# ----------------------------------------
# SAVE RECORD
# ----------------------------------------
if st.button("💾 Save"):
    new_data = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description],
        "Vendor": [vendor],
        "Amount": [amount],
        "Receipt": [receipt_name]
    })

    if os.path.exists(excel_file):
        old_data = pd.read_excel(excel_file)
        df = pd.concat([old_data, new_data], ignore_index=True)
    else:
        df = new_data

    df.to_excel(excel_file, index=False)
    st.success("✅ Data saved successfully!")

# ----------------------------------------
# DISPLAY TABLE + FILTER
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    st.subheader("📋 Saved Records")

    # --- Filter Section ---
    f1, f2, f3 = st.columns([1.5, 1.5, 1])
    with f1:
        month_filter = st.selectbox("📅 Filter by Month", ["All"] + sorted(df["Month"].unique(), reverse=True))
    with f2:
        cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["Category"].unique()))
    with f3:
        reset = st.button("🔄 Reset Filters")

    filtered_df = df.copy()
    if month_filter != "All":
        filtered_df = filtered_df[filtered_df["Month"] == month_filter]
    if cat_filter != "All":
        filtered_df = filtered_df[filtered_df["Category"] == cat_filter]
    if reset:
        filtered_df = df.copy()

    # --- Table Header ---
    st.markdown(
        "<div class='record-header'>"
        "<div>Date</div><div>Category</div><div>Description</div><div>Vendor</div><div>Amount</div><div>Receipt</div>"
        "</div>",
        unsafe_allow_html=True
    )

    # --- Table Rows ---
    for idx, row in filtered_df.iterrows():
        st.markdown("<div class='record-row'>", unsafe_allow_html=True)
        cols = st.columns([1.4, 1.4, 2.2, 1.3, 1, 0.8])
        cols[0].write(row["Date"].strftime("%Y-%m-%d"))
        cols[1].write(row["Category"])
        cols[2].write(row["Description"])
        cols[3].write(row["Vendor"])
        cols[4].write(f"Rp {int(row['Amount']):,}")

        if pd.notna(row["Receipt"]) and os.path.exists(os.path.join(receipt_folder, row["Receipt"])):
            with cols[5].expander("🔍 View"):
                file_path = os.path.join(receipt_folder, row["Receipt"])
                if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(file_path, width=500)
                elif file_path.lower().endswith(".pdf"):
                    st.markdown(f"📄 [Open PDF Receipt]({file_path})")
        else:
            cols[5].write("-")
        st.markdown("</div>", unsafe_allow_html=True)

    # ----------------------------------------
    # SUMMARY SECTION (Filtered)
    # ----------------------------------------
    st.markdown("---")
    st.subheader("📊 Summary (Filtered Data)")
    col1, col2 = st.columns(2)
    with col1:
        cat_summary = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        st.write("**Total by Category**")
        st.dataframe(cat_summary)
    with col2:
        month_summary = filtered_df.groupby("Month")["Amount"].sum().reset_index()
        st.write("**Total by Month**")
        st.dataframe(month_summary)
else:
    st.info("No data saved yet.")
