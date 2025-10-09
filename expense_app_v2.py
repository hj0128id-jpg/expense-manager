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

# ----------------------------------------
# Save Button
# ----------------------------------------
if st.button("💾 Save"):
    new_data = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Description": [description],
        "Vendor": [vendor],
        "Amount": [amount]
    })

    # Load previous data if exists
    if os.path.exists(excel_file):
        old_data = pd.read_excel(excel_file)
        df = pd.concat([old_data, new_data], ignore_index=True)
    else:
        df = new_data

    df.to_excel(excel_file, index=False)
    st.success("✅ Data saved successfully!")

# ----------------------------------------
# Display Data + Filter + Summary + Export
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    st.subheader("📅 Filter Records by Month")
    month_list = sorted(df["Month"].unique(), reverse=True)
    selected_month = st.selectbox("Select Month", ["All"] + month_list)

    if selected_month != "All":
        df_filtered = df[df["Month"] == selected_month]
    else:
        df_filtered = df

    st.subheader("📋 Records")
    st.dataframe(df_filtered, use_container_width=True)

    # Summary Section
    st.markdown("---")
    st.subheader("📊 Summary")

    col1, col2 = st.columns(2)
    with col1:
        cat_summary = df_filtered.groupby("Category")["Amount"].sum().reset_index()
        st.write("**Total by Category**")
        st.dataframe(cat_summary)

    with col2:
        month_summary = df.groupby("Month")["Amount"].sum().reset_index()
        st.write("**Total by Month (All)**")
        st.dataframe(month_summary)

    # Excel Download (raw data)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Expenses")
    st.download_button(
        label="📥 Download All Data (Excel)",
        data=buffer,
        file_name="DuckSan_Expenses_All.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ----------------------------------------
    # Generate Expense Report (Formal Style)
    # ----------------------------------------
    st.markdown("---")
    st.subheader("📄 Generate Expense Report (Formal Format)")

    if st.button("📘 Export Expense Form (Filtered Month)"):
        if selected_month == "All":
            st.warning("⚠️ Please select a specific month to export.")
        else:
            report_buffer = BytesIO()
            with pd.ExcelWriter(report_buffer, engine="openpyxl") as writer:
                df_filtered.to_excel(writer, index=False, sheet_name="Expense Report")

                # Summary Sheet
                summary = df_filtered.groupby("Category")["Amount"].sum().reset_index()
                summary.to_excel(writer, index=False, sheet_name="Summary")

            st.download_button(
                label="⬇️ Download Expense Report (Excel Form)",
                data=report_buffer,
                file_name=f"DuckSan_Expense_Report_{selected_month}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("No data saved yet.")
