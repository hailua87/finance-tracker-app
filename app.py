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

# 2. HALLMARK CUSTOM CSS INJECTION
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

BANK_ACCOUNTS = ["VCB chồng", "TCB chồng", "HSBC chồng", "UOB chồng", "UOB vợ", "TCB vợ"]
# Cập nhật danh sách kỳ hạn theo yêu cầu
TERMS = ["Không kỳ hạn", "1 Tháng", "2 Tháng", "3 Tháng", "6 Tháng", "7 Tháng", "8 Tháng", "9 Tháng", "10 Tháng", "11 Tháng", "12 Tháng", "13 Tháng", "18 Tháng", "24 Tháng", "36 Tháng"]

# 3. KHO MODAL (@st.dialog)
@st.dialog("GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    with st.form("cashflow_form", clear_on_submit=True):
        account = st.selectbox("Tài khoản nguồn", BANK_ACCOUNTS)
        category = st.selectbox("Phân loại", ["Ăn uống", "Mẹ & Bé", "Nhà cửa", "Đầu tư", "Lương/Thu nhập", "Khác"])
        amount = st.number_input("Số tiền (VND)", min_value=0, step=50000)
        note = st.text_input("Ghi chú")
        
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True):
            try:
                data = {"account": account, "amount": amount, "category": category, "note": note}
                supabase.table("cashflow").insert(data).execute()
                st.success(f"Đã lưu thành công {amount:,.0f} VND!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}")

@st.dialog("THÊM ĐỢT THANH TOÁN BĐS")
def modal_realestate():
    with st.form("realestate_form", clear_on_submit=True):
        bds_name = st.text_input("Tên dự án / Căn hộ")
        dot_tt = st.text_input("Tên đợt (Ví dụ: Đợt 4, Đợt cất nóc)")
        so_tien_tt = st.number_input("Số tiền thanh toán (VND)", min_value=0, step=10000000)
        ngay_tt = st.date_input("Hạn thanh toán")
        trang_thai = st.selectbox("Trạng thái", ["Đã thanh toán", "Chưa thanh toán"])
        if st.form_submit_button("LƯU TIẾN ĐỘ BĐS", use_container_width=True):
            st.success("Đã ghi nhận tiến độ BĐS mới!")

@st.dialog("THÊM KHOẢN VAY / TÍN DỤNG")
def modal_debt():
    with st.form("debt_form", clear_on_submit=True):
        muc_dich = st.text_input("Mục đích vay")
        ngan_hang = st.selectbox("Ngân hàng cho vay", BANK_ACCOUNTS + ["Khác"])
        du_no = st.number_input("Dư nợ gốc (VND)", min_value=0, step=10000000)
        lai_suat = st.number_input("Lãi suất (%/năm)", min_value=0.0, format="%.1f")
        goc_lai_thang = st.number_input("Tiền gốc & lãi phải trả hàng tháng (VND)", min_value=0, step=500000)
        if st.form_submit_button("LƯU KHOẢN VAY", use_container_width=True):
            st.success("Đã ghi nhận khoản vay mới!")

