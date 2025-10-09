import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time

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
        border-bottom: 1px solid #e0e0e0;
        align-items: center;
    }
    .record-row div {
        padding-left: 6px;
        font-size: 14px;
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
    .small-btn {
        background-color: transparent;
        border: none;
        cursor: pointer;
        font-size: 18px;
        margin-right: 5px;
    }
    .small-btn:hover {
        opacity: 0.7;
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
    time.sleep(1)
    st.rerun()

# ----------------------------------------
# DISPLAY + EDIT / DELETE
# ----------------------------------------
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    st.subheader("📋 Saved Records")

    # --- Filters ---
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
        "<div>Date</div><div>Category</div><div>Description</div><div>Vendor</div><div>Amount</div><div>Action</div>"
        "</div>",
        unsafe_allow_html=True
    )

    # --- Editable Rows ---
    for idx, row in filtered_df.iterrows():
        st.markdown("<div class='record-row'>", unsafe_allow_html=True)
        cols = st.columns([1.4, 1.4, 2.2, 1.3, 1, 0.8])
        cols[0].write(row["Date"].strftime("%Y-%m-%d"))
        cols[1].write(row["Category"])
        cols[2].write(row["Description"])
        cols[3].write(row["Vendor"])
        cols[4].write(f"Rp {int(row['Amount']):,}")

        edit_key = f"edit_{idx}"
        delete_key = f"delete_{idx}"

        c = cols[5]
        c.markdown(
            f"""
            <button class='small-btn' id='edit_{idx}'>✏️</button>
            <button class='small-btn' id='delete_{idx}'>🗑️</button>
            """,
            unsafe_allow_html=True
        )

        # Streamlit native buttons (invisible CSS buttons for actions)
        if c.button("✏️", key=edit_key):
            with st.form(f"edit_form_{idx}"):
                st.write("**✏️ Edit Record**")
                new_date = st.date_input("Date", row["Date"])
                new_category = st.selectbox("Category", 
                    ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                    index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(row["Category"])
                )
                new_desc = st.text_input("Description", row["Description"])
                new_vendor = st.text_input("Vendor", row["Vendor"])
                new_amount = st.number_input("Amount (Rp)", value=int(row["Amount"]), step=1000)
                submitted = st.form_submit_button("💾 Update")
                if submitted:
                    df.loc[row.name, "Date"] = new_date
                    df.loc[row.name, "Category"] = new_category
                    df.loc[row.name, "Description"] = new_desc
                    df.loc[row.name, "Vendor"] = new_vendor
                    df.loc[row.name, "Amount"] = new_amount
                    df.to_excel(excel_file, index=False)
                    st.success("✅ Record updated successfully!")
                    time.sleep(0.5)
                    st.rerun()

        if c.button("🗑️", key=delete_key):
            df = df.drop(row.name).reset_index(drop=True)
            df.to_excel(excel_file, index=False)
            st.success(f"🗑️ Deleted: {row['Description']}")
            time.sleep(0.5)
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ----------------------------------------
    # SUMMARY SECTION
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
        st.write
