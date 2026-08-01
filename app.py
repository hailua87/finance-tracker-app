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

# 1. THIẾT LẬP CẤU HÌNH & KẾT NỐI SUPABASE
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

# 2. KHỞI TẠO SESSION STATE
if "last_account" not in st.session_state:
    st.session_state.last_account = "VCB chồng"

# 3. HALLMARK CUSTOM CSS INJECTION & MODERN UI ENHANCEMENTS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Inter:wght@400;500;600&display=swap');
    
    html, body, p, div, span, button, input, select, textarea, label, td, th { font-family: 'Inter', sans-serif; }
    .stIcon, span[data-baseweb="icon"], svg { font-family: inherit !important; }
    h1, h2, h3, .hallmark-header, .stMetricValue { font-family: 'Playfair Display', serif !important; letter-spacing: -0.01em; }
    
    /* 📱 TỐI ƯU CHO MOBILE: Đẩy padding top xuống để tránh tai thỏ (Notch) / Status bar */
    .block-container { 
        padding-top: 3rem !important; 
        padding-bottom: 1.5rem !important; 
        gap: 0.5rem !important; 
    }
    
    .hallmark-header { 
        font-size: 2.2rem; font-weight: 700; color: #f8fafc; 
        border-left: 6px solid #10b981; padding-left: 15px; 
        margin-bottom: 15px; 
        margin-top: 0px; 
    }
    
    /* 💻 TỐI ƯU CHO PC/LAPTOP: Tự động thu gọn lại khoảng cách */
    @media (min-width: 768px) {
        .block-container { padding-top: 1.5rem !important; }
        .hallmark-header { margin-top: -25px; }
    }
    
    .metric-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; font-weight: 600; }
    
    div[data-testid="metric-container"] { 
        border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.2); 
        padding: 15px; background-color: rgba(16, 185, 129, 0.03); 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
    }
    
    #stHeader { display: none; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hallmark-header">NHÀ QUÊ TẬP CHI TIÊU.</div>', unsafe_allow_html=True)

# --- THUẬT TOÁN NHẬP LIỆU THÔNG MINH (SMART PARSER) ---
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
    
    if '.' in num_part and ',' in num_part:
        num_part = num_part.replace('.', '').replace(',', '.')
    elif ',' in num_part:
        if num_part.count(',') > 1 or len(num_part.split(',')[-1]) == 3:
            num_part = num_part.replace(',', '')
        else:
            num_part = num_part.replace(',', '.')
    elif '.' in num_part:
        if num_part.count('.') > 1 or len(num_part.split('.')[-1]) == 3:
            num_part = num_part.replace('.', '')
            
    try:
        val = float(num_part)
        if unit_part == 'k': val *= 1_000
        elif unit_part in ['tr', 'triệu', 'm']: val *= 1_000_000
        elif unit_part in ['tỷ', 'ty', 'b']: val *= 1_000_000_000
        elif unit_part and unit_part.startswith('e'): 
            val = float(num_part + unit_part)
        return val
    except:
        return -1

# --- DANH MỤC CƠ SỞ ---
DEBIT_ACCOUNTS = ["VCB chồng", "TCB chồng", "TCB vợ"]
CREDIT_CARDS = ["UOB vợ", "UOB chồng", "HSBC chồng"]
BROKER_ACCOUNTS = ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Mirae Asset"]

BANK_ACCOUNTS = DEBIT_ACCOUNTS + CREDIT_CARDS + BROKER_ACCOUNTS
FUNDING_SOURCES = BANK_ACCOUNTS + ["Tiền mặt", "Giải ngân vốn vay", "Khác"]
TERMS = ["Không kỳ hạn", "1 Tháng", "2 Tháng", "3 Tháng", "6 Tháng", "7 Tháng", "8 Tháng", "9 Tháng", "10 Tháng", "11 Tháng", "12 Tháng", "13 Tháng", "18 Tháng", "24 Tháng", "36 Tháng"]

CATS = ["Lương/Thu nhập", "Ăn uống & Sinh hoạt", "Giáo dục (Con cái)", "Nhà cửa & Tiện ích", "Sức khỏe & Y tế", "Đi lại & Phương tiện", "Hiếu hỉ & Mua sắm", "Đầu tư & Trả nợ", "Khác"]
FUNDS = ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"]
GOLD_TYPES = ["SJC Miếng", "Nhẫn trơn 9999", "PNJ", "DOJI", "Vàng trang sức", "Khác"]

# =====================================================================
# 4. KHO MODAL (@st.dialog) - SMART FORMS
# =====================================================================

@st.dialog("💸 GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    with st.form("cashflow_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            default_idx = BANK_ACCOUNTS.index(st.session_state.last_account) if st.session_state.last_account in BANK_ACCOUNTS else 0
            account = st.selectbox("Tài khoản nguồn", BANK_ACCOUNTS, index=default_idx)
        with c2:
            category = st.selectbox("Phân loại", CATS)
            
        amount_str = st.text_input("Số tiền (Hỗ trợ nhập tắt: 1,5tr, 500k, 1e6)", placeholder="VD: 50k, 1.5tr, 2000000")
        note = st.text_input("Ghi chú")
        
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True):
            amount = parse_smart_amount(amount_str)
            if amount <= 0: 
                st.error("⚠️ Số tiền không hợp lệ! Vui lòng nhập số lớn hơn 0.")
            else:
                try:
                    data = {"account": account, "amount": int(amount), "category": category, "note": note}
                    supabase.table("cashflow").insert(data).execute()
                    st.session_state.last_account = account
                    st.toast(f"✅ Đã lưu thành công {amount:,.0f} đ!", icon="🎉")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi khi lưu: {e}")

@st.dialog("SỬA GIAO DỊCH DÒNG TIỀN")
def modal_edit_cashflow(row_data):
    with st.form("edit_cashflow_form", clear_on_submit=True):
        idx_acc = BANK_ACCOUNTS.index(row_data['account']) if row_data['account'] in BANK_ACCOUNTS else 0
        idx_cat = CATS.index(row_data['category']) if row_data['category'] in CATS else 0
        
        c1, c2 = st.columns(2)
        with c1: account = st.selectbox("Tài khoản nguồn", BANK_ACCOUNTS, index=idx_acc)
        with c2: category = st.selectbox("Phân loại", CATS, index=idx_cat)
            
        current_amt = f"{int(row_data['amount']):,}"
        amount_str = st.text_input("Số tiền (Hỗ trợ nhập tắt: 1.5tr, 500k)", value=current_amt)
        note = st.text_input("Ghi chú", value=row_data['note'] if row_data['note'] else "")
        
        if st.form_submit_button("CẬP NHẬT", use_container_width=True):
            amount = parse_smart_amount(amount_str)
            if amount <= 0: st.error("⚠️ Số tiền không hợp lệ!")
            else:
                try:
                    data = {"account": account, "amount": int(amount), "category": category, "note": note}
                    supabase.table("cashflow").update(data).eq("id", row_data['id']).execute()
                    st.toast("✅ Đã cập nhật thành công!", icon="🔄")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