@st.dialog("ĐẶT LỆNH CỔ PHIẾU")
def modal_stock():
    with st.form("invest_stock_form", clear_on_submit=True):
        broker = st.selectbox("Nơi lưu ký (CTCK)", ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Khác"])
        fund_owner_stock = st.selectbox("Thuộc Portfolio", ["Daddy Funding", "Mama Funding", "Tieu Boi Funding"])
        ticker = st.text_input("Mã cổ phiếu (VD: VIB, MBB, VCI...)").upper()
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        volume = st.number_input("Khối lượng (CP)", min_value=100, step=100)
        price = st.number_input("Giá khớp (VND)", min_value=0)
        if st.form_submit_button("LƯU LỆNH", use_container_width=True):
            if ticker.strip() == "":
                st.error("Vui lòng nhập mã cổ phiếu!")
            else:
                st.success(f"Đã lưu lệnh {action} {volume} CP {ticker} qua {broker}!")

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("invest_ccq_form", clear_on_submit=True):
        platform = st.selectbox("Nền tảng giao dịch", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM"])
        fund_owner_ccq = st.selectbox("Thuộc Portfolio", ["Tieu Boi Funding", "Mama Funding", "Daddy Funding"])
        fund_ticker = st.text_input("Mã Quỹ (VD: DCDS, VESAF...)").upper()
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
        new_term = st.selectbox("Kỳ hạn", TERMS)
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

# 4. TAB ĐIỀU HƯỚNG CHÍNH
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# --- TAB 0: TỔNG QUAN ---
with tab_home:
    try:
        res_savings = supabase.table("savings").select("amount").execute()
        tong_tiet_kiem = sum([row["amount"] for row in res_savings.data]) if res_savings.data else 0
    except:
        tong_tiet_kiem = 0

    # Các thông số đã được reset về 0 để chờ kết nối DB
    tong_ccq, tong_cp, bds_da_dong, no_khoan_vay = 0, 0, 0, 0 
    
    tong_tai_san = tong_tiet_kiem + tong_ccq + tong_cp + bds_da_dong
    tai_san_rong = tong_tai_san - no_khoan_vay
    
    c_left, c_right = st.columns([1.6, 1])
    with c_left:
        st.markdown(f"""
        <div class="dashboard-card" style="border-left: 5px solid #10b981; background: linear-gradient(135deg, #111827 0%, #0f172a 100%);">
            <div class="metric-title">💰 TÀI SẢN RÒNG HIỆN TẠI (NET WORTH)</div>
            <div style="font-family: 'Space Grotesk'; font-size: 2.8rem; font-weight: 700; color: #10b981; margin: 5px 0;">
                {tai_san_rong:,.0f} ₫
            </div>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                Tổng tài sản: <b style="color: #f8fafc;">{tong_tai_san:,.0f} ₫</b> &nbsp;|&nbsp; Tổng dư nợ: <b style="color: #ef4444;">{no_khoan_vay:,.0f} ₫</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_right:
        ty_le_don_bay = (no_khoan_vay / tong_tai_san * 100) if tong_tai_san > 0 else 0
        st.markdown(f"""
        <div class="dashboard-card">
            <div class="metric-title">📊 TỶ LỆ ĐÒN BẨY TÀI CHÍNH</div>
            <div style="font-family: 'Space Grotesk'; font-size: 1.8rem; font-weight: 700; color: #f8fafc; margin: 10px 0;">
                {ty_le_don_bay:.1f}% <span style="font-size: 1rem; color: #94a3b8; font-weight: 400;">vốn vay</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("CƠ CẤU PHÂN BỔ TÀI SẢN")
    
    col_bar1, col_bar2, col_bar3, col_bar4 = st.columns(4)
    with col_bar1:
        st.metric("Tiết kiệm", f"{tong_tiet_kiem:,.0f} ₫")
    with col_bar2:
        st.metric("BĐS theo tiến độ", f"{bds_da_dong:,.0f} ₫")
    with col_bar3:
        st.metric("Chứng chỉ quỹ", f"{tong_ccq:,.0f} ₫")
    with col_bar4:
        st.metric("Cổ phiếu đầu tư", f"{tong_cp:,.0f} ₫")
    st.divider()

# --- TAB 1: DÒNG TIỀN ---
with tab_cashflow:
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("+ THÊM GIAO DỊCH MỚI", use_container_width=True):
            modal_cashflow()
            
    st.markdown("**LỊCH SỬ GIAO DỊCH (TỪ DATABASE)**")
    try:
        res_cf = supabase.table("cashflow").select("*").order("created_at", desc=True).limit(20).execute()
        if res_cf.data:
            df_cf = pd.DataFrame(res_cf.data)
            df_cf['created_at'] = pd.to_datetime(df_cf['created_at']).dt.strftime('%d/%m/%Y %H:%M')
            df_display = df_cf[['id', 'created_at', 'account', 'category', 'amount', 'note']].rename(
                columns={'created_at': 'Thời gian', 'account': 'Tài khoản', 'category': 'Phân loại', 'amount': 'Số tiền', 'note': 'Ghi chú'}
            )
            
            st.dataframe(
                df_display,
                column_config={"id": None, "Số tiền": st.column_config.NumberColumn("Số tiền (VND)", format="%d ₫")},
                use_container_width=True, hide_index=True
            )
            
            with st.expander("TÙY CHỌN: XÓA GIAO DỊCH NHẬP SAI"):
                del_id = st.selectbox("Chọn giao dịch cần xóa (Dựa theo Thời gian & Số tiền):", 
                                      df_cf['id'].tolist(), 
                                      format_func=lambda x: f"{df_cf[df_cf['id'] == x]['created_at'].values[0]} - {df_cf[df_cf['id'] == x]['amount'].values[0]:,.0f} ₫")
                if st.button("Xóa giao dịch này"):
                    supabase.table("cashflow").delete().eq("id", del_id).execute()
                    st.success("Đã xóa giao dịch!")
                    st.rerun()
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
        st.info("Danh mục Cổ phiếu hiện đang trống. Vui lòng thêm lệnh mới để bắt đầu theo dõi.")

    with subtab_ccq:
        col_btn_ccq, _ = st.columns([1, 3])
        with col_btn_ccq:
            if st.button("+ GIAO DỊCH CCQ MỚI", use_container_width=True):
                modal_ccq()
        st.info("Danh mục Chứng chỉ quỹ hiện đang trống. Vui lòng thêm giao dịch mới để bắt đầu theo dõi.")

# --- TAB 3: TIẾT KIỆM ---
with tab_savings:
    col_btn3, _ = st.columns([1, 3])
    with col_btn3:
        if st.button("+ TẠO SỔ TIẾT KIỆM MỚI", use_container_width=True):
            modal_savings()
            
    try:
        res_sav = supabase.table("savings").select("*").execute()
        df_savings = pd.DataFrame(res_sav.data) if res_sav.data else pd.DataFrame()
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

# --- TAB 4: BĐS & TÍN DỤNG ---
with tab_realestate:
    col_re_btn, col_debt_btn, _ = st.columns([1.2, 1.2, 2])
    with col_re_btn:
        if st.button("+ THÊM TIẾN ĐỘ BĐS", use_container_width=True):
            modal_realestate()
    with col_debt_btn:
        if st.button("+ THÊM KHOẢN VAY MỚI", use_container_width=True):
            modal_debt()
            
    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("Bất động sản mua theo tiến độ")
    st.info("Dữ liệu tiến độ BĐS hiện đang trống. Vui lòng thêm đợt thanh toán mới.")
    
    st.divider()
    
    st.subheader("Khoản vay tín dụng & Dư nợ")
    st.info("Dữ liệu dư nợ hiện đang trống. Vui lòng thêm khoản vay mới.")
