import streamlit as st
import pandas as pd
from datetime import date

# 1. THIẾT LẬP CẤU HÌNH CƠ BẢN
st.set_page_config(page_title="Nhà Quê Tập Chi Tiêu", layout="wide")

# 2. HALLMARK INJECTION: ÉP CUSTOM CSS (ANTI-SLOP)
st.markdown("""
<style>
    /* Import font Space Grotesk cho Số liệu & Tiêu đề, font Inter cho văn bản */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Ép font Space Grotesk cho các con số Metric và Tiêu đề để tạo cá tính Fintech */
    h1, h2, h3, .stMetricValue {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.03em;
    }
    
    /* Thiết kế lại Header chính: Căn trái, đường viền accent cứng cáp */
    .hallmark-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #f8fafc;
        border-left: 6px solid #10b981;
        padding-left: 15px;
        margin-bottom: 30px;
        margin-top: -20px;
    }
    
    /* Giấu đi tiêu đề mặc định của Streamlit để tránh lặp */
    #stHeader { display: none; }
</style>
""", unsafe_allow_html=True)

# Render Header tùy biến
st.markdown('<div class="hallmark-header">NHÀ QUÊ TẬP CHI TIÊU.</div>', unsafe_allow_html=True)

def color_profit_loss(val):
    color = '#10b981' if val > 0 else '#ef4444' if val < 0 else '#94a3b8'
    return f'color: {color}; font-weight: bold; font-family: "Space Grotesk";'

# Khai báo các Modal (Giữ nguyên logic cực mượt từ phiên bản trước)
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
        broker = st.selectbox("Nơi lưu ký (CTCK)", ["TCBS", "SSI", "VPS", "VNDirect", "Khác"])
        fund_owner_stock = st.selectbox("Thuộc Portfolio", ["Daddy Funding", "Mama Funding", "Tieu Boi Funding"])
        ticker = st.selectbox("Mã cổ phiếu", ["VIB", "VCI", "MBB", "SSI", "TPB"])
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        volume = st.number_input("Khối lượng (CP)", min_value=100, step=100)
        price = st.number_input("Giá khớp (VND)", min_value=0)
        if st.form_submit_button("LƯU LỆNH", use_container_width=True):
            st.success(f"Đã lưu lệnh qua {broker}!")

# 3. GIAO DIỆN HIỂN THỊ (VIEW)
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# --- TAB 0: TỔNG QUAN ---
with tab_home:
    # RULE HALLMARK: Bias the layout (Bẻ gãy đối xứng). Cột quan trọng nhất to nhất.
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
    # RULE HALLMARK: Layout bất đối xứng cho nút bấm (Button bên trái, tiêu đề nhỏ bên phải)
    col_btn, col_blank = st.columns([1, 3])
    with col_btn:
        if st.button("+ THÊM GIAO DỊCH MỚI", use_container_width=True):
            modal_cashflow()
            
    st.markdown("<br/>**LỊCH SỬ GIAO DỊCH**", unsafe_allow_html=True)
    st.caption("Database pending...")

# --- TAB 2: ĐẦU TƯ ---
with tab_invest:
    subtab_stock, subtab_ccq = st.tabs(["CỔ PHIẾU", "CHỨNG CHỈ QUỸ"])
    with subtab_stock:
        col_btn2, _ = st.columns([1, 3])
        with col_btn2:
            if st.button("+ LỆNH MỚI", use_container_width=True):
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

    with subtab_ccq:
        st.caption("Khu vực quản lý CCQ đang được tối ưu UI...")

# --- TAB 3: TIẾT KIỆM ---
with tab_savings:
    col_btn3, _ = st.columns([1, 3])
    with col_btn3:
        if st.button("+ TẠO SỔ TIẾT KIỆM", use_container_width=True):
            pass # Sẽ gọi modal sau
            
    st.caption("Khu vực quản lý tiết kiệm đang được tối ưu UI...")

# --- TAB 4: BĐS & TÍN DỤNG ---
with tab_realestate:
    st.caption("Đang đồng bộ dữ liệu...")
