import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# ----------------------------------------
# Basic Config
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .ag-theme-streamlit {
        --ag-header-background-color: #2b5876;
        --ag-header-foreground-color: white;
        --ag-row-hover-color: #e3f2fd;
        --ag-odd-row-background-color: #fafafa;
        --ag-font-size: 15px;
        border-radius: 10px;
        overflow: hidden;
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
# Display Table
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    # 링크 만들기
    def make_receipt_link(name):
        if pd.isna(name):
            return ""
        return f"🔍 View ({name})"
    df["View Receipt"] = df["Receipt"].apply(make_receipt_link)

    st.subheader("📋 Saved Records")

    gb = GridOptionsBuilder.from_dataframe(df[["Date", "Category", "Description", "Vendor", "Amount", "View Receipt"]])
    gb.configure_default_column(resizable=True, wrapText=True, autoHeight=True)
    gb.configure_selection("single", use_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        theme="streamlit",
        height=400,
        fit_columns_on_grid_load=True,
        update_mode=GridUpdateMode.SELECTION_CHANGED
    )

    selected = grid_response.get("selected_rows", [])

    # ----------------------------------------
    # Receipt Popup Modal
    # ----------------------------------------
    if selected:
        selected_row = selected[0]
        receipt_file = selected_row.get("Receipt")
        if receipt_file and isinstance(receipt_file, str):
            receipt_path = os.path.join(receipt_folder, receipt_file)
            if os.path.exists(receipt_path):
                with st.modal("🧾 Receipt Preview"):
                    if receipt_path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(receipt_path, width=500, caption=f"{receipt_file}")
                    elif receipt_path.lower().endswith(".pdf"):
                        st.write(f"📄 [Open PDF Receipt]({receipt_path})")
                    st.button("Close")
            else:
                st.warning("⚠️ Receipt file not found.")
        else:
            st.info("Select a record with a receipt to preview.")
    else:
        st.caption("Select a record and click to view its receipt.")

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