@st.dialog("ĐẶT LỆNH MUA / BÁN CỔ PHIẾU")
def modal_stock():
    with st.form("invest_stock_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: broker = st.selectbox("Nơi lưu ký (CTCK)", BROKER_ACCOUNTS + ["Khác"])
        with c2: fund_owner_stock = st.selectbox("Thuộc Portfolio", FUNDS)
            
        ticker = st.text_input("Mã cổ phiếu (VD: VIB, MBB, VCI...)").upper()
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        
        c3, c4 = st.columns(2)
        with c3: vol_str = st.text_input("Khối lượng (VD: 1k, 500)", value="100")
        with c4: price_str = st.text_input("Giá khớp / Giá vốn TB (VD: 22.5k)", placeholder="Nhập giá...")
            
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày giao dịch")
        with c6: note = st.text_input("Ghi chú", placeholder="VD: Mua mới")
            
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
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi khi lưu lệnh: {e}")

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("invest_ccq_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: platform = st.selectbox("Nền tảng giao dịch", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM", "SSI", "VNDirect"])
        with c2: fund_owner_ccq = st.selectbox("Thuộc Portfolio", FUNDS)
            
        fund_ticker = st.text_input("Mã Quỹ (VD: DCDS, VESAF...)").upper()
        action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
        
        c3, c4 = st.columns(2)
        with c3: vol_str = st.text_input("Số lượng CCQ (Lẻ thập phân)", value="10.0")
        with c4: price_str = st.text_input("Giá NAV (VD: 25.4k, 25400)", placeholder="Nhập giá NAV...")
            
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày giao dịch")
        with c6: note = st.text_input("Ghi chú", placeholder="VD: Đầu tư SIP hàng tháng")
            
        if st.form_submit_button("LƯU GIAO DỊCH QUỸ", use_container_width=True):
            volume_ccq = parse_smart_amount(vol_str)
            nav_price = parse_smart_amount(price_str)
            
            if fund_ticker.strip() == "": st.error("⚠️ Vui lòng nhập mã quỹ!")
            elif volume_ccq <= 0 or nav_price <= 0: st.error("⚠️ Số lượng và Giá NAV phải hợp lệ!")
            else:
                try:
                    data = {"trade_date": str(trade_date), "platform": platform, "fund_owner": fund_owner_ccq, "ticker": fund_ticker.strip(), "action": action_ccq, "volume": float(volume_ccq), "price": float(nav_price), "note": note}
                    supabase.table("ccq_funds").insert(data).execute()
                    st.toast(f"✅ Đã lưu lệnh {fund_ticker}!", icon="📊")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

@st.dialog("🥇 GIAO DỊCH MUA / BÁN VÀNG")
def modal_gold():
    with st.form("invest_gold_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: gold_type = st.selectbox("Loại Vàng", GOLD_TYPES)
        with c2: fund_owner_gold = st.selectbox("Thuộc Portfolio", FUNDS)
            
        action = st.radio("Lệnh giao dịch", ["Mua", "Bán"], horizontal=True)
        
        c3, c4 = st.columns(2)
        with c3: qty_str = st.text_input("Số lượng (Chỉ)", placeholder="VD: 5 (chỉ) hoặc 10 (chỉ)")
        with c4: price_str = st.text_input("Giá vốn / Đơn giá (VND/Chỉ)", placeholder="VD: 7.5tr, 7500k hoặc 8tr")
            
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày giao dịch")
        with c6: note = st.text_input("Ghi chú", placeholder="VD: Mua tích sản tháng 8")
            
        if st.form_submit_button("LƯU LỆNH VÀNG", use_container_width=True):
            quantity = parse_smart_amount(qty_str)
            price = parse_smart_amount(price_str)
            
            if quantity <= 0 or price <= 0:
                st.error("⚠️ Số lượng và Đơn giá mua/bán vàng phải lớn hơn 0!")
            else:
                try:
                    data = {"trade_date": str(trade_date), "gold_type": gold_type, "fund_owner": fund_owner_gold, "action": action, "quantity": float(quantity), "price": float(price), "note": note}
                    supabase.table("gold").insert(data).execute()
                    st.toast(f"✅ Đã ghi nhận lệnh {action} {quantity} chỉ vàng {gold_type}!", icon="🥇")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi khi lưu lệnh vàng: {e}. Vui lòng tạo bảng 'gold' trên Supabase.")

@st.dialog("THÊM KHOẢN GỬI TIẾT KIỆM")
def modal_savings():
    with st.form("new_deposit_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1: new_fund = st.selectbox("Chọn Portfolio", FUNDS)
        with c2: new_bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS)
            
        amount_str = st.text_input("Số tiền gốc (VD: 50tr, 100tr)", placeholder="Nhập tiền gốc...")
        
        c3, c4 = st.columns(2)
        with c3: new_date = st.date_input("Ngày gửi")
        with c4: new_term = st.selectbox("Kỳ hạn", TERMS)
            
        new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, format="%.2f")
        
        if st.form_submit_button("LƯU KHOẢN GỬI", use_container_width=True):
            new_amount = parse_smart_amount(amount_str)
            if new_amount <= 0: st.error("⚠️ Vui lòng nhập số tiền gốc hợp lệ!")
            else:
                try:
                    data = {"fund_owner": new_fund, "bank": new_bank, "deposit_date": str(new_date), "term": new_term, "interest_rate": new_rate, "amount": int(new_amount)}
                    supabase.table("savings").insert(data).execute()
                    st.toast("✅ Đã lưu sổ tiết kiệm mới!", icon="💰")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi khi lưu: {e}")

@st.dialog("SỬA KHOẢN GỬI TIẾT KIỆM")
def modal_edit_savings(row_data):
    with st.form("edit_deposit_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            idx_fund = FUNDS.index(row_data['fund_owner']) if row_data['fund_owner'] in FUNDS else 0
            new_fund = st.selectbox("Chọn Portfolio", FUNDS, index=idx_fund)
        with c2:
            idx_bank = BANK_ACCOUNTS.index(row_data['bank']) if row_data['bank'] in BANK_ACCOUNTS else 0
            new_bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS, index=idx_bank)
            
        current_amt = f"{int(row_data['amount']):,}"
        amount_str = st.text_input("Số tiền gốc", value=current_amt)
        
        c3, c4 = st.columns(2)
        with c3:
            try: dep_dt = pd.to_datetime(row_data['deposit_date']).date()
            except: dep_dt = date.today()
            new_date = st.date_input("Ngày gửi", value=dep_dt)
        with c4:
            idx_term = TERMS.index(row_data['term']) if row_data['term'] in TERMS else 0
            new_term = st.selectbox("Kỳ hạn", TERMS, index=idx_term)
            
        new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, format="%.2f", value=float(row_data['interest_rate']))
        
        if st.form_submit_button("CẬP NHẬT SỔ TIẾT KIỆM", use_container_width=True):
            new_amount = parse_smart_amount(amount_str)
            if new_amount <= 0: st.error("⚠️ Vui lòng nhập số tiền gốc hợp lệ!")
            else:
                try:
                    data = {"fund_owner": new_fund, "bank": new_bank, "deposit_date": str(new_date), "term": new_term, "interest_rate": new_rate, "amount": int(new_amount)}
                    supabase.table("savings").update(data).eq("id", row_data['id']).execute()
                    st.toast("✅ Đã cập nhật thành công!", icon="🔄")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi khi lưu: {e}")

