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
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# Custom CSS for AgGrid
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
# Display Data + Receipt Preview
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])

    st.subheader("📋 Saved Records")

    # Add clickable 'View' link for receipts
    def make_receipt_link(row):
        if pd.isna(row["Receipt"]):
            return ""
        path = os.path.join(receipt_folder, row["Receipt"])
        if os.path.exists(path) and row["Receipt"].lower().endswith((".png", ".jpg", ".jpeg")):
            return f"🔍 [View]({path})"
        elif os.path.exists(path) and row["Receipt"].lower().endswith(".pdf"):
            return f"📄 [PDF]({path})"
        else:
            return ""

    df["Receipt View"] = df.apply(make_receipt_link, axis=1)

    # AgGrid setup
    gb = GridOptionsBuilder.from_dataframe(df[["Date", "Category", "Description", "Vendor", "Amount", "Receipt View"]])
    gb.configure_default_column(resizable=True, wrapText=True, autoHeight=True)
    gb.configure_grid_options(domLayout="autoHeight", rowHeight=40)
    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        theme="streamlit",
        height=400,
        fit_columns_on_grid_load=True,
        update_mode=GridUpdateMode.NO_UPDATE
    )

    # ----------------------------------------
    # Receipt Preview Side Panel
    # ----------------------------------------
    st.markdown("---")
    st.subheader("🧾 Receipt Preview")

    selected = grid_response.get("selected_rows", [])
    if selected and selected[0].get("Receipt"):
        receipt_path = os.path.join(receipt_folder, selected[0]["Receipt"])
        if os.path.exists(receipt_path):
            if receipt_path.lower().endswith((".png", ".jpg", ".jpeg")):
                st.image(receipt_path, width=400, caption=f"Receipt: {selected[0]['Receipt']}")
            elif receipt_path.lower().endswith(".pdf"):
                st.write(f"📄 [Open PDF Receipt]({receipt_path})")
        else:
            st.info("⚠️ Receipt file not found.")
    else:
        st.info("Select a record to preview its receipt.")

else:
    st.info("No data saved yet.")
