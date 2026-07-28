import streamlit as st
import pandas as pd
from datetime import date

# Thiết lập cấu hình trang
st.set_page_config(page_title="Nhà quê tập chi tiêu", layout="wide")

# Tiêu đề chính của ứng dụng
st.title("🌾 Nhà quê tập chi tiêu")

# Phân chia 5 tab chính (thêm Tổng quan và BĐS & Nợ)
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "🏠 Tổng quan", "💰 Dòng tiền", "📈 Đầu tư", "🏦 Tiết kiệm", "🏢 BĐS & Nợ"
])

# --- TAB 0: TRANG CHỦ (DASHBOARD TỔNG QUAN) ---
with tab_home:
    st.header("Báo cáo Tài sản Ròng (Net Worth)")
    
    # Mockup tính toán (Sau này sẽ dùng hàm sum() từ các DataFrame thực tế)
    tong_tiet_kiem = 410000000  # Tổng từ Tab Tiết kiệm
    tong_dau_tu = 135000000     # Tổng từ Cổ phiếu + CCQ
    bds_da_dong = 800000000     # Số tiền đã đóng cho căn hộ
    
    no_bds_con_lai = 1700000000 # Số tiền căn hộ chưa đóng
    no_khoan_vay = 500000000    # Dư nợ vay ngân hàng
    
    tong_tai_san = tong_tiet_kiem + tong_dau_tu + bds_da_dong
    tong_no = no_bds_con_lai + no_khoan_vay
    tai_san_rong = tong_tai_san - tong_no
    
    # Hiển thị các thẻ Metric nổi bật
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng Tài Sản (Assets)", f"{tong_tai_san:,.0f} đ", "Bao gồm BĐS, Tiết kiệm, Đầu tư")
    col2.metric("Tổng Dư Nợ (Liabilities)", f"{tong_no:,.0f} đ", "- Khoản vay & Tiến độ BĐS", delta_color="inverse")
    col3.metric("Tài Sản Ròng (Net Worth)", f"{tai_san_rong:,.0f} đ", "Sức khỏe tài chính")
    
    st.divider()
    
    # Phân bổ tài sản theo quỹ (Portfolio Overview)
    st.subheader("Cơ cấu Tài sản theo Quỹ (Tieu Boi / Daddy / Mama)")
    st.info("Tính năng vẽ biểu đồ Tròn (Pie Chart) phân bổ % tài sản cho từng quỹ sẽ được tích hợp ở bản cập nhật sau.")

# --- TAB 1: DÒNG TIỀN ---
with tab_cashflow:
    st.header("Nhập liệu Dòng tiền")
    with st.form("cashflow_form"):
        col1, col2 = st.columns(2)
        with col1:
            account = st.selectbox("Tài khoản", ["TK TCB Vợ", "TK TCB Chồng", "Tiền mặt"])
            amount = st.number_input("Số tiền (VND)", min_value=0, step=50000)
        with col2:
            category = st.selectbox("Phân loại", ["Ăn uống", "Mẹ & Bé", "Nhà cửa", "Đầu tư", "Trả nợ/Tiến độ", "Lương/Thu nhập", "Khác"])
            note = st.text_input("Ghi chú")
        
        if st.form_submit_button("Lưu Giao dịch"):
            st.success(f"Đã lưu {amount:,.0f} VND từ {account} vào mục {category}!")

