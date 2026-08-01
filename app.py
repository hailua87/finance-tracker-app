import streamlit as st
import pandas as pd
from datetime import date, datetime
import time
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import calendar
import streamlit_antd_components as sac
from supabase import create_client, Client
from components.ui import load_css, net_worth_dashboard

# =====================================================================
# 1. PAGE CONFIG & SUPABASE
# =====================================================================
st.set_page_config(page_title="Nhà Quê Tập Chi Tiêu", page_icon="💰", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# =====================================================================
# 2. GLOBAL VARIABLES
# =====================================================================
DEBIT_ACCOUNTS = ["VCB chồng", "TCB chồng", "TCB vợ"]
CREDIT_CARDS = ["UOB vợ", "UOB chồng", "HSBC chồng"]
BROKER_ACCOUNTS = ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Mirae Asset"]
BANK_ACCOUNTS = DEBIT_ACCOUNTS + CREDIT_CARDS + BROKER_ACCOUNTS
FUNDING_SOURCES = BANK_ACCOUNTS + ["Tiền mặt", "Giải ngân vốn vay", "Khác"]
FUNDS = ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"]
GOLD_TYPES = ["SJC Miếng", "Nhẫn trơn 9999", "PNJ", "DOJI", "Vàng trang sức", "Khác"]
CATS = ["Lương/Thu nhập", "Ăn uống & Sinh hoạt", "Giáo dục (Con cái)", "Nhà cửa & Tiện ích",
        "Sức khỏe & Y tế", "Đi lại & Phương tiện", "Hiếu hỉ & Mua sắm", "Đầu tư & Trả nợ", "Khác"]
EXPENSE_CATS = [c for c in CATS if c != "Lương/Thu nhập"]
SAVINGS_GOALS = {"Tieu Boi Funding": 500_000_000, "Daddy Funding": 300_000_000, "Mama Funding": 300_000_000}
FUND_MEMBER_MAP = {"Tieu Boi Funding": "Baby", "Daddy Funding": "Daddy", "Mama Funding": "Mommy"}
FUND_THEME_MAP = {"Tieu Boi Funding": "card-baby", "Daddy Funding": "card-daddy", "Mama Funding": "card-mommy"}

# =====================================================================
# 3. SESSION STATE
# =====================================================================
_defaults = {
    "last_account": "VCB chồng", "cf_amount_str": "", "current_member": "Tất cả",
    "cat_budgets": {
        "Ăn uống & Sinh hoạt": 8_000_000, "Nhà cửa & Tiện ích": 3_000_000,
        "Giáo dục (Con cái)": 3_000_000, "Đi lại & Phương tiện": 1_500_000,
        "Sức khỏe & Y tế": 1_000_000, "Hiếu hỉ & Mua sắm": 3_000_000,
        "Đầu tư & Trả nợ": 5_000_000, "Khác": 1_000_000,
    },
    "editing_stock": None, "editing_ccq": None, "editing_gold": None,
    "editing_savings": None, "editing_realestate": None, "editing_debt": None,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# =====================================================================
# 4. CSS & HELPERS
# =====================================================================
load_css("assets/style.css")

def parse_smart_amount(s: str) -> float:
    try:
        s = str(s).lower().replace(",", "").replace(" ", "")
        if "tỷ" in s or "ty" in s:
            return float(s.replace("tỷ", "").replace("ty", "")) * 1_000_000_000
        if "tr" in s:
            return float(s.replace("tr", "")) * 1_000_000
        if s.endswith("t"):
            return float(s[:-1]) * 1_000_000
        if "k" in s:
            return float(s.replace("k", "")) * 1_000
        if s.count('.') > 1:
            return float(s.replace(".", ""))
        return float(s)
    except Exception:
        return 0.0

def safe_float(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val) if not pd.isna(val) else 0.0
    if isinstance(val, str):
        val = val.replace('%', '').replace(',', '').replace('₫', '').strip()
        if val == '':
            return 0.0
    try:
        return float(val)
    except Exception:
        return 0.0

def filter_by_member(df, member, col='fund_owner'):
    if member == "Tất cả" or df.empty or col not in df.columns:
        return df
    return df[df[col].astype(str).str.contains(member, na=False, case=False)]

def fund_matches_member(fund_name, member):
    if member == "Tất cả":
        return True
    return FUND_MEMBER_MAP.get(fund_name, "") == member

def fetch_table(name):
    try:
        res = supabase.table(name).select("*").execute()
        df = pd.DataFrame(res.data) if res and res.data else pd.DataFrame()
        for col in ['created_at', 'trade_date', 'start_date', 'deposit_date', 'due_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    except Exception:
        return pd.DataFrame()

def calc_investment_total(df, group_col, vol_col='volume'):
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(), 0
    df = df.copy()
    df[vol_col] = pd.to_numeric(df[vol_col], errors='coerce').fillna(0)
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    rows, total = [], 0
    for name, grp in df.groupby(group_col):
        buys = grp[grp['action'].astype(str).str.contains('Mua', na=False, case=False)]
        sells = grp[grp['action'].astype(str).str.contains('Bán', na=False, case=False)]
        net = buys[vol_col].sum() - sells[vol_col].sum()
        if net > 0:
            bv = (buys[vol_col] * buys['price']).sum()
            bvol = buys[vol_col].sum()
            avg = bv / bvol if bvol > 0 else 0
            val = net * avg
            total += val
            rows.append({"Tài sản": name, "SL nắm giữ": net, "Giá vốn TB": avg, "Giá trị": val})
    return pd.DataFrame(rows), total

# =====================================================================
# 5. SIDEBAR
# =====================================================================
with st.sidebar:
    st.markdown('<div class="hallmark-header" style="font-size:1.5rem;margin-top:20px;">THÀNH VIÊN</div>', unsafe_allow_html=True)
    _members = ["Tất cả", "Daddy", "Mommy", "Baby"]
    _idx = _members.index(st.session_state.current_member) if st.session_state.current_member in _members else 0
    st.session_state.current_member = sac.segmented(
        items=[
            sac.SegmentedItem(label='Tất cả', icon='people-fill'),
            sac.SegmentedItem(label='Daddy', icon='person-workspace'),
            sac.SegmentedItem(label='Mommy', icon='person-hearts'),
            sac.SegmentedItem(label='Baby', icon='person-arms-up'),
        ], label='', align='center', use_container_width=True, index=_idx
    )

current_member = st.session_state.current_member
st.markdown(f'<div class="hallmark-header">NHÀ QUÊ TẬP CHI TIÊU{f" <span style=font-size:1.2rem;>({current_member})</span>" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)

# =====================================================================
# 6. ALL @st.dialog FUNCTIONS
# =====================================================================

@st.dialog("NHẬP CHI TIÊU NHANH")
def modal_cashflow():
    amount_str = st.text_input("SỐ TIỀN (VND)", value=st.session_state.cf_amount_str, placeholder="Ví dụ: 50k, 1.2tr")
    def _add(v):
        cur = parse_smart_amount(st.session_state.cf_amount_str)
        st.session_state.cf_amount_str = f"{cur + v:,.0f}"
    b1, b2, b3 = st.columns(3)
    with b1: st.button("+50k", on_click=_add, args=(50000,), use_container_width=True, key="cf_q50")
    with b2: st.button("+100k", on_click=_add, args=(100000,), use_container_width=True, key="cf_q100")
    with b3: st.button("+500k", on_click=_add, args=(500000,), use_container_width=True, key="cf_q500")
    c1, c2 = st.columns(2)
    with c1: category = st.selectbox("Phân loại", CATS, key="cf_cat")
    with c2:
        _ai = BANK_ACCOUNTS.index(st.session_state.last_account) if st.session_state.last_account in BANK_ACCOUNTS else 0
        account = st.selectbox("Tài khoản", BANK_ACCOUNTS, index=_ai, key="cf_acc")
    note = st.text_input("Ghi chú", key="cf_note")
    if st.button("💾 LƯU GIAO DỊCH", use_container_width=True, type="primary", key="cf_save"):
        amt = parse_smart_amount(amount_str)
        if amt <= 0:
            st.error("⚠️ Nhập số tiền hợp lệ!")
        else:
            supabase.table("cashflow").insert({"account": account, "amount": amt, "category": category, "note": note, "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}).execute()
            st.session_state.last_account = account
            st.session_state.cf_amount_str = ""
            st.toast("✅ Đã lưu!", icon="🔥"); time.sleep(1); st.rerun()

@st.dialog("ĐẶT LỆNH CỔ PHIẾU")
def modal_stock():
    with st.form("add_stock_form"):
        c1, c2 = st.columns(2)
        with c1: broker = st.selectbox("Nơi lưu ký", BROKER_ACCOUNTS + ["Khác"])
        with c2: fund_owner = st.selectbox("Portfolio", FUNDS)
        ticker = st.text_input("Mã CK (VD: VIB)").upper()
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: vol_str = st.text_input("Khối lượng", value="100")
        with c4: price_str = st.text_input("Giá (VD: 22.5k)")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày GD")
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("💾 LƯU LỆNH", use_container_width=True):
            vol, price = parse_smart_amount(vol_str), parse_smart_amount(price_str)
            if not ticker.strip(): st.error("⚠️ Nhập mã!")
            elif vol <= 0 or price <= 0: st.error("⚠️ KL & Giá > 0!")
            else:
                supabase.table("stocks").insert({"trade_date": str(trade_date), "broker": broker, "fund_owner": fund_owner, "ticker": ticker.strip(), "action": action, "volume": int(vol), "price": float(price), "note": note}).execute()
                st.toast("✅ Đã lưu!", icon="📈"); time.sleep(1); st.rerun()

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("add_ccq_form"):
        c1, c2 = st.columns(2)
        with c1: platform = st.selectbox("Nền tảng", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM", "SSI", "VNDirect"])
        with c2: fund_owner = st.selectbox("Portfolio", FUNDS)
        ticker = st.text_input("Mã Quỹ (VD: DCDS)").upper()
        action = st.radio("Lệnh", ["Mua (SIP)", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: val_str = st.text_input("Giá trị GD (VD: 5tr)")
        with c4: vol_str = st.text_input("Số lượng CCQ")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày GD")
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("💾 LƯU", use_container_width=True):
            total_val, vol = parse_smart_amount(val_str), parse_smart_amount(vol_str)
            if not ticker.strip(): st.error("⚠️ Nhập mã!")
            elif vol <= 0 or total_val <= 0: st.error("⚠️ Giá trị & SL > 0!")
            else:
                nav = total_val / vol
                supabase.table("ccq_funds").insert({"trade_date": str(trade_date), "platform": platform, "fund_owner": fund_owner, "ticker": ticker.strip(), "action": action, "volume": float(vol), "price": float(nav), "note": note}).execute()
                st.toast("✅ Đã lưu!", icon="📊"); time.sleep(1); st.rerun()

@st.dialog("🥇 GIAO DỊCH VÀNG")
def modal_gold():
    with st.form("add_gold_form"):
        c1, c2 = st.columns(2)
        with c1: gold_type = st.selectbox("Loại Vàng", GOLD_TYPES)
        with c2: fund_owner = st.selectbox("Portfolio", FUNDS)
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: qty_str = st.text_input("Số lượng (Chỉ)")
        with c4: price_str = st.text_input("Đơn giá (VND/Chỉ)")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày GD")
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("💾 LƯU", use_container_width=True):
            qty, price = parse_smart_amount(qty_str), parse_smart_amount(price_str)
            if qty <= 0 or price <= 0: st.error("⚠️ SL & Giá > 0!")
            else:
                supabase.table("gold").insert({"trade_date": str(trade_date), "gold_type": gold_type, "fund_owner": fund_owner, "action": action, "quantity": float(qty), "price": float(price), "note": note}).execute()
                st.toast("✅ Đã lưu!", icon="🥇"); time.sleep(1); st.rerun()

@st.dialog("THÊM KHOẢN VAY MỚI")
def modal_debt():
    with st.form("add_debt_form"):
        purpose = st.text_input("Mục đích vay")
        bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS + ["Khác"])
        c1, c2 = st.columns(2)
        with c1: vay_str = st.text_input("Tiền vay GỐC (VD: 1.8tỷ)")
        with c2: total_months = st.number_input("Tổng tháng", min_value=1, step=1, value=180)
        c3, c4 = st.columns(2)
        with c3: start_date = st.date_input("Ngày giải ngân")
        with c4: payment_day = st.number_input("Ngày TT (mùng)", min_value=1, max_value=31, value=5)
        c5, c6 = st.columns(2)
        with c5: grace = st.number_input("Ân hạn gốc (tháng)", min_value=0, step=1, value=1)
        with c6: rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, format="%.2f", value=7.3)
        if st.form_submit_button("💾 LƯU KHOẢN VAY", use_container_width=True):
            principal = parse_smart_amount(vay_str)
            if principal <= 0: st.error("⚠️ Tiền vay > 0!")
            else:
                supabase.table("debts").insert({"purpose": purpose, "bank": bank, "original_principal": int(principal), "total_months": int(total_months), "start_date": str(start_date), "interest_rate": rate, "payment_day": int(payment_day), "grace_period": int(grace)}).execute()
                st.toast("✅ Đã lưu!", icon="🏦"); time.sleep(1); st.rerun()

@st.dialog("➕ THÊM TIẾN ĐỘ BĐS")
def modal_add_realestate():
    res = supabase.table("realestate").select("project_name, contract_value").execute()
    existing_projects = {}
    if res and res.data:
        for r in res.data:
            pname = r.get("project_name")
            cval = r.get("contract_value")
            if pname and pname not in existing_projects:
                existing_projects[pname] = safe_float(cval)

    proj_options = ["➕ Thêm dự án mới..."] + list(existing_projects.keys())
    selected_proj = st.selectbox("Chọn dự án", proj_options, key="re_proj_sel")
    
    if selected_proj == "➕ Thêm dự án mới...":
        c1, c2 = st.columns(2)
        with c1:
            bds_name = st.text_input("Tên dự án mới", key="re_bds_name")
        with c2:
            gia_tri_hd_str = st.text_input("Giá trị HĐ (VD: 3.5tỷ)", key="re_hd_val")
        final_project_name = bds_name.strip()
        final_contract_value = parse_smart_amount(gia_tri_hd_str)
    else:
        final_project_name = selected_proj
        final_contract_value = existing_projects[selected_proj]
        st.info(f"Dự án: **{final_project_name}** | Giá trị HĐ: **{final_contract_value:,.0f} ₫**")

    st.markdown("---", unsafe_allow_html=True)
    st.markdown("### Chi tiết đợt thanh toán", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        installment_name = st.text_input("Tên đợt (VD: Đợt 1)", value="Đợt 1", key="re_inst_name")
    with c2:
        amount_str = st.text_input("Số tiền thanh toán đợt này (VD: 500tr)", key="re_inst_amt")
    
    c3, c4, c5 = st.columns(3)
    with c3:
        funding_source = st.selectbox("Nguồn tiền", FUNDING_SOURCES, key="re_fund_src")
    with c4:
        due_date = st.date_input("Hạn thanh toán", value=date.today(), key="re_due_date")
    with c5:
        status = st.selectbox("Trạng thái", ["Chưa thanh toán", "Đã thanh toán"], key="re_status")
        
    note = st.text_input("Ghi chú", key="re_note")

    if st.button("💾 LƯU ĐỢT THANH TOÁN", use_container_width=True, type="primary", key="re_save_btn"):
        amt = parse_smart_amount(amount_str)
        if not final_project_name:
            st.error("⚠️ Vui lòng nhập tên dự án!")
        elif final_contract_value <= 0:
            st.error("⚠️ Giá trị HĐ phải lớn hơn 0!")
        elif amt <= 0:
            st.error("⚠️ Số tiền thanh toán đợt này phải lớn hơn 0!")
        else:
            payload = {
                "project_name": final_project_name,
                "contract_value": float(final_contract_value),
                "installment_name": installment_name.strip(),
                "amount": float(amt),
                "funding_source": funding_source,
                "due_date": str(due_date),
                "status": status,
                "note": note,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            supabase.table("realestate").insert(payload).execute()
            st.toast("✅ Đã thêm đợt thanh toán BĐS!", icon="🏠")
            time.sleep(1)
            st.rerun()

@st.dialog("➕ TẠO SỔ TIẾT KIỆM MỚI")
def modal_add_savings():
    with st.form("add_savings_form"):
        fund_owner = st.selectbox("Thuộc Quỹ", FUNDS)
        bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS)
        c1, c2 = st.columns(2)
        with c1: amount_str = st.text_input("Số tiền gửi (VD: 50tr)")
        with c2: rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, format="%.1f")
        c3, c4 = st.columns(2)
        with c3: term = st.number_input("Kỳ hạn (tháng)", min_value=0, step=1)
        with c4: deposit_date = st.date_input("Ngày gửi")
        note = st.text_input("Ghi chú")
        if st.form_submit_button("💾 TẠO SỔ", use_container_width=True):
            amt = parse_smart_amount(amount_str)
            if amt <= 0: st.error("⚠️ Số tiền > 0!")
            else:
                supabase.table("savings").insert({"fund_owner": fund_owner, "bank": bank, "amount": int(amt), "interest_rate": float(rate), "term": int(term), "deposit_date": str(deposit_date), "note": note, "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}).execute()
                st.toast("✅ Đã tạo sổ!", icon="💰"); time.sleep(1); st.rerun()

# --- EDIT MODALS ---
@st.dialog("✏️ SỬA LỆNH CỔ PHIẾU")
def modal_edit_stock():
    row = st.session_state.editing_stock
    if not row:
        st.warning("Không có dữ liệu."); return
    with st.form("edit_stock_form"):
        c1, c2 = st.columns(2)
        with c1: broker = st.selectbox("Nơi lưu ký", BROKER_ACCOUNTS + ["Khác"], index=(BROKER_ACCOUNTS + ["Khác"]).index(row.get('broker', 'TCBS')) if row.get('broker') in BROKER_ACCOUNTS + ["Khác"] else 0)
        with c2: fund_owner = st.selectbox("Portfolio", FUNDS, index=FUNDS.index(row['fund_owner']) if row.get('fund_owner') in FUNDS else 0)
        ticker = st.text_input("Mã CK", value=row.get('ticker', ''))
        action = st.radio("Lệnh", ["Mua", "Bán"], index=0 if 'Mua' in str(row.get('action', '')) else 1, horizontal=True)
        c3, c4 = st.columns(2)
        with c3: volume = st.number_input("Khối lượng", value=int(safe_float(row.get('volume'))), min_value=0)
        with c4: price = st.number_input("Giá", value=safe_float(row.get('price')), min_value=0.0, format="%.0f")
        note = st.text_input("Ghi chú", value=row.get('note', '') or '')
        if st.form_submit_button("💾 CẬP NHẬT", use_container_width=True):
            supabase.table("stocks").update({"broker": broker, "fund_owner": fund_owner, "ticker": ticker.upper().strip(), "action": action, "volume": int(volume), "price": float(price), "note": note}).eq("id", row['id']).execute()
            st.session_state.editing_stock = None
            st.toast("✅ Đã cập nhật!", icon="📈"); time.sleep(1); st.rerun()

@st.dialog("✏️ SỬA GD CHỨNG CHỈ QUỸ")
def modal_edit_ccq():
    row = st.session_state.editing_ccq
    if not row:
        st.warning("Không có dữ liệu."); return
    platforms = ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM", "SSI", "VNDirect"]
    with st.form("edit_ccq_form"):
        c1, c2 = st.columns(2)
        with c1: platform = st.selectbox("Nền tảng", platforms, index=platforms.index(row['platform']) if row.get('platform') in platforms else 0)
        with c2: fund_owner = st.selectbox("Portfolio", FUNDS, index=FUNDS.index(row['fund_owner']) if row.get('fund_owner') in FUNDS else 0)
        ticker = st.text_input("Mã Quỹ", value=row.get('ticker', ''))
        action = st.radio("Lệnh", ["Mua (SIP)", "Bán"], index=0 if 'Mua' in str(row.get('action', '')) else 1, horizontal=True)
        c3, c4 = st.columns(2)
        with c3: volume = st.number_input("Số lượng CCQ", value=safe_float(row.get('volume')), min_value=0.0, format="%.2f")
        with c4: price = st.number_input("NAV/Giá", value=safe_float(row.get('price')), min_value=0.0, format="%.0f")
        note = st.text_input("Ghi chú", value=row.get('note', '') or '')
        if st.form_submit_button("💾 CẬP NHẬT", use_container_width=True):
            supabase.table("ccq_funds").update({"platform": platform, "fund_owner": fund_owner, "ticker": ticker.upper().strip(), "action": action, "volume": float(volume), "price": float(price), "note": note}).eq("id", row['id']).execute()
            st.session_state.editing_ccq = None
            st.toast("✅ Đã cập nhật!", icon="📊"); time.sleep(1); st.rerun()

@st.dialog("✏️ SỬA GD VÀNG")
def modal_edit_gold():
    row = st.session_state.editing_gold
    if not row:
        st.warning("Không có dữ liệu."); return
    with st.form("edit_gold_form"):
        c1, c2 = st.columns(2)
        with c1: gold_type = st.selectbox("Loại Vàng", GOLD_TYPES, index=GOLD_TYPES.index(row['gold_type']) if row.get('gold_type') in GOLD_TYPES else 0)
        with c2: fund_owner = st.selectbox("Portfolio", FUNDS, index=FUNDS.index(row['fund_owner']) if row.get('fund_owner') in FUNDS else 0)
        action = st.radio("Lệnh", ["Mua", "Bán"], index=0 if 'Mua' in str(row.get('action', '')) else 1, horizontal=True)
        c3, c4 = st.columns(2)
        with c3: qty = st.number_input("Số lượng (Chỉ)", value=safe_float(row.get('quantity')), min_value=0.0, format="%.2f")
        with c4: price = st.number_input("Đơn giá", value=safe_float(row.get('price')), min_value=0.0, format="%.0f")
        note = st.text_input("Ghi chú", value=row.get('note', '') or '')
        if st.form_submit_button("💾 CẬP NHẬT", use_container_width=True):
            supabase.table("gold").update({"gold_type": gold_type, "fund_owner": fund_owner, "action": action, "quantity": float(qty), "price": float(price), "note": note}).eq("id", row['id']).execute()
            st.session_state.editing_gold = None
            st.toast("✅ Đã cập nhật!", icon="🥇"); time.sleep(1); st.rerun()

@st.dialog("✏️ SỬA SỔ TIẾT KIỆM")
def modal_edit_savings():
    row = st.session_state.editing_savings
    if not row:
        st.warning("Không có dữ liệu."); return
    with st.form("edit_savings_form"):
        fund_owner = st.selectbox("Quỹ", FUNDS, index=FUNDS.index(row['fund_owner']) if row.get('fund_owner') in FUNDS else 0)
        c1, c2 = st.columns(2)
        with c1: amount = st.number_input("Số tiền", value=int(safe_float(row.get('amount'))), min_value=0, step=1000000, format="%d")
        with c2: rate = st.number_input("Lãi suất (%/năm)", value=safe_float(row.get('interest_rate')), min_value=0.0, step=0.1, format="%.1f")
        c3, c4 = st.columns(2)
        with c3: term = st.number_input("Kỳ hạn (tháng)", value=int(safe_float(row.get('term'))), min_value=0, step=1)
        with c4: bank = st.text_input("Ngân hàng", value=row.get('bank', '') or '')
        note = st.text_input("Ghi chú", value=row.get('note', '') or '')
        if st.form_submit_button("💾 CẬP NHẬT", use_container_width=True):
            supabase.table("savings").update({"fund_owner": fund_owner, "amount": int(amount), "interest_rate": float(rate), "term": int(term), "bank": bank, "note": note}).eq("id", row['id']).execute()
            st.session_state.editing_savings = None
            st.toast("✅ Đã cập nhật!", icon="💰"); time.sleep(1); st.rerun()

@st.dialog("✏️ SỬA THÔNG TIN BĐS")
def modal_edit_realestate():
    row = st.session_state.editing_realestate
    if not row:
        st.warning("Không có dữ liệu."); return
    with st.form("edit_re_form"):
        project_name = st.text_input("Tên dự án", value=row.get('project_name', row.get('name', '')) or '')
        c1, c2 = st.columns(2)
        with c1: cv = st.number_input("Giá trị HĐ", value=int(safe_float(row.get('contract_value'))), min_value=0, step=1000000, format="%d")
        with c2: installment_name = st.text_input("Tên đợt", value=row.get('installment_name', 'Đợt 1') or 'Đợt 1')
        c3, c4 = st.columns(2)
        with c3: amount = st.number_input("Số tiền đợt này", value=int(safe_float(row.get('amount', row.get('paid_amount', 0)))), min_value=0, step=1000000, format="%d")
        with c4: funding_source = st.selectbox("Nguồn tiền", FUNDING_SOURCES, index=FUNDING_SOURCES.index(row['funding_source']) if row.get('funding_source') in FUNDING_SOURCES else 0)
        c5, c6 = st.columns(2)
        with c5:
            d_val = pd.to_datetime(row.get('due_date')).date() if row.get('due_date') and not pd.isna(row.get('due_date')) else date.today()
            due_date = st.date_input("Hạn thanh toán", value=d_val)
        with c6:
            statuses = ["Chưa thanh toán", "Đã thanh toán"]
            status = st.selectbox("Trạng thái", statuses, index=statuses.index(row['status']) if row.get('status') in statuses else 0)
        note = st.text_input("Ghi chú", value=row.get('note', '') or '')
        if st.form_submit_button("💾 CẬP NHẬT", use_container_width=True):
            supabase.table("realestate").update({
                "project_name": project_name,
                "contract_value": int(cv),
                "installment_name": installment_name,
                "amount": int(amount),
                "funding_source": funding_source,
                "due_date": str(due_date),
                "status": status,
                "note": note
            }).eq("id", row['id']).execute()
            st.session_state.editing_realestate = None
            st.toast("✅ Đã cập nhật!", icon="🏠"); time.sleep(1); st.rerun()

@st.dialog("✏️ SỬA KHOẢN VAY")
def modal_edit_debt():
    row = st.session_state.editing_debt
    if not row:
        st.warning("Không có dữ liệu."); return
    with st.form("edit_debt_form"):
        purpose = st.text_input("Mục đích", value=row.get('purpose', '') or '')
        bank_list = BANK_ACCOUNTS + ["Khác"]
        bank = st.selectbox("Ngân hàng", bank_list, index=bank_list.index(row['bank']) if row.get('bank') in bank_list else 0)
        c1, c2 = st.columns(2)
        with c1: principal = st.number_input("Gốc ban đầu", value=int(safe_float(row.get('original_principal'))), min_value=0, step=1000000, format="%d")
        with c2: total_months = st.number_input("Tổng tháng", value=int(safe_float(row.get('total_months'))), min_value=1, step=1)
        c3, c4 = st.columns(2)
        with c3: rate = st.number_input("Lãi suất (%/năm)", value=safe_float(row.get('interest_rate')), min_value=0.0, step=0.1, format="%.2f")
        with c4: payment_day = st.number_input("Ngày TT (mùng)", value=int(safe_float(row.get('payment_day', 5))), min_value=1, max_value=31)
        grace = st.number_input("Ân hạn gốc (tháng)", value=int(safe_float(row.get('grace_period'))), min_value=0, step=1)
        if st.form_submit_button("💾 CẬP NHẬT", use_container_width=True):
            supabase.table("debts").update({"purpose": purpose, "bank": bank, "original_principal": int(principal), "total_months": int(total_months), "interest_rate": float(rate), "payment_day": int(payment_day), "grace_period": int(grace)}).eq("id", row['id']).execute()
            st.session_state.editing_debt = None
            st.toast("✅ Đã cập nhật!", icon="🏦"); time.sleep(1); st.rerun()

# =====================================================================
# 7. QUICK ACTION BUTTONS
# =====================================================================
st.markdown('<div class="metric-title" style="margin-bottom:10px;">⚡ THAO TÁC NHANH</div>', unsafe_allow_html=True)
qa1, qa2, qa3, qa4 = st.columns(4)
with qa1:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("💸\nNhập Chi Tiêu", key="qa_cf", use_container_width=True): modal_cashflow()
    st.markdown('</div>', unsafe_allow_html=True)
with qa2:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("📈\nCổ Phiếu", key="qa_stk", use_container_width=True): modal_stock()
    st.markdown('</div>', unsafe_allow_html=True)
with qa3:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("📊\nChứng Chỉ Quỹ", key="qa_ccq", use_container_width=True): modal_ccq()
    st.markdown('</div>', unsafe_allow_html=True)
with qa4:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("🥇\nVàng", key="qa_gld", use_container_width=True): modal_gold()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# =====================================================================
# 8. DATA FETCHING — ALL 8 TABLES FROM SUPABASE
# =====================================================================
df_cf = fetch_table("cashflow")
df_stk = fetch_table("stocks")
df_ccq = fetch_table("ccq_funds")
df_gold = fetch_table("gold")
df_savings = fetch_table("savings")
df_re = fetch_table("realestate")
df_debts = fetch_table("debts")
df_ob = fetch_table("opening_balances")

# =====================================================================
# METRIC PRE-COMPUTATION FOR ACCURACY & TABS
# =====================================================================

# 1. CASH (TIỀN MẶT): Opening balances (DEBIT + BROKER) + Income - Expenses
target_accounts = DEBIT_ACCOUNTS + BROKER_ACCOUNTS
df_ob_target = df_ob[df_ob['account'].isin(target_accounts)] if not df_ob.empty and 'account' in df_ob.columns else pd.DataFrame()
df_ob_f = filter_by_member(df_ob_target, current_member, col='account')
col_ob = 'balance' if 'balance' in df_ob_f.columns else ('amount' if 'amount' in df_ob_f.columns else None)
sum_ob = pd.to_numeric(df_ob_f[col_ob], errors='coerce').fillna(0).sum() if (not df_ob_f.empty and col_ob) else 0.0

df_cf_f_cash = filter_by_member(df_cf, current_member, col='account')
sum_income, sum_expense = 0.0, 0.0
if not df_cf_f_cash.empty and 'category' in df_cf_f_cash.columns and 'amount' in df_cf_f_cash.columns:
    df_cf_f_cash['amount_num'] = pd.to_numeric(df_cf_f_cash['amount'], errors='coerce').fillna(0)
    sum_income = df_cf_f_cash[df_cf_f_cash['category'] == 'Lương/Thu nhập']['amount_num'].sum()
    sum_expense = df_cf_f_cash[df_cf_f_cash['category'] != 'Lương/Thu nhập']['amount_num'].sum()

tong_tien_mat = sum_ob + sum_income - sum_expense

# 2. REAL ESTATE (BĐS): Sum of 'amount' column WHERE status == 'Đã thanh toán'
bds_da_dong = 0.0
if not df_re.empty and 'amount' in df_re.columns:
    df_re_paid = df_re[df_re['status'].astype(str).str.strip() == 'Đã thanh toán'] if 'status' in df_re.columns else df_re
    df_re_paid_f = filter_by_member(df_re_paid, current_member, col='project_name')
    bds_da_dong = pd.to_numeric(df_re_paid_f['amount'], errors='coerce').fillna(0).sum()

# 3. INVESTMENTS (STOCKS, CCQ, GOLD)
df_stk_f = filter_by_member(df_stk, current_member)
_, tong_cp = calc_investment_total(df_stk_f, 'ticker')

df_ccq_f = filter_by_member(df_ccq, current_member)
_, tong_ccq = calc_investment_total(df_ccq_f, 'ticker')

df_gold_f = filter_by_member(df_gold, current_member)
_, tong_vang = calc_investment_total(df_gold_f, 'gold_type', vol_col='quantity')

# 4. SAVINGS (TIẾT KIỆM)
df_savings_f = filter_by_member(df_savings, current_member, col='fund_owner')
tong_tiet_kiem = pd.to_numeric(df_savings_f['amount'], errors='coerce').fillna(0).sum() if not df_savings_f.empty and 'amount' in df_savings_f.columns else 0.0

# 5. DEBTS (NỢ)
no_khoan_vay = 0.0
df_debts_f = filter_by_member(df_debts, current_member)
if not df_debts_f.empty:
    today_dt = pd.to_datetime(date.today())
    for _, row in df_debts_f.iterrows():
        principal = safe_float(row.get('original_principal'))
        months = int(safe_float(row.get('total_months')))
        grace = int(safe_float(row.get('grace_period')))
        pay_day = int(safe_float(row.get('payment_day', 5)))
        start_dt = row.get('start_date')
        if pd.isna(start_dt):
            continue
        months_diff = (today_dt.year - start_dt.year) * 12 + (today_dt.month - start_dt.month)
        if today_dt.day < pay_day:
            months_diff -= 1
        months_elapsed = max(0, min(months_diff, months))
        effective_months = max(1, months - grace)
        monthly_principal = principal / effective_months
        balance = max(0, principal - (monthly_principal * max(0, months_elapsed - grace)))
        no_khoan_vay += balance

# =====================================================================
# 9. TAB DEFINITIONS
# =====================================================================
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# =====================================================================
# TAB 0: TỔNG QUAN
# =====================================================================
with tab_home:
    tong_tai_san = tong_tien_mat + tong_tiet_kiem + tong_ccq + tong_cp + bds_da_dong + tong_vang

    net_worth_dashboard(tong_tai_san, no_khoan_vay)

    st.subheader("CƠ CẤU PHÂN BỔ TÀI SẢN")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: st.metric("💵 Tiền mặt", f"{tong_tien_mat:,.0f} ₫")
    with m2: st.metric("💰 Tiết kiệm", f"{tong_tiet_kiem:,.0f} ₫")
    with m3: st.metric("🏠 BĐS", f"{bds_da_dong:,.0f} ₫")
    with m4: st.metric("📊 CCQ", f"{tong_ccq:,.0f} ₫")
    with m5: st.metric("📈 Cổ phiếu", f"{tong_cp:,.0f} ₫")
    with m6: st.metric("🥇 Vàng", f"{tong_vang:,.0f} ₫")

    st.markdown("<br/>", unsafe_allow_html=True)

    if tong_tai_san > 0:
        df_chart = pd.DataFrame({
            "Danh mục": ["Tiền mặt", "Tiết kiệm", "BĐS", "CCQ", "Cổ phiếu", "Vàng"],
            "Giá trị": [tong_tien_mat, tong_tiet_kiem, bds_da_dong, tong_ccq, tong_cp, tong_vang]
        })
        df_chart = df_chart[df_chart["Giá trị"] > 0]
        fig = px.pie(df_chart, names="Danh mục", values="Giá trị", hole=0.55,
                     color_discrete_sequence=["#10b981", "#38bdf8", "#f59e0b", "#8b5cf6", "#eab308", "#ef4444"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f8fafc",
                          legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                          margin=dict(t=10, b=10, l=10, r=10))
        fig.update_traces(textposition='inside', textinfo='percent+label')
        _, col_center, _ = st.columns([0.5, 2, 0.5])
        with col_center:
            st.plotly_chart(fig, use_container_width=True, key="pie_overview")

    # Trend chart
    def plot_trend(asset_val, debt_val):
        dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
        np.random.seed(42)
        a = np.linspace(asset_val * 0.9, asset_val, 30) + np.random.normal(0, max(asset_val * 0.01, 1), 30)
        d = np.linspace(debt_val * 1.05, debt_val, 30) - np.random.normal(0, max(debt_val * 0.005, 1), 30)
        df_t = pd.DataFrame({'Date': dates, 'Asset': np.maximum(a, 0), 'Debt': np.maximum(d, 0)})
        df_t['Net'] = df_t['Asset'] - df_t['Debt']
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=df_t['Date'], y=df_t['Debt'], mode='lines', fill='tozeroy', name='Nợ',
                                   line=dict(color='#FF7F50', width=2), fillcolor='rgba(255,127,80,0.4)',
                                   hovertemplate="<b>%{x|%d/%m}</b><br>Nợ: %{y:,.0f}₫<extra></extra>"))
        fig_t.add_trace(go.Scatter(x=df_t['Date'], y=df_t['Asset'], mode='lines', fill='tonexty', name='Tài sản',
                                   line=dict(color='#008080', width=2), fillcolor='rgba(0,128,128,0.4)',
                                   customdata=df_t['Net'],
                                   hovertemplate="<b>%{x|%d/%m}</b><br>TS: %{y:,.0f}₫<br>Ròng: %{customdata:,.0f}₫<extra></extra>"))
        fig_t.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            hovermode="x unified", margin=dict(t=30, b=10, l=0, r=0),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            title="📈 Xu hướng Tài sản & Nợ (30 ngày)", title_font=dict(family="Playfair Display", size=20))
        fig_t.update_xaxes(showgrid=False, zeroline=False)
        fig_t.update_yaxes(showgrid=False, zeroline=False)
        return fig_t

    st.plotly_chart(plot_trend(tong_tai_san, no_khoan_vay), use_container_width=True, key="trend_chart")

# =====================================================================
# TAB 1: DÒNG TIỀN
# =====================================================================
with tab_cashflow:
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">DÒNG TIỀN{f" ({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)
    df_cf_f = filter_by_member(df_cf, current_member, col='account')
    today = date.today()
    month_start = today.replace(day=1)

    if not df_cf_f.empty and 'created_at' in df_cf_f.columns:
        fc1, fc2 = st.columns(2)
        with fc1: d_start = st.date_input("Từ ngày", month_start, key="cf_d1")
        with fc2: d_end = st.date_input("Đến ngày", today, key="cf_d2")
        mask = (df_cf_f['created_at'].dt.date >= d_start) & (df_cf_f['created_at'].dt.date <= d_end)
        df_period = df_cf_f[mask].copy()
    else:
        df_period = pd.DataFrame()

    tong_thu, tong_chi = 0, 0
    if not df_period.empty and 'amount' in df_period.columns:
        df_period['amount'] = pd.to_numeric(df_period['amount'], errors='coerce').fillna(0)
        tong_thu = df_period[df_period['category'] == 'Lương/Thu nhập']['amount'].sum()
        tong_chi = df_period[df_period['category'] != 'Lương/Thu nhập']['amount'].sum()

    mc1, mc2 = st.columns(2)
    with mc1:
        st.markdown(f'<div class="ios-card"><div class="savings-goal-title" style="color:#f87171;">💸 ĐÃ CHI</div><div style="font-size:2rem;font-weight:bold;">{tong_chi:,.0f} ₫</div></div>', unsafe_allow_html=True)
    with mc2:
        st.markdown(f'<div class="ios-card"><div class="savings-goal-title" style="color:#4ade80;">🤑 TỔNG THU</div><div style="font-size:2rem;font-weight:bold;">{tong_thu:,.0f} ₫</div></div>', unsafe_allow_html=True)

    with st.expander("⚙️ CẤU HÌNH NGÂN SÁCH & LỌC DỮ LIỆU", expanded=False):
        bt1, bt2 = st.tabs(["📊 Lọc giao dịch", "⚙️ Cấu hình Ngân sách"])
        with bt2:
            st.markdown("### Thiết lập Ngân sách Chi tiêu Tháng")
            bg1, bg2 = st.columns(2)
            for idx_cat, cat in enumerate(EXPENSE_CATS):
                with (bg1 if idx_cat % 2 == 0 else bg2):
                    st.session_state.cat_budgets[cat] = st.number_input(
                        f"{cat}", value=st.session_state.cat_budgets.get(cat, 3000000),
                        step=500000, format="%d", key=f"budget_{idx_cat}")
        with bt1:
            if not df_period.empty:
                display_cols = [c for c in ['created_at', 'account', 'category', 'amount', 'note'] if c in df_period.columns]
                st.dataframe(df_period[display_cols].sort_values('created_at', ascending=False), hide_index=True, use_container_width=True,
                    column_config={"created_at": st.column_config.DatetimeColumn("Ngày", format="DD/MM/YYYY HH:mm"), "amount": st.column_config.NumberColumn("Số tiền", format="%,.0f ₫"), "account": "Tài khoản", "category": "Danh mục", "note": "Ghi chú"})
            else:
                st.info("Không có giao dịch trong kỳ.")

    st.markdown("<br/>", unsafe_allow_html=True)
    col_pie, col_budget = st.columns([1, 1])
    selected_cat = None
    with col_pie:
        st.subheader("📊 Phân bổ chi tiêu")
        if not df_period.empty:
            df_exp = df_period[df_period['category'] != 'Lương/Thu nhập']
            if not df_exp.empty:
                df_pie = df_exp.groupby('category')['amount'].sum().reset_index()
                palette = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#1A535C', '#8b5cf6', '#F7FFF7', '#FF8C42', '#38bdf8']
                fig = px.pie(df_pie, names='category', values='amount', hole=0.55, color_discrete_sequence=palette)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f8fafc", showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="pie_cf")
                if event and isinstance(event, dict) and event.get("selection"):
                    pts = event["selection"].get("points", [])
                    if pts:
                        selected_cat = pts[0].get("label")
            else:
                st.info("Chưa có chi tiêu.")
        else:
            st.info("Không có dữ liệu.")

    with col_budget:
        st.subheader("🎯 Ngân sách")
        if not df_period.empty:
            df_exp = df_period[df_period['category'] != 'Lương/Thu nhập']
            cats_show = [selected_cat] if selected_cat else EXPENSE_CATS
            for cat in cats_show:
                spent = df_exp[df_exp['category'] == cat]['amount'].sum() if not df_exp.empty and cat in df_exp['category'].values else 0
                if spent > 0 or cat == selected_cat:
                    limit = st.session_state.cat_budgets.get(cat, 0)
                    pct = (spent / limit) * 100 if limit > 0 else (100 if spent > 0 else 0)
                    color = "#4ade80" if pct <= 50 else ("#facc15" if pct <= 80 else "#f87171")
                    card_bg_html = f"""<div class="ios-card" style="margin-bottom:10px;padding:15px;">
<div style="display:flex;justify-content:space-between;"><b>{cat}</b><span>{spent:,.0f} / {limit:,.0f} ₫</span></div>
<div class="progress-container" style="margin-top:8px;"><div class="progress-bar-fill" style="width:{min(pct,100)}%;background-color:{color};"></div></div>
</div>"""
                    st.markdown(card_bg_html, unsafe_allow_html=True)

# =====================================================================
# TAB 2: ĐẦU TƯ
# =====================================================================
with tab_invest:
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">DANH MỤC ĐẦU TƯ{f" ({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)
    inv_stk, inv_ccq, inv_gld = st.tabs(["📈 Chứng khoán", "📊 Chứng chỉ quỹ", "🥇 Vàng"])

    # --- STOCKS ---
    with inv_stk:
        stk_sum_tab, stk_hist_tab = st.tabs(["📊 Tổng hợp", "📋 Lịch sử GD"])
        with stk_sum_tab:
            summary_stk, _ = calc_investment_total(df_stk_f, 'ticker')
            if not summary_stk.empty:
                st.dataframe(summary_stk, hide_index=True, use_container_width=True,
                    column_config={"Giá vốn TB": st.column_config.NumberColumn(format="%,.0f ₫"), "Giá trị": st.column_config.NumberColumn(format="%,.0f ₫"), "SL nắm giữ": st.column_config.NumberColumn(format="%,.0f")})
                st.metric("📈 Tổng giá trị Cổ phiếu", f"{tong_cp:,.0f} ₫")
            else:
                st.info("Chưa có vị thế cổ phiếu.")
        with stk_hist_tab:
            if not df_stk_f.empty:
                display_stk = df_stk_f.copy()
                st.dataframe(display_stk, hide_index=True, use_container_width=True,
                    column_config={"id": None, "trade_date": st.column_config.DatetimeColumn("Ngày GD", format="DD/MM/YYYY"), "volume": st.column_config.NumberColumn("KL", format="%d"), "price": st.column_config.NumberColumn("Giá", format="%,.0f ₫")})
                options_stk = [f"{r.get('ticker','')} | {r.get('action','')} | KL:{r.get('volume','')} | {str(r.get('trade_date',''))[:10]}" for _, r in df_stk_f.iterrows()]
                sel_idx_stk = st.selectbox("Chọn GD để sửa/xóa", range(len(options_stk)), format_func=lambda i: options_stk[i], key="sel_stk")
                ce1, ce2 = st.columns(2)
                with ce1:
                    if st.button("✏️ SỬA", key="btn_edit_stk", use_container_width=True):
                        st.session_state.editing_stock = df_stk_f.iloc[sel_idx_stk].to_dict()
                with ce2:
                    if st.button("❌ XÓA", key="btn_del_stk", use_container_width=True):
                        supabase.table("stocks").delete().eq("id", df_stk_f.iloc[sel_idx_stk]['id']).execute()
                        st.toast("🗑️ Đã xóa!", icon="✅"); time.sleep(1); st.rerun()
                if st.session_state.get("editing_stock"):
                    modal_edit_stock()
            else:
                st.info("Chưa có giao dịch cổ phiếu.")

    # --- CCQ ---
    with inv_ccq:
        ccq_sum_tab, ccq_hist_tab = st.tabs(["📊 Tổng hợp", "📋 Lịch sử GD"])
        with ccq_sum_tab:
            summary_ccq, _ = calc_investment_total(df_ccq_f, 'ticker')
            if not summary_ccq.empty:
                st.dataframe(summary_ccq, hide_index=True, use_container_width=True,
                    column_config={"Giá vốn TB": st.column_config.NumberColumn(format="%,.0f ₫"), "Giá trị": st.column_config.NumberColumn(format="%,.0f ₫"), "SL nắm giữ": st.column_config.NumberColumn(format="%,.2f")})
                st.metric("📊 Tổng giá trị CCQ", f"{tong_ccq:,.0f} ₫")
            else:
                st.info("Chưa có vị thế CCQ.")
        with ccq_hist_tab:
            if not df_ccq_f.empty:
                st.dataframe(df_ccq_f, hide_index=True, use_container_width=True,
                    column_config={"id": None, "trade_date": st.column_config.DatetimeColumn("Ngày GD", format="DD/MM/YYYY"), "volume": st.column_config.NumberColumn("SL", format="%.2f"), "price": st.column_config.NumberColumn("NAV", format="%,.0f ₫")})
                options_ccq = [f"{r.get('ticker','')} | {r.get('action','')} | {str(r.get('trade_date',''))[:10]}" for _, r in df_ccq_f.iterrows()]
                sel_idx_ccq = st.selectbox("Chọn GD để sửa/xóa", range(len(options_ccq)), format_func=lambda i: options_ccq[i], key="sel_ccq")
                ce1, ce2 = st.columns(2)
                with ce1:
                    if st.button("✏️ SỬA", key="btn_edit_ccq", use_container_width=True):
                        st.session_state.editing_ccq = df_ccq_f.iloc[sel_idx_ccq].to_dict()
                with ce2:
                    if st.button("❌ XÓA", key="btn_del_ccq", use_container_width=True):
                        supabase.table("ccq_funds").delete().eq("id", df_ccq_f.iloc[sel_idx_ccq]['id']).execute()
                        st.toast("🗑️ Đã xóa!", icon="✅"); time.sleep(1); st.rerun()
                if st.session_state.get("editing_ccq"):
                    modal_edit_ccq()
            else:
                st.info("Chưa có giao dịch CCQ.")

    # --- GOLD ---
    with inv_gld:
        gld_sum_tab, gld_hist_tab = st.tabs(["📊 Tổng hợp", "📋 Lịch sử GD"])
        with gld_sum_tab:
            summary_gld, _ = calc_investment_total(df_gold_f, 'gold_type', vol_col='quantity')
            if not summary_gld.empty:
                st.dataframe(summary_gld, hide_index=True, use_container_width=True,
                    column_config={"Giá vốn TB": st.column_config.NumberColumn(format="%,.0f ₫"), "Giá trị": st.column_config.NumberColumn(format="%,.0f ₫"), "SL nắm giữ": st.column_config.NumberColumn(format="%,.2f")})
                st.metric("🥇 Tổng giá trị Vàng", f"{tong_vang:,.0f} ₫")
            else:
                st.info("Chưa có vị thế Vàng.")
        with gld_hist_tab:
            if not df_gold_f.empty:
                st.dataframe(df_gold_f, hide_index=True, use_container_width=True,
                    column_config={"id": None, "trade_date": st.column_config.DatetimeColumn("Ngày GD", format="DD/MM/YYYY"), "quantity": st.column_config.NumberColumn("SL (Chỉ)", format="%.2f"), "price": st.column_config.NumberColumn("Giá", format="%,.0f ₫")})
                options_gld = [f"{r.get('gold_type','')} | {r.get('action','')} | {r.get('quantity','')} chỉ | {str(r.get('trade_date',''))[:10]}" for _, r in df_gold_f.iterrows()]
                sel_idx_gld = st.selectbox("Chọn GD để sửa/xóa", range(len(options_gld)), format_func=lambda i: options_gld[i], key="sel_gld")
                ce1, ce2 = st.columns(2)
                with ce1:
                    if st.button("✏️ SỬA", key="btn_edit_gld", use_container_width=True):
                        st.session_state.editing_gold = df_gold_f.iloc[sel_idx_gld].to_dict()
                with ce2:
                    if st.button("❌ XÓA", key="btn_del_gld", use_container_width=True):
                        supabase.table("gold").delete().eq("id", df_gold_f.iloc[sel_idx_gld]['id']).execute()
                        st.toast("🗑️ Đã xóa!", icon="✅"); time.sleep(1); st.rerun()
                if st.session_state.get("editing_gold"):
                    modal_edit_gold()
            else:
                st.info("Chưa có giao dịch Vàng.")

# =====================================================================
# TAB 3: TIẾT KIỆM
# =====================================================================
with tab_savings:
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">TIẾT KIỆM MỤC TIÊU{f" ({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)

    if st.button("➕ TẠO SỔ TIẾT KIỆM MỚI", key="btn_add_savings", type="primary", use_container_width=True):
        modal_add_savings()

    # Summary cards
    sc1, sc2, sc3 = st.columns(3)
    cols_sv = [sc1, sc2, sc3]
    for i, fund_name in enumerate(FUNDS):
        if not fund_matches_member(fund_name, current_member):
            continue
        target = SAVINGS_GOALS.get(fund_name, 300_000_000)
        theme = FUND_THEME_MAP.get(fund_name, "card-daddy")
        fund_total, fund_interest = 0, 0
        if not df_savings.empty and 'fund_owner' in df_savings.columns:
            fund_df = df_savings[df_savings['fund_owner'] == fund_name]
            for _, r in fund_df.iterrows():
                amt = safe_float(r.get('amount'))
                rate = safe_float(r.get('interest_rate'))
                trm = safe_float(r.get('term'))
                fund_total += amt
                if rate > 0 and trm > 0:
                    fund_interest += amt * (rate / 100.0) * (trm / 12.0)
        pct = fund_total / target if target > 0 else 0
        with cols_sv[i % 3]:
            interest_html = f'<div style="font-size:0.85rem;color:#4ade80;margin-top:5px;">+ Lãi dự kiến: {fund_interest:,.0f} ₫</div>' if fund_interest > 0 else ''
            card_html = f"""<div class="ios-card {theme}" style="min-height:180px;">
<div class="savings-goal-title">{fund_name}</div>
<div style="font-size:1.8rem;font-weight:700;font-family:'Playfair Display';">{fund_total:,.0f} ₫</div>
<div style="font-size:0.85rem;opacity:0.8;margin-top:5px;">Mục tiêu: {target:,.0f} ₫ ({pct*100:.1f}%)</div>
{interest_html}
<div class="progress-container" style="margin-top:12px;background-color:rgba(255,255,255,0.3);">
<div class="progress-bar-fill" style="width:{min(pct*100,100)}%;background-color:white;"></div>
</div>
</div>"""
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Detailed view per fund
    for fund_name in FUNDS:
        if not fund_matches_member(fund_name, current_member):
            continue
        st.subheader(f"💰 {fund_name}")
        if not df_savings.empty and 'fund_owner' in df_savings.columns:
            fund_df = df_savings[df_savings['fund_owner'] == fund_name].copy()
            if not fund_df.empty:
                fund_df['amount'] = pd.to_numeric(fund_df['amount'], errors='coerce').fillna(0)
                st.dataframe(fund_df, hide_index=True, use_container_width=True, column_config={
                    "id": None, "fund_owner": None,
                    "amount": st.column_config.NumberColumn("Số tiền", format="%,.0f ₫"),
                    "interest_rate": st.column_config.NumberColumn("Lãi suất (%)", format="%.1f"),
                    "term": st.column_config.NumberColumn("Kỳ hạn (th)"),
                    "bank": "Ngân hàng", "note": "Ghi chú",
                    "created_at": st.column_config.DatetimeColumn("Ngày tạo", format="DD/MM/YYYY"),
                })
                safe_key = fund_name.replace(" ", "_")
                options_sv = [f"#{r.get('id','')} | {safe_float(r.get('amount')):,.0f}₫ | LS:{r.get('interest_rate',0)}% | {r.get('term',0)}th" for _, r in fund_df.iterrows()]
                sel_sv = st.selectbox("Chọn sổ tiết kiệm", range(len(options_sv)), format_func=lambda i: options_sv[i], key=f"sel_sv_{safe_key}")
                sv_e1, sv_e2 = st.columns(2)
                with sv_e1:
                    if st.button("✏️ SỬA SỔ", key=f"btn_edit_sv_{safe_key}", use_container_width=True):
                        st.session_state.editing_savings = fund_df.iloc[sel_sv].to_dict()
                with sv_e2:
                    if st.button("❌ TẤT TOÁN", key=f"btn_del_sv_{safe_key}", use_container_width=True):
                        supabase.table("savings").delete().eq("id", fund_df.iloc[sel_sv]['id']).execute()
                        st.toast("🗑️ Đã tất toán!", icon="✅"); time.sleep(1); st.rerun()
            else:
                st.info(f"Chưa có sổ tiết kiệm nào cho {fund_name}.")
        else:
            st.info("Bảng savings chưa có dữ liệu.")

    if st.session_state.get("editing_savings"):
        modal_edit_savings()

# =====================================================================
# TAB 4: BĐS & TÍN DỤNG
# =====================================================================
with tab_realestate:
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">BẤT ĐỘNG SẢN & KHOẢN VAY{f" ({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)

    btn_re1, btn_re2 = st.columns(2)
    with btn_re1:
        if st.button("🏠 + THÊM TIẾN ĐỘ BĐS", key="btn_add_re", use_container_width=True, type="primary"):
            modal_add_realestate()
    with btn_re2:
        if st.button("🏦 + THÊM KHOẢN VAY", key="btn_add_debt", use_container_width=True, type="primary"):
            modal_debt()

    st.markdown("<br/>", unsafe_allow_html=True)

    # --- REAL ESTATE ---
    st.subheader("🏠 Bất động sản đang sở hữu")
    df_re_f = filter_by_member(df_re, current_member, col='project_name')
    if not df_re_f.empty:
        display_cols = [c for c in ['project_name', 'contract_value', 'installment_name', 'amount', 'funding_source', 'due_date', 'status', 'note'] if c in df_re_f.columns]
        st.dataframe(
            df_re_f[display_cols],
            hide_index=True,
            use_container_width=True,
            column_config={
                "project_name": "Dự án",
                "contract_value": st.column_config.NumberColumn("Giá trị HĐ", format="%,.0f ₫"),
                "installment_name": "Tên đợt",
                "amount": st.column_config.NumberColumn("Số tiền đợt này", format="%,.0f ₫"),
                "funding_source": "Nguồn tiền",
                "due_date": st.column_config.DatetimeColumn("Hạn TT", format="DD/MM/YYYY"),
                "status": "Trạng thái",
                "note": "Ghi chú"
            }
        )

        options_re = [f"{r.get('project_name', 'BĐS')} | {r.get('installment_name', '')} | {safe_float(r.get('amount', 0)):,.0f}₫ ({r.get('status','')})" for _, r in df_re_f.iterrows()]
        sel_re = st.selectbox("Chọn đợt BĐS để sửa/xóa", range(len(options_re)), format_func=lambda i: options_re[i], key="sel_re")
        re_e1, re_e2 = st.columns(2)
        with re_e1:
            if st.button("✏️ SỬA", key="btn_edit_re", use_container_width=True):
                st.session_state.editing_realestate = df_re_f.iloc[sel_re].to_dict()
        with re_e2:
            if st.button("❌ XÓA", key="btn_del_re", use_container_width=True):
                supabase.table("realestate").delete().eq("id", df_re_f.iloc[sel_re]['id']).execute()
                st.toast("🗑️ Đã xóa!", icon="✅"); time.sleep(1); st.rerun()
        if st.session_state.get("editing_realestate"):
            modal_edit_realestate()
    else:
        st.info("Chưa có bất động sản nào.")

    st.markdown("---", unsafe_allow_html=True)

    # --- DEBTS ---
    st.subheader("🏦 Quản lý Khoản Vay")
    df_debts_f = filter_by_member(df_debts, current_member)
    if not df_debts_f.empty:
        debt_summary_rows = []
        today_dt = pd.to_datetime(date.today())
        for _, row in df_debts_f.iterrows():
            principal = safe_float(row.get('original_principal'))
            rate = safe_float(row.get('interest_rate'))
            months = int(safe_float(row.get('total_months')))
            grace = int(safe_float(row.get('grace_period')))
            pay_day = int(safe_float(row.get('payment_day', 5)))
            start_dt = row.get('start_date')
            if pd.isna(start_dt):
                continue

            months_diff = (today_dt.year - start_dt.year) * 12 + (today_dt.month - start_dt.month)
            if today_dt.day < pay_day:
                months_diff -= 1
            months_elapsed = max(0, min(months_diff, months))
            effective_months = max(1, months - grace)
            monthly_principal = principal / effective_months
            balance = principal - (monthly_principal * max(0, months_elapsed - grace))
            balance = max(0, balance)
            monthly_interest = balance * (rate / 100.0 / 12.0)
            goc_thang = 0 if months_elapsed < grace else monthly_principal

            next_m = today_dt.month + (1 if today_dt.day > pay_day else 0)
            next_y = today_dt.year
            if next_m > 12:
                next_m = 1; next_y += 1
            max_d = calendar.monthrange(next_y, next_m)[1]
            safe_day = min(pay_day, max_d)
            next_pay = datetime(next_y, next_m, safe_day)
            progress_pct = ((principal - balance) / principal * 100) if principal > 0 else 0

            debt_summary_rows.append({
                "Mục đích": row.get('purpose', ''),
                "Ngân hàng": row.get('bank', ''),
                "Gốc ban đầu": principal,
                "Dư nợ hiện tại": balance,
                "Gốc/Tháng": goc_thang,
                "Lãi/Tháng": monthly_interest,
                "Ngày TT tiếp": next_pay.strftime('%d/%m/%Y'),
                "Đã trả (%)": progress_pct,
            })

        if debt_summary_rows:
            df_debt_display = pd.DataFrame(debt_summary_rows)
            st.dataframe(df_debt_display, hide_index=True, use_container_width=True, column_config={
                "Gốc ban đầu": st.column_config.NumberColumn(format="%,.0f ₫"),
                "Dư nợ hiện tại": st.column_config.NumberColumn(format="%,.0f ₫"),
                "Gốc/Tháng": st.column_config.NumberColumn(format="%,.0f ₫"),
                "Lãi/Tháng": st.column_config.NumberColumn(format="%,.0f ₫"),
                "Đã trả (%)": st.column_config.ProgressColumn("Tiến độ", min_value=0, max_value=100, format="%.1f%%"),
            })

        st.metric("💳 Tổng dư nợ hiện tại", f"{no_khoan_vay:,.0f} ₫")

        options_debt = [f"{r.get('purpose', 'Khoản vay')} | {r.get('bank', '')} | Gốc: {safe_float(r.get('original_principal')):,.0f}₫" for _, r in df_debts_f.iterrows()]
        sel_debt = st.selectbox("Chọn khoản vay để sửa/xóa", range(len(options_debt)), format_func=lambda i: options_debt[i], key="sel_debt")
        de1, de2 = st.columns(2)
        with de1:
            if st.button("✏️ SỬA", key="btn_edit_debt", use_container_width=True):
                st.session_state.editing_debt = df_debts_f.iloc[sel_debt].to_dict()
        with de2:
            if st.button("❌ XÓA", key="btn_del_debt", use_container_width=True):
                supabase.table("debts").delete().eq("id", df_debts_f.iloc[sel_debt]['id']).execute()
                st.toast("🗑️ Đã xóa!", icon="✅"); time.sleep(1); st.rerun()
        if st.session_state.get("editing_debt"):
            modal_edit_debt()
    else:
        st.info("Chưa có khoản vay nào.")
