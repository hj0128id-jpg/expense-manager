import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO

# ----------------------------------------
# Basic Config
# ----------------------------------------
st.set_page_config(page_title="Expense Manager", layout="wide")

# Company Logo
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
receipt_file = st.file_uploader("Upload Receipt", type=["png","jpg","jpeg","pdf"])

receipt_name = None
if receipt_file is not None:
    receipt_bytes = receipt_file.read()
    receipt_name = receipt_file.name
    if not os.path.exists("receipts"):
        os.makedirs("receipts")
    with open(f"receipts/{receipt_name}", "wb") as f:
        f.write(receipt_bytes)
    if receipt_file.type.startswith("image"):
        st.image(receipt_bytes, width=200)
    else:
        st.write(f"Uploaded: {receipt_name}")

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
# Display Data + Summary + Edit/Delete
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    st.subheader("📋 Saved Records")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("✏️ Edit / Delete Records")

    if not df.empty:
        selected_index = st.selectbox("Select Record to Edit/Delete", df.index)

        # Display current values
        edit_date = st.date_input("Date", pd.to_datetime(df.loc[selected_index, "Date"]))
        edit_category = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                                     index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(df.loc[selected_index, "Category"]))
        edit_description = st.text_input("Description", df.loc[selected_index, "Description"])
        edit_vendor = st.text_input("Vendor", df.loc[selected_index, "Vendor"])
        edit_amount = st.number_input("Amount", value=int(df.loc[selected_index, "Amount"]))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update"):
                df.loc[selected_index, "Date"] = edit_date
                df.loc[selected_index, "Category"] = edit_category
                df.loc[selected_index, "Description"] = edit_description
                df.loc[selected_index, "Vendor"] = edit_vendor
                df.loc[selected_index, "Amount"] = edit_amount
                df.to_excel(excel_file, index=False)
                st.success("✅ Record updated!")

        with col2:
            if st.button("Delete"):
                df = df.drop(selected_index)
                df.to_excel(excel_file, index=False)
                st.success("✅ Record deleted!")

    # Summary Section
    st.markdown("---")
    st.subheader("📊 Summary")

    col1, col2 = st.columns(2)
    with col1:
        cat_summary = df.groupby("Category")["Amount"].sum().reset_index()
        st.write("**Total by Category**")
        st.dataframe(cat_summary)

    with col2:
        df["Month"] = pd.to_datetime(df["Date"]).dt.to_period("M")
        month_summary = df.groupby("Month")["Amount"].sum().reset_index()
        st.write("**Total by Month**")
        st.dataframe(month_summary)

    # Excel Download Button
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Expenses")
    st.download_button(
        label="📥 Download Excel",
        data=buffer,
        file_name="DuckSan_Expenses.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No data saved yet.")
