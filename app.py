import streamlit as st
import pandas as pd
from datetime import date

# Thiết lập cấu hình trang
st.set_page_config(page_title="Nhà Quê Tập Chi Tiêu", layout="wide")

# Tiêu đề chính dạng Minimalist
st.title("NHÀ QUÊ TẬP CHI TIÊU")
st.markdown("---")

# Hàm hỗ trợ tô màu Xanh/Đỏ cho cột Lãi/Lỗ
def color_profit_loss(val):
    color = '#10b981' if val > 0 else '#ef4444' if val < 0 else '#f8fafc'
    return f'color: {color}; font-weight: bold;'

# Loại bỏ Emoji, dùng chữ In hoa để tạo cấu trúc thanh điều hướng chuẩn mực
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# --- TAB 0: TRANG CHỦ (DASHBOARD TỔNG QUAN) ---
with tab_home:
    st.header("Báo cáo Tài sản Ròng (Net Worth)")
    
    tong_tiet_kiem = 410000000 
    tong_dau_tu = 135000000    
    bds_da_dong = 800000000    
    no_bds_con_lai = 1700000000
    no_khoan_vay = 500000000   
    
    tong_tai_san = tong_tiet_kiem + tong_dau_tu + bds_da_dong
    tong_no = no_bds_con_lai + no_khoan_vay
    tai_san_rong = tong_tai_san - tong_no
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng Tài Sản", f"{tong_tai_san:,.0f} đ", "Bao gồm BĐS, Tiết kiệm, Đầu tư")
    col2.metric("Tổng Dư Nợ", f"{tong_no:,.0f} đ", "- Khoản vay & Tiến độ BĐS", delta_color="inverse")
    col3.metric("Tài Sản Ròng", f"{tai_san_rong:,.0f} đ", "Sức khỏe tài chính")
    
    st.divider()
    st.subheader("Cơ cấu Tài sản theo Portfolio")
    st.info("Tính năng vẽ biểu đồ phân bổ (Asset Allocation) sẽ được tích hợp khi kết nối Database.")

# --- TAB 1: DÒNG TIỀN ---
with tab_cashflow:
    st.header("Quản lý Dòng tiền")
    
    with st.popover("+ THÊM GIAO DỊCH", use_container_width=True):
        with st.form("cashflow_form"):
            st.write("**Ghi nhận luân chuyển tiền**")
            col1, col2 = st.columns(2)
            with col1:
                account = st.selectbox("Tài khoản", ["TK TCB Vợ", "TK TCB Chồng", "Tiền mặt"])
                amount = st.number_input("Số tiền (VND)", min_value=0, step=50000)
            with col2:
                category = st.selectbox("Phân loại", ["Ăn uống", "Mẹ & Bé", "Nhà cửa", "Đầu tư", "Trả nợ/Tiến độ", "Lương/Thu nhập", "Khác"])
                note = st.text_input("Ghi chú")
            
            if st.form_submit_button("Lưu Giao dịch"):
                st.success(f"Đã lưu {amount:,.0f} VND từ {account} vào mục {category}!")
    
    st.markdown("**Lịch sử giao dịch**")
    st.caption("Dữ liệu đang chờ đồng bộ từ cơ sở dữ liệu hệ thống.")