@st.dialog("THÊM ĐỢT THANH TOÁN BĐS")
def modal_realestate():
    try:
        res = supabase.table("realestate").select("project_name, contract_value").execute()
        existing_projects = {row['project_name']: row.get('contract_value', 0) for row in res.data} if res.data else {}
    except: existing_projects = {}
        
    project_opts = list(existing_projects.keys()) + ["➕ Thêm dự án mới..."]
    choice = st.selectbox("Chọn Dự án / Căn hộ", project_opts)
    
    if choice == "➕ Thêm dự án mới...":
        bds_name = st.text_input("Nhập tên dự án mới (VD: TT Avio B.30.05)")
        gia_tri_str = st.text_input("Giá trị hợp đồng (VD: 1.5tỷ, 1500tr)", placeholder="Nhập giá trị...")
        gia_tri_hd = parse_smart_amount(gia_tri_str)
    else:
        bds_name = choice
        gia_tri_hd = existing_projects[choice]
        st.info(f"💡 Giá trị hợp đồng của dự án này: **{gia_tri_hd:,.0f} ₫**")
        
    st.markdown("---")
    dot_tt = st.text_input("Tên đợt thanh toán (VD: Đợt 4 - Cất nóc)")
    
    c1, c2 = st.columns(2)
    with c1: tien_tt_str = st.text_input("Số tiền thanh toán (VD: 50tr)")
    with c2: nguon_tien = st.selectbox("Nguồn tiền", FUNDING_SOURCES)
        
    c3, c4 = st.columns(2)
    with c3: ngay_tt = st.date_input("Hạn thanh toán")
    with c4: trang_thai = st.selectbox("Trạng thái", ["Chưa thanh toán", "Đã thanh toán"])
        
    ghi_chu = st.text_input("Ghi chú (Tùy chọn)")
    
    if st.button("LƯU TIẾN ĐỘ BĐS", use_container_width=True):
        so_tien_tt = parse_smart_amount(tien_tt_str)
        if not bds_name.strip() or not dot_tt.strip(): st.error("⚠️ Vui lòng nhập tên dự án và đợt thanh toán!")
        elif so_tien_tt <= 0 or gia_tri_hd <= 0: st.error("⚠️ Vui lòng nhập số tiền thanh toán / Giá trị HĐ hợp lệ!")
        else:
            try:
                data = {"project_name": bds_name, "contract_value": int(gia_tri_hd), "installment_name": dot_tt, "amount": int(so_tien_tt), "funding_source": nguon_tien, "due_date": str(ngay_tt), "status": trang_thai, "note": ghi_chu}
                supabase.table("realestate").insert(data).execute()
                st.rerun()
            except Exception as e: st.error(f"Lỗi: {e}")

@st.dialog("THÊM / CẤU HÌNH KHOẢN VAY NGÂN HÀNG")
def modal_debt():
    with st.form("debt_form", clear_on_submit=False):
        muc_dich = st.text_input("Mục đích vay (VD: Mua chung cư Q7)")
        ngan_hang = st.selectbox("Ngân hàng cho vay", BANK_ACCOUNTS + ["Khác"])
        
        st.markdown("**Thông số giải ngân & Thời hạn**")
        c1, c2 = st.columns(2)
        with c1: vay_str = st.text_input("Tổng tiền vay GỐC (VD: 1.8tỷ)", placeholder="1.8tỷ")
        with c2: tong_thoi_gian = st.number_input("Tổng thời gian vay (Tháng)", min_value=1, step=1, format="%d", value=180)
            
        st.markdown("**Thông số thanh toán (Ân hạn & Ngày TT)**")
        c3, c4 = st.columns(2)
        with c3: ngay_giai_ngan = st.date_input("Ngày giải ngân (Bắt đầu tính nợ)")
        with c4: payment_day = st.number_input("Ngày thanh toán hàng tháng", min_value=1, max_value=31, value=5)
        
        c5, c6 = st.columns(2)
        with c5: grace_period = st.number_input("Số tháng Ân hạn gốc", min_value=0, step=1, value=1)
        with c6: lai_suat = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, format="%.2f", value=7.3)
            
        st.info("💡 Hệ thống tự động xử lý thuật toán ân hạn gốc và tính dư nợ theo ngày thanh toán cố định.")
        
        if st.form_submit_button("LƯU KHOẢN VAY", use_container_width=True):
            tien_vay_ban_dau = parse_smart_amount(vay_str)
            if tien_vay_ban_dau <= 0: st.error("⚠️ Số tiền vay không hợp lệ!")
            else:
                try:
                    data = {
                        "purpose": muc_dich, "bank": ngan_hang, "original_principal": int(tien_vay_ban_dau),
                        "total_months": int(tong_thoi_gian), "start_date": str(ngay_giai_ngan), "interest_rate": lai_suat,
                        "payment_day": int(payment_day), "grace_period": int(grace_period)
                    }
                    supabase.table("debts").insert(data).execute()
                    st.toast("✅ Đã ghi nhận khoản vay!", icon="🏦")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

@st.dialog("SỬA KHOẢN VAY")
def modal_edit_debt(row_data):
    with st.form("edit_debt_form", clear_on_submit=False):
        muc_dich = st.text_input("Mục đích vay", value=row_data['purpose'])
        bank_opts = BANK_ACCOUNTS + ["Khác"]
        idx_bank = bank_opts.index(row_data['bank']) if row_data['bank'] in bank_opts else 0
        ngan_hang = st.selectbox("Ngân hàng cho vay", bank_opts, index=idx_bank)
        
        c1, c2 = st.columns(2)
        with c1: 
            current_amt = f"{int(row_data['original_principal']):,}"
            vay_str = st.text_input("Tổng tiền vay BAN ĐẦU", value=current_amt)
        with c2: 
            tong_thoi_gian = st.number_input("Tổng thời gian (Tháng)", min_value=1, step=1, value=int(row_data['total_months']))
            
        c3, c4 = st.columns(2)
        with c3:
            try: start_dt = pd.to_datetime(row_data['start_date']).date()
            except: start_dt = date.today()
            ngay_giai_ngan = st.date_input("Ngày giải ngân", value=start_dt)
        with c4:
            lai_suat = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, format="%.3f", value=float(row_data['interest_rate']))
            
        if st.form_submit_button("CẬP NHẬT KHOẢN VAY", use_container_width=True):
            tien_vay_ban_dau = parse_smart_amount(vay_str)
            if tien_vay_ban_dau <= 0: st.error("⚠️ Tiền vay phải lớn hơn 0!")
            else:
                try:
                    data = {"purpose": muc_dich, "bank": ngan_hang, "original_principal": int(tien_vay_ban_dau), "total_months": int(tong_thoi_gian), "start_date": str(ngay_giai_ngan), "interest_rate": lai_suat}
                    supabase.table("debts").update(data).eq("id", row_data['id']).execute()
                    st.toast("✅ Đã cập nhật!", icon="🔄")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

@st.dialog("CẤU HÌNH SỐ DƯ GỐC BAN ĐẦU")
def modal_opening_balance():
    with st.form("opening_balance_form"):
        try:
            res = supabase.table("opening_balances").select("*").execute()
            old_data = {row['account']: row['balance'] for row in res.data} if res.data else {}
        except: old_data = {}
            
        balances = {}
        tab_debit, tab_broker, tab_credit = st.tabs(["💳 Thanh toán", "📈 Chứng khoán", "💳 Tín dụng"])
        
        with tab_debit:
            for i in range(0, len(DEBIT_ACCOUNTS), 2):
                c1, c2 = st.columns(2)
                with c1:
                    acc1 = DEBIT_ACCOUNTS[i]
                    balances[acc1] = st.number_input(f"{acc1}", step=100000, format="%d", value=int(old_data.get(acc1, 0)), key=f"ob_{acc1}")
                with c2:
                    if i + 1 < len(DEBIT_ACCOUNTS):
                        acc2 = DEBIT_ACCOUNTS[i+1]
                        balances[acc2] = st.number_input(f"{acc2}", step=100000, format="%d", value=int(old_data.get(acc2, 0)), key=f"ob_{acc2}")
                        
        with tab_broker:
            for i in range(0, len(BROKER_ACCOUNTS), 2):
                c1, c2 = st.columns(2)
                with c1:
                    acc1 = BROKER_ACCOUNTS[i]
                    balances[acc1] = st.number_input(f"{acc1} (Tiền mặt)", step=100000, format="%d", value=int(old_data.get(acc1, 0)), key=f"ob_{acc1}")
                with c2:
                    if i + 1 < len(BROKER_ACCOUNTS):
                        acc2 = BROKER_ACCOUNTS[i+1]
                        balances[acc2] = st.number_input(f"{acc2} (Tiền mặt)", step=100000, format="%d", value=int(old_data.get(acc2, 0)), key=f"ob_{acc2}")
                        
        with tab_credit:
            for i in range(0, len(CREDIT_CARDS), 2):
                c1, c2 = st.columns(2)
                with c1:
                    acc1 = CREDIT_CARDS[i]
                    balances[acc1] = st.number_input(f"{acc1} (Dư nợ)", step=100000, format="%d", value=int(old_data.get(acc1, 0)), key=f"ob_{acc1}")
                with c2:
                    if i + 1 < len(CREDIT_CARDS):
                        acc2 = CREDIT_CARDS[i+1]
                        balances[acc2] = st.number_input(f"{acc2} (Dư nợ)", step=100000, format="%d", value=int(old_data.get(acc2, 0)), key=f"ob_{acc2}")
            
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.form_submit_button("LƯU SỐ DƯ GỐC", use_container_width=True):
            try:
                for acc, bal in balances.items():
                    supabase.table("opening_balances").upsert({"account": acc, "balance": int(bal)}, on_conflict="account").execute()
                st.rerun()
            except Exception as e: st.error(f"Lỗi: {e}")

