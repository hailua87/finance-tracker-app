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

# --- TAB 2: ĐẦU TƯ (Chia làm Cổ phiếu & Chứng chỉ quỹ) ---
with tab_invest:
    # Tạo 2 tab con bên trong tab Đầu tư
    subtab_stock, subtab_ccq = st.tabs(["📈 Cổ phiếu (Stocks)", "📊 Chứng chỉ quỹ (Mutual Funds)"])
    
    # -- Tab con 1: CỔ PHIẾU --
    with subtab_stock:
        st.subheader("Giao dịch Cổ phiếu")
        with st.form("invest_stock_form"):
            col1, col2 = st.columns(2)
            with col1:
                ticker = st.selectbox("Mã cổ phiếu", ["VIB", "VCI", "MBB", "SSI", "TPB"])
                action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
            with col2:
                volume = st.number_input("Khối lượng (CP)", min_value=100, step=100)
                price = st.number_input("Giá khớp (VND)", min_value=0)
                
            if st.form_submit_button("Lưu Giao dịch"):
                st.success(f"Đã {action} {volume} cổ phiếu {ticker} với giá {price:,.0f} VND!")

        st.markdown("**Trạng thái Danh mục Cổ phiếu**")
        df_stock = pd.DataFrame({
            "Mã CP": ["SSI", "VIB", "MBB"],
            "Khối lượng": [1000, 2500, 1500],
            "Giá vốn trung bình": [32500, 20100, 22000]
        })
        # Giả lập giá hiện tại để tính Lãi/Lỗ
        df_stock["Giá hiện tại"] = [34000, 19500, 23100]
        df_stock["Tổng vốn (VND)"] = df_stock["Khối lượng"] * df_stock["Giá vốn trung bình"]
        df_stock["Lãi/Lỗ (%)"] = ((df_stock["Giá hiện tại"] - df_stock["Giá vốn trung bình"]) / df_stock["Giá vốn trung bình"]) * 100
        
        st.dataframe(
            df_stock.style.format({
                "Giá vốn trung bình": "{:,.0f}",
                "Giá hiện tại": "{:,.0f}",
                "Tổng vốn (VND)": "{:,.0f}",
                "Lãi/Lỗ (%)": "{:.2f}%"
            }),
            use_container_width=True, hide_index=True
        )

    # -- Tab con 2: CHỨNG CHỈ QUỸ --
    with subtab_ccq:
        st.subheader("Giao dịch Chứng chỉ quỹ (CCQ)")
        with st.form("invest_ccq_form"):
            col1, col2 = st.columns(2)
            with col1:
                fund_ticker = st.selectbox("Mã Quỹ / Công ty", [
                    "DCDS (Dragon Capital)", 
                    "VESAF (VinaCapital)", 
                    "TCBF (Techcom Capital - Trái phiếu)",
                    "TCEF (Techcom Capital - Cổ phiếu)",
                    "SSI-SCA (SSIAM)"
                ])
                action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
            with col2:
                volume_ccq = st.number_input("Số lượng CCQ", min_value=0.0, step=10.0, format="%.2f")
                nav_price = st.number_input("Giá NAV/CCQ (VND)", min_value=0)
                
            if st.form_submit_button("Lưu Giao dịch Quỹ"):
                st.success(f"Đã {action_ccq} {volume_ccq} CCQ {fund_ticker.split(' ')[0]} với giá NAV {nav_price:,.0f} VND!")
                
        st.markdown("**Danh mục Chứng chỉ quỹ tích lũy**")
        df_ccq = pd.DataFrame({
            "Quỹ Đầu Tư": ["DCDS", "TCBF", "VESAF"],
            "Loại quỹ": ["Cổ phiếu", "Trái phiếu", "Cổ phiếu"],
            "Số lượng CCQ": [1250.5, 3400.0, 850.2],
            "Giá vốn (NAV)": [65000, 15200, 21000]
        })
        df_ccq["Tổng giá trị (VND)"] = df_ccq["Số lượng CCQ"] * df_ccq["Giá vốn (NAV)"]
        
        st.dataframe(
            df_ccq.style.format({
                "Số lượng CCQ": "{:.2f}",
                "Giá vốn (NAV)": "{:,.0f}",
                "Tổng giá trị (VND)": "{:,.0f}"
            }),
            use_container_width=True, hide_index=True
        )

# --- TAB 3: TIẾT KIỆM (FUNDING) ---
with tab_savings:
    st.header("Danh mục Sổ Tiết Kiệm (Funding)")
    
    # Đã bổ sung cột "Ngân hàng" vào dữ liệu
    df_savings = pd.DataFrame({
        "Chủ quỹ": ["Tieu Boi Funding", "Daddy Funding", "Mama Funding", "Tieu Boi Funding", "Mama Funding"],
        "Ngân hàng": ["Techcombank (TCB)", "Techcombank (TCB)", "Vietcombank (VCB)", "MBBank", "Techcombank (TCB)"],
        "Ngày gửi": [date(2026, 1, 15), date(2026, 3, 10), date(2026, 5, 20), date(2026, 7, 10), date(2026, 6, 5)],
        "Kỳ hạn": ["6 Tháng", "12 Tháng", "3 Tháng", "12 Tháng", "6 Tháng"],
        "Lãi suất (%)": [5.0, 5.5, 4.0, 5.2, 4.8],
        "Tiền gốc (VND)": [50000000, 100000000, 150000000, 30000000, 80000000]
    })
    
    funds_info = [
        ("👧 Tieu Boi Funding", "Tieu Boi Funding"),
        ("👨 Daddy Funding", "Daddy Funding"),
        ("👩 Mama Funding", "Mama Funding")
    ]
    
    for icon_title, fund_name in funds_info:
        st.subheader(icon_title)
        fund_data = df_savings[df_savings["Chủ quỹ"] == fund_name].copy()
        
        total_goc = fund_data["Tiền gốc (VND)"].sum()
        st.markdown(f"**Tổng vốn đang gửi:** <span style='color:#2e7d32; font-size:18px'>{total_goc:,.0f} VND</span>", unsafe_allow_html=True)
        
        if not fund_data.empty:
            # Render thêm cột Ngân hàng ra bảng hiển thị
            display_df = fund_data[['Ngân hàng', 'Ngày gửi', 'Kỳ hạn', 'Lãi suất (%)', 'Tiền gốc (VND)']]
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
        st.divider()

    with st.expander("➕ Thêm khoản gửi tiết kiệm mới"):
        with st.form("new_deposit_form"):
            new_fund = st.selectbox("Chọn Quỹ", ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"])
            new_amount = st.number_input("Số tiền (VND)", min_value=0, step=1000000)
            
            # Tổ chức lại layout 2 cột x 2 dòng để hiển thị tốt trên màn hình dọc của điện thoại
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                new_date = st.date_input("Ngày gửi")
                new_term = st.selectbox("Kỳ hạn", ["1 Tháng", "3 Tháng", "6 Tháng", "12 Tháng"])
            with col_d2:
                new_bank = st.selectbox("Ngân hàng", ["Techcombank (TCB)", "Vietcombank (VCB)", "BIDV", "VietinBank", "MBBank", "Khác"])
                new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, format="%.1f")
                
            if st.form_submit_button("Lưu Khoản Gửi"):
                st.success(f"Đã lưu khoản gửi {new_amount:,.0f} VND tại {new_bank} vào {new_fund}!")