# --- TAB 2: ĐẦU TƯ ---
with tab_invest:
    subtab_stock, subtab_ccq = st.tabs(["CỔ PHIẾU", "CHỨNG CHỈ QUỸ"])
    
    with subtab_stock:
        with st.popover("+ ĐẶT LỆNH CỔ PHIẾU", use_container_width=True):
            with st.form("invest_stock_form"):
                col1, col2 = st.columns(2)
                with col1:
                    ticker = st.selectbox("Mã cổ phiếu", ["VIB", "VCI", "MBB", "SSI", "TPB"])
                    action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
                    fund_owner_stock = st.selectbox("Thuộc Portfolio", ["Daddy Funding", "Mama Funding", "Tieu Boi Funding"])
                with col2:
                    volume = st.number_input("Khối lượng (CP)", min_value=100, step=100)
                    price = st.number_input("Giá khớp (VND)", min_value=0)
                    
                if st.form_submit_button("Lưu Giao dịch"):
                    st.success(f"Đã {action} {volume} CP {ticker} ({fund_owner_stock})!")

        st.markdown("**Trạng thái Danh mục Cổ phiếu**")
        df_stock = pd.DataFrame({
            "Portfolio": ["Daddy Funding", "Daddy Funding", "Tieu Boi Funding"],
            "Mã CP": ["SSI", "VIB", "MBB"],
            "Khối lượng": [1000, 2500, 1500],
            "Giá vốn": [32500, 20100, 22000]
        })
        df_stock["Giá hiện tại"] = [34000, 19500, 23100]
        df_stock["Tổng vốn (VND)"] = df_stock["Khối lượng"] * df_stock["Giá vốn"]
        df_stock["Lãi/Lỗ (%)"] = ((df_stock["Giá hiện tại"] - df_stock["Giá vốn"]) / df_stock["Giá vốn"]) * 100
        
        styled_stock = df_stock.style.format({
            "Giá vốn": "{:,.0f}", "Giá hiện tại": "{:,.0f}", 
            "Tổng vốn (VND)": "{:,.0f}", "Lãi/Lỗ (%)": "{:.2f}%"
        }).map(color_profit_loss, subset=['Lãi/Lỗ (%)'])
        
        st.dataframe(styled_stock, use_container_width=True, hide_index=True)

    with subtab_ccq:
        with st.popover("+ GIAO DỊCH CCQ", use_container_width=True):
            with st.form("invest_ccq_form"):
                col1, col2 = st.columns(2)
                with col1:
                    fund_ticker = st.selectbox("Mã Quỹ", ["DCDS", "VESAF", "TCBF", "TCEF", "SSI-SCA", "VCBF-BCF", "VCBF-FIF"])
                    action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
                    fund_owner_ccq = st.selectbox("Thuộc Portfolio", ["Tieu Boi Funding", "Mama Funding", "Daddy Funding"])
                with col2:
                    volume_ccq = st.number_input("Số lượng CCQ", min_value=0.0, step=10.0, format="%.2f")
                    nav_price = st.number_input("Giá NAV (VND)", min_value=0)
                    
                if st.form_submit_button("Lưu Giao dịch"):
                    st.success(f"Đã {action_ccq} {volume_ccq} CCQ {fund_ticker} ({fund_owner_ccq})!")
                
        st.markdown("**Danh mục Chứng chỉ quỹ tích lũy**")
        df_ccq = pd.DataFrame({
            "Portfolio": ["Tieu Boi Funding", "Mama Funding", "Tieu Boi Funding", "Daddy Funding"],
            "Quỹ": ["DCDS", "TCBF", "VCBF-BCF", "VESAF"],
            "Số lượng": [1250.5, 3400.0, 500.0, 850.2],
            "Giá vốn NAV": [65000, 15200, 25500, 21000]
        })
        df_ccq["Tổng giá trị (VND)"] = df_ccq["Số lượng"] * df_ccq["Giá vốn NAV"]
        
        st.dataframe(df_ccq.style.format({"Số lượng": "{:.2f}", "Giá vốn NAV": "{:,.0f}", "Tổng giá trị (VND)": "{:,.0f}"}), use_container_width=True, hide_index=True)