# =====================================================================
# 5. QUICK ACTION MENU (OPTIMIZED FOR MOBILE)
# =====================================================================
st.markdown("### ⚡ Thao tác nhanh")
qa1, qa2, qa3, qa4 = st.columns(4)
with qa1:
    if st.button("💸 Nhập Chi Tiêu", use_container_width=True): modal_cashflow()
with qa2:
    if st.button("📈 Thêm Mã CK", use_container_width=True): modal_stock()
with qa3:
    if st.button("📊 Giao dịch Quỹ", use_container_width=True): modal_ccq()
with qa4:
    if st.button("💳 Cập Nhật Nợ", use_container_width=True): modal_debt()

st.divider()

# =====================================================================
# 6. TAB ĐIỀU HƯỚNG CHÍNH
# =====================================================================
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# =====================================================================
# TAB 0: TỔNG QUAN & KHÁM SỨC KHỎE TÀI CHÍNH
# =====================================================================
with tab_home:
    try:
        res_savings = supabase.table("savings").select("amount").execute()
        tong_tiet_kiem = sum([row["amount"] for row in res_savings.data]) if res_savings.data else 0
    except: tong_tiet_kiem = 0
        
    try:
        res_re_total = supabase.table("realestate").select("amount").eq("status", "Đã thanh toán").execute()
        bds_da_dong = sum([row["amount"] for row in res_re_total.data]) if res_re_total.data else 0
    except: bds_da_dong = 0
        
    try:
        res_debts = supabase.table("debts").select("*").execute()
        no_khoan_vay = 0
        total_monthly_debt_payment = 0
        if res_debts.data:
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
                principal_paying_months = max(1, total_months - grace_period)
                monthly_principal = original_principal / principal_paying_months
                months_paid_principal = max(0, months_elapsed - grace_period)
                current_balance = original_principal - (monthly_principal * months_paid_principal)
                no_khoan_vay += current_balance
                
                is_grace_active = (months_elapsed < grace_period)
                current_monthly_principal = 0 if is_grace_active else monthly_principal
                monthly_interest = current_balance * (interest_rate / 100 / 12)
                total_monthly_debt_payment += (current_monthly_principal + monthly_interest)
    except:
        no_khoan_vay = 0
        total_monthly_debt_payment = 0

    # FIX LOGIC: Dùng .str.contains('Mua') thay vì == 'Mua'
    tong_cp = 0
    try:
        res_stk = supabase.table("stocks").select("*").execute()
        if res_stk.data:
            df_stk = pd.DataFrame(res_stk.data)
            for ticker, grp in df_stk.groupby('ticker'):
                buy_rows = grp[grp['action'].str.contains('Mua', na=False, case=False)]
                sell_rows = grp[grp['action'].str.contains('Bán', na=False, case=False)]
                buy_vol = buy_rows['volume'].sum()
                sell_vol = sell_rows['volume'].sum()
                net_vol = buy_vol - sell_vol
                buy_val = (buy_rows['volume'] * buy_rows['price']).sum()
                avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                tong_cp += net_vol * avg_price
    except: tong_cp = 0

    tong_ccq = 0
    try:
        res_fund = supabase.table("ccq_funds").select("*").execute()
        if res_fund.data:
            df_fund = pd.DataFrame(res_fund.data)
            for ticker, grp in df_fund.groupby('ticker'):
                buy_rows = grp[grp['action'].str.contains('Mua', na=False, case=False)]
                sell_rows = grp[grp['action'].str.contains('Bán', na=False, case=False)]
                buy_vol = buy_rows['volume'].sum()
                sell_vol = sell_rows['volume'].sum()
                net_vol = buy_vol - sell_vol
                buy_val = (buy_rows['volume'] * buy_rows['price']).sum()
                avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                tong_ccq += net_vol * avg_price
    except: tong_ccq = 0

    tong_vang = 0
    try:
        res_gold = supabase.table("gold").select("*").execute()
        if res_gold.data:
            df_gold = pd.DataFrame(res_gold.data)
            for gtype, grp in df_gold.groupby('gold_type'):
                buy_rows = grp[grp['action'].str.contains('Mua', na=False, case=False)]
                sell_rows = grp[grp['action'].str.contains('Bán', na=False, case=False)]
                buy_vol = buy_rows['quantity'].sum()
                sell_vol = sell_rows['quantity'].sum()
                net_vol = buy_vol - sell_vol
                buy_val = (buy_rows['quantity'] * buy_rows['price']).sum()
                avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                tong_vang += net_vol * avg_price
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

