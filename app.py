import streamlit as st
import pandas as pd
from datetime import date

# Thiết lập cấu hình trang
st.set_page_config(page_title="Nhà quê tập chi tiêu", layout="wide")

# Tiêu đề chính của ứng dụng
st.title("🌾 Nhà quê tập chi tiêu")

# Phân chia 3 tab chính
tab_cashflow, tab_invest, tab_savings = st.tabs(["💰 Dòng tiền", "📈 Đầu tư", "🏦 Tiết kiệm"])

# --- TAB 1: DÒNG TIỀN ---
with tab_cashflow:
    st.header("Nhập liệu Dòng tiền")
    with st.form("cashflow_form"):
        col1, col2 = st.columns(2)
        with col1:
            account = st.selectbox("Tài khoản", ["TK TCB Vợ", "TK TCB Chồng", "Tiền mặt"])
            amount = st.number_input("Số tiền (VND)", min_value=0, step=50000)
        with col2:
            category = st.selectbox("Phân loại", ["Ăn uống", "Mẹ & Bé", "Nhà cửa", "Đầu tư", "Khác"])
            note = st.text_input("Ghi chú")
        
        submitted = st.form_submit_button("Lưu Giao dịch")
        if submitted:
            st.success(f"Đã lưu {amount:,.0f} VND từ {account} vào mục {category}!")

# --- TAB 2: ĐẦU TƯ ---
with tab_invest:
    st.header("Danh mục Cổ phiếu")
    with st.form("invest_form"):
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.selectbox("Mã cổ phiếu", ["VIB", "VCI", "MBB", "SSI", "TPB"])
            action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        with col2:
            volume = st.number_input("Khối lượng", min_value=100, step=100)
            price = st.number_input("Giá khớp (VND)", min_value=0)
            
        invest_submit = st.form_submit_button("Lưu Giao dịch")
        if invest_submit:
            st.success(f"Đã {action} {volume} cổ phiếu {ticker} với giá {price:,.0f} VND!")

    st.subheader("Trạng thái Danh mục (Mockup)")
    df_invest = pd.DataFrame({
        "Mã CP": ["SSI", "VIB", "MBB"],
        "Khối lượng": [1000, 2500, 1500],
        "Giá vốn": [32.5, 20.1, 22.0]
    })
    st.dataframe(df_invest, use_container_width=True, hide_index=True)

# --- TAB 3: TIẾT KIỆM ---
with tab_savings:
    st.header("Phân bổ Quỹ Tích Lũy")
    
    # 1. Tieu Boi Funding
    st.subheader("👧 Tieu Boi Funding")
    st.write("**Quỹ giáo dục & Phát triển cho bé**")
    st.caption("Hiện tại: 45,000,000 VND / Mục tiêu: 200,000,000 VND (22.5%)")
    st.progress(0.225)
    st.divider() # Đường gạch ngang phân cách
    
    # 2. Daddy Funding
    st.subheader("👨 Daddy Funding")
    st.write("**Quỹ đầu tư & Tiêu dùng của Chồng**")
    st.caption("Hiện tại: 30,000,000 VND / Mục tiêu: 100,000,000 VND (30.0%)")
    st.progress(0.30)
    st.divider()
    
    # 3. Mama Funding
    st.subheader("👩 Mama Funding")
    st.write("**Quỹ tích lũy & Mua sắm của Vợ**")
    st.caption("Hiện tại: 75,000,000 VND / Mục tiêu: 150,000,000 VND (50.0%)")
    st.progress(0.50)
    st.divider()
    
    # Nút chuyển tiền nhanh vào quỹ (UI Mockup)
    with st.expander("➕ Nạp tiền vào quỹ"):
        with st.form("fund_add_form"):
            fund_sel = st.selectbox("Chọn quỹ", ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"])
            fund_add_amt = st.number_input("Số tiền nạp (VND)", min_value=0, step=500000)
            if st.form_submit_button("Xác nhận"):
                st.success(f"Đã cập nhật {fund_add_amt:,.0f} VND vào {fund_sel}")
