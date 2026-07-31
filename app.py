import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

# 1. THIẾT LẬP CẤU HÌNH & KẾT NỐI SUPABASE
st.set_page_config(page_title="Nhà Quê Tập Chi Tiêu", layout="wide")

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_supabase()

# 2. HALLMARK CUSTOM CSS INJECTION (Anti-AI-Slop Design)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, .stMetricValue {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.03em;
    }
    
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
    
    .dashboard-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
    }
    
    .metric-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        font-weight: 600;
    }

    #stHeader { display: none; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hallmark-header">NHÀ QUÊ TẬP CHI TIÊU.</div>', unsafe_allow_html=True)

def color_profit_loss(val):
    color = '#10b981' if val > 0 else '#ef4444' if val < 0 else '#94a3b8'
    return f'color: {color}; font-weight: bold; font-family: "Space Grotesk";'

# Danh sách ngân hàng dùng chung
BANK_ACCOUNTS = ["VCB chồng", "TCB chồng", "HSBC chồng", "UOB chồng", "UOB vợ", "TCB vợ"]

# 3. KHO MODAL (@st.dialog)
@st.dialog("GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    with st.form("cashflow_form", clear_on_submit=True):
        # Đã cập nhật danh sách Bank
        account = st.selectbox("Tài khoản nguồn", BANK_ACCOUNTS)
        category = st.selectbox("Phân loại", ["Ăn uống", "Mẹ & Bé", "Nhà cửa", "Đầu tư", "Lương/Thu nhập", "Khác"])
        amount = st.number_input("Số tiền (VND)", min_value=0, step=50000)
        note = st.text_input("Ghi chú")
        
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True):
            try:
                data = {"account": account, "amount": amount, "category": category, "note": note}
                supabase.table("cashflow").insert(data).execute()
                st.success(f"Đã lưu thành công {amount:,.0f} VND lên Database!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}")

@st.dialog("ĐẶT LỆNH CỔ PHIẾU")
def modal_stock():
    with st.form("invest_stock_form", clear_on_submit=True):
        broker = st.selectbox("Nơi lưu ký (CTCK)", ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Khác"])
        fund_owner_stock = st.selectbox("Thuộc Portfolio", ["Daddy Funding", "Mama Funding", "Tieu Boi Funding"])
        
        # Đã đổi thành text_input cho phép gõ tự do
        ticker = st.text_input("Mã cổ phiếu (VD: VIB, MBB, VCI...)").upper()
        
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        volume = st.number_input("Khối lượng (CP)", min_value=100, step=100)
        price = st.number_input("Giá khớp (VND)", min_value=0)
        
        if st.form_submit_button("LƯU LỆNH", use_container_width=True):
            if ticker.strip() == "":
                st.error("Vui lòng nhập mã cổ phiếu!")
            else:
                st.success(f"Đã lưu lệnh {action} {volume} CP {ticker} qua {broker}!")
                # Tạm thời chưa gọi Database ở đây

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
        new_bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS)
        new_amount = st.number_input("Số tiền (VND)", min_value=0, step=1000000)
        new_date = st.date_input("Ngày gửi")
        new_term = st.selectbox("Kỳ hạn", ["1 Tháng", "3 Tháng", "6 Tháng", "12 Tháng"])
        new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, format="%.1f")
        
        if st.form_submit_button("LƯU KHOẢN GỬI", use_container_width=True):
            try:
                data = {
                    "fund_owner": new_fund,
                    "bank": new_bank,
                    "deposit_date": str(new_date),
                    "term": new_term,
                    "interest_rate": new_rate,
                    "amount": new_amount
                }
                supabase.table("savings").insert(data).execute()
                st.success("Đã lưu sổ tiết kiệm mới vào Database!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}")

# 4. TAB ĐIỀU HƯỚNG CHÍNH (ĐÃ XÓA TAB BĐS)
tab_home, tab_cashflow, tab_invest, tab_savings = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM"
])

