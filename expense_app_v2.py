import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO

# ----------------------------------------
# Basic Config
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] > div {
        border-bottom: 1px solid #e5e5e5;
        padding: 6px 0;
    }
    th {
        background-color: #2b5876 !important;
        color: white !important;
        text-align: center !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------
# Header
# ----------------------------------------
if os.path.exists("unnamed.png"):
    logo = Image.open("unnamed.png")
    st.image(logo, width=280)
else:
    st.warning("⚠️ Please upload your logo file (unnamed.png) in the same folder.")

st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Management System</h1>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# Input Section
# ----------------------------------------
excel_file = "expenses.xlsx"
receipt_folder = "receipts"

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
    if not os.path.exists(receipt_folder):
        os.makedirs(receipt_folder)
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_bytes)
    st.success(f"📎 Uploaded: {receipt_name}")

# ----------------------------------------
# Save Button
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
# Display Table + Popup
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    st.subheader("📋 Saved Records")

    # Display header
    st.markdown(
        "<div style='font-weight:bold;display:grid;grid-template-columns:140px 160px 250px 160px 120px 80px;'>"
        "<div>Date</div><div>Category</div><div>Description</div><div>Vendor</div><div>Amount</div><div>Receipt</div>"
        "</div>",
        unsafe_allow_html=True
    )

    # Show rows
    for idx, row in df.iterrows():
        cols = st.columns([1.5, 1.5, 2, 1.5, 1, 0.6])
        cols[0].write(row["Date"].strftime("%Y-%m-%d"))
        cols[1].write(row["Category"])
        cols[2].write(row["Description"])
        cols[3].write(row["Vendor"])
        cols[4].write(f"Rp {int(row['Amount']):,}")

        if pd.notna(row["Receipt"]) and os.path.exists(os.path.join(receipt_folder, row["Receipt"])):
            if cols[5].button("🔍 View", key=f"view_{idx}"):
                file_path = os.path.join(receipt_folder, row["Receipt"])
                with st.modal(f"🧾 Receipt Preview — {row['Receipt']}"):
                    if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(file_path, width=500)
                    elif file_path.lower().endswith(".pdf"):
                        st.markdown(f"📄 [Open PDF Receipt]({file_path})")
                    st.button("Close")
        else:
            cols[5].write("-")

    # ----------------------------------------
    # Summary Section
    # ----------------------------------------
    st.markdown("---")
    st.subheader("📊 Summary")

    col1, col2 = st.columns(2)
    with col1:
        cat_summary = df.groupby("Category")["Amount"].sum().reset_index()
        st.write("**Total by Category**")
        st.dataframe(cat_summary)
    with col2:
        month_summary = df.groupby("Month")["Amount"].sum().reset_index()
        st.write("**Total by Month**")
        st.dataframe(month_summary)
else:
    st.info("No data saved yet.")
