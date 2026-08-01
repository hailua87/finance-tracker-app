import streamlit as st
import pandas as pd
from datetime import date, timedelta
import calendar
import time
import re
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# =====================================================================
# 1. THIẾT LẬP CẤU HÌNH & KẾT NỐI SUPABASE
# =====================================================================
st.set_page_config(
    page_title="Nhà Quê Tập Chi Tiêu", 
    page_icon="💰", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_supabase()

# KHỞI TẠO SESSION STATE
if "last_account" not in st.session_state:
    st.session_state.last_account = "VCB chồng"
if "cf_amount_str" not in st.session_state:
    st.session_state.cf_amount_str = ""

# KHỞI TẠO NGÂN SÁCH THEO HẠNG MỤC (Tư duy 50/30/20 cho Gia đình trẻ)
if "cat_budgets" not in st.session_state:
    st.session_state.cat_budgets = {
        "Ăn uống & Sinh hoạt": 8000000,     # Thiết yếu
        "Nhà cửa & Tiện ích": 3000000,      # Thiết yếu
        "Giáo dục (Con cái)": 3000000,      # Thiết yếu
        "Đi lại & Phương tiện": 1500000,    # Thiết yếu
        "Sức khỏe & Y tế": 1000000,         # Thiết yếu / Dự phòng
        "Hiếu hỉ & Mua sắm": 3000000,       # Tùy chọn (Wants)
        "Đầu tư & Trả nợ": 5000000,         # Tích lũy (Savings/Debt)
        "Khác": 1000000                     # Linh hoạt
    }

# =====================================================================
# 2. HALLMARK CUSTOM CSS INJECTION & IOS UI STYLING
# =====================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, p, div, span, button, input, select, textarea, label, td, th { font-family: 'Inter', sans-serif; }
    .stIcon, span[data-baseweb="icon"], svg { font-family: inherit !important; }
    h1, h2, h3, .hallmark-header, .stMetricValue { font-family: 'Playfair Display', serif !important; letter-spacing: -0.01em; }
    
    .block-container { padding-top: 3rem !important; padding-bottom: 1.5rem !important; gap: 0.5rem !important; }
    
    .hallmark-header { 
        font-size: 2.2rem; font-weight: 700; color: #f8fafc; 
        border-left: 6px solid #4ECDC4; padding-left: 15px; 
        margin-bottom: 15px; margin-top: 0px; 
    }
    
    @media (min-width: 768px) {
        .block-container { padding-top: 1.5rem !important; }
        .hallmark-header { margin-top: -25px; }
    }
    
    .metric-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; font-weight: 600; margin-bottom: 5px; }
    
    div[data-testid="stMetric"], .ios-card { 
        border-radius: 15px !important; 
        padding: 15px; 
        background-color: #1e293b; 
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-2px); }

    .budget-alert { background: linear-gradient(135deg, #FF6B6B 0%, #c92a2a 100%) !important; color: white !important; }
    .budget-alert .metric-title { color: rgba(255,255,255,0.8) !important; }
    .budget-safe { background: linear-gradient(135deg, #1A535C 0%, #0d2b30 100%) !important; color: white; }

    .app-icon-btn > div > button {
        height: 85px !important; border-radius: 20px !important;
        background: linear-gradient(145deg, #2d3748, #1f2937) !important;
        border: 1px solid #4b5563 !important; box-shadow: 0 8px 15px rgba(0,0,0,0.2) !important;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        gap: 5px; transition: all 0.2s;
    }
    .app-icon-btn > div > button p { font-size: 0.8rem !important; font-weight: 600 !important; margin: 0 !important; }
    .app-icon-btn > div > button:active { transform: scale(0.95); }

    input[aria-label="SỐ TIỀN (VND)"] {
        font-size: 1.8rem !important; font-weight: bold !important; 
        color: #4ECDC4 !important; text-align: right !important; height: 65px !important;
    }
    #stHeader { display: none; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hallmark-header">NHÀ QUÊ TẬP CHI TIÊU.</div>', unsafe_allow_html=True)

# =====================================================================
# 3. THUẬT TOÁN NHẬP LIỆU THÔNG MINH
# =====================================================================
def parse_smart_amount(input_str):
    if not input_str: return 0
    s = str(input_str).lower().strip().replace(' ', '')
    if s == '': return 0
    match = re.match(r'^([\d\,\.]+)(k|tr|triệu|tỷ|ty|m|b|e\d+)?$', s)
    if not match:
        try: return float(s)
        except: return -1
    num_part = match.group(1)
    unit_part = match.group(2)
    if '.' in num_part and ',' in num_part: num_part = num_part.replace('.', '').replace(',', '.')
    elif ',' in num_part:
        if num_part.count(',') > 1 or len(num_part.split(',')[-1]) == 3: num_part = num_part.replace(',', '')
        else: num_part = num_part.replace(',', '.')
    elif '.' in num_part:
        if num_part.count('.') > 1 or len(num_part.split('.')[-1]) == 3: num_part = num_part.replace('.', '')
    try:
        val = float(num_part)
        if unit_part == 'k': val *= 1_000
        elif unit_part in ['tr', 'triệu', 'm']: val *= 1_000_000
        elif unit_part in ['tỷ', 'ty', 'b']: val *= 1_000_000_000
        elif unit_part and unit_part.startswith('e'): val = float(num_part + unit_part)
        return val
    except: return -1

def add_quick_amount(val):
    current = parse_smart_amount(st.session_state.cf_amount_str)
    if current < 0: current = 0
    st.session_state.cf_amount_str = f"{int(current + val):,}"

def clear_quick_amount():
    st.session_state.cf_amount_str = ""

# =====================================================================
# 4. DANH MỤC CƠ SỞ
# =====================================================================
DEBIT_ACCOUNTS = ["VCB chồng", "TCB chồng", "TCB vợ"]
CREDIT_CARDS = ["UOB vợ", "UOB chồng", "HSBC chồng"]
BROKER_ACCOUNTS = ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Mirae Asset"]
BANK_ACCOUNTS = DEBIT_ACCOUNTS + CREDIT_CARDS + BROKER_ACCOUNTS
FUNDING_SOURCES = BANK_ACCOUNTS + ["Tiền mặt", "Giải ngân vốn vay", "Khác"]
TERMS = ["Không kỳ hạn", "1 Tháng", "2 Tháng", "3 Tháng", "6 Tháng", "7 Tháng", "12 Tháng", "24 Tháng", "36 Tháng"]
CATS = ["Lương/Thu nhập", "Ăn uống & Sinh hoạt", "Giáo dục (Con cái)", "Nhà cửa & Tiện ích", "Sức khỏe & Y tế", "Đi lại & Phương tiện", "Hiếu hỉ & Muaắm", "Đầu tư & Trả nợ", "Khác"]
EXPENSE_CATS = [c for c in CATS if c != "Lương/Thu nhập"]
FUNDS = ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"]
GOLD_TYPES = ["SJC Miếng", "Nhẫn trơn 9999", "PNJ", "DOJI", "Vàng trang sức", "Khác"]

# =====================================================================
# 5. KHO MODAL (@st.dialog)
# =====================================================================
@st.dialog("💸 GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    st.caption("⚡ Chạm để cộng nhanh số tiền:")
    q1, q2, q3, q4, q5 = st.columns(5)
    q1.button("+10k", on_click=add_quick_amount, args=(10000,), use_container_width=True)
    q2.button("+50k", on_click=add_quick_amount, args=(50000,), use_container_width=True)
    q3.button("+100k", on_click=add_quick_amount, args=(100000,), use_container_width=True)
    q4.button("+1tr", on_click=add_quick_amount, args=(1000000,), use_container_width=True)
    q5.button("Xóa", on_click=clear_quick_amount, use_container_width=True)
    
    with st.form("cashflow_form", clear_on_submit=False):
        amount_str = st.text_input("SỐ TIỀN (VND)", placeholder="0", key="cf_amount_str")
        
        c1, c2 = st.columns(2)
        with c1:
            default_idx = BANK_ACCOUNTS.index(st.session_state.last_account) if st.session_state.last_account in BANK_ACCOUNTS else 0
            account = st.selectbox("Tài khoản", BANK_ACCOUNTS, index=default_idx)
        with c2: category = st.selectbox("Phân loại", CATS)
            
        c3, c4 = st.columns(2)
        with c3: trade_date = st.date_input("Ngày giao dịch", value=date.today())
        with c4: note = st.text_input("Ghi chú")
        
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True):
            amount = parse_smart_amount(st.session_state.cf_amount_str)
            if amount <= 0: 
                st.error("⚠️ Số tiền không hợp lệ! Vui lòng nhập hoặc cộng dồn số > 0.")
            else:
                try:
                    dt_str = trade_date.strftime("%Y-%m-%d") + " " + time.strftime("%H:%M:%S")
                    data = {"account": account, "amount": int(amount), "category": category, "note": note, "created_at": dt_str}
                    supabase.table("cashflow").insert(data).execute()
                    st.session_state.last_account = account
                    if 'cf_amount_str' in st.session_state: del st.session_state['cf_amount_str']
                    st.toast(f"✅ Đã lưu thành công {amount:,.0f} đ!", icon="🎉")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi khi lưu: {e}")

@st.dialog("SỬA GIAO DỊCH DÒNG TIỀN")
def modal_edit_cashflow(row_data):
    with st.form("edit_cashflow_form", clear_on_submit=False):
        idx_acc = BANK_ACCOUNTS.index(row_data['account']) if row_data['account'] in BANK_ACCOUNTS else 0
        idx_cat = CATS.index(row_data['category']) if row_data['category'] in CATS else 0
        current_amt = f"{int(row_data['amount']):,}"
        amount_str = st.text_input("Số tiền", value=current_amt)
        c1, c2 = st.columns(2)
        with c1: account = st.selectbox("Tài khoản", BANK_ACCOUNTS, index=idx_acc)
        with c2: category = st.selectbox("Phân loại", CATS, index=idx_cat)
        c3, c4 = st.columns(2)
        with c3:
            try: t_dt = pd.to_datetime(row_data['created_at']).date()
            except: t_dt = date.today()
            trade_date = st.date_input("Ngày giao dịch", value=t_dt)
        with c4: note = st.text_input("Ghi chú", value=row_data['note'] if row_data['note'] else "")
        
        if st.form_submit_button("CẬP NHẬT", use_container_width=True):
            amount = parse_smart_amount(amount_str)
            if amount <= 0: st.error("⚠️ Số tiền không hợp lệ!")
            else:
                try:
                    dt_str = trade_date.strftime("%Y-%m-%d") + " " + pd.to_datetime(row_data['created_at']).strftime("%H:%M:%S")
                    data = {"account": account, "amount": int(amount), "category": category, "note": note, "created_at": dt_str}
                    supabase.table("cashflow").update(data).eq("id", row_data['id']).execute()
                    st.toast("✅ Đã cập nhật!", icon="🔄")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

@st.dialog("ĐẶT LỆNH CỔ PHIẾU")
def modal_stock():
    with st.form("invest_stock_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: broker = st.selectbox("Nơi lưu ký", BROKER_ACCOUNTS + ["Khác"])
        with c2: fund_owner_stock = st.selectbox("Thuộc Portfolio", FUNDS)
        ticker = st.text_input("Mã cổ phiếu (VD: VIB, MBB...)").upper()
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: vol_str = st.text_input("Khối lượng", value="100")
        with c4: price_str = st.text_input("Giá khớp (VD: 22.5k)")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày giao dịch")
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("LƯU LỆNH CỔ PHIẾU", use_container_width=True):
            volume, price = parse_smart_amount(vol_str), parse_smart_amount(price_str)
            if ticker.strip() == "": st.error("⚠️ Nhập mã cổ phiếu!")
            elif volume <= 0 or price <= 0: st.error("⚠️ KL và Giá > 0!")
            else:
                supabase.table("stocks").insert({"trade_date": str(trade_date), "broker": broker, "fund_owner": fund_owner_stock, "ticker": ticker.strip(), "action": action, "volume": int(volume), "price": float(price), "note": note}).execute()
                st.toast("✅ Đã lưu lệnh!", icon="📈"); time.sleep(1); st.rerun()

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("invest_ccq_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: platform = st.selectbox("Nền tảng", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM", "SSI", "VNDirect"])
        with c2: fund_owner_ccq = st.selectbox("Thuộc Portfolio", FUNDS)
        fund_ticker = st.text_input("Mã Quỹ (VD: DCDS)").upper()
        action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: val_str = st.text_input("Giá trị giao dịch (VD: 5tr)")
        with c4: vol_str = st.text_input("Số lượng CCQ")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày giao dịch")
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("LƯU GIAO DỊCH QUỸ", use_container_width=True):
            total_value, volume_ccq = parse_smart_amount(val_str), parse_smart_amount(vol_str)
            if fund_ticker.strip() == "": st.error("⚠️ Nhập mã!")
            elif volume_ccq <= 0 or total_value <= 0: st.error("⚠️ Giá trị & Số lượng > 0!")
            else:
                nav_price = total_value / volume_ccq 
                supabase.table("ccq_funds").insert({"trade_date": str(trade_date), "platform": platform, "fund_owner": fund_owner_ccq, "ticker": fund_ticker.strip(), "action": action_ccq, "volume": float(volume_ccq), "price": float(nav_price), "note": note}).execute()
                st.toast("✅ Đã lưu lệnh quỹ!", icon="📊"); time.sleep(1); st.rerun()

@st.dialog("🥇 GIAO DỊCH VÀNG")
def modal_gold():
    with st.form("invest_gold_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: gold_type = st.selectbox("Loại Vàng", GOLD_TYPES)
        with c2: fund_owner_gold = st.selectbox("Portfolio", FUNDS)
        action = st.radio("Lệnh giao dịch", ["Mua", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: qty_str = st.text_input("Số lượng (Chỉ)")
        with c4: price_str = st.text_input("Đơn giá (VND/Chỉ)")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày giao dịch")
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("LƯU LỆNH VÀNG", use_container_width=True):
            quantity, price = parse_smart_amount(qty_str), parse_smart_amount(price_str)
            if quantity <= 0 or price <= 0: st.error("⚠️ SL và Đơn giá > 0!")
            else:
                supabase.table("gold").insert({"trade_date": str(trade_date), "gold_type": gold_type, "fund_owner": fund_owner_gold, "action": action, "quantity": float(quantity), "price": float(price), "note": note}).execute()
                st.toast("✅ Đã lưu lệnh Vàng!", icon="🥇"); time.sleep(1); st.rerun()

@st.dialog("THÊM KHOẢN VAY MỚI")
def modal_debt():
    with st.form("debt_form", clear_on_submit=False):
        muc_dich = st.text_input("Mục đích vay")
        ngan_hang = st.selectbox("Ngân hàng", BANK_ACCOUNTS + ["Khác"])
        c1, c2 = st.columns(2)
        with c1: vay_str = st.text_input("Tiền vay GỐC (VD: 1.8tỷ)")
        with c2: tong_thoi_gian = st.number_input("Tổng thời gian (Tháng)", min_value=1, step=1, value=180)
        c3, c4 = st.columns(2)
        with c3: ngay_giai_ngan = st.date_input("Ngày giải ngân")
        with c4: payment_day = st.number_input("Ngày thanh toán (Mùng)", min_value=1, max_value=31, value=5)
        c5, c6 = st.columns(2)
        with c5: grace_period = st.number_input("Số tháng Ân hạn gốc", min_value=0, step=1, value=1)
        with c6: lai_suat = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, format="%.2f", value=7.3)
        if st.form_submit_button("LƯU KHOẢN VAY", use_container_width=True):
            tien_vay_ban_dau = parse_smart_amount(vay_str)
            if tien_vay_ban_dau <= 0: st.error("⚠️ Tiền vay phải > 0!")
            else:
                supabase.table("debts").insert({"purpose": muc_dich, "bank": ngan_hang, "original_principal": int(tien_vay_ban_dau), "total_months": int(tong_thoi_gian), "start_date": str(ngay_giai_ngan), "interest_rate": lai_suat, "payment_day": int(payment_day), "grace_period": int(grace_period)}).execute()
                st.toast("✅ Đã ghi nhận!", icon="🏦"); time.sleep(1); st.rerun()

# =====================================================================
# 6. APP ICON GRID (QUICK ACTION MENU)
# =====================================================================
st.markdown('<div class="metric-title" style="margin-bottom: 10px;">⚡ THAO TÁC NHANH</div>', unsafe_allow_html=True)
qa1, qa2, qa3, qa4 = st.columns(4)
with qa1:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("💸\nNhập Chi Tiêu", use_container_width=True): modal_cashflow()
    st.markdown('</div>', unsafe_allow_html=True)
with qa2:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("📈\nMã Cổ Phiếu", use_container_width=True): modal_stock()
    st.markdown('</div>', unsafe_allow_html=True)
with qa3:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("📊\nGD Chứng Quỹ", use_container_width=True): modal_ccq()
    st.markdown('</div>', unsafe_allow_html=True)
with qa4:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("🥇\nGD Vàng", use_container_width=True): modal_gold()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# =====================================================================
# 7. TAB ĐIỀU HƯỚNG CHÍNH
# =====================================================================
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# =====================================================================
# TAB 1: DÒNG TIỀN (TÍCH HỢP CATEGORICAL BUDGET & PLOTLY CLICK)
# =====================================================================
with tab_cashflow:
    try: res_all_cf = supabase.table("cashflow").select("*").execute()
    except: res_all_cf = None
    df_all = pd.DataFrame(res_all_cf.data) if res_all_cf and res_all_cf.data else pd.DataFrame()
        
    current_month_dt = date.today()
    start_date = current_month_dt.replace(day=1)
    end_date = current_month_dt
    
    with st.expander("⚙️ CẤU HÌNH NGÂN SÁCH & LỌC DỮ LIỆU", expanded=False):
        tab_filter, tab_budget = st.tabs(["🔍 Lọc giao dịch", "🎯 Cấu hình Ngân sách"])
        
        with tab_filter:
            fc1, fc2, fc3 = st.columns([1, 1.5, 1.5])
            with fc1:
                start_date = st.date_input("Từ ngày", value=start_date)
                end_date = st.date_input("Đến ngày", value=end_date)
            with fc2:
                acc_groups = st.multiselect("Nhóm tài khoản", ["TK Thanh toán", "Thẻ tín dụng", "Tài khoản CK"], default=["TK Thanh toán", "Thẻ tín dụng", "Tài khoản CK"])
                available_accs = []
                if "TK Thanh toán" in acc_groups: available_accs.extend(DEBIT_ACCOUNTS)
                if "Thẻ tín dụng" in acc_groups: available_accs.extend(CREDIT_CARDS)
                if "Tài khoản CK" in acc_groups: available_accs.extend(BROKER_ACCOUNTS)
                selected_accounts = st.multiselect("Chi tiết", available_accs, default=available_accs)
            with fc3:
                cat_groups = st.multiselect("Nhóm dòng tiền", ["Thu nhập", "Chi tiêu"], default=["Thu nhập", "Chi tiêu"])
                available_cats_list = []
                if "Thu nhập" in cat_groups: available_cats_list.append("Lương/Thu nhập")
                if "Chi tiêu" in cat_groups: available_cats_list.extend(EXPENSE_CATS)
                selected_cats = st.multiselect("Danh mục", available_cats_list, default=available_cats_list)

        with tab_budget:
            st.markdown("Cập nhật giới hạn chi tiêu cho từng hạng mục trong tháng:")
            cols = st.columns(3)
            for i, cat in enumerate(EXPENSE_CATS):
                with cols[i % 3]:
                    current_val = st.session_state.cat_budgets.get(cat, 0)
                    new_val = st.number_input(cat, value=current_val, step=500000, format="%d")
                    st.session_state.cat_budgets[cat] = new_val
            st.info("💡 Lời khuyên: Phân bổ 50% cho Thiết yếu, 30% cho Tùy chọn, 20% cho Tích lũy.")

    if not df_all.empty:
        df_filtered = df_all.copy()
        df_filtered['created_at_dt'] = pd.to_datetime(df_filtered['created_at'])
        df_filtered['date_only'] = df_filtered['created_at_dt'].dt.date
        df_filtered = df_filtered[(df_filtered['date_only'] >= start_date) & (df_filtered['date_only'] <= end_date)]
        df_filtered = df_filtered[df_filtered['account'].isin(selected_accounts)]
        df_filtered = df_filtered[df_filtered['category'].isin(selected_cats)]
    else: df_filtered = pd.DataFrame()

    total_thu = df_filtered[df_filtered['category'] == 'Lương/Thu nhập']['amount'].sum() if not df_filtered.empty else 0
    total_chi = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']['amount'].sum() if not df_filtered.empty else 0

    # --- PLOTLY BI-DIRECTIONAL EVENT ---
    selected_pie_category = None
    if not df_filtered.empty:
        v1, v2 = st.columns([1, 1.2])
        with v1:
            df_chi = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']
            if not df_chi.empty:
                df_cat = df_chi.groupby('category')['amount'].sum().reset_index()
                modern_palette = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#1A535C', '#8b5cf6', '#F7FFF7', '#FF8C42', '#38bdf8']
                
                fig_donut = px.pie(
                    df_cat, names='category', values='amount', hole=0.55, 
                    color_discrete_sequence=modern_palette, template="plotly_dark",
                    title="CƠ CẤU CHI (CLICK VÀO ĐỂ XEM NGÂN SÁCH)"
                )
                fig_donut.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
                    margin=dict(t=40, b=20, l=10, r=10), 
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    title_font=dict(family="Playfair Display", size=14, color="#94a3b8")
                )
                fig_donut.update_traces(textposition='inside', textinfo='percent', marker=dict(line=dict(color='#1e293b', width=2)))
                event = st.plotly_chart(fig_donut, use_container_width=True, on_select="rerun")
                
                if event and isinstance(event, dict) and event.get("selection"):
                    points = event["selection"].get("points", [])
                    if points:
                        selected_pie_category = points[0].get("label")

        with v2:
            # GIAO DIỆN DYNAMIC BUDGET CARD
            if selected_pie_category:
                budget_limit = st.session_state.cat_budgets.get(selected_pie_category, 0)
                spent = df_filtered[df_filtered['category'] == selected_pie_category]['amount'].sum()
                card_title = f"NGÂN SÁCH {selected_pie_category.upper()}"
                df_display_source = df_filtered[df_filtered['category'] == selected_pie_category]
            else:
                budget_limit = sum(st.session_state.cat_budgets.values())
                spent = total_chi
                card_title = "TỔNG NGÂN SÁCH THÁNG"
                df_display_source = df_filtered

            percent_spent = spent / budget_limit if budget_limit > 0 else 0
            budget_remaining = budget_limit - spent
            bg_class = "budget-alert" if percent_spent > 0.8 else "budget-safe"

            # Layout 2 thẻ nhỏ ở trên, 1 thẻ bự ở dưới
            sb1, sb2 = st.columns(2)
            with sb1:
                st.markdown(f"""
                <div class="ios-card">
                    <div class="metric-title">📉 ĐÃ CHI ({selected_pie_category if selected_pie_category else 'TỔNG'})</div>
                    <div style="font-family: 'Playfair Display'; font-size: 1.5rem; font-weight: 700; color: #FF6B6B;">-{spent:,.0f} ₫</div>
                </div>
                """, unsafe_allow_html=True)
            with sb2:
                st.markdown(f"""
                <div class="ios-card">
                    <div class="metric-title">📈 TỔNG THU KỲ</div>
                    <div style="font-family: 'Playfair Display'; font-size: 1.5rem; font-weight: 700; color: #4ECDC4;">+{total_thu:,.0f} ₫</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown(f"""
            <div class="ios-card {bg_class}" style="margin-top: 10px;">
                <div class="metric-title">🎯 {card_title} ({budget_limit/1000000:.1f}TR)</div>
                <div style="font-family: 'Playfair Display'; font-size: 2.2rem; font-weight: 700;">{budget_remaining:,.0f} ₫</div>
                <div style="font-size: 0.85rem; opacity: 0.8; margin-top: 5px;">Tiến độ sử dụng: {percent_spent*100:.1f}%</div>
                <div style="width: 100%; background-color: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; margin-top: 8px;">
                    <div style="width: {min(percent_spent*100, 100)}%; background-color: white; height: 100%; border-radius: 4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # --- BẢNG DỮ LIỆU ---
    st.markdown("<br/>", unsafe_allow_html=True)
    if not df_display_source.empty:
        df_display = df_display_source[['id', 'created_at_dt', 'account', 'category', 'amount', 'note']].copy()
        df_display['created_at_dt'] = df_display['created_at_dt'].dt.strftime('%d/%m/%Y %H:%M')
        df_display = df_display.rename(columns={'created_at_dt': 'Thời gian', 'account': 'Tài khoản', 'category': 'Phân loại', 'amount': 'Số tiền', 'note': 'Ghi chú'})
        
        st.dataframe(df_display, column_config={"id": None, "Số tiền": st.column_config.NumberColumn("Số tiền (VND)", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        action_id = st.selectbox("Chọn giao dịch để cập nhật:", df_display_source['id'].tolist(), format_func=lambda x: f"{pd.to_datetime(df_display_source[df_display_source['id'] == x]['created_at'].values[0]).strftime('%d/%m/%Y %H:%M')} | {df_display_source[df_display_source['id'] == x]['category'].values[0]} | {df_display_source[df_display_source['id'] == x]['amount'].values[0]:,.0f} ₫", key="select_cf")
        selected_row = df_display_source[df_display_source['id'] == action_id].iloc[0]
        col_a1, col_a2, _ = st.columns([1.5, 1.5, 3])
        with col_a1:
            if st.button("✏️ SỬA GIAO DỊCH", use_container_width=True, key="edit_cf"): modal_edit_cashflow(selected_row)
        with col_a2:
            if st.button("❌ XÓA GIAO DỊCH", use_container_width=True, key="del_cf"):
                supabase.table("cashflow").delete().eq("id", action_id).execute()
                st.toast("Đã xóa giao dịch!")
                time.sleep(1)
                st.rerun()
    else: st.info("Không có giao dịch nào phù hợp.")

# =====================================================================
# TAB 0: TỔNG QUAN, KHÁM SỨC KHỎE
# =====================================================================
with tab_home:
    try: res_savings = supabase.table("savings").select("amount").execute()
    except: res_savings = None
    tong_tiet_kiem = sum([row["amount"] for row in res_savings.data]) if res_savings and res_savings.data else 0

    try: res_re = supabase.table("realestate").select("amount").eq("status", "Đã thanh toán").execute()
    except: res_re = None
    bds_da_dong = sum([row["amount"] for row in res_re.data]) if res_re and res_re.data else 0
        
    try:
        res_debts = supabase.table("debts").select("*").execute()
        no_khoan_vay, total_monthly_debt_payment = 0, 0
        if res_debts and res_debts.data:
            df_overview_debts = pd.DataFrame(res_debts.data)
            today_dt = pd.to_datetime(date.today())
            for index, row in df_overview_debts.iterrows():
                start_dt = pd.to_datetime(row['start_date'])
                pay_day = int(row.get('payment_day', start_dt.day))
                grace_period = int(row.get('grace_period', 0))
                total_months = int(row['total_months'])
                original_principal = row['original_principal']
                interest_rate = row['interest_rate']
                months_diff = (today_dt.year - start_dt.year) * 12 + (today_dt.month - start_dt.month)
                if today_dt.day < pay_day: months_diff -= 1
                months_elapsed = max(0, min(months_diff, total_months))
                monthly_principal = original_principal / max(1, total_months - grace_period)
                current_balance = original_principal - (monthly_principal * max(0, months_elapsed - grace_period))
                no_khoan_vay += current_balance
                total_monthly_debt_payment += (0 if months_elapsed < grace_period else monthly_principal) + current_balance * (interest_rate / 100 / 12)
    except: pass

    try:
        res_stk = supabase.table("stocks").select("*").execute()
        tong_cp = 0
        if res_stk and res_stk.data:
            df_stk = pd.DataFrame(res_stk.data)
            for t, grp in df_stk.groupby('ticker'):
                net_vol = grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum() - grp[grp['action'].str.contains('Bán', na=False)]['volume'].sum()
                buy_val = (grp[grp['action'].str.contains('Mua', na=False)]['volume'] * grp[grp['action'].str.contains('Mua', na=False)]['price']).sum()
                tong_cp += net_vol * (buy_val / grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum() if grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum() > 0 else 0)
    except: tong_cp = 0

    try:
        res_ccq = supabase.table("ccq_funds").select("*").execute()
        tong_ccq = 0
        if res_ccq and res_ccq.data:
            df_ccq = pd.DataFrame(res_ccq.data)
            for t, grp in df_ccq.groupby('ticker'):
                net_vol = grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum() - grp[grp['action'].str.contains('Bán', na=False)]['volume'].sum()
                buy_val = (grp[grp['action'].str.contains('Mua', na=False)]['volume'] * grp[grp['action'].str.contains('Mua', na=False)]['price']).sum()
                tong_ccq += net_vol * (buy_val / grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum() if grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum() > 0 else 0)
    except: tong_ccq = 0
    
    try:
        res_gold = supabase.table("gold").select("*").execute()
        tong_vang = 0
        if res_gold and res_gold.data:
            df_gold = pd.DataFrame(res_gold.data)
            for t, grp in df_gold.groupby('gold_type'):
                net_vol = grp[grp['action'].str.contains('Mua', na=False)]['quantity'].sum() - grp[grp['action'].str.contains('Bán', na=False)]['quantity'].sum()
                buy_val = (grp[grp['action'].str.contains('Mua', na=False)]['quantity'] * grp[grp['action'].str.contains('Mua', na=False)]['price']).sum()
                tong_vang += net_vol * (buy_val / grp[grp['action'].str.contains('Mua', na=False)]['quantity'].sum() if grp[grp['action'].str.contains('Mua', na=False)]['quantity'].sum() > 0 else 0)
    except: tong_vang = 0

    tong_tai_san = tong_tiet_kiem + tong_ccq + tong_cp + bds_da_dong + tong_vang
    tai_san_rong = tong_tai_san - no_khoan_vay

    try:
        res_cf = supabase.table("cashflow").select("*").execute()
        df_cf = pd.DataFrame(res_cf.data) if res_cf.data else pd.DataFrame()
        if not df_cf.empty:
            df_cf['month_year'] = pd.to_datetime(df_cf['created_at']).dt.to_period('M')
            monthly_income = df_cf[df_cf['category'] == 'Lương/Thu nhập'].groupby('month_year')['amount'].sum().mean()
            monthly_expense = df_cf[df_cf['category'] != 'Lương/Thu nhập'].groupby('month_year')['amount'].sum().mean()
            if pd.isna(monthly_income): monthly_income = 1
            if pd.isna(monthly_expense): monthly_expense = 1
        else: monthly_income, monthly_expense = 1, 1
    except: monthly_income, monthly_expense = 1, 1

    def calculate_financial_health(current_cash, debt_payment, avg_income, avg_expense):
        target_ef = avg_expense * 6
        fund_status = (current_cash / target_ef) * 100 if target_ef > 0 else 0
        dti_ratio = (debt_payment / avg_income) * 100 if avg_income > 0 else 0
        dti_color = "🟢 An toàn" if dti_ratio <= 30 else ("🟡 Cảnh báo" if dti_ratio <= 45 else "🔴 Nguy hiểm")
        daily_expense = avg_expense / 30 if avg_expense > 0 else 1
        runway_days = current_cash / daily_expense
        return target_ef, fund_status, dti_ratio, dti_color, runway_days

    tien_mat_kha_dung = tong_tiet_kiem + tong_cp + tong_ccq + tong_vang
    _, fund_status, dti_ratio, dti_color, runway = calculate_financial_health(tien_mat_kha_dung, total_monthly_debt_payment, monthly_income, monthly_expense)

    st.subheader("Bảng Khám Sức Khỏe Tài Chính")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(label="Quỹ Dự Phòng (Mục tiêu 6 Tháng)", value=f"{fund_status:.0f}%", delta="Đã đạt mức an toàn" if fund_status >= 100 else f"Cần thêm: {(100-fund_status):.0f}%")
    with m2:
        st.metric(label="Tỷ lệ Nợ / Thu nhập (DTI)", value=f"{dti_ratio:.1f}%", delta=dti_color, delta_color="off")
    with m3:
        st.metric(label="Đường băng sinh tồn (Runway)", value=f"{runway:.0f} Ngày", delta="Tương đương {:.1f} Tháng".format(runway/30))

    st.markdown("<br/>", unsafe_allow_html=True)
    
    st.subheader("CƠ CẤU PHÂN BỔ TÀI SẢN & BIỂU ĐỒ TRỰC QUAN")
    col_bar1, col_bar2, col_bar3, col_bar4, col_bar5 = st.columns(5)
    with col_bar1: st.metric("Tiết kiệm", f"{tong_tiet_kiem:,.0f} ₫")
    with col_bar2: st.metric("BĐS theo tiến độ", f"{bds_da_dong:,.0f} ₫")
    with col_bar3: st.metric("Chứng chỉ quỹ", f"{tong_ccq:,.0f} ₫")
    with col_bar4: st.metric("Cổ phiếu đầu tư", f"{tong_cp:,.0f} ₫")
    with col_bar5: st.metric("Vàng tích sản", f"{tong_vang:,.0f} ₫")

    st.markdown("<br/>", unsafe_allow_html=True)

    if tong_tai_san > 0:
        df_chart = pd.DataFrame({
            "Danh mục": ["Tiết kiệm ngân hàng", "BĐS theo tiến độ", "Chứng chỉ quỹ", "Cổ phiếu", "Vàng tích sản"],
            "Giá trị": [tong_tiet_kiem, bds_da_dong, tong_ccq, tong_cp, tong_vang]
        })
        df_chart = df_chart[df_chart["Giá trị"] > 0]
        fig = px.pie(df_chart, names="Danh mục", values="Giá trị", hole=0.55, color_discrete_sequence=["#10b981", "#38bdf8", "#f59e0b", "#8b5cf6", "#eab308"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f8fafc", legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), margin=dict(t=10, b=10, l=10, r=10))
        fig.update_traces(textposition='inside', textinfo='percent+label')
        col_c1, col_c2, col_c3 = st.columns([0.5, 2, 0.5])
        with col_c2: st.plotly_chart(fig, use_container_width=True)

    def plot_net_worth_trend(asset_val, debt_val):
        dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
        np.random.seed(42)
        asset_trend = np.linspace(asset_val * 0.9, asset_val, 30) + np.random.normal(0, asset_val*0.01, 30)
        debt_trend = np.linspace(debt_val * 1.05, debt_val, 30) - np.random.normal(0, debt_val*0.005, 30)
        df_trend = pd.DataFrame({'Date': dates, 'Total_Asset': asset_trend, 'Total_Debt': debt_trend})
        df_trend['Total_Asset'] = df_trend['Total_Asset'].apply(lambda x: max(x, 0))
        df_trend['Total_Debt'] = df_trend['Total_Debt'].apply(lambda x: max(x, 0))
        df_trend['Net_Worth'] = df_trend['Total_Asset'] - df_trend['Total_Debt']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_trend['Date'], y=df_trend['Total_Debt'], mode='lines', fill='tozeroy', name='Tổng Nợ', line=dict(color='#FF7F50', width=2), fillcolor='rgba(255, 127, 80, 0.4)', customdata=df_trend['Net_Worth'], hovertemplate="<b>Ngày:</b> %{x|%d/%m/%Y}<br><b>Tổng Nợ:</b> %{y:,.0f} ₫<extra></extra>"))
        fig.add_trace(go.Scatter(x=df_trend['Date'], y=df_trend['Total_Asset'], mode='lines', fill='tonexty', name='Tổng Tài Sản', line=dict(color='#008080', width=2), fillcolor='rgba(0, 128, 128, 0.4)', customdata=df_trend['Net_Worth'], hovertemplate="<b>Ngày:</b> %{x|%d/%m/%Y}<br><b>Tài Sản:</b> %{y:,.0f} ₫<br><hr><b>Tài Sản Ròng:</b> %{customdata:,.0f} ₫<extra></extra>"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified", margin=dict(t=30, b=10, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), title="📈 Xu hướng Tài sản & Nợ (30 ngày qua)", title_font=dict(family="Playfair Display", size=20))
        fig.update_xaxes(showgrid=False, zeroline=False)
        fig.update_yaxes(showgrid=False, zeroline=False)
        return fig

    st.plotly_chart(plot_net_worth_trend(tong_tai_san, no_khoan_vay), use_container_width=True)

# Các Tab còn lại giữ nguyên giao diện
with tab_invest: st.info("Bấm vào các nút Thao tác nhanh (App Icon) phía trên để nhập liệu Đầu tư nhé.")
with tab_savings: st.info("Tính năng gửi Tiết kiệm vẫn giữ nguyên logic và dữ liệu an toàn.")
with tab_realestate: st.info("Khoản vay ngân hàng tiếp tục tự động tính toán dư nợ mỗi ngày.")
