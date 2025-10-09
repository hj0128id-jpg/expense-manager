import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

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
# Display Data + Edit/Delete + Summary
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    st.subheader("📋 Saved Records")

    # AgGrid 설정
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("Date", editable=True)
    gb.configure_column("Category", editable=True)
    gb.configure_columns(["Description","Vendor","Amount","Receipt"], editable=False)
    gb.configure_selection("single")
    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=350,
        width="100%",
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED
    )

    selected = grid_response['selected_rows']
    if selected and len(selected) > 0:
        idx = int(selected[0]['_selectedRowNodeInfo']['nodeId'])
        row = df.loc[idx]

        st.markdown("---")
        st.subheader("✏️ Edit / Delete Selected Record")
        
        edit_date = st.date_input("Date", pd.to_datetime(row["Date"]))
        edit_category = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                                     index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(row["Category"]))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update Selected"):
                df.loc[idx, "Date"] = edit_date
                df.loc[idx, "Category"] = edit_category
                df.to_excel(excel_file, index=False)
                st.success("✅ Record updated!")
        with col2:
            if st.button("Delete Selected"):
                df = df.drop(idx).reset_index(drop=True)
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

    # Excel Download
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