# --- TAB 3: TIẾT KIỆM (FUNDING) ---
with tab_savings:
    col_header, col_btn = st.columns([2, 1])
    with col_header:
        st.header("Sổ Tiết Kiệm")
    with col_btn:
        with st.popover("+ THÊM KHOẢN GỬI", use_container_width=True):
            with st.form("new_deposit_form"):
                new_fund = st.selectbox("Chọn Portfolio", ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"])
                new_amount = st.number_input("Số tiền (VND)", min_value=0, step=1000000)
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    new_date = st.date_input("Ngày gửi")
                    new_term = st.selectbox("Kỳ hạn", ["1 Tháng", "3 Tháng", "6 Tháng", "12 Tháng"])
                with col_d2:
                    new_bank = st.selectbox("Ngân hàng", ["Techcombank (TCB)", "Vietcombank (VCB)", "BIDV", "VietinBank", "MBBank", "Khác"])
                    new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, format="%.1f")
                if st.form_submit_button("Lưu Khoản Gửi"):
                    st.success(f"Đã lưu khoản gửi {new_amount:,.0f} VND tại {new_bank}!")

    df_savings = pd.DataFrame({
        "Portfolio": ["Tieu Boi Funding", "Daddy Funding", "Mama Funding", "Tieu Boi Funding", "Mama Funding"],
        "Ngân hàng": ["TCB", "TCB", "VCB", "MBBank", "TCB"],
        "Ngày gửi": [date(2026, 1, 15), date(2026, 3, 10), date(2026, 5, 20), date(2026, 7, 10), date(2026, 6, 5)],
        "Kỳ hạn": ["6 Tháng", "12 Tháng", "3 Tháng", "12 Tháng", "6 Tháng"],
        "Lãi suất (%)": [5.0, 5.5, 4.0, 5.2, 4.8],
        "Tiền gốc (VND)": [50000000, 100000000, 150000000, 30000000, 80000000]
    })
    
    # Loại bỏ emoji trong danh sách render
    funds_info = [("Tieu Boi Funding", "Tieu Boi Funding"), ("Daddy Funding", "Daddy Funding"), ("Mama Funding", "Mama Funding")]
    for display_title, fund_name in funds_info:
        st.subheader(display_title)
        fund_data = df_savings[df_savings["Portfolio"] == fund_name].copy()
        total_goc = fund_data["Tiền gốc (VND)"].sum()
        st.markdown(f"**Tổng vốn:** <span style='color:#10b981; font-size:18px'>{total_goc:,.0f} VND</span>", unsafe_allow_html=True)
        
        if not fund_data.empty:
            st.dataframe(fund_data[['Ngân hàng', 'Ngày gửi', 'Kỳ hạn', 'Lãi suất (%)', 'Tiền gốc (VND)']].style.format({"Lãi suất (%)": "{:.1f}", "Tiền gốc (VND)": "{:,.0f}"}), use_container_width=True, hide_index=True)
        st.divider()

# --- TAB 4: BĐS & TÍN DỤNG ---
with tab_realestate:
    st.header("Bất động sản & Khoản vay")
    
    st.subheader("Căn hộ mua theo tiến độ")
    tong_gia_tri_bds = 2500000000
    da_thanh_toan = 800000000
    tien_do_phan_tram = da_thanh_toan / tong_gia_tri_bds
    
    st.caption(f"Đã thanh toán: {da_thanh_toan:,.0f} / {tong_gia_tri_bds:,.0f} VND ({tien_do_phan_tram*100:.1f}%)")
    st.progress(tien_do_phan_tram)
    
    df_tiendo = pd.DataFrame({
        "Đợt": ["Đợt 1", "Đợt 2", "Đợt 3"],
        "Ngày dự kiến": [date(2025, 12, 1), date(2026, 4, 1), date(2026, 8, 1)],
        "Số tiền (VND)": [500000000, 300000000, 200000000],
        "Trạng thái": ["Đã thanh toán", "Đã thanh toán", "Chưa thanh toán"]
    })
    st.dataframe(df_tiendo.style.format({"Số tiền (VND)": "{:,.0f}"}), use_container_width=True, hide_index=True)
    st.divider()
    
    st.subheader("Khoản vay tín dụng")
    df_vay = pd.DataFrame({
        "Mục đích vay": ["Vay tiêu dùng"],
        "Ngân hàng": ["Techcombank"],
        "Lãi suất": ["8.5%"],
        "Dư nợ gốc (VND)": [500000000],
        "Gốc & Lãi (Tháng tới)": [12500000]
    })
    st.dataframe(df_vay.style.format({"Dư nợ gốc (VND)": "{:,.0f}", "Gốc & Lãi (Tháng tới)": "{:,.0f}"}), use_container_width=True, hide_index=True)
