import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time
from io import BytesIO

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# ----------------------------------------
# STATE
# ----------------------------------------
if "view_index" not in st.session_state:
    st.session_state.view_index = None
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

# ----------------------------------------
# STYLE
# ----------------------------------------
st.markdown("""
<style>
.stButton > button {
    border: none;
    background-color: transparent;
    color: #007bff;
    font-weight: 600;
    cursor: pointer;
}
.stButton > button:hover {
    text-decoration: underline;
}
.header-cell {
    font-weight: 700;
    color: white;
    background: linear-gradient(90deg, #2b5876, #4e4376);
    padding: 8px 10px;
    border-radius: 6px 6px 0 0;
    text-align: left;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# HEADER
# ----------------------------------------
if os.path.exists("unnamed.png"):
    logo = Image.open("unnamed.png")
    st.image(logo, width=240)

st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Management System</h1>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# PATHS
# ----------------------------------------
excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# ----------------------------------------
# INPUT FORM
# ----------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("Date", datetime.today())
with col2:
    category = st.selectbox("Category", ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"])
with col3:
    amount_str = st.text_input("Amount (Rp)", value="", placeholder="e.g. 1,000,000")
    if amount_str:
        clean_amount = amount_str.replace(",", "").strip()
        amount = int(clean_amount) if clean_amount.isdigit() else 0
    else:
        amount = 0

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

    left, right = st.columns([4, 1])
    with left:
        st.subheader("📋 Saved Records")
    with right:
        months = sorted(df["Month"].unique(), reverse=True)
        with st.popover("📥 Download Excel"):
            sel = st.selectbox("Select month", months)
            filtered = df[df["Month"] == sel]
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                filtered.to_excel(writer, index=False, sheet_name=sel)
            st.download_button(
                label=f"📤 Download {sel}.xlsx",
                data=buf.getvalue(),
                file_name=f"DuckSan_Expense_{sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Filters
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

    st.markdown("### 💾 Expense Records")

    # Header
    header_cols = st.columns([1, 1.2, 2, 1.3, 1, 0.8, 0.6])
    headers = ["Date", "Category", "Description", "Vendor", "Amount", "Receipt", "Action"]
    for i, h in enumerate(headers):
        header_cols[i].markdown(f"<div class='header-cell'>{h}</div>", unsafe_allow_html=True)

    # Rows
    for idx, row in view_df.iterrows():
        cols = st.columns([1, 1.2, 2, 1.3, 1, 0.8, 0.6])
        cols[0].write(row["Date"].strftime("%Y-%m-%d"))
        cols[1].write(row["Category"])
        cols[2].write(row["Description"])
        cols[3].write(row["Vendor"])
        cols[4].write(f"Rp {int(row['Amount']):,}")
        with cols[5]:
            if pd.notna(row["Receipt"]):
                if st.button("View", key=f"view_{idx}"):
                    st.session_state.view_index = idx
                    st.session_state.edit_index = None
                    st.rerun()
            else:
                st.write("-")

        with cols[6]:
            e1, e2 = st.columns(2)
            with e1:
                if st.button("✏️", key=f"edit_{idx}"):
                    st.session_state.edit_index = idx
                    st.session_state.view_index = None
                    st.rerun()
            with e2:
                if st.button("🗑️", key=f"del_{idx}"):
                    df = df.drop(idx).reset_index(drop=True)
                    df.to_excel(excel_file, index=False)
                    st.success("🗑️ Record deleted!")
                    time.sleep(0.5)
                    st.rerun()

        # View (expand)
        if st.session_state.view_index == idx:
            with st.expander("🧾 Receipt Preview", expanded=True):
                file_path = os.path.join(receipt_folder, str(row["Receipt"]))
                if os.path.exists(file_path):
                    if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(file_path, use_container_width=True)
                    elif file_path.lower().endswith(".pdf"):
                        st.markdown(f"📄 [Open PDF Receipt]({file_path})")
                else:
                    st.warning("⚠️ File not found.")
                if st.button("Close Preview", key=f"close_view_{idx}"):
                    st.session_state.view_index = None
                    st.rerun()

        # Edit (expand)
        if st.session_state.edit_index == idx:
            with st.expander("✏️ Edit Record", expanded=True):
                edit_date = st.date_input("Date", value=row["Date"], key=f"edit_date_{idx}")
                edit_cat = st.selectbox(
                    "Category",
                    ["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"],
                    index=["Transportation", "Meals", "Entertainment", "Office", "Office Supply", "ETC"].index(row["Category"]),
                    key=f"edit_cat_{idx}"
                )
                edit_desc = st.text_input("Description", value=row["Description"], key=f"edit_desc_{idx}")
                edit_vendor = st.text_input("Vendor", value=row["Vendor"], key=f"edit_vendor_{idx}")
                edit_amount = st.text_input("Amount (Rp)", value=f"{int(row['Amount']):,}", key=f"edit_amount_{idx}")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Save Changes", key=f"save_edit_{idx}"):
                        new_amount = int(edit_amount.replace(",", "")) if edit_amount.replace(",", "").isdigit() else 0
                        df.loc[row.name, "Date"] = edit_date
                        df.loc[row.name, "Category"] = edit_cat
                        df.loc[row.name, "Description"] = edit_desc
                        df.loc[row.name, "Vendor"] = edit_vendor
                        df.loc[row.name, "Amount"] = new_amount
                        df.to_excel(excel_file, index=False)
                        st.success("✅ Updated successfully!")
                        st.session_state.edit_index = None
                        time.sleep(0.5)
                        st.rerun()
                with c2:
                    if st.button("Cancel", key=f"cancel_edit_{idx}"):
                        st.session_state.edit_index = None
                        st.rerun()

    # Summary
    st.markdown("---")
    st.subheader("📊 Summary (Filtered Data)")

    cat_sum = view_df.groupby("Category")["Amount"].sum().reset_index()
    cat_sum["Amount"] = cat_sum["Amount"].apply(lambda x: f"Rp {int(x):,}")

    mon_sum = view_df.groupby("Month")["Amount"].sum().reset_index()
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