# =====================================================================
# TAB 1: DÒNG TIỀN
# =====================================================================
with tab_cashflow:
    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
        if st.button("➕ THÊM GIAO DỊCH MỚI", use_container_width=True): modal_cashflow()
    with col_btn2:
        if st.button("⚙️ CẬP NHẬT SỐ DƯ ĐẦU KỲ", use_container_width=True): modal_opening_balance()
            
    st.markdown("<br/>", unsafe_allow_html=True)
    
    try:
        res_all_cf = supabase.table("cashflow").select("*").execute()
        df_all = pd.DataFrame(res_all_cf.data) if res_all_cf.data else pd.DataFrame()
    except: df_all = pd.DataFrame()
        
    default_start = date(2026, 8, 1)
    default_end = date.today()
    
    with st.expander("🔍 BỘ LỌC ĐA CHIỀU (DRILL-DOWN FILTER)", expanded=False):
        fc1, fc2, fc3 = st.columns([1, 1.5, 1.5])
        with fc1:
            start_date = st.date_input("Từ ngày", value=default_start)
            end_date = st.date_input("Đến ngày", value=default_end)
        with fc2:
            acc_groups = st.multiselect("1. Nhóm tài khoản", ["TK Thanh toán", "Thẻ tín dụng", "Tài khoản CK"], default=["TK Thanh toán", "Thẻ tín dụng", "Tài khoản CK"])
            available_accs = []
            if "TK Thanh toán" in acc_groups: available_accs.extend(DEBIT_ACCOUNTS)
            if "Thẻ tín dụng" in acc_groups: available_accs.extend(CREDIT_CARDS)
            if "Tài khoản CK" in acc_groups: available_accs.extend(BROKER_ACCOUNTS)
            selected_accounts = st.multiselect("↳ Tài khoản chi tiết", available_accs, default=available_accs)
        with fc3:
            cat_groups = st.multiselect("2. Nhóm dòng tiền", ["Thu nhập", "Chi tiêu"], default=["Thu nhập", "Chi tiêu"])
            available_cats_list = []
            if "Thu nhập" in cat_groups: available_cats_list.append("Lương/Thu nhập")
            if "Chi tiêu" in cat_groups: available_cats_list.extend([c for c in CATS if c != "Lương/Thu nhập"])
            selected_cats = st.multiselect("↳ Danh mục chi tiết", available_cats_list, default=available_cats_list)

    if not df_all.empty:
        df_filtered = df_all.copy()
        df_filtered['created_at_dt'] = pd.to_datetime(df_filtered['created_at'])
        df_filtered['date_only'] = df_filtered['created_at_dt'].dt.date
        df_filtered = df_filtered[(df_filtered['date_only'] >= start_date) & (df_filtered['date_only'] <= end_date)]
        df_filtered = df_filtered[df_filtered['account'].isin(selected_accounts)]
        df_filtered = df_filtered[df_filtered['category'].isin(selected_cats)]
    else: df_filtered = pd.DataFrame()

    try:
        res_ob = supabase.table("opening_balances").select("*").execute()
        base_opening = {row['account']: row['balance'] for row in res_ob.data} if res_ob.data else {}
    except: base_opening = {}

    try:
        res_prior = supabase.table("cashflow").select("*").lt("created_at", str(start_date)).execute()
        df_prior = pd.DataFrame(res_prior.data) if res_prior.data else pd.DataFrame()
    except: df_prior = pd.DataFrame()

    total_debit_opening = 0
    total_credit_opening = 0

    for acc in selected_accounts:
        base_val = base_opening.get(acc, 0.0)
        if not df_prior.empty and 'account' in df_prior.columns:
            acc_prior = df_prior[df_prior['account'] == acc]
            if not acc_prior.empty:
                thu_prior = acc_prior[acc_prior['category'] == 'Lương/Thu nhập']['amount'].sum()
                chi_prior = acc_prior[acc_prior['category'] != 'Lương/Thu nhập']['amount'].sum()
                base_val = base_val + thu_prior - chi_prior
                
        if acc in DEBIT_ACCOUNTS or acc in BROKER_ACCOUNTS: total_debit_opening += base_val
        elif acc in CREDIT_CARDS: total_credit_opening += base_val

    if not df_filtered.empty:
        total_thu = df_filtered[df_filtered['category'] == 'Lương/Thu nhập']['amount'].sum()
        total_chi = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']['amount'].sum()
        dong_tien_thuan = total_thu - total_chi
    else: total_thu, total_chi, dong_tien_thuan = 0, 0, 0

    tong_quy = (total_debit_opening + dong_tien_thuan) - total_credit_opening

    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    with kc1:
        with st.container(border=True):
            st.markdown('<div class="metric-title">🏦 TK THANH TOÁN & CK</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: #38bdf8;'>{total_debit_opening:,.0f} ₫</div>", unsafe_allow_html=True)
    with kc2:
        with st.container(border=True):
            st.markdown('<div class="metric-title">💳 DƯ NỢ TÍN DỤNG</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: #ef4444;'>-{total_credit_opening:,.0f} ₫</div>", unsafe_allow_html=True)
    with kc3:
        with st.container(border=True):
            st.markdown('<div class="metric-title">📈 TỔNG THU KỲ</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: #10b981;'>+{total_thu:,.0f} ₫</div>", unsafe_allow_html=True)
    with kc4:
        with st.container(border=True):
            st.markdown('<div class="metric-title">📉 TỔNG CHI KỲ</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: #ef4444;'>-{total_chi:,.0f} ₫</div>", unsafe_allow_html=True)
    with kc5:
        with st.container(border=True):
            st.markdown('<div class="metric-title">⚖️ TỔNG QUỸ RÒNG</div>', unsafe_allow_html=True)
            color_dt = "#10b981" if tong_quy >= 0 else "#ef4444"
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: {color_dt};'>{tong_quy:,.0f} ₫</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    if not df_filtered.empty:
        viz1, viz2 = st.columns(2)
        with viz1:
            df_filtered['Ngay'] = df_filtered['created_at_dt'].dt.strftime('%d/%m/%Y')
            df_filtered['Loại giao dịch'] = df_filtered['category'].apply(lambda x: 'Thu nhập' if x == 'Lương/Thu nhập' else 'Chi tiêu')
            df_trend = df_filtered.groupby(['Ngay', 'Loại giao dịch'])['amount'].sum().reset_index()
            fig_trend = px.bar(df_trend, x='Ngay', y='amount', color='Loại giao dịch', barmode='group', color_discrete_map={'Thu nhập': '#10b981', 'Chi tiêu': '#ef4444'}, template="plotly_dark")
            fig_trend.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_trend, use_container_width=True)

        with viz2:
            df_chi = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']
            if not df_chi.empty:
                df_cat = df_chi.groupby('category')['amount'].sum().reset_index()
                fig_donut = px.pie(df_cat, names='category', values='amount', hole=0.5, color_discrete_sequence=['#38bdf8', '#f59e0b', '#8b5cf6', '#ec4899', '#10b981'], template="plotly_dark")
                fig_donut.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
                fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("**LỊCH SỬ GIAO DỊCH (ĐÃ LỌC)**")
    if not df_filtered.empty:
        df_display = df_filtered[['id', 'created_at_dt', 'account', 'category', 'amount', 'note']].copy()
        df_display['created_at_dt'] = df_display['created_at_dt'].dt.strftime('%d/%m/%Y %H:%M')
        df_display = df_display.rename(columns={'created_at_dt': 'Thời gian', 'account': 'Tài khoản', 'category': 'Phân loại', 'amount': 'Số tiền', 'note': 'Ghi chú'})
        st.dataframe(df_display, column_config={"id": None, "Số tiền": st.column_config.NumberColumn("Số tiền (VND)", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        action_id = st.selectbox("Chọn giao dịch để cập nhật:", df_filtered['id'].tolist(), format_func=lambda x: f"{pd.to_datetime(df_filtered[df_filtered['id'] == x]['created_at'].values[0]).strftime('%d/%m/%Y %H:%M')} | {df_filtered[df_filtered['id'] == x]['category'].values[0]} | {df_filtered[df_filtered['id'] == x]['amount'].values[0]:,.0f} ₫", key="select_cf")
        selected_row = df_filtered[df_filtered['id'] == action_id].iloc[0]
        
        col_a1, col_a2, _ = st.columns([1.5, 1.5, 3])
        with col_a1:
            if st.button("✏️ SỬA GIAO DỊCH", use_container_width=True, key="edit_cf"): modal_edit_cashflow(selected_row)
        with col_a2:
            if st.button("❌ XÓA GIAO DỊCH", use_container_width=True, key="del_cf"):
                supabase.table("cashflow").delete().eq("id", action_id).execute()
                st.toast("Đã xóa giao dịch!")
                time.sleep(1)
                st.rerun()
    else: st.info("Không có giao dịch nào phù hợp với bộ lọc hiện tại.")

# =====================================================================
# TAB 2: ĐẦU TƯ
# =====================================================================
with tab_invest:
    subtab_stock, subtab_ccq, subtab_gold = st.tabs(["📈 CỔ PHIẾU", "📊 CHỨNG CHỈ QUỸ", "🥇 VÀNG TÍCH SẢN"])
    
    # --- SUBTAB 1: CỔ PHIẾU ---
    with subtab_stock:
        col_btn2, _ = st.columns([1.5, 3])
        with col_btn2:
            if st.button("+ ĐẶT LỆNH CP", use_container_width=True): modal_stock()
                
        st.markdown("<br/>", unsafe_allow_html=True)
        stk_sub1, stk_sub2 = st.tabs(["Danh mục tồn kho", "Lịch sử đặt lệnh"])
        
        try:
            res_stk = supabase.table("stocks").select("*").execute()
            df_stk = pd.DataFrame(res_stk.data) if res_stk.data else pd.DataFrame()
        except: df_stk = pd.DataFrame()
            
        with stk_sub1:
            if not df_stk.empty and 'ticker' in df_stk.columns:
                summary_list = []
                for ticker, grp in df_stk.groupby('ticker'):
                    buy_rows = grp[grp['action'].str.contains('Mua', na=False, case=False)]
                    sell_rows = grp[grp['action'].str.contains('Bán', na=False, case=False)]
                    buy_vol = buy_rows['volume'].sum()
                    sell_vol = sell_rows['volume'].sum()
                    net_vol = buy_vol - sell_vol
                    buy_val = (buy_rows['volume'] * buy_rows['price']).sum()
                    avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                    total_cost = net_vol * avg_price
                    broker_name = grp['broker'].iloc[0] if 'broker' in grp.columns else 'N/A'
                    
                    if net_vol > 0:
                        summary_list.append({"Mã CK": ticker, "CTCK": broker_name, "SL tồn": net_vol, "Giá vốn TB": avg_price, "Tổng vốn": total_cost})
                        
                if summary_list:
                    st.dataframe(pd.DataFrame(summary_list), column_config={"SL tồn": st.column_config.NumberColumn("SL tồn", format="%,.0f"), "Giá vốn TB": st.column_config.NumberColumn("Giá vốn TB", format="%,.0f ₫"), "Tổng vốn": st.column_config.NumberColumn("Tổng vốn", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
            else: st.info("Chưa có cổ phiếu nào.")

        with stk_sub2:
            if not df_stk.empty:
                df_stk['Ngày'] = pd.to_datetime(df_stk['trade_date']).dt.strftime('%d/%m/%Y') if 'trade_date' in df_stk.columns else ""
                df_stk_display = df_stk[['id', 'Ngày', 'broker', 'fund_owner', 'ticker', 'action', 'volume', 'price', 'note']].rename(columns={'broker': 'CTCK', 'fund_owner': 'Portfolio', 'ticker': 'Mã CK', 'action': 'Lệnh', 'volume': 'Khối lượng', 'price': 'Giá khớp', 'note': 'Ghi chú'})
                st.dataframe(df_stk_display, column_config={"id": None, "Khối lượng": st.column_config.NumberColumn("Khối lượng", format="%,.0f"), "Giá khớp": st.column_config.NumberColumn("Giá khớp", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
                st.markdown("---")
                del_stk_id = st.selectbox("Chọn lệnh xóa:", df_stk['id'].tolist(), key="del_stk_id")
                if st.button("❌ XÓA LỆNH NÀY", key="btn_del_stk"):
                    supabase.table("stocks").delete().eq("id", del_stk_id).execute()
                    st.toast("Đã xóa lệnh!")
                    time.sleep(1)
                    st.rerun()

    # --- SUBTAB 2: CHỨNG CHỈ QUỸ ---
    with subtab_ccq:
        col_btn_ccq, _ = st.columns([1.5, 3])
        with col_btn_ccq:
            if st.button("+ ĐẶT LỆNH CCQ", use_container_width=True): modal_ccq()
                
        st.markdown("<br/>", unsafe_allow_html=True)
        ccq_sub1, ccq_sub2 = st.tabs(["Danh mục CCQ tồn kho", "Lịch sử lệnh quỹ"])
        
        try:
            res_fund = supabase.table("ccq_funds").select("*").execute()
            df_fund = pd.DataFrame(res_fund.data) if res_fund.data else pd.DataFrame()
        except: df_fund = pd.DataFrame()
            
        with ccq_sub1:
            if not df_fund.empty and 'ticker' in df_fund.columns:
                fund_summary = []
                for ticker, grp in df_fund.groupby('ticker'):
                    buy_rows = grp[grp['action'].str.contains('Mua', na=False, case=False)]
                    sell_rows = grp[grp['action'].str.contains('Bán', na=False, case=False)]
                    buy_vol = buy_rows['volume'].sum()
                    sell_vol = sell_rows['volume'].sum()
                    net_vol = buy_vol - sell_vol
                    buy_val = (buy_rows['volume'] * buy_rows['price']).sum()
                    avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                    total_cost = net_vol * avg_price
                    platform_name = grp['platform'].iloc[0] if 'platform' in grp.columns else 'N/A'
                    
                    if net_vol > 0:
                        fund_summary.append({"Mã Quỹ": ticker, "Nền tảng": platform_name, "SL tồn": net_vol, "Giá NAV TB": avg_price, "Tổng vốn": total_cost})
                        
                if fund_summary:
                    st.dataframe(pd.DataFrame(fund_summary), column_config={"SL tồn": st.column_config.NumberColumn("SL tồn", format="%,.2f"), "Giá NAV TB": st.column_config.NumberColumn("Giá NAV TB", format="%,.0f ₫"), "Tổng vốn": st.column_config.NumberColumn("Tổng vốn", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
            else: st.info("Chưa có chứng chỉ quỹ nào.")

        with ccq_sub2:
            if not df_fund.empty:
                df_fund['Ngày'] = pd.to_datetime(df_fund['trade_date']).dt.strftime('%d/%m/%Y') if 'trade_date' in df_fund.columns else ""
                df_fund_display = df_fund[['id', 'Ngày', 'platform', 'fund_owner', 'ticker', 'action', 'volume', 'price', 'note']].rename(columns={'platform': 'Nền tảng', 'fund_owner': 'Portfolio', 'ticker': 'Mã Quỹ', 'action': 'Lệnh', 'volume': 'Số lượng', 'price': 'Giá NAV', 'note': 'Ghi chú'})
                st.dataframe(df_fund_display, column_config={"id": None, "Số lượng": st.column_config.NumberColumn("Số lượng", format="%,.2f"), "Giá NAV": st.column_config.NumberColumn("Giá NAV", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
                st.markdown("---")
                del_ccq_id = st.selectbox("Chọn lệnh xóa:", df_fund['id'].tolist(), key="del_ccq_id")
                if st.button("❌ XÓA LỆNH NÀY", key="btn_del_ccq"):
                    supabase.table("ccq_funds").delete().eq("id", del_ccq_id).execute()
                    st.toast("Đã xóa lệnh!")
                    time.sleep(1)
                    st.rerun()

    # --- SUBTAB 3: VÀNG ---
    with subtab_gold:
        col_btn_gold, _ = st.columns([1.5, 3])
        with col_btn_gold:
            if st.button("+ ĐẶT LỆNH VÀNG", use_container_width=True): modal_gold()
                
        st.markdown("<br/>", unsafe_allow_html=True)
        gold_sub1, gold_sub2 = st.tabs(["Danh mục Vàng", "Lịch sử mua/bán"])
        
        try:
            res_gold = supabase.table("gold").select("*").execute()
            df_gold = pd.DataFrame(res_gold.data) if res_gold.data else pd.DataFrame()
        except: df_gold = pd.DataFrame()
            
        with gold_sub1:
            if not df_gold.empty and 'gold_type' in df_gold.columns:
                gold_summary = []
                for gtype, grp in df_gold.groupby('gold_type'):
                    buy_rows = grp[grp['action'].str.contains('Mua', na=False, case=False)]
                    sell_rows = grp[grp['action'].str.contains('Bán', na=False, case=False)]
                    buy_vol = buy_rows['quantity'].sum()
                    sell_vol = sell_rows['quantity'].sum()
                    net_vol = buy_vol - sell_vol
                    buy_val = (buy_rows['quantity'] * buy_rows['price']).sum()
                    avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                    total_cost = net_vol * avg_price
                    
                    if net_vol > 0:
                        gold_summary.append({"Loại Vàng": gtype, "SL tồn (Chỉ)": net_vol, "Giá vốn TB": avg_price, "Tổng vốn": total_cost})
                        
                if gold_summary:
                    st.dataframe(pd.DataFrame(gold_summary), column_config={"SL tồn (Chỉ)": st.column_config.NumberColumn("SL tồn (Chỉ)", format="%,.1f Chỉ"), "Giá vốn TB": st.column_config.NumberColumn("Giá vốn TB", format="%,.0f ₫"), "Tổng vốn": st.column_config.NumberColumn("Tổng vốn", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
            else: st.info("Chưa có dữ liệu Vàng.")

        with gold_sub2:
            if not df_gold.empty:
                df_gold['Ngày'] = pd.to_datetime(df_gold['trade_date']).dt.strftime('%d/%m/%Y') if 'trade_date' in df_gold.columns else ""
                df_gold_display = df_gold[['id', 'Ngày', 'gold_type', 'fund_owner', 'action', 'quantity', 'price', 'note']].rename(columns={'gold_type': 'Loại Vàng', 'fund_owner': 'Portfolio', 'action': 'Lệnh', 'quantity': 'Số lượng (Chỉ)', 'price': 'Đơn giá', 'note': 'Ghi chú'})
                st.dataframe(df_gold_display, column_config={"id": None, "Số lượng (Chỉ)": st.column_config.NumberColumn("Số lượng (Chỉ)", format="%,.1f Chỉ"), "Đơn giá": st.column_config.NumberColumn("Đơn giá", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
                st.markdown("---")
                del_gold_id = st.selectbox("Chọn lệnh xóa:", df_gold['id'].tolist(), key="del_gold_id")
                if st.button("❌ XÓA LỆNH NÀY", key="btn_del_gold"):
                    supabase.table("gold").delete().eq("id", del_gold_id).execute()
                    st.toast("Đã xóa lệnh!")
                    time.sleep(1)
                    st.rerun()

# =====================================================================
# TAB 3: TIẾT KIỆM
# =====================================================================
with tab_savings:
    col_btn3, _ = st.columns([1, 3])
    with col_btn3:
        if st.button("+ TẠO SỔ TIẾT KIỆM", use_container_width=True): modal_savings()
            
    try:
        res_sav = supabase.table("savings").select("*").execute()
        df_savings = pd.DataFrame(res_sav.data) if res_sav.data else pd.DataFrame()
    except: df_savings = pd.DataFrame()

    for fund_name in FUNDS:
        st.subheader(fund_name)
        if not df_savings.empty and "fund_owner" in df_savings.columns:
            fund_data = df_savings[df_savings["fund_owner"] == fund_name].copy()
            total_goc = fund_data["amount"].sum() if not fund_data.empty else 0
        else:
            fund_data = pd.DataFrame()
            total_goc = 0
            
        st.markdown(f"**Tổng vốn:** <span style='color:#10b981; font-size:18px'>{total_goc:,.0f} ₫</span>", unsafe_allow_html=True)
        
        if not fund_data.empty:
            fund_data['Ngày gửi'] = pd.to_datetime(fund_data['deposit_date']).dt.strftime('%d/%m/%Y')
            df_display_sav = fund_data[['id', 'bank', 'Ngày gửi', 'term', 'interest_rate', 'amount']].rename(columns={'bank': 'Ngân hàng', 'term': 'Kỳ hạn', 'interest_rate': 'Lãi suất (%/năm)', 'amount': 'Tiền gốc'})
            st.dataframe(df_display_sav, column_config={"id": None, "Tiền gốc": st.column_config.NumberColumn("Tiền gốc", format="%,.0f ₫"), "Lãi suất (%/năm)": st.column_config.NumberColumn("Lãi suất (%/năm)", format="%.2f")}, use_container_width=True, hide_index=True)
            
            st.markdown(f"**⚙️ TÙY CHỈNH SỔ TIẾT KIỆM ({fund_name.upper()})**")
            action_id_sav = st.selectbox("Chọn sổ tiết kiệm:", fund_data['id'].tolist(), format_func=lambda x: f"{fund_data[fund_data['id'] == x]['bank'].values[0]} | {fund_data[fund_data['id'] == x]['amount'].values[0]:,.0f} ₫", key=f"select_sav_{fund_name}")
            selected_sav_row = fund_data[fund_data['id'] == action_id_sav].iloc[0]
            
            col_s1, col_s2, _ = st.columns([1.5, 1.5, 3])
            with col_s1:
                if st.button("✏️ SỬA", use_container_width=True, key=f"edit_sav_{fund_name}"): modal_edit_savings(selected_sav_row)
            with col_s2:
                if st.button("❌ TẤT TOÁN", use_container_width=True, key=f"del_sav_{fund_name}"):
                    supabase.table("savings").delete().eq("id", action_id_sav).execute()
                    st.toast("Đã xóa sổ tiết kiệm!")
                    time.sleep(1)
                    st.rerun()

# =====================================================================
# TAB 4: BĐS & TÍN DỤNG
# =====================================================================
with tab_realestate:
    col_re_btn, col_debt_btn, _ = st.columns([1.2, 1.2, 2])
    with col_re_btn:
        if st.button("+ THÊM TIẾN ĐỘ BĐS", use_container_width=True): modal_realestate()
    with col_debt_btn:
        if st.button("+ THÊM KHOẢN VAY", use_container_width=True): modal_debt()
            
    st.markdown("<br/>", unsafe_allow_html=True)
    
    # --- BẤT ĐỘNG SẢN ---
    st.subheader("Bất động sản mua theo tiến độ")
    try:
        res_re = supabase.table("realestate").select("*").execute()
        df_re = pd.DataFrame(res_re.data) if res_re.data else pd.DataFrame()
    except: df_re = pd.DataFrame()

    if not df_re.empty and "project_name" in df_re.columns:
        if "contract_value" not in df_re.columns: df_re["contract_value"] = 0
            
        st.markdown("##### 📈 Tiến độ thanh toán tổng thể")
        summary_re = []
        for proj, grp in df_re.groupby('project_name'):
            contract_val = grp['contract_value'].iloc[0] if 'contract_value' in grp.columns else 0
            paid_val = grp[grp['status'] == 'Đã thanh toán']['amount'].sum()
            progress = (paid_val / contract_val * 100) if contract_val > 0 else 0
            summary_re.append({"Dự án": proj, "Giá trị HĐ (VND)": contract_val, "Đã thanh toán (VND)": paid_val, "Còn lại (VND)": contract_val - paid_val, "Tiến độ (%)": progress})
            
        if summary_re:
            st.dataframe(pd.DataFrame(summary_re), column_config={"Giá trị HĐ (VND)": st.column_config.NumberColumn("Giá trị HĐ (VND)", format="%,.0f ₫"), "Đã thanh toán (VND)": st.column_config.NumberColumn("Đã thanh toán (VND)", format="%,.0f ₫"), "Còn lại (VND)": st.column_config.NumberColumn("Còn lại (VND)", format="%,.0f ₫"), "Tiến độ (%)": st.column_config.ProgressColumn("Tiến độ (%)", format="%.1f%%", min_value=0, max_value=100)}, use_container_width=True, hide_index=True)
            
        st.markdown("##### 📄 Chi tiết các đợt thanh toán")
        if "funding_source" not in df_re.columns: df_re["funding_source"] = "N/A"
        if "note" not in df_re.columns: df_re["note"] = ""
            
        df_re_display = df_re[['id', 'project_name', 'installment_name', 'contract_value', 'amount', 'funding_source', 'due_date', 'status', 'note']].rename(columns={'project_name': 'Dự án', 'installment_name': 'Tên Đợt', 'contract_value': 'Giá trị HĐ', 'amount': 'Thanh toán', 'funding_source': 'Nguồn tiền', 'due_date': 'Hạn TT', 'status': 'Trạng thái', 'note': 'Ghi chú'})
        
        def style_bds(row):
            if row['Trạng thái'] == 'Đã thanh toán': return ['background-color: rgba(16, 185, 129, 0.15); color: #34d399; font-weight: 500'] * len(row)
            else: return ['background-color: rgba(239, 68, 68, 0.1); color: #f87171'] * len(row)
                
        st.dataframe(df_re_display.style.apply(style_bds, axis=1), column_config={"id": None, "Giá trị HĐ": st.column_config.NumberColumn("Giá trị HĐ", format="%,.0f ₫"), "Thanh toán": st.column_config.NumberColumn("Thanh toán", format="%,.0f ₫")}, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        action_id_re = st.selectbox("Chọn tiến độ BĐS để xóa:", df_re['id'].tolist(), format_func=lambda x: f"{df_re[df_re['id'] == x]['project_name'].values[0]} | {df_re[df_re['id'] == x]['installment_name'].values[0]} | {df_re[df_re['id'] == x]['amount'].values[0]:,.0f} ₫", key="select_re")
        
        if st.button("❌ XÓA TIẾN ĐỘ NÀY", key="del_re"):
            supabase.table("realestate").delete().eq("id", action_id_re).execute()
            st.toast("Đã xóa BĐS!", icon="🗑️")
            time.sleep(1)
            st.rerun()

    # --- KHOẢN VAY ---
    st.subheader("Khoản vay tín dụng & Dư nợ")
    try:
        res_debt = supabase.table("debts").select("*").execute()
        df_vay = pd.DataFrame(res_debt.data) if res_debt.data else pd.DataFrame()
    except: df_vay = pd.DataFrame()

    if not df_vay.empty and "original_principal" in df_vay.columns:
        today = pd.to_datetime(date.today())
        
        def calculate_loan_schedule(row):
            start_date = pd.to_datetime(row['start_date'])
            payment_day = int(row.get('payment_day', start_date.day))
            grace_period = int(row.get('grace_period', 0))
            total_months = int(row['total_months'])
            original_principal = row['original_principal']
            interest_rate = row['interest_rate']

            months_diff = (today.year - start_date.year) * 12 + (today.month - start_date.month)
            if today.day < payment_day: months_diff -= 1
                
            months_elapsed = max(0, min(months_diff, total_months))
            principal_paying_months = max(1, total_months - grace_period)
            monthly_principal = original_principal / principal_paying_months
            months_paid_principal = max(0, months_elapsed - grace_period)
            current_balance = original_principal - (monthly_principal * months_paid_principal)
            
            is_grace_active = (months_elapsed < grace_period)
            current_monthly_principal = 0 if is_grace_active else monthly_principal
            monthly_interest = current_balance * (interest_rate / 100 / 12)
            total_payment = current_monthly_principal + monthly_interest

            next_month = today.month if today.day <= payment_day else today.month + 1
            next_year = today.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            
            try: next_payment_date = pd.Timestamp(year=next_year, month=next_month, day=payment_day)
            except ValueError:
                last_day = calendar.monthrange(next_year, next_month)[1]
                next_payment_date = pd.Timestamp(year=next_year, month=next_month, day=min(payment_day, last_day))

            return pd.Series({
                'Kỳ TT kế tiếp': next_payment_date.strftime('%d/%m/%Y'), 'Tổng kỳ hạn': total_months, 'Ân hạn': f"{grace_period}T" if grace_period > 0 else "0",
                'Tháng đã qua': months_elapsed, 'Vay ban đầu': original_principal, 'Dư nợ HIỆN TẠI': current_balance,
                'Đã trả (Gốc)': original_principal - current_balance, 'Tiến độ (%)': ((original_principal - current_balance) / original_principal) * 100,
                'Lãi suất (%/năm)': interest_rate, 'Gốc/Tháng': current_monthly_principal, 'Lãi/Tháng': monthly_interest, 'Tổng phải trả': total_payment
            })

        loan_metrics = df_vay.apply(calculate_loan_schedule, axis=1)
        df_display_vay = pd.concat([df_vay[['id', 'purpose', 'bank']].rename(columns={'purpose': 'Mục đích', 'bank': 'Ngân hàng'}), loan_metrics], axis=1)
        
        cols_to_show = ['id', 'Mục đích', 'Ngân hàng', 'Kỳ TT kế tiếp', 'Tổng kỳ hạn', 'Ân hạn', 'Tháng đã qua', 'Lãi suất (%/năm)', 'Vay ban đầu', 'Đã trả (Gốc)', 'Dư nợ HIỆN TẠI', 'Tiến độ (%)', 'Gốc/Tháng', 'Lãi/Tháng', 'Tổng phải trả']
        
        def style_debt(row):
            if row['Dư nợ HIỆN TẠI'] <= 0: return ['background-color: rgba(16, 185, 129, 0.15); color: #34d399; font-weight: 500'] * len(row)
            if row['Ân hạn'] != "0": return ['background-color: rgba(245, 158, 11, 0.1)'] * len(row)
            return [''] * len(row)
            
        st.dataframe(
            df_display_vay[cols_to_show].style.apply(style_debt, axis=1),
            column_config={
                "id": None, "Tổng kỳ hạn": st.column_config.NumberColumn("Tổng kỳ hạn", format="%d Tháng"), "Tháng đã qua": st.column_config.NumberColumn("Đã qua", format="%d Tháng"),
                "Vay ban đầu": st.column_config.NumberColumn("Vay ban đầu", format="%,.0f ₫"), "Đã trả (Gốc)": st.column_config.NumberColumn("Đã trả (Gốc)", format="%,.0f ₫"),
                "Dư nợ HIỆN TẠI": st.column_config.NumberColumn("Dư nợ HIỆN TẠI", format="%,.0f ₫"), "Gốc/Tháng": st.column_config.NumberColumn("Gốc/Tháng", format="%,.0f ₫"),
                "Lãi/Tháng": st.column_config.NumberColumn("Lãi/Tháng", format="%,.0f ₫"), "Tổng phải trả": st.column_config.NumberColumn("Tổng TT", format="%,.0f ₫"),
                "Lãi suất (%/năm)": st.column_config.NumberColumn("Lãi suất", format="%.2f%%"), "Tiến độ (%)": st.column_config.ProgressColumn("Tiến độ (%)", format="%.1f%%", min_value=0, max_value=100)
            },
            use_container_width=True, hide_index=True
        )
        
        st.markdown("---")
        action_id_debt = st.selectbox("Chọn khoản vay để xóa:", df_vay['id'].tolist(), format_func=lambda x: f"{df_vay[df_vay['id'] == x]['purpose'].values[0]} | {df_vay[df_vay['id'] == x]['bank'].values[0]}", key="select_debt")
        if st.button("❌ XÓA KHOẢN VAY NÀY", key="del_debt"):
            supabase.table("debts").delete().eq("id", action_id_debt).execute()
            st.toast("Đã xóa khoản vay!", icon="🗑️")
            time.sleep(1)
            st.rerun()
