import streamlit as st
import pandas as pd
from datetime import date

# 1. THIẾT LẬP CẤU HÌNH CƠ BẢN
st.set_page_config(page_title="Nhà Quê Tập Chi Tiêu", layout="wide")

# 2. HALLMARK CUSTOM CSS INJECTION (Anti-AI-Slop Design)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Ép font Space Grotesk cá tính cho tiêu đề và các chỉ số tài chính */
    h1, h2, h3, .stMetricValue {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.03em;
    }
    
    /* Header tùy biến ấn tượng */
    .hallmark-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #f8fafc;
        border-left: 6px solid #10b981;
        padding-left: 15px;
        margin-bottom: 25px;
        margin-top: -10px;
    }
    
    #stHeader { display: none; }
</style>
""", unsafe_allow_html=True)

# Render Header chính
st.markdown('<div class="hallmark-header">NHÀ QUÊ TẬP CHI TIÊU.</div>', unsafe_allow_html=True)

# Hàm hỗ trợ tô màu Lãi/Lỗ
def color_profit_loss(val):
    color = '#10b981' if val > 0 else '#ef4444' if val < 0 else '#94a3b8'
    return f'color: {color}; font-weight: bold; font-family: "Space Grotesk";'

# 3. KHO MODAL (@st.dialog) - HIỂN THỊ DẠNG POPUP TRÀN VIỀN
@st.dialog("GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    with st.form("cashflow_form", clear_on_submit=True):
        account = st.selectbox("Tài khoản nguồn", ["TK TCB Vợ", "TK TCB Chồng", "Tiền mặt"])
        category = st.selectbox("Phân loại", ["Ăn uống", "Mẹ & Bé", "Nhà cửa", "Đầu tư", "Trả nợ/Tiến độ", "Lương/Thu nhập", "Khác"])
        amount = st.number_input("Số tiền (VND)", min_value=0, step=50000)
        note = st.text_input("Ghi chú")
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True):
            st.success(f"Đã lưu {amount:,.0f} VND!")

@st.dialog("ĐẶT LỆNH CỔ PHIẾU")
def modal_stock():
    with st.form("invest_stock_form", clear_on_submit=True):
        broker = st.selectbox("Nơi lưu ký (CTCK)", ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Khác"])
        fund_owner_stock = st.selectbox("Thuộc Portfolio", ["Daddy Funding", "Mama Funding", "Tieu Boi Funding"])
        ticker = st.selectbox("Mã cổ phiếu", ["VIB", "VCI", "MBB", "SSI", "TPB"])
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        volume = st.number_input("Khối lượng (CP)", min_value=100, step=100)
        price = st.number_input("Giá khớp (VND)", min_value=0)
        if st.form_submit_button("LƯU LỆNH", use_container_width=True):
            st.success(f"Đã lưu lệnh {action} {volume} CP {ticker} qua {broker}!")

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("invest_ccq_form", clear_on_submit=True):
        platform = st.selectbox("Nền tảng giao dịch", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM"])
        fund_owner_ccq = st.selectbox("Thuộc Portfolio", ["Tieu Boi Funding", "Mama Funding", "Daddy Funding"])
        fund_ticker = st.selectbox("Mã Quỹ", ["DCDS", "VESAF", "TCBF", "TCEF", "SSI-SCA", "VCBF-BCF", "VCBF-FIF"])
        action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
        volume_ccq = st.number_input("Số lượng CCQ", min_value=0.0, step=10.0, format="%.2f")
        nav_price = st.number_input("Giá NAV (VND)", min_value=0)
        if st.form_submit_button("LƯU GIAO DỊCH QUỸ", use_container_width=True):
            st.success(f"Đã lưu lệnh {fund_ticker} qua {platform}!")

@st.dialog("THÊM KHOẢN GỬI TIẾT KIỆM")
def modal_savings():
    with st.form("new_deposit_form", clear_on_submit=True):
        new_fund = st.selectbox("Chọn Portfolio", ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"])
        new_bank = st.selectbox("Ngân hàng", ["Techcombank (TCB)", "Vietcombank (VCB)", "BIDV", "VietinBank", "MBBank", "Khác"])
        new_amount = st.number_input("Số tiền (VND)", min_value=0, step=1000000)
        new_date = st.date_input("Ngày gửi")
        new_term = st.selectbox("Kỳ hạn", ["1 Tháng", "3 Tháng", "6 Tháng", "12 Tháng"])
        new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, format="%.1f")
        if st.form_submit_button("LƯU KHOẢN GỬI", use_container_width=True):
            st.success("Đã ghi nhận sổ tiết kiệm mới!")

# 4. THANH ĐIỀU HƯỚNG BẢNG
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# --- TAB 0: TỔNG QUAN ---
with tab_home:
    # Rule Hallmark: Layout bất đối xứng [1.5, 1, 1]
    col_nw, col_asset, col_liab = st.columns([1.5, 1, 1])
    tong_tiet_kiem, tong_dau_tu, bds_da_dong = 410000000, 135000000, 800000000    
    no_bds_con_lai, no_khoan_vay = 1700000000, 500000000   
    tong_tai_san = tong_tiet_kiem + tong_dau_tu + bds_da_dong
    tong_no = no_bds_con_lai + no_khoan_vay
    tai_san_rong = tong_tai_san - tong_no
    
    with col_nw:
        st.metric("TÀI SẢN RÒNG (NET WORTH)", f"{tai_san_rong:,.0f} ₫")
    with col_asset:
        st.metric("TỔNG TÀI SẢN", f"{tong_tai_san:,.0f} ₫")
    with col_liab:
        st.metric("TỔNG DƯ NỢ", f"{tong_no:,.0f} ₫", delta_color="inverse")
    
    st.divider()

# --- TAB 1: DÒNG TIỀN ---
with tab_cashflow:
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("+ THÊM GIAO DỊCH MỚI", use_container_width=True):
            modal_cashflow()
            
    st.markdown("**LỊCH SỬ GIAO DỊCH**")
    st.caption("Dữ liệu đang chờ kết nối từ Supabase...")

# --- TAB 2: ĐẦU TƯ ---
with tab_invest:
    subtab_stock, subtab_ccq = st.tabs(["CỔ PHIẾU", "CHỨNG CHỈ QUỸ"])
    
    # 2.1 CỔ PHIẾU
    with subtab_stock:
        col_btn2, _ = st.columns([1, 3])
        with col_btn2:
            if st.button("+ LỆNH CỔ PHIẾU MỚI", use_container_width=True):
                modal_stock()
                
        df_stock = pd.DataFrame({
            "Mã CP": ["SSI", "VIB", "MBB"],
            "CTCK": ["SSI", "TCBS", "TCBS"],
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

    # 2.2 CHỨNG CHỈ QUỸ
    with subtab_ccq:
        col_btn_ccq, _ = st.columns([1, 3])
        with col_btn_ccq:
            if st.button("+ GIAO DỊCH CCQ MỚI", use_container_width=True):
                modal_ccq()
                
        st.markdown("**DANH MỤC CHỨNG CHỈ QUỸ TÍCH LŨY**")
        df_ccq = pd.DataFrame({
            "Portfolio": ["Tieu Boi Funding", "Mama Funding", "Tieu Boi Funding", "Daddy Funding"],
            "Quỹ": ["DCDS", "TCBF", "VCBF-BCF", "VESAF"],
            "Nền tảng": ["DragonX", "TCBS", "VCB Digibank", "Fmarket"],
            "Số lượng": [1250.5, 3400.0, 500.0, 850.2],
            "Giá vốn NAV": [65000, 15200, 25500, 21000]
        })
        df_ccq["Tổng giá trị (VND)"] = df_ccq["Số lượng"] * df_ccq["Giá vốn NAV"]
        st.dataframe(
            df_ccq.style.format({"Số lượng": "{:.2f}", "Giá vốn NAV": "{:,.0f}", "Tổng giá trị (VND)": "{:,.0f}"}),
            use_container_width=True, hide_index=True
        )

# --- TAB 3: TIẾT KIỆM (FUNDING PORTFOLIOS) ---
with tab_savings:
    col_btn3, _ = st.columns([1, 3])
    with col_btn3:
        if st.button("+ TẠO SỔ TIẾT KIỆM MỚI", use_container_width=True):
            modal_savings()
            
    df_savings = pd.DataFrame({
        "Portfolio": ["Tieu Boi Funding", "Daddy Funding", "Mama Funding", "Tieu Boi Funding", "Mama Funding"],
        "Ngân hàng": ["TCB", "TCB", "VCB", "MBBank", "TCB"],
        "Ngày gửi": [date(2026, 1, 15), date(2026, 3, 10), date(2026, 5, 20), date(2026, 7, 10), date(2026, 6, 5)],
        "Kỳ hạn": ["6 Tháng", "12 Tháng", "3 Tháng", "12 Tháng", "6 Tháng"],
        "Lãi suất (%)": [5.0, 5.5, 4.0, 5.2, 4.8],
        "Tiền gốc (VND)": [50000000, 100000000, 150000000, 30000000, 80000000]
    })
    
    funds_info = [("Tieu Boi Funding", "Tieu Boi Funding"), ("Daddy Funding", "Daddy Funding"), ("Mama Funding", "Mama Funding")]
    for display_title, fund_name in funds_info:
        st.subheader(display_title)
        fund_data = df_savings[df_savings["Portfolio"] == fund_name].copy()
        total_goc = fund_data["Tiền gốc (VND)"].sum()
        st.markdown(f"**Tổng vốn:** <span style='color:#10b981; font-size:18px'>{total_goc:,.0f} VND</span>", unsafe_allow_html=True)
        
        if not fund_data.empty:
            st.dataframe(
                fund_data[['Ngân hàng', 'Ngày gửi', 'Kỳ hạn', 'Lãi suất (%)', 'Tiền gốc (VND)']].style.format({"Lãi suất (%)": "{:.1f}", "Tiền gốc (VND)": "{:,.0f}"}),
                use_container_width=True, hide_index=True
            )
        st.divider()

# --- TAB 4: BĐS & TÍN DỤNG ---
with tab_realestate:
    st.header("BẤT ĐỘNG SẢN & KHOẢN VAY")
    
    st.subheader("Căn hộ mua theo tiến độ")
    tong_gia_tri_bds = 2500000000
    da_thanh_toan = 800000000
    tien_do_phan_tram = da_thanh_toan / tong_gia_tri_bds
    
    st.caption(f"Đã thanh toán: {da_thanh_toan:,.0f} / {tong_gia_tri_bds:,.0f} VND ({tien_do_phan_tram*100:.1f}%)")
    st.progress(tien_do_phan_tram)
    
    df_tiendo = pd.DataFrame({
        "Đợt": ["Đợt 1", "Đợt 2", "Đợt 3"],
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
