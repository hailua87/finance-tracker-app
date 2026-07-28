import streamlit as st
import pandas as pd
from datetime import date

# Thiết lập cấu hình trang với tên mới
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
    st.header("Sổ Tiết Kiệm & Quỹ Mục Tiêu")
    
    # Sổ tiết kiệm có kỳ hạn
    st.subheader("Sổ Tiết Kiệm (Term Deposits)")
    df_savings = pd.DataFrame({
        "Nguồn tiền": ["TK TCB Vợ", "TK TCB Chồng"],
        "Kỳ hạn": ["6 Tháng", "12 Tháng"],
        "Tiền gốc (VND)": [100000000, 150000000],
        "Lãi suất (%)": [4.5, 5.2],
        "Ngày đáo hạn": [date(2026, 9, 15), date(2027, 2, 20)]
    })
    
    # Tính lãi dự kiến
    df_savings['Lãi dự kiến'] = df_savings['Tiền gốc (VND)'] * (df_savings['Lãi suất (%)'] / 100)
    
    # Hiển thị bảng data format đẹp
    st.dataframe(
        df_savings.style.format({
            "Tiền gốc (VND)": "{:,.0f}", 
            "Lãi suất (%)": "{:.1f}", 
            "Lãi dự kiến": "{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # Quỹ mục tiêu (Ví dụ: Quỹ giáo dục)
    st.subheader("Quỹ Tích Lũy")
    st.write("**Quỹ giáo dục cho bé**")
    st.caption("45,000,000 / 200,000,000 VND (22.5%)")
    st.progress(0.225)
