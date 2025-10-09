# expense_app_v2.py (v23) — Header/Rows perfectly aligned
import streamlit as st
import pandas as pd
import os
from PIL import Image
from datetime import datetime
import time
from io import BytesIO

st.set_page_config(page_title="Duck San Expense Manager", layout="wide")

# CSS: 작은 버튼, 표 스타일
st.markdown("""
    <style>
    .hdr {
        background-color:#2b5876;
        color: white;
        padding: 8px 6px;
        border-radius: 6px;
        font-weight:600;
    }
    .small-btn {
        font-size:15px !important;
        padding: 2px 6px !important;
        margin:0 2px !important;
    }
    .receipt-expander > div {
        padding: 6px 0;
    }
    </style>
""", unsafe_allow_html=True)

# logo + title
if os.path.exists("unnamed.png"):
    logo = Image.open("unnamed.png")
    st.image(logo, width=240)
st.markdown("<h1 style='color:#2b5876;'>💰 Duck San Expense Management System</h1>", unsafe_allow_html=True)
st.markdown("---")

# paths
excel_file = "expenses.xlsx"
receipt_folder = "receipts"
os.makedirs(receipt_folder, exist_ok=True)

# Input form
c1, c2, c3 = st.columns(3)
with c1:
    date = st.date_input("Date", datetime.today())
with c2:
    category = st.selectbox("Category", ["Transportation","Meals","Entertainment","Office","Office Supply","ETC"])
with c3:
    amount = st.number_input("Amount (Rp)", min_value=0, step=1000)

description = st.text_input("Description")
vendor = st.text_input("Vendor")
receipt_file = st.file_uploader("Upload Receipt", type=["png","jpg","jpeg","pdf"])

receipt_name = None
if receipt_file is not None:
    receipt_bytes = receipt_file.read()
    receipt_name = receipt_file.name
    with open(os.path.join(receipt_folder, receipt_name), "wb") as f:
        f.write(receipt_bytes)
    st.success(f"📎 Uploaded: {receipt_name}")

# Save
if st.button("💾 Save"):
    new = pd.DataFrame({
        "Date":[date],
        "Category":[category],
        "Description":[description],
        "Vendor":[vendor],
        "Amount":[amount],
        "Receipt":[receipt_name]
    })
    if os.path.exists(excel_file):
        df_old = pd.read_excel(excel_file)
        df = pd.concat([df_old, new], ignore_index=True)
    else:
        df = new
    df.to_excel(excel_file, index=False)
    st.success("✅ Saved")
    time.sleep(0.4)
    st.rerun()

# If data exists -> display with perfectly aligned header & rows
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    # Title row with Download (on same visual line)
    left, right = st.columns([4,1])
    with left:
        st.subheader("📋 Saved Records")
    with right:
        # Download popover: select month -> download
        with st.expander("📥 Download", expanded=False):
            months = sorted(df["Month"].unique(), reverse=True)
            if months:
                sel_m = st.selectbox("Select month", months)
                filt = df[df["Month"]==sel_m]
                buf = BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    filt.to_excel(writer, index=False, sheet_name=sel_m)
                st.download_button(f"📤 Download {sel_m}.xlsx", data=buf.getvalue(),
                                   file_name=f"DuckSan_Expense_{sel_m}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.write("No data")

    # Filters
    f1, f2, f3 = st.columns([1.5,1.5,1])
    with f1:
        month_filter = st.selectbox("📅 Filter by Month", ["All"] + sorted(df["Month"].unique(), reverse=True))
    with f2:
        cat_filter = st.selectbox("📂 Filter by Category", ["All"] + sorted(df["Category"].unique()))
    with f3:
        reset = st.button("🔄 Reset Filters")

    filtered = df.copy()
    if month_filter != "All":
        filtered = filtered[filtered["Month"]==month_filter]
    if cat_filter != "All":
        filtered = filtered[filtered["Category"]==cat_filter]
    if reset:
        filtered = df.copy()

    st.markdown("")  # spacer

    # ---- HEADER: use st.columns with SAME ratios as rows ----
    col_ratios = [1.2, 1.4, 2.0, 1.4, 1.0, 0.9, 0.9]  # must match rows below
    hcols = st.columns(col_ratios)
    headers = ["Date","Category","Description","Vendor","Amount","Receipt","Action"]
    for hc, title in zip(hcols, headers):
        hc.markdown(f"<div class='hdr'>{title}</div>", unsafe_allow_html=True)

    # ---- ROWS: use same ratios ----
    for idx, row in filtered.iterrows():
        rows = st.columns(col_ratios)
        rows[0].write(row["Date"].strftime("%Y-%m-%d"))
        rows[1].write(row["Category"])
        rows[2].write(row["Description"])
        rows[3].write(row["Vendor"])
        rows[4].write(f"Rp {int(row['Amount']):,}")

        # Receipt preview (expander)
        if pd.notna(row.get("Receipt")) and os.path.exists(os.path.join(receipt_folder, row["Receipt"])):
            with rows[5].expander("🔍 View"):
                p = os.path.join(receipt_folder, row["Receipt"])
                if p.lower().endswith((".png",".jpg",".jpeg")):
                    st.image(p, width=480)
                else:
                    st.markdown(f"📄 [Open PDF]({p})")
        else:
            rows[5].write("-")

        # Actions (small icon buttons)
        with rows[6]:
            c_edit, c_del = st.columns([1,1])
            if c_edit.button("✏️", key=f"edit_{idx}"):
                with st.form(f"form_edit_{idx}"):
                    nd = st.date_input("Date", value=row["Date"])
                    nc = st.selectbox("Category",
                                      ["Transportation","Meals","Entertainment","Office","Office Supply","ETC"],
                                      index=["Transportation","Meals","Entertainment","Office","Office Supply","ETC"].index(row["Category"]))
                    nds = st.text_input("Description", value=row["Description"])
                    nv = st.text_input("Vendor", value=row["Vendor"])
                    na = st.number_input("Amount (Rp)", value=int(row["Amount"]), step=1000)
                    submitted = st.form_submit_button("💾 Update")
                    if submitted:
                        # update by original index (row.name)
                        df.loc[row.name, "Date"] = nd
                        df.loc[row.name, "Category"] = nc
                        df.loc[row.name, "Description"] = nds
                        df.loc[row.name, "Vendor"] = nv
                        df.loc[row.name, "Amount"] = na
                        df.to_excel(excel_file, index=False)
                        st.success("✅ Updated")
                        time.sleep(0.3)
                        st.rerun()
            if c_del.button("🗑️", key=f"del_{idx}"):
                df = df.drop(row.name).reset_index(drop=True)
                df.to_excel(excel_file, index=False)
                st.success("🗑️ Deleted")
                time.sleep(0.3)
                st.rerun()

    # Summary
    st.markdown("---")
    st.subheader("📊 Summary (Filtered)")
    s1, s2 = st.columns(2)
    with s1:
        s_cat = filtered.groupby("Category")["Amount"].sum().reset_index()
        st.dataframe(s_cat)
    with s2:
        s_mon = filtered.groupby("Month")["Amount"].sum().reset_index()
        st.dataframe(s_mon)

else:
    st.info("No data yet.")