# --- TAB 2: ĐẦU TƯ (Cổ phiếu & CCQ có phân bổ Quỹ) ---
with tab_invest:
    subtab_stock, subtab_ccq = st.tabs(["📈 Cổ phiếu (Stocks)", "📊 Chứng chỉ quỹ (Mutual Funds)"])
    
    with subtab_stock:
        st.subheader("Giao dịch Cổ phiếu")
        with st.form("invest_stock_form"):
            col1, col2 = st.columns(2)
            with col1:
                ticker = st.selectbox("Mã cổ phiếu", ["VIB", "VCI", "MBB", "SSI", "TPB"])
                action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
                fund_owner_stock = st.selectbox("Thuộc quỹ", ["Daddy Funding", "Mama Funding", "Tieu Boi Funding"])
            with col2:
                volume = st.number_input("Khối lượng (CP)", min_value=100, step=100)
                price = st.number_input("Giá khớp (VND)", min_value=0)
                
            if st.form_submit_button("Lưu Giao dịch"):
                st.success(f"Đã {action} {volume} CP {ticker} ({fund_owner_stock}) với giá {price:,.0f} VND!")

        st.markdown("**Trạng thái Danh mục Cổ phiếu**")
        df_stock = pd.DataFrame({
            "Thuộc quỹ": ["Daddy Funding", "Daddy Funding", "Tieu Boi Funding"],
            "Mã CP": ["SSI", "VIB", "MBB"],
            "Khối lượng": [1000, 2500, 1500],
            "Giá vốn trung bình": [32500, 20100, 22000]
        })
        df_stock["Giá hiện tại"] = [34000, 19500, 23100]
        df_stock["Tổng vốn (VND)"] = df_stock["Khối lượng"] * df_stock["Giá vốn trung bình"]
        df_stock["Lãi/Lỗ (%)"] = ((df_stock["Giá hiện tại"] - df_stock["Giá vốn trung bình"]) / df_stock["Giá vốn trung bình"]) * 100
        
        st.dataframe(df_stock.style.format({"Giá vốn trung bình": "{:,.0f}", "Giá hiện tại": "{:,.0f}", "Tổng vốn (VND)": "{:,.0f}", "Lãi/Lỗ (%)": "{:.2f}%"}), use_container_width=True, hide_index=True)

    with subtab_ccq:
        st.subheader("Giao dịch Chứng chỉ quỹ (CCQ)")
        with st.form("invest_ccq_form"):
            col1, col2 = st.columns(2)
            with col1:
                fund_ticker = st.selectbox("Mã Quỹ / Công ty", ["DCDS (Dragon Capital)", "VESAF (VinaCapital)", "TCBF (Techcom Capital)", "TCEF", "SSI-SCA", "VCBF-BCF", "VCBF-FIF"])
                action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
                fund_owner_ccq = st.selectbox("Thuộc quỹ", ["Tieu Boi Funding", "Mama Funding", "Daddy Funding"])
            with col2:
                volume_ccq = st.number_input("Số lượng CCQ", min_value=0.0, step=10.0, format="%.2f")
                nav_price = st.number_input("Giá NAV/CCQ (VND)", min_value=0)
                
            if st.form_submit_button("Lưu Giao dịch Quỹ"):
                st.success(f"Đã {action_ccq} {volume_ccq} CCQ {fund_ticker.split(' ')[0]} ({fund_owner_ccq}) với giá NAV {nav_price:,.0f} VND!")
                
        st.markdown("**Danh mục Chứng chỉ quỹ tích lũy**")
        df_ccq = pd.DataFrame({
            "Thuộc quỹ": ["Tieu Boi Funding", "Mama Funding", "Tieu Boi Funding", "Daddy Funding"],
            "Quỹ Đầu Tư": ["DCDS", "TCBF", "VCBF-BCF", "VESAF"],
            "Loại quỹ": ["Cổ phiếu", "Trái phiếu", "Cổ phiếu", "Cổ phiếu"],
            "Số lượng CCQ": [1250.5, 3400.0, 500.0, 850.2],
            "Giá vốn (NAV)": [65000, 15200, 25500, 21000]
        })
        df_ccq["Tổng giá trị (VND)"] = df_ccq["Số lượng CCQ"] * df_ccq["Giá vốn (NAV)"]
        
        st.dataframe(df_ccq.style.format({"Số lượng CCQ": "{:.2f}", "Giá vốn (NAV)": "{:,.0f}", "Tổng giá trị (VND)": "{:,.0f}"}), use_container_width=True, hide_index=True)

