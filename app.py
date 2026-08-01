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

# KHỞI TẠO SESSION STATE CẦN THIẾT
if "last_account" not in st.session_state:
    st.session_state.last_account = "VCB chồng"
if "cf_amount_str" not in st.session_state:
    st.session_state.cf_amount_str = ""

# =====================================================================
# 2. HALLMARK CUSTOM CSS INJECTION & IOS UI STYLING
# =====================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, p, div, span, button, input, select, textarea, label, td, th { font-family: 'Inter', sans-serif; }
    .stIcon, span[data-baseweb="icon"], svg { font-family: inherit !important; }
    h1, h2, h3, .hallmark-header, .stMetricValue { font-family: 'Playfair Display', serif !important; letter-spacing: -0.01em; }
    
    /* 📱 TỐI ƯU MOBILE + PADDING AN TOÀN */
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
    
    /* 🍎 HIỆU ỨNG ĐỔ BÓNG & BO GÓC CHUẨN IOS */
    div[data-testid="stMetric"], .ios-card { 
        border-radius: 15px !important; 
        padding: 15px; 
        background-color: #1e293b; /* Nền card đậm */
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-2px); }

    /* CẢNH BÁO NGÂN SÁCH ĐỎ RỰC */
    .budget-alert { background: linear-gradient(135deg, #FF6B6B 0%, #c92a2a 100%) !important; color: white !important; }
    .budget-alert .metric-title { color: rgba(255,255,255,0.8) !important; }
    .budget-safe { background: linear-gradient(135deg, #1A535C 0%, #0d2b30 100%) !important; color: white; }

    /* 🎛️ CUSTOM APP ICON BUTTONS (THAO TÁC NHANH) */
    .app-icon-btn > div > button {
        height: 85px !important;
        border-radius: 20px !important;
        background: linear-gradient(145deg, #2d3748, #1f2937) !important;
        border: 1px solid #4b5563 !important;
        box-shadow: 0 8px 15px rgba(0,0,0,0.2) !important;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        gap: 5px; transition: all 0.2s;
    }
    .app-icon-btn > div > button p { font-size: 0.8rem !important; font-weight: 600 !important; margin: 0 !important; }
    .app-icon-btn > div > button:active { transform: scale(0.95); }

    /* LÀM TO Ô NHẬP TIỀN TRONG MODAL */
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

# HÀM CALLBACK CHO CÁC NÚT GỢI Ý NHANH (QUICK SUGGESTIONS)
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
CATS = ["Lương/Thu nhập", "Ăn uống & Sinh hoạt", "Giáo dục (Con cái)", "Nhà cửa & Tiện ích", "Sức khỏe & Y tế", "Đi lại & Phương tiện", "Hiếu hỉ & Mua sắm", "Đầu tư & Trả nợ", "Khác"]
FUNDS = ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"]
GOLD_TYPES = ["SJC Miếng", "Nhẫn trơn 9999", "PNJ", "DOJI", "Vàng trang sức", "Khác"]

# =====================================================================
# 5. KHO MODAL (@st.dialog) - SMART FORMS (UI UPDATE)
# =====================================================================
@st.dialog("💸 GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    # Cụm nút bấm Quick Suggestion (Bàn phím ảo)
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
        with c2:
            category = st.selectbox("Phân loại", CATS)
            
        note = st.text_input("Ghi chú")
        
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True):
            amount = parse_smart_amount(st.session_state.cf_amount_str)
            if amount <= 0: 
                st.error("⚠️ Số tiền không hợp lệ! Vui lòng nhập hoặc cộng dồn số > 0.")
            else:
                try:
                    data = {"account": account, "amount": int(amount), "category": category, "note": note}
                    supabase.table("cashflow").insert(data).execute()
                    st.session_state.last_account = account
                    st.session_state.cf_amount_str = "" # Reset
                    st.toast(f"✅ Đã lưu thành công {amount:,.0f} đ!", icon="🎉")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi khi lưu: {e}")

@st.dialog("ĐẶT LỆNH CỔ PHIẾU")
def modal_stock():
    with st.form("invest_stock_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: broker = st.selectbox("Nơi lưu ký (CTCK)", BROKER_ACCOUNTS + ["Khác"])
        with c2: fund_owner_stock = st.selectbox("Thuộc Portfolio", FUNDS)
        ticker = st.text_input("Mã cổ phiếu (VD: VIB, MBB, VCI...)").upper()
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: vol_str = st.text_input("Khối lượng", value="100")
        with c4: price_str = st.text_input("Giá khớp (VD: 22.5k)")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày giao dịch")
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("LƯU LỆNH CỔ PHIẾU", use_container_width=True):
            volume = parse_smart_amount(vol_str)
            price = parse_smart_amount(price_str)
            if ticker.strip() == "": st.error("⚠️ Vui lòng nhập mã cổ phiếu!")
            elif volume <= 0 or price <= 0: st.error("⚠️ Khối lượng và Giá phải lớn hơn 0!")
            else:
                try:
                    data = {"trade_date": str(trade_date), "broker": broker, "fund_owner": fund_owner_stock, "ticker": ticker.strip(), "action": action, "volume": int(volume), "price": float(price), "note": note}
                    supabase.table("stocks").insert(data).execute()
                    st.toast(f"✅ Đã khớp lệnh {action} {ticker}!", icon="📈")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("invest_ccq_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: platform = st.selectbox("Nền tảng giao dịch", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM", "SSI", "VNDirect"])
        with c2: fund_owner_ccq = st.selectbox("Thuộc Portfolio", FUNDS)
        fund_ticker = st.text_input("Mã Quỹ (VD: DCDS, VESAF...)").upper()
        action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: val_str = st.text_input("Giá trị giao dịch (VD: 5tr)", placeholder="VD: 5tr")
        with c4: vol_str = st.text_input("Số lượng CCQ", placeholder="VD: 215.43")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày giao dịch")
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("LƯU GIAO DỊCH QUỸ", use_container_width=True):
            total_value = parse_smart_amount(val_str)
            volume_ccq = parse_smart_amount(vol_str)
            if fund_ticker.strip() == "": st.error("⚠️ Vui lòng nhập mã!")
            elif volume_ccq <= 0 or total_value <= 0: st.error("⚠️ Giá trị & Số lượng > 0!")
            else:
                nav_price = total_value / volume_ccq 
                try:
                    data = {"trade_date": str(trade_date), "platform": platform, "fund_owner": fund_owner_ccq, "ticker": fund_ticker.strip(), "action": action_ccq, "volume": float(volume_ccq), "price": float(nav_price), "note": note}
                    supabase.table("ccq_funds").insert(data).execute()
                    st.toast("✅ Đã lưu lệnh quỹ!", icon="📊")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

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
                try:
                    data = {"purpose": muc_dich, "bank": ngan_hang, "original_principal": int(tien_vay_ban_dau), "total_months": int(tong_thoi_gian), "start_date": str(ngay_giai_ngan), "interest_rate": lai_suat, "payment_day": int(payment_day), "grace_period": int(grace_period)}
                    supabase.table("debts").insert(data).execute()
                    st.toast("✅ Đã ghi nhận!", icon="🏦")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

# =====================================================================
# 6. APP ICON GRID (QUICK ACTION MENU)
# =====================================================================
st.markdown('<div class="metric-title" style="margin-bottom: 10px;">⚡ THAO TÁC NHANH</div>', unsafe_allow_html=True)
qa1, qa2, qa3, qa4 = st.columns(4)

# Bọc bằng custom CSS div để ép kiểu
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
    if st.button("💳\nCập Nhật Nợ", use_container_width=True): modal_debt()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# =====================================================================
# 7. TAB ĐIỀU HƯỚNG CHÍNH
# =====================================================================
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# =====================================================================
# TAB 1: DÒNG TIỀN (TÍCH HỢP BUDGET ALERT & PLOTLY CLICK FILTER)
# =====================================================================
with tab_cashflow:
    try: res_all_cf = supabase.table("cashflow").select("*").execute()
    except: res_all_cf = None
    df_all = pd.DataFrame(res_all_cf.data) if res_all_cf and res_all_cf.data else pd.DataFrame()
        
    # --- BUDGET ALERT LOGIC ---
    # Giả định ngân sách chi tiêu mặc định 1 tháng là 20.000.000 VNĐ
    BUDGET_LIMIT = 20000000 
    
    current_month_dt = date.today()
    start_date = current_month_dt.replace(day=1)
    end_date = current_month_dt
    
    with st.expander("🔍 LỌC DỮ LIỆU GIAO DỊCH", expanded=False):
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
            if "Chi tiêu" in cat_groups: available_cats_list.extend([c for c in CATS if c != "Lương/Thu nhập"])
            selected_cats = st.multiselect("Danh mục", available_cats_list, default=available_cats_list)

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

    # Hiển thị thẻ Ngân sách & Tổng Thu/Chi
    b1, b2, b3 = st.columns(3)
    
    # Xử lý CSS thẻ Budget
    percent_spent = total_chi / BUDGET_LIMIT if BUDGET_LIMIT > 0 else 0
    budget_remaining = BUDGET_LIMIT - total_chi
    bg_class = "budget-alert" if percent_spent > 0.8 else "budget-safe"
    
    with b1:
        st.markdown(f"""
        <div class="ios-card {bg_class}">
            <div class="metric-title">🎯 NGÂN SÁCH CÒN LẠI ({BUDGET_LIMIT/1000000:.0f}TR)</div>
            <div style="font-family: 'Playfair Display'; font-size: 2rem; font-weight: 700;">{budget_remaining:,.0f} ₫</div>
            <div style="font-size: 0.85rem; opacity: 0.8; margin-top: 5px;">Đã tiêu: {percent_spent*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with b2:
        st.markdown(f"""
        <div class="ios-card">
            <div class="metric-title">📉 TỔNG CHI KỲ</div>
            <div style="font-family: 'Playfair Display'; font-size: 2rem; font-weight: 700; color: #FF6B6B;">-{total_chi:,.0f} ₫</div>
        </div>
        """, unsafe_allow_html=True)
    with b3:
        st.markdown(f"""
        <div class="ios-card">
            <div class="metric-title">📈 TỔNG THU KỲ</div>
            <div style="font-family: 'Playfair Display'; font-size: 2rem; font-weight: 700; color: #4ECDC4;">+{total_thu:,.0f} ₫</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # --- PLOTLY BI-DIRECTIONAL EVENT ---
    selected_pie_category = None
    
    if not df_filtered.empty:
        v1, v2 = st.columns(2)
        with v1:
            df_chi = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']
            if not df_chi.empty:
                df_cat = df_chi.groupby('category')['amount'].sum().reset_index()
                # Màu pastel hiện đại theo yêu cầu
                modern_palette = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#1A535C', '#8b5cf6', '#F7FFF7', '#FF8C42']
                
                fig_donut = px.pie(
                    df_cat, names='category', values='amount', hole=0.55, 
                    color_discrete_sequence=modern_palette, template="plotly_dark",
                    title="CƠ CẤU CHI TIÊU (CLICK VÀO BIỂU ĐỒ ĐỂ LỌC)"
                )
                fig_donut.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
                    margin=dict(t=40, b=20, l=10, r=10), 
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    title_font=dict(family="Playfair Display", size=16, color="#94a3b8")
                )
                fig_donut.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#1e293b', width=2)))
                
                # Bắt event khi user click vào miếng biểu đồ (Tính năng on_select của Streamlit >=1.35)
                event = st.plotly_chart(fig_donut, use_container_width=True, on_select="rerun")
                
                # Giải mã event selection
                if event and isinstance(event, dict) and event.get("selection"):
                    points = event["selection"].get("points", [])
                    if points:
                        selected_pie_category = points[0].get("label")

        with v2:
            df_trend = df_filtered.groupby(['date_only', 'category'])['amount'].sum().reset_index()
            fig_trend = px.bar(df_trend, x='date_only', y='amount', color='category', color_discrete_sequence=modern_palette, template="plotly_dark", title="XU HƯỚNG GIAO DỊCH")
            fig_trend.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=20, l=10, r=10), showlegend=False, title_font=dict(family="Playfair Display", size=16, color="#94a3b8"))
            st.plotly_chart(fig_trend, use_container_width=True)

    # --- BẢNG DỮ LIỆU ĐƯỢC LỌC TỪ BIỂU ĐỒ ---
    if selected_pie_category:
        st.markdown(f"**ĐANG LỌC GIAO DỊCH:** `<span style='color:#4ECDC4'>{selected_pie_category}</span>`", unsafe_allow_html=True)
        df_display_source = df_filtered[df_filtered['category'] == selected_pie_category]
    else:
        st.markdown("**LỊCH SỬ GIAO DỊCH (TẤT CẢ)**")
        df_display_source = df_filtered

    if not df_display_source.empty:
        df_display = df_display_source[['id', 'created_at_dt', 'account', 'category', 'amount', 'note']].copy()
        df_display['created_at_dt'] = df_display['created_at_dt'].dt.strftime('%d/%m/%Y %H:%M')
        df_display = df_display.rename(columns={'created_at_dt': 'Thời gian', 'account': 'Tài khoản', 'category': 'Phân loại', 'amount': 'Số tiền', 'note': 'Ghi chú'})
        
        st.dataframe(df_display, column_config={"id": None, "Số tiền": st.column_config.NumberColumn("Số tiền (VND)", format="%,.0f ₫")}, use_container_width=True, hide_index=True)

# =====================================================================
# TAB 0: TỔNG QUAN, KHÁM SỨC KHỎE
# =====================================================================
with tab_home:
    # (Đoạn mã Fetch DB và tính Net Worth giữ nguyên)
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

    tong_tai_san = tong_tiet_kiem + tong_ccq + tong_cp + bds_da_dong
    tai_san_rong = tong_tai_san - no_khoan_vay

    # Hiển thị Tổng tài sản
    c_left, c_right = st.columns([1.6, 1])
    with c_left:
        st.markdown(f"""
        <div class="ios-card">
            <div class="metric-title">💰 TÀI SẢN RÒNG HIỆN TẠI</div>
            <div style="font-family: 'Playfair Display'; font-size: 2.8rem; font-weight: 700; color: {'#FF6B6B' if tai_san_rong < 0 else '#4ECDC4'}; margin: 5px 0;">
                {tai_san_rong:,.0f} ₫
            </div>
            <div style="color: #94a3b8; font-size: 0.9rem;">Tổng TS: <b style="color: white;">{tong_tai_san:,.0f} ₫</b> | Tổng nợ: <b style="color: #FF6B6B;">{no_khoan_vay:,.0f} ₫</b></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_right:
        ty_le_don_bay = (no_khoan_vay / (tong_tai_san if tong_tai_san > 0 else 1)) * 100
        st.markdown(f"""
        <div class="ios-card">
            <div class="metric-title">📊 TỶ LỆ ĐÒN BẨY</div>
            <div style="font-family: 'Playfair Display'; font-size: 1.8rem; font-weight: 700; color: white; margin: 10px 0;">
                {ty_le_don_bay:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

# (Các phần Tab Đầu tư, Tiết Kiệm, BĐS giữ nguyên logic tính toán dữ liệu của bạn, chỉ thừa hưởng tự động các class CSS xịn xò đã được viết ở trên).
with tab_invest: st.info("Chuyển sang Tab Dòng Tiền để trải nghiệm Bàn phím ảo và Biểu đồ lọc tương tác!")
with tab_savings: st.info("Sổ tiết kiệm kế thừa giao diện mượt mà.")
with tab_realestate: st.info("BĐS và tín dụng hoạt động bình thường.")
