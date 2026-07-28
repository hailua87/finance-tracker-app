import streamlit as st
import pandas as pd
from datetime import date

# Thiết lập cấu hình trang
st.set_page_config(page_title="Nhà quê tập chi tiêu", layout="wide")

# Tiêu đề chính của ứng dụng
st.title("🌾 Nhà quê tập chi tiêu")

# Phân chia 3 tab chính
tab_cashflow, tab_invest, tab_savings = st.tabs(["💰 Dòng tiền", "📈 Đầu tư", "🏦 Tiết kiệm (Funding)"])

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

# --- TAB 3: TIẾT KIỆM (FUNDING) ---
with tab_savings:
    st.header("Danh mục Sổ Tiết Kiệm (Funding)")
    
    # Tạo mockup data chứa toàn bộ sổ tiết kiệm của gia đình
    # Dữ liệu này sau này sẽ được kéo từ Database/Google Sheets
    df_savings = pd.DataFrame({
        "Chủ quỹ": ["Tieu Boi Funding", "Daddy Funding", "Mama Funding", "Tieu Boi Funding", "Mama Funding"],
        "Ngày gửi": [date(2026, 1, 15), date(2026, 3, 10), date(2026, 5, 20), date(2026, 7, 10), date(2026, 6, 5)],
        "Kỳ hạn": ["6 Tháng", "12 Tháng", "3 Tháng", "12 Tháng", "6 Tháng"],
        "Lãi suất (%)": [5.0, 5.5, 4.0, 5.2, 4.8],
        "Tiền gốc (VND)": [50000000, 100000000, 150000000, 30000000, 80000000]
    })
    
    # Danh sách các quỹ để render UI
    funds_info = [
        ("👧 Tieu Boi Funding", "Tieu Boi Funding"),
        ("👨 Daddy Funding", "Daddy Funding"),
        ("👩 Mama Funding", "Mama Funding")
    ]
    
    # Render từng quỹ
    for icon_title, fund_name in funds_info:
        st.subheader(icon_title)
        
        # Lọc dữ liệu theo từng quỹ
        fund_data = df_savings[df_savings["Chủ quỹ"] == fund_name].copy()
        
        # Tính tổng tiền gốc đang gửi của quỹ đó
        total_goc = fund_data["Tiền gốc (VND)"].sum()
        st.markdown(f"**Tổng vốn đang gửi:** <span style='color:#2e7d32; font-size:18px'>{total_goc:,.0f} VND</span>", unsafe_allow_html=True)
        
        # Định dạng lại bảng để hiển thị đẹp hơn
        if not fund_data.empty:
            display_df = fund_data[['Ngày gửi', 'Kỳ hạn', 'Lãi suất (%)', 'Tiền gốc (VND)']]
            st.dataframe(
                display_df.style.format({
                    "Lãi suất (%)": "{:.1f}", 
                    "Tiền gốc (VND)": "{:,.0f}"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.caption("Chưa có khoản gửi nào.")
            
        st.divider() # Đường kẻ ngang phân cách

    # Form thêm sổ tiết kiệm mới
    with st.expander("➕ Thêm khoản gửi tiết kiệm mới"):
        with st.form("new_deposit_form"):
            new_fund = st.selectbox("Chọn Quỹ", ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"])
            new_amount = st.number_input("Số tiền (VND)", min_value=0, step=1000000)
            
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                new_date = st.date_input("Ngày gửi")
            with col_d2:
                new_term = st.selectbox("Kỳ hạn", ["1 Tháng", "3 Tháng", "6 Tháng", "12 Tháng"])
            with col_d3:
                new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, format="%.1f")
                
            if st.form_submit_button("Lưu Khoản Gửi"):
                st.success(f"Đã lưu khoản gửi {new_amount:,.0f} VND vào {new_fund}!")