# --- TAB 3: TIẾT KIỆM (FUNDING) ---
with tab_savings:
    st.header("Danh mục Sổ Tiết Kiệm (Funding)")
    df_savings = pd.DataFrame({
        "Chủ quỹ": ["Tieu Boi Funding", "Daddy Funding", "Mama Funding", "Tieu Boi Funding", "Mama Funding"],
        "Ngân hàng": ["Techcombank (TCB)", "Techcombank (TCB)", "Vietcombank (VCB)", "MBBank", "Techcombank (TCB)"],
        "Ngày gửi": [date(2026, 1, 15), date(2026, 3, 10), date(2026, 5, 20), date(2026, 7, 10), date(2026, 6, 5)],
        "Kỳ hạn": ["6 Tháng", "12 Tháng", "3 Tháng", "12 Tháng", "6 Tháng"],
        "Lãi suất (%)": [5.0, 5.5, 4.0, 5.2, 4.8],
        "Tiền gốc (VND)": [50000000, 100000000, 150000000, 30000000, 80000000]
    })
    
    funds_info = [("👧 Tieu Boi Funding", "Tieu Boi Funding"), ("👨 Daddy Funding", "Daddy Funding"), ("👩 Mama Funding", "Mama Funding")]
    
    for icon_title, fund_name in funds_info:
        st.subheader(icon_title)
        fund_data = df_savings[df_savings["Chủ quỹ"] == fund_name].copy()
        total_goc = fund_data["Tiền gốc (VND)"].sum()
        st.markdown(f"**Tổng vốn đang gửi:** <span style='color:#2e7d32; font-size:18px'>{total_goc:,.0f} VND</span>", unsafe_allow_html=True)
        
        if not fund_data.empty:
            st.dataframe(fund_data[['Ngân hàng', 'Ngày gửi', 'Kỳ hạn', 'Lãi suất (%)', 'Tiền gốc (VND)']].style.format({"Lãi suất (%)": "{:.1f}", "Tiền gốc (VND)": "{:,.0f}"}), use_container_width=True, hide_index=True)
        else:
            st.caption("Chưa có khoản gửi nào.")
        st.divider()

# --- TAB 4: BĐS & TÍN DỤNG ---
with tab_realestate:
    st.header("Quản lý Bất động sản & Khoản vay")
    
    # Phần 1: Căn hộ đóng theo tiến độ
    st.subheader("🏢 Căn hộ mua theo tiến độ")
    
    tong_gia_tri_bds = 2500000000
    da_thanh_toan = 800000000
    tien_do_phan_tram = da_thanh_toan / tong_gia_tri_bds
    
    st.markdown(f"**Dự án:** Khu căn hộ Quận 7 (Mockup)")
    st.caption(f"Đã thanh toán: {da_thanh_toan:,.0f} / {tong_gia_tri_bds:,.0f} VND ({tien_do_phan_tram*100:.1f}%)")
    st.progress(tien_do_phan_tram)
    
    # Bảng lịch sử / Kế hoạch đóng tiền
    df_tiendo = pd.DataFrame({
        "Đợt": ["Đợt 1 (Ký HĐMB)", "Đợt 2", "Đợt 3 (Sắp tới)"],
        "Ngày dự kiến": [date(2025, 12, 1), date(2026, 4, 1), date(2026, 8, 1)],
        "Số tiền (VND)": [500000000, 300000000, 200000000],
        "Trạng thái": ["Đã thanh toán", "Đã thanh toán", "Chưa thanh toán"]
    })
    st.dataframe(df_tiendo.style.format({"Số tiền (VND)": "{:,.0f}"}), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Phần 2: Khoản vay ngân hàng
    st.subheader("💳 Khoản vay tín dụng")
    
    df_vay = pd.DataFrame({
        "Mục đích vay": ["Vay mua xe / Tiêu dùng"],
        "Ngân hàng": ["Techcombank"],
        "Lãi suất hiện tại": ["8.5% / năm"],
        "Dư nợ gốc (VND)": [500000000],
        "Gốc & Lãi tháng tới": [12500000]
    })
    st.dataframe(df_vay.style.format({"Dư nợ gốc (VND)": "{:,.0f}", "Gốc & Lãi tháng tới": "{:,.0f}"}), use_container_width=True, hide_index=True)
    
    with st.expander("Cập nhật thanh toán khoản vay"):
        st.write("Tính năng trừ lùi dư nợ gốc tự động sẽ được kích hoạt khi kết nối với Database.")