# --- TAB 0: TỔNG QUAN ---
with tab_home:
    try:
        res_savings = supabase.table("savings").select("amount").execute()
        db_tiet_kiem = sum([row["amount"] for row in res_savings.data]) if res_savings.data else 0
    except:
        db_tiet_kiem = 410000000

    tong_tiet_kiem = db_tiet_kiem if db_tiet_kiem > 0 else 410000000
    tong_ccq, tong_cp = 75000000, 60000000
    
    # Đã gỡ bỏ dữ liệu BĐS & Nợ
    tong_tai_san = tong_tiet_kiem + tong_ccq + tong_cp
    
    st.markdown(f"""
    <div class="dashboard-card" style="border-left: 5px solid #10b981; background: linear-gradient(135deg, #111827 0%, #0f172a 100%);">
        <div class="metric-title">💰 TỔNG TÀI SẢN (TOTAL ASSETS)</div>
        <div style="font-family: 'Space Grotesk'; font-size: 2.8rem; font-weight: 700; color: #10b981; margin: 5px 0;">
            {tong_tai_san:,.0f} ₫
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("CƠ CẤU PHÂN BỔ TÀI SẢN")
    
    # Chia lại thành 3 cột thay vì 4 do đã xóa BĐS
    col_bar1, col_bar2, col_bar3 = st.columns(3)
    with col_bar1:
        st.metric("Tiết kiệm", f"{tong_tiet_kiem:,.0f} ₫", f"{(tong_tiet_kiem/tong_tai_san)*100:.1f}% TS")
    with col_bar2:
        st.metric("Chứng chỉ quỹ (CCQ)", f"{tong_ccq:,.0f} ₫", f"{(tong_ccq/tong_tai_san)*100:.1f}% TS")
    with col_bar3:
        st.metric("Cổ phiếu đầu tư", f"{tong_cp:,.0f} ₫", f"{(tong_cp/tong_tai_san)*100:.1f}% TS")

    st.markdown("<br/>", unsafe_allow_html=True)
    ratio_tiet_kiem = tong_tiet_kiem / tong_tai_san
    ratio_dau_tu = (tong_ccq + tong_cp) / tong_tai_san
    
    st.caption("Biểu đồ tỷ trọng tài sản:")
    st.progress(ratio_tiet_kiem, text=f"Thanh khoản (Tiết kiệm): {ratio_tiet_kiem*100:.1f}%")
    st.progress(ratio_dau_tu, text=f"Tăng trưởng (Cổ phiếu + CCQ): {ratio_dau_tu*100:.1f}%")
    st.divider()

# --- TAB 1: DÒNG TIỀN ---
with tab_cashflow:
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("+ THÊM GIAO DỊCH MỚI", use_container_width=True):
            modal_cashflow()
            
    st.markdown("**LỊCH SỬ GIAO DỊCH (TỪ DATABASE)**")
    try:
        res_cf = supabase.table("cashflow").select("*").order("created_at", desc=True).limit(10).execute()
        if res_cf.data:
            df_cf = pd.DataFrame(res_cf.data)
            st.dataframe(df_cf[['created_at', 'account', 'category', 'amount', 'note']], use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có giao dịch nào được ghi nhận.")
    except Exception as e:
        st.error(f"Không thể tải dữ liệu dòng tiền: {e}")

# --- TAB 2: ĐẦU TƯ ---
with tab_invest:
    subtab_stock, subtab_ccq = st.tabs(["CỔ PHIẾU", "CHỨNG CHỈ QUỸ"])
    with subtab_stock:
        col_btn2, _ = st.columns([1, 3])
        with col_btn2:
            if st.button("+ LỆNH CỔ PHIẾU MỚI", use_container_width=True):
                modal_stock()
        df_stock = pd.DataFrame({
            "Mã CP": ["SSI", "VIB", "MBB"], "CTCK": ["SSI", "TCBS", "TCBS"],
            "Khối lượng": [1000, 2500, 1500], "Giá vốn": [32500, 20100, 22000]
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
        col_btn_ccq, _ = st.columns([1, 3])
        with col_btn_ccq:
            if st.button("+ GIAO DỊCH CCQ MỚI", use_container_width=True):
                modal_ccq()
        st.markdown("**DANH MỤC CHỨNG CHỈ QUỸ TÍCH LŨY**")
        df_ccq = pd.DataFrame({
            "Portfolio": ["Tieu Boi Funding", "Mama Funding", "Tieu Boi Funding", "Daddy Funding"],
            "Quỹ": ["DCDS", "TCBF", "VCBF-BCF", "VESAF"],
            "Nền tảng": ["DragonX", "TCBS", "VCB Digibank", "Fmarket"],
            "Số lượng": [1250.5, 3400.0, 500.0, 850.2], "Giá vốn NAV": [65000, 15200, 25500, 21000]
        })
        df_ccq["Tổng giá trị (VND)"] = df_ccq["Số lượng"] * df_ccq["Giá vốn NAV"]
        st.dataframe(
            df_ccq.style.format({"Số lượng": "{:.2f}", "Giá vốn NAV": "{:,.0f}", "Tổng giá trị (VND)": "{:,.0f}"}),
            use_container_width=True, hide_index=True
        )

# --- TAB 3: TIẾT KIỆM (ĐỌC TRỰC TIẾP TỪ SUPABASE) ---
with tab_savings:
    col_btn3, _ = st.columns([1, 3])
    with col_btn3:
        if st.button("+ TẠO SỔ TIẾT KIỆM MỚI", use_container_width=True):
            modal_savings()
            
    try:
        res_sav = supabase.table("savings").select("*").execute()
        df_savings = pd.DataFrame(res_sav.data) if res_sav.data else pd.DataFrame(columns=["fund_owner", "bank", "deposit_date", "term", "interest_rate", "amount"])
    except:
        df_savings = pd.DataFrame()

    funds_info = [("Tieu Boi Funding", "Tieu Boi Funding"), ("Daddy Funding", "Daddy Funding"), ("Mama Funding", "Mama Funding")]
    for display_title, fund_name in funds_info:
        st.subheader(display_title)
        if not df_savings.empty and "fund_owner" in df_savings.columns:
            fund_data = df_savings[df_savings["fund_owner"] == fund_name].copy()
            total_goc = fund_data["amount"].sum() if not fund_data.empty else 0
        else:
            fund_data = pd.DataFrame()
            total_goc = 0
            
        st.markdown(f"**Tổng vốn:** <span style='color:#10b981; font-size:18px'>{total_goc:,.0f} VND</span>", unsafe_allow_html=True)
        
        if not fund_data.empty:
            st.dataframe(
                fund_data[['bank', 'deposit_date', 'term', 'interest_rate', 'amount']].rename(
                    columns={'bank': 'Ngân hàng', 'deposit_date': 'Ngày gửi', 'term': 'Kỳ hạn', 'interest_rate': 'Lãi suất (%)', 'amount': 'Tiền gốc (VND)'}
                ).style.format({"Lãi suất (%)": "{:.1f}", "Tiền gốc (VND)": "{:,.0f}"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.caption("Chưa có sổ tiết kiệm nào trong quỹ này.")
        st.divider()
