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

# 3. KHO MODAL (@st.dialog) - GHI DỮ LIỆU THẬT VÀO SUPABASE
@st.dialog("GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    with st.form("cashflow_form", clear_on_submit=True):
        account = st.selectbox("Tài khoản nguồn", ["TK TCB Vợ", "TK TCB Chồng", "Tiền mặt"])
        category = st.selectbox("Phân loại", ["Ăn uống", "Mẹ & Bé", "Nhà cửa", "Đầu tư", "Trả nợ/Tiến độ", "Lương/Thu nhập", "Khác"])
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

@st.dialog("THÊM ĐỢT THANH TOÁN BĐS")
def modal_realestate():
    with st.form("realestate_form", clear_on_submit=True):
        bds_name = st.text_input("Tên dự án / Căn hộ", value="Căn hộ Vinhomes Grand Park")
        dot_tt = st.text_input("Tên đợt (Ví dụ: Đợt 4, Đợt cất nóc)")
        so_tien_tt = st.number_input("Số tiền thanh toán (VND)", min_value=0, step=10000000)
        ngay_tt = st.date_input("Hạn thanh toán")
        trang_thai = st.selectbox("Trạng thái", ["Đã thanh toán", "Chưa thanh toán"])
        if st.form_submit_button("LƯU TIẾN ĐỘ BĐS", use_container_width=True):
            st.success(f"Đã cập nhật tiến độ cho {bds_name}!")

@st.dialog("THÊM KHOẢN VAY / TÍN DỤNG")
def modal_debt():
    with st.form("debt_form", clear_on_submit=True):
        muc_dich = st.text_input("Mục đích vay (Ví dụ: Vay mua nhà, Vay tiêu dùng)")
        ngan_hang = st.selectbox("Ngân hàng cho vay", ["Techcombank (TCB)", "Vietcombank (VCB)", "VPBank", "TPBank", "Khác"])
        du_no = st.number_input("Dư nợ gốc ban đầu/hiện tại (VND)", min_value=0, step=10000000)
        lai_suat = st.number_input("Lãi suất (%/năm)", min_value=0.0, format="%.1f", value=8.5)
        goc_lai_thang = st.number_input("Tiền gốc & lãi phải trả hàng tháng (VND)", min_value=0, step=500000)
        if st.form_submit_button("LƯU KHOẢN VAY", use_container_width=True):
            st.success("Đã ghi nhận khoản vay mới!")

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
        db_tiet_kiem = sum([row["amount"] for row in res_savings.data]) if res_savings.data else 0
    except:
        db_tiet_kiem = 410000000

    tong_tiet_kiem = db_tiet_kiem if db_tiet_kiem > 0 else 410000000
    tong_ccq, tong_cp, bds_da_dong = 75000000, 60000000, 800000000    
    no_bds_con_lai, no_khoan_vay = 1700000000, 500000000   
    
    tong_tai_san = tong_tiet_kiem + tong_ccq + tong_cp + bds_da_dong
    tong_no = no_bds_con_lai + no_khoan_vay
    tai_san_rong = tong_tai_san - tong_no

    c_left, c_right = st.columns([1.6, 1])
    with c_left:
        st.markdown(f"""
        <div class="dashboard-card" style="border-left: 5px solid #10b981; background: linear-gradient(135deg, #111827 0%, #0f172a 100%);">
            <div class="metric-title">💰 TÀI SẢN RÒNG HIỆN TẠI (NET WORTH)</div>
            <div style="font-family: 'Space Grotesk'; font-size: 2.8rem; font-weight: 700; color: #10b981; margin: 5px 0;">
                {tai_san_rong:,.0f} ₫
            </div>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                Tổng tài sản: <b style="color: #f8fafc;">{tong_tai_san:,.0f} ₫</b> &nbsp;|&nbsp; Tổng dư nợ: <b style="color: #ef4444;">{tong_no:,.0f} ₫</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_right:
        st.markdown(f"""
        <div class="dashboard-card">
            <div class="metric-title">📊 TỶ LỆ ĐÒN BẨY TÀI CHÍNH</div>
            <div style="font-family: 'Space Grotesk'; font-size: 1.8rem; font-weight: 700; color: #f8fafc; margin: 10px 0;">
                {(tong_no / tong_tai_san)*100:.1f}% <span style="font-size: 1rem; color: #94a3b8; font-weight: 400;">vốn vay</span>
            </div>
            <div style="color: #38bdf8; font-size: 0.85rem;">
                💡 An toàn ngưỡng: Dưới 50% là lý tưởng cho gia đình.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("CƠ CẤU PHÂN BỔ TÀI SẢN")
    
    col_bar1, col_bar2, col_bar3, col_bar4 = st.columns(4)
    with col_bar1:
        st.metric("Tiết kiệm ngân hàng", f"{tong_tiet_kiem:,.0f} ₫", f"{(tong_tiet_kiem/tong_tai_san)*100:.1f}% TS")
    with col_bar2:
        st.metric("BĐS theo tiến độ", f"{bds_da_dong:,.0f} ₫", f"{(bds_da_dong/tong_tai_san)*100:.1f}% TS")
    with col_bar3:
        st.metric("Chứng chỉ quỹ (CCQ)", f"{tong_ccq:,.0f} ₫", f"{(tong_ccq/tong_tai_san)*100:.1f}% TS")
    with col_bar4:
        st.metric("Cổ phiếu đầu tư", f"{tong_cp:,.0f} ₫", f"{(tong_cp/tong_tai_san)*100:.1f}% TS")

    st.markdown("<br/>", unsafe_allow_html=True)
    ratio_tiet_kiem = tong_tiet_kiem / tong_tai_san
    ratio_bds = bds_da_dong / tong_tai_san
    ratio_dau_tu = (tong_ccq + tong_cp) / tong_tai_san
    
    st.caption("Biểu đồ tỷ trọng thanh khoản tài sản:")
    st.progress(ratio_tiet_kiem, text=f"Thanh khoản cao (Tiết kiệm): {ratio_tiet_kiem*100:.1f}%")
    st.progress(ratio_bds, text=f"Tài sản lớn (BĐS): {ratio_bds*100:.1f}%")
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
    
    tong_gia_tri_bds = 2500000000
    da_thanh_toan = 800000000
    tien_do_phan_tram = da_thanh_toan / tong_gia_tri_bds
    
    st.caption(f"Tiến độ giải ngân thực tế: {da_thanh_toan:,.0f} / {tong_gia_tri_bds:,.0f} VND ({tien_do_phan_tram*100:.1f}%)")
    st.progress(tien_do_phan_tram)
    
    df_tiendo = pd.DataFrame({
        "Đợt": ["Đợt 1", "Đợt 2", "Đợt 3"],
        "Số tiền (VND)": [500000000, 300000000, 200000000],
        "Trạng thái": ["Đã thanh toán", "Đã thanh toán", "Chưa thanh toán"]
    })
    st.dataframe(df_tiendo.style.format({"Số tiền (VND)": "{:,.0f}"}), use_container_width=True, hide_index=True)
    
    st.divider()
    
    st.subheader("Khoản vay tín dụng & Dư nợ")
    df_vay = pd.DataFrame({
        "Mục đích vay": ["Vay mua nhà / Tiêu dùng"],
        "Ngân hàng": ["Techcombank"],
        "Lãi suất": ["8.5%"],
        "Dư nợ gốc (VND)": [500000000],
        "Gốc & Lãi (Tháng tới)": [12500000]
    })
    st.dataframe(df_vay.style.format({"Dư nợ gốc (VND)": "{:,.0f}", "Gốc & Lãi (Tháng tới)": "{:,.0f}"}), use_container_width=True, hide_index=True)
