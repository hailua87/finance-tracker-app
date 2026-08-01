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

# --- BẢO MẬT BẰNG MẬT KHẨU ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    st.markdown("<h2 style='text-align: center; margin-top: 50px;'>🔒 Đăng nhập hệ thống</h2>", unsafe_allow_html=True)
    pw = st.text_input("Nhập mật khẩu để truy cập:", type="password")
    
    if pw:
        input_pw = str(pw).strip()
        secret_pw = str(st.secrets.get("APP_PASSWORD", "123456")).strip()
        if input_pw == secret_pw:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Mật khẩu không đúng")
            
    return False

if not check_password():
    st.stop()


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
FUND_MEMBER_MAP = {"Tieu Boi Funding": "Baby", "Daddy Funding": "Daddy", "Mama Funding": "Mommy"}
FUND_THEME_MAP = {"Tieu Boi Funding": "card-baby", "Daddy Funding": "card-daddy", "Mama Funding": "card-mommy"}


def calc_investment_total(df, group_col):
    import pandas as pd
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(), 0
    summary_list = []
    total_val = 0
    for name, grp in df.groupby(group_col):
        buy_rows = grp[grp['action'].str.lower().str.contains('buy|mua', na=False)]
        sell_rows = grp[grp['action'].str.lower().str.contains('sell|bán', na=False)]
        
        col_amt = 'volume' if 'volume' in grp.columns else ('quantity' if 'quantity' in grp.columns else None)
        if not col_amt:
            continue
            
        buy_vol = buy_rows[col_amt].sum()
        sell_vol = sell_rows[col_amt].sum()
        net_vol = buy_vol - sell_vol
        
        buy_val = (buy_rows[col_amt] * buy_rows['price']).sum()
        avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
        cost = net_vol * avg_price
        
        if net_vol > 0:
            summary_list.append({group_col: name, "SL tồn": net_vol, "Giá vốn TB": avg_price, "Tổng vốn": cost})
            total_val += cost
    return pd.DataFrame(summary_list), total_val

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
    "savings_goals": {
        "Tieu Boi Funding": 500_000_000,
        "Daddy Funding": 300_000_000,
        "Mama Funding": 300_000_000,
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
    if col == 'fund_owner':
        valid_funds = [f for f, m in FUND_MEMBER_MAP.items() if m == member]
        if valid_funds:
            return df[df[col].isin(valid_funds)]
        return pd.DataFrame(columns=df.columns)
    elif col == 'account':
        if member == "Daddy":
            return df[df[col].astype(str).str.contains("chồng|Daddy", case=False, na=False)]
        elif member == "Mommy":
            return df[df[col].astype(str).str.contains("vợ|Mommy", case=False, na=False)]
        elif member == "Baby":
            return df[df[col].astype(str).str.contains("baby|con", case=False, na=False)]
    return df[df[col].astype(str).str.contains(member, na=False, case=False)]

def fund_matches_member(fund_name, member):
    if member == "Tất cả":
        return True
    return FUND_MEMBER_MAP.get(fund_name, "") == member

@st.cache_data(ttl=60, show_spinner=False)
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

def clear_cache_and_rerun():
    fetch_table.clear()
    time.sleep(1)
    st.rerun()


# =====================================================================
# 5. SIDEBAR
# =====================================================================
with st.sidebar:
    st.markdown('<div class="hallmark-header" style="font-size:1.5rem;margin-top:20px;">THÀNH VIÊN</div>', unsafe_allow_html=True)
    _members = ["Tất cả", "Daddy", "Mommy", "Baby"]
    _idx = _members.index(st.session_state.current_member) if st.session_state.current_member in _members else 0
    st.session_state.current_member = sac.buttons(
        items=[
            sac.ButtonsItem(label='Tất cả', icon='people-fill', color='gray'),
            sac.ButtonsItem(label='Daddy', icon='person-workspace', color='blue'),
            sac.ButtonsItem(label='Mommy', icon='person-hearts', color='pink'),
            sac.ButtonsItem(label='Baby', icon='person-arms-up', color='green'),
        ], align='center', use_container_width=True, index=_idx, variant='filled'
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
    
    trade_date = st.date_input("Ngày giao dịch", value=date.today(), key="cf_trade_date")
    
    c1, c2 = st.columns(2)
    with c1: category = st.selectbox("Phân loại", CATS, key="cf_cat")
    with c2:
        _ai = BANK_ACCOUNTS.index(st.session_state.last_account) if st.session_state.last_account in BANK_ACCOUNTS else 0
        account = st.selectbox("Tài khoản", BANK_ACCOUNTS, index=_ai, key="cf_acc")
        
    try:
        import pandas as pd
        df_ob_loc = fetch_table("opening_balances")
        df_cf_loc = fetch_table("cashflow")
        ob_val = 0.0
        if not df_ob_loc.empty and 'account' in df_ob_loc.columns:
            ob_row = df_ob_loc[df_ob_loc['account'] == account]
            if not ob_row.empty:
                col_ob = 'balance' if 'balance' in ob_row.columns else 'amount'
                ob_val = pd.to_numeric(ob_row[col_ob], errors='coerce').fillna(0).sum()
        cf_val = 0.0
        if not df_cf_loc.empty and 'account' in df_cf_loc.columns:
            acc_cf = df_cf_loc[df_cf_loc['account'] == account]
            if not acc_cf.empty:
                acc_cf['amount_num'] = pd.to_numeric(acc_cf['amount'], errors='coerce').fillna(0)
                inc = acc_cf[acc_cf['category'] == 'Lương/Thu nhập']['amount_num'].sum()
                exp = acc_cf[acc_cf['category'] != 'Lương/Thu nhập']['amount_num'].sum()
                cf_val = inc - exp
        st.caption(f"💡 Số dư khả dụng ({account}): **{ob_val + cf_val:,.0f} ₫**")
    except: pass
    
    note = st.text_input("Ghi chú", key="cf_note")
    if st.button("💾 LƯU GIAO DỊCH", use_container_width=True, type="primary", key="cf_save"):
        amt = parse_smart_amount(amount_str)
        if amt <= 0:
            st.error("⚠️ Nhập số tiền hợp lệ!")
        else:
            created_at_str = f"{trade_date} {time.strftime('%H:%M:%S')}"
            try:
                supabase.table("cashflow").insert({"account": account, "amount": amt, "category": category, "note": note, "created_at": created_at_str}).execute()
                st.session_state.last_account = account
                st.session_state.cf_amount_str = ""
                st.success("✅ Đã lưu giao dịch thành công!")
                time.sleep(1)
                clear_cache_and_rerun()
            except Exception as e:
                st.error(f"❌ Lỗi kết nối CSDL: {str(e)}")

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
        with c5: trade_date = st.date_input("Ngày GD", value=date.today())
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("💾 LƯU LỆNH", use_container_width=True):
            vol, price = parse_smart_amount(vol_str), parse_smart_amount(price_str)
            if not ticker.strip(): st.error("⚠️ Nhập mã!")
            elif vol <= 0 or price <= 0: st.error("⚠️ KL & Giá > 0!")
            else:
                try:
                    supabase.table("stocks").insert({"trade_date": str(trade_date), "broker": broker, "fund_owner": fund_owner, "ticker": ticker.strip(), "action": action, "volume": int(vol), "price": float(price), "note": note}).execute()
                    st.success("✅ Đã lưu lệnh cổ phiếu thành công!")
                    time.sleep(1)
                    clear_cache_and_rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi kết nối CSDL: {str(e)}")

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("add_ccq_form"):
        c1, c2 = st.columns(2)
        with c1: platform = st.selectbox("Nền tảng", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM", "SSI", "VNDirect"])
        with c2: fund_owner = st.selectbox("Portfolio", FUNDS)
        ticker = st.text_input("Mã Quỹ (VD: DCDS)").upper()
        action = st.radio("Lệnh", ["Mua (SIP)", "Bán"], horizontal=True)
        c3, c4 = st.columns(2)
        with c3: val_str = st.text_input("Tổng giá trị giao dịch (VD: 5tr)")
        with c4: vol_str = st.text_input("Số lượng CCQ (VD: 100)")
        c5, c6 = st.columns(2)
        with c5: trade_date = st.date_input("Ngày GD", value=date.today())
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("💾 LƯU", use_container_width=True):
            total_val, vol = parse_smart_amount(val_str), parse_smart_amount(vol_str)
            if not ticker.strip(): st.error("⚠️ Nhập mã!")
            elif vol <= 0 or total_val <= 0: st.error("⚠️ Giá trị & SL > 0!")
            else:
                nav = total_val / vol
                try:
                    supabase.table("ccq_funds").insert({"trade_date": str(trade_date), "platform": platform, "fund_owner": fund_owner, "ticker": ticker.strip(), "action": action, "volume": float(vol), "price": float(nav), "note": note}).execute()
                    st.success("✅ Đã lưu giao dịch CCQ thành công!")
                    time.sleep(1)
                    clear_cache_and_rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi kết nối CSDL: {str(e)}")

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
        with c5: trade_date = st.date_input("Ngày GD", value=date.today())
        with c6: note = st.text_input("Ghi chú")
        if st.form_submit_button("💾 LƯU", use_container_width=True):
            qty, price = parse_smart_amount(qty_str), parse_smart_amount(price_str)
            if qty <= 0 or price <= 0: st.error("⚠️ SL & Giá > 0!")
            else:
                try:
                    supabase.table("gold").insert({"trade_date": str(trade_date), "gold_type": gold_type, "fund_owner": fund_owner, "action": action, "quantity": float(qty), "price": float(price), "note": note}).execute()
                    st.success("✅ Đã lưu giao dịch vàng thành công!")
                    time.sleep(1)
                    clear_cache_and_rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi kết nối CSDL: {str(e)}")

@st.dialog("THÊM KHOẢN VAY MỚI")
def modal_debt():
    with st.form("add_debt_form"):
        purpose = st.text_input("Mục đích vay")
        bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS + ["Khác"])
        c1, c2 = st.columns(2)
        with c1: vay_str = st.text_input("Tiền vay GỐC (VD: 1.8tỷ)")
        with c2: total_months = st.number_input("Tổng tháng", min_value=1, step=1, value=180)
        c3, c4 = st.columns(2)
        with c3: start_date = st.date_input("Ngày giải ngân", value=date.today())
        with c4: payment_day = st.number_input("Ngày TT (mùng)", min_value=1, max_value=31, value=5)
        c5, c6 = st.columns(2)
        with c5: grace = st.number_input("Ân hạn gốc (tháng)", min_value=0, step=1, value=1)
        with c6: rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, format="%.2f", value=7.3)
        if st.form_submit_button("💾 LƯU KHOẢN VAY", use_container_width=True):
            principal = parse_smart_amount(vay_str)
            if principal <= 0: st.error("⚠️ Tiền vay > 0!")
            else:
                try:
                    supabase.table("debts").insert({"purpose": purpose, "bank": bank, "original_principal": int(principal), "total_months": int(total_months), "start_date": str(start_date), "interest_rate": rate, "payment_day": int(payment_day), "grace_period": int(grace)}).execute()
                    st.success("✅ Đã thêm khoản vay mới thành công!")
                    time.sleep(1)
                    clear_cache_and_rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi kết nối CSDL: {str(e)}")

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
        rc1, rc2 = st.columns(2)
        with rc1:
            bds_name = st.text_input("Tên dự án mới", key="re_bds_name")
        with rc2:
            gia_tri_hd_str = st.text_input("Giá trị HĐ (VD: 3.5tỷ)", key="re_hd_val")
        final_project_name = bds_name.strip()
        final_contract_value = parse_smart_amount(gia_tri_hd_str)
    else:
        final_project_name = selected_proj
        final_contract_value = existing_projects[selected_proj]
        st.info(f"Dự án: **{final_project_name}** | Giá trị HĐ: **{final_contract_value:,.0f} ₫**")

    st.markdown("---", unsafe_allow_html=True)
    st.markdown("### Chi tiết đợt thanh toán", unsafe_allow_html=True)
    
    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        installment_name = st.text_input("Tên đợt (VD: Đợt 1)", value="Đợt 1", key="re_inst_name")
    with r2_c2:
        amount_str = st.text_input("Số tiền thanh toán đợt này (VD: 500tr)", key="re_inst_amt")
    
    r3_c1, r3_c2 = st.columns(2)
    with r3_c1:
        funding_source = st.selectbox("Nguồn tiền", FUNDING_SOURCES, key="re_fund_src")
    with r3_c2:
        due_date = st.date_input("Hạn thanh toán", value=date.today(), key="re_due_date")
        
    r4_c1, r4_c2 = st.columns(2)
    with r4_c1:
        status = st.selectbox("Trạng thái", ["Chưa thanh toán", "Đã thanh toán"], key="re_status")
    with r4_c2:
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
            try:
                supabase.table("realestate").insert(payload).execute()
                st.success("✅ Đã thêm đợt thanh toán BĐS thành công!")
                time.sleep(1)
                clear_cache_and_rerun()
            except Exception as e:
                st.error(f"❌ Lỗi kết nối CSDL: {str(e)}")

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
        with c4: deposit_date = st.date_input("Ngày gửi", value=date.today())
        note = st.text_input("Ghi chú")
        if st.form_submit_button("💾 TẠO SỔ", use_container_width=True):
            amt = parse_smart_amount(amount_str)
            if amt <= 0: st.error("⚠️ Số tiền > 0!")
            else:
                try:
                    supabase.table("savings").insert({"fund_owner": fund_owner, "bank": bank, "amount": int(amt), "interest_rate": float(rate), "term": int(term), "deposit_date": str(deposit_date), "note": note, "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}).execute()
                    st.success("✅ Đã tạo sổ tiết kiệm thành công!")
                    time.sleep(1)
                    clear_cache_and_rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi kết nối CSDL: {str(e)}")

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
            st.toast("✅ Đã cập nhật!", icon="📈")
            clear_cache_and_rerun()

@st.dialog("✏️ SỬA GD CHỨNG CHỈ QUỸ")
def modal_edit_ccq():
    row = st.session_state.editing_ccq
    if not row:
        st.warning("Không có dữ liệu."); return
    platforms = ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM", "SSI", "VNDirect"]
    init_vol = safe_float(row.get('volume'))
    init_price = safe_float(row.get('price'))
    init_total_val = init_vol * init_price
    
    with st.form("edit_ccq_form"):
        c1, c2 = st.columns(2)
        with c1: platform = st.selectbox("Nền tảng", platforms, index=platforms.index(row['platform']) if row.get('platform') in platforms else 0)
        with c2: fund_owner = st.selectbox("Portfolio", FUNDS, index=FUNDS.index(row['fund_owner']) if row.get('fund_owner') in FUNDS else 0)
        ticker = st.text_input("Mã Quỹ", value=row.get('ticker', ''))
        action = st.radio("Lệnh", ["Mua (SIP)", "Bán"], index=0 if 'Mua' in str(row.get('action', '')) else 1, horizontal=True)
        c3, c4 = st.columns(2)
        with c3: val_str = st.text_input("Tổng giá trị giao dịch (VD: 5tr)", value=f"{init_total_val:,.0f}" if init_total_val > 0 else "")
        with c4: vol_str = st.text_input("Số lượng CCQ", value=f"{init_vol:.2f}" if init_vol > 0 else "")
        note = st.text_input("Ghi chú", value=row.get('note', '') or '')
        if st.form_submit_button("💾 CẬP NHẬT", use_container_width=True):
            total_val, vol = parse_smart_amount(val_str), parse_smart_amount(vol_str)
            if not ticker.strip(): st.error("⚠️ Nhập mã!")
            elif vol <= 0 or total_val <= 0: st.error("⚠️ Giá trị & SL > 0!")
            else:
                nav = total_val / vol
                supabase.table("ccq_funds").update({"platform": platform, "fund_owner": fund_owner, "ticker": ticker.upper().strip(), "action": action, "volume": float(vol), "price": float(nav), "note": note}).eq("id", row['id']).execute()
                st.session_state.editing_ccq = None
                st.toast("✅ Đã cập nhật!", icon="📊")
                clear_cache_and_rerun()

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
            st.toast("✅ Đã cập nhật!", icon="🥇")
            clear_cache_and_rerun()

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
            st.toast("✅ Đã cập nhật!", icon="💰")
            clear_cache_and_rerun()

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
            d_val = pd.to_datetime(row.get('due_date'), errors='coerce')
            d_date = d_val.date() if not pd.isna(d_val) else date.today()
            due_date = st.date_input("Hạn thanh toán", value=d_date)
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
            st.toast("✅ Đã cập nhật!", icon="🏠")
            clear_cache_and_rerun()

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
            st.toast("✅ Đã cập nhật!", icon="🏦")
            clear_cache_and_rerun()

# =====================================================================
# 7. QUICK ACTION BUTTONS
# =====================================================================
st.markdown('<div class="metric-title" style="margin-bottom:10px;">⚡ THAO TÁC NHANH</div>', unsafe_allow_html=True)
qa1, qa2, qa3 = st.columns(3)
with qa1:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("➕ Chi tiêu", key="qa_cf", use_container_width=True): modal_cashflow()
    st.markdown('</div>', unsafe_allow_html=True)
with qa2:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("📈 Cổ phiếu", key="qa_stk", use_container_width=True): modal_stock()
    st.markdown('</div>', unsafe_allow_html=True)
with qa3:
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    if st.button("💰 Vàng", key="qa_gld", use_container_width=True): modal_gold()
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
def calculate_net_worth(supabase_client, fund_owner=None):
    """
    Tính toán tổng tài sản ròng dựa trên tất cả các bảng trong Supabase.
    Có hỗ trợ lọc theo fund_owner (Daddy, Mommy, Baby).
    """
    import pandas as pd
    
    def get_data(table_name):
        query = supabase_client.table(table_name).select("*")
        if fund_owner and fund_owner != "Tất cả" and table_name in ['savings', 'stocks', 'gold', 'ccq_funds']:
            # Lọc bằng dictionary mapping hoặc string tùy theo schema
            valid_funds = [f for f, m in FUND_MEMBER_MAP.items() if m == fund_owner]
            if valid_funds:
                query = query.in_('fund_owner', valid_funds)
            else:
                # If no mapping, just eq
                query = query.eq('fund_owner', fund_owner)
        
        response = query.execute()
        return pd.DataFrame(response.data) if response and response.data else pd.DataFrame()

    df_balances = get_data('opening_balances')
    total_cash = 0
    if not df_balances.empty and 'balance' in df_balances.columns:
        total_cash = pd.to_numeric(df_balances['balance'], errors='coerce').fillna(0).sum()
    elif not df_balances.empty and 'amount' in df_balances.columns:
        total_cash = pd.to_numeric(df_balances['amount'], errors='coerce').fillna(0).sum()

    df_savings = get_data('savings')
    total_savings = pd.to_numeric(df_savings['amount'], errors='coerce').fillna(0).sum() if not df_savings.empty and 'amount' in df_savings.columns else 0

    df_stocks = get_data('stocks')
    total_stocks = 0
    if not df_stocks.empty and 'volume' in df_stocks.columns and 'price' in df_stocks.columns:
        df_stocks['volume'] = pd.to_numeric(df_stocks['volume'], errors='coerce').fillna(0)
        df_stocks['price'] = pd.to_numeric(df_stocks['price'], errors='coerce').fillna(0)
        df_stocks['value'] = df_stocks.apply(
            lambda x: x['volume'] * x['price'] if any(w in str(x['action']).lower() for w in ['buy', 'mua']) else -x['volume'] * x['price'], axis=1
        )
        total_stocks = df_stocks['value'].sum()

    df_gold = get_data('gold')
    total_gold = 0
    if not df_gold.empty and 'quantity' in df_gold.columns and 'price' in df_gold.columns:
        df_gold['quantity'] = pd.to_numeric(df_gold['quantity'], errors='coerce').fillna(0)
        df_gold['price'] = pd.to_numeric(df_gold['price'], errors='coerce').fillna(0)
        df_gold['value'] = df_gold.apply(
            lambda x: x['quantity'] * x['price'] if any(w in str(x['action']).lower() for w in ['buy', 'mua']) else -x['quantity'] * x['price'], axis=1
        )
        total_gold = df_gold['value'].sum()

    df_ccq = get_data('ccq_funds')
    total_ccq = 0
    if not df_ccq.empty and 'volume' in df_ccq.columns and 'price' in df_ccq.columns:
        df_ccq['volume'] = pd.to_numeric(df_ccq['volume'], errors='coerce').fillna(0)
        df_ccq['price'] = pd.to_numeric(df_ccq['price'], errors='coerce').fillna(0)
        df_ccq['value'] = df_ccq.apply(
            lambda x: x['volume'] * x['price'] if any(w in str(x['action']).lower() for w in ['buy', 'mua']) else -x['volume'] * x['price'], axis=1
        )
        total_ccq = df_ccq['value'].sum()

    df_re = get_data('realestate')
    total_re = pd.to_numeric(df_re['contract_value'], errors='coerce').fillna(0).unique().sum() if not df_re.empty and 'contract_value' in df_re.columns else 0

    df_debts = get_data('debts')
    total_debts = 0
    if not df_debts.empty and 'original_principal' in df_debts.columns:
        today_dt = pd.to_datetime(pd.Timestamp.today().date())
        for _, row in df_debts.iterrows():
            principal = pd.to_numeric(row.get('original_principal', 0), errors='coerce')
            if pd.isna(principal): principal = 0
            months = pd.to_numeric(row.get('total_months', 1), errors='coerce')
            if pd.isna(months): months = 1
            grace = pd.to_numeric(row.get('grace_period', 0), errors='coerce')
            if pd.isna(grace): grace = 0
            pay_day = pd.to_numeric(row.get('payment_day', 5), errors='coerce')
            if pd.isna(pay_day): pay_day = 5
            
            start_dt = pd.to_datetime(row.get('start_date'), errors='coerce')
            if pd.isna(start_dt) or start_dt is pd.NaT:
                total_debts += principal
                continue
                
            months_diff = (today_dt.year - start_dt.year) * 12 + (today_dt.month - start_dt.month)
            if today_dt.day < pay_day:
                months_diff -= 1
            months_elapsed = max(0, min(months_diff, months))
            effective_months = max(1, months - grace)
            monthly_principal = principal / effective_months
            balance = max(0, principal - (monthly_principal * max(0, months_elapsed - grace)))
            total_debts += balance

    total_assets = total_cash + total_savings + total_stocks + total_gold + total_ccq + total_re
    net_worth = total_assets - total_debts

    return {
        "net_worth": net_worth,
        "assets": {
            "Cash": total_cash,
            "Savings": total_savings,
            "Stocks": total_stocks,
            "Gold": total_gold,
            "Funds": total_ccq,
            "Real Estate": total_re
        },
        "liabilities": total_debts
    }

nw_data = calculate_net_worth(supabase, current_member)
tong_tien_mat = nw_data['assets']['Cash']
tong_tiet_kiem = nw_data['assets']['Savings']
tong_cp = nw_data['assets']['Stocks']
tong_vang = nw_data['assets']['Gold']
tong_ccq = nw_data['assets']['Funds']
bds_da_dong = nw_data['assets']['Real Estate']
tong_tai_san = sum(nw_data['assets'].values())
no_khoan_vay = nw_data['liabilities']
net_worth = nw_data['net_worth']


def render_net_worth_dashboard(data):
    st.markdown('<div class="metric-title" style="margin-bottom:10px; font-size:1.5rem;">💰 Tổng Quan Tài Sản Ròng</div>', unsafe_allow_html=True)
    
    st.markdown(f"""<div class="ios-card" style="background: var(--primary-navy); border-left: 4px solid var(--accent-gold); padding: 25px; margin-bottom: 25px;">
<div class="metric-title" style="color: var(--accent-gold);">TÀI SẢN RÒNG (NET WORTH)</div>
<div style="font-family: 'Inter', sans-serif; font-size: 3rem; font-weight: 700; color: #f8fafc;">{data['net_worth']:,.0f} VNĐ</div>
</div>""", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="metric-title">Phân bổ tài sản</div>', unsafe_allow_html=True)
        import pandas as pd
        asset_df = pd.DataFrame(data['assets'].items(), columns=['Loại', 'Giá trị'])
        asset_df = asset_df[asset_df['Giá trị'] > 0]
        import plotly.express as px
        if not asset_df.empty:
            fig = px.pie(asset_df, values='Giá trị', names='Loại', hole=0.55,
                         color_discrete_sequence=["#10b981", "#38bdf8", "#f59e0b", "#8b5cf6", "#eab308", "#ef4444"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f8fafc",
                              legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                              margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.markdown('<div class="metric-title">Chi tiết phân loại</div>', unsafe_allow_html=True)
        for asset, val in data['assets'].items():
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <span style="color:#94a3b8; font-weight:600;">{asset}</span>
                <span style="font-weight:700;">{val:,.0f} VNĐ</span>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; margin-top: 20px; padding: 15px; background: rgba(239, 68, 68, 0.2); border-radius: 8px;">
            <span style="color:#f87171; font-weight:600;">Tổng Nợ</span>
            <span style="font-weight:700; color:#f87171;">{data['liabilities']:,.0f} VNĐ</span>
        </div>
        """, unsafe_allow_html=True)


# =====================================================================
# 9. TAB DEFINITIONS
# =====================================================================
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "🏠 Tổng quan", "📊 Dòng tiền", "📈 Đầu tư", "🐷 Tiết kiệm", "🏠 BĐS & Tín dụng"
])

# =====================================================================
# TAB 0: TỔNG QUAN
# =====================================================================
with tab_home:
    render_net_worth_dashboard(nw_data)

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

    with st.expander("⚙️ CẤU HÌNH NGÂN SÁCH", expanded=False):
        st.markdown("### Thiết lập Ngân sách Chi tiêu Tháng")
        bg1, bg2 = st.columns(2)
        for idx_cat, cat in enumerate(EXPENSE_CATS):
            with (bg1 if idx_cat % 2 == 0 else bg2):
                st.session_state.cat_budgets[cat] = st.number_input(
                    f"{cat}", value=st.session_state.cat_budgets.get(cat, 3000000),
                    step=500000, format="%d", key=f"budget_{idx_cat}")

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

    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader(f"📋 Chi tiết giao dịch {f'- {selected_cat}' if selected_cat else ''}")
    df_show = df_period.copy()
    if selected_cat:
        df_show = df_show[df_show['category'] == selected_cat]
        
    if not df_show.empty:
        df_sorted = df_show.sort_values('created_at', ascending=False)
        for _, row in df_sorted.iterrows():
            cat = row.get('category', '')
            is_income = (cat == 'Lương/Thu nhập')
            color_cls = "text-green" if is_income else "text-red"
            sign = "+" if is_income else "-"
            amt = safe_float(row.get('amount'))
            dt_val = row.get('created_at')
            dt_str = pd.to_datetime(dt_val).strftime('%d/%m/%Y %H:%M') if pd.notna(dt_val) else ''
            note_str = f"<div class='fintech-card-note'>{row.get('note', '')}</div>" if row.get('note') else ""
            acc = row.get('account', '')
            st.markdown(f'''
            <div class="fintech-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div class="fintech-card-title">{cat}</div>
                        <div class="fintech-card-subtitle">{dt_str} • {acc}</div>{note_str}
                    </div>
                    <div class="fintech-card-amount {color_cls}">
                        {sign}{amt:,.0f} ₫
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("Không có giao dịch phù hợp.")

# =====================================================================
# TAB 2: ĐẦU TƯ
# =====================================================================
with tab_invest:
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">DANH MỤC ĐẦU TƯ{f" ({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)
    df_stk_f = filter_by_member(df_stk, current_member)
    df_ccq_f = filter_by_member(df_ccq, current_member)
    df_gold_f = filter_by_member(df_gold, current_member)
    inv_stk, inv_ccq, inv_gld = st.tabs(["📈 Chứng khoán", "📊 Chứng chỉ quỹ", "🥇 Vàng"])

    # --- STOCKS ---
    with inv_stk:
        stk_sum_tab, stk_hist_tab = st.tabs(["📊 Tổng hợp", "📋 Lịch sử GD"])
        with stk_sum_tab:
            summary_stk, _ = calc_investment_total(df_stk_f, 'ticker')
            if not summary_stk.empty:
                st.metric("📈 Tổng giá trị Cổ phiếu", f"{tong_cp:,.0f} ₫")
                for _, row in summary_stk.iterrows():
                    st.markdown(f'''
                    <div class="fintech-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="fintech-card-title">{row['ticker']}</div>
                                <div class="fintech-card-subtitle">SL: {row['SL tồn']:,.0f} • Giá TB: {row['Giá vốn TB']:,.0f} ₫</div>
                            </div>
                            <div class="fintech-card-amount text-green">
                                {row['Tổng vốn']:,.0f} ₫
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("Chưa có vị thế cổ phiếu.")
        with stk_hist_tab:
            if not df_stk_f.empty:
                df_stk_sorted = df_stk_f.sort_values('trade_date', ascending=False)
                for _, row in df_stk_sorted.iterrows():
                    act = str(row.get('action', ''))
                    color_cls = "text-green" if "Mua" in act else "text-yellow"
                    sign = "-" if "Mua" in act else "+"
                    vol = safe_float(row.get('volume'))
                    prc = safe_float(row.get('price'))
                    val = vol * prc
                    dt_val = row.get('trade_date')
                    dt_str = pd.to_datetime(dt_val).strftime('%d/%m/%Y') if pd.notna(dt_val) else ''
                    note_str = f"<div class='fintech-card-note'>{row.get('note', '')}</div>" if row.get('note') else ""
                    action = str(row.get('action', ''))
                    color_cls = "text-green" if "Mua" in action else "text-yellow"
                    sign = "-" if "Mua" in action else "+"
                    volume = safe_float(row.get('volume'))
                    price = safe_float(row.get('price'))
                    val = volume * price
                    dt_val = row.get('trade_date')
                    dt_str = pd.to_datetime(dt_val).strftime('%d/%m/%Y') if pd.notna(dt_val) else ''
                    note_str = f"<div class='fintech-card-note'>{row.get('note', '')}</div>" if row.get('note') else ""
                    st.markdown(f'''
                    <div class="fintech-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="fintech-card-title">{row.get('ticker', '')} <span style="font-size:0.85rem; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.1); margin-left: 5px;">{action}</span></div>
                                <div class="fintech-card-subtitle">{dt_str} • KL: {volume:,.0f} • Giá: {price:,.0f} ₫</div>{note_str}
                            </div>
                            <div class="fintech-card-amount {color_cls}">
                                {sign}{val:,.0f} ₫
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)

                options_stk = [f"{r.get('ticker','')} | {r.get('action','')} | KL:{r.get('volume','')} | {str(r.get('trade_date',''))[:10]}" for _, r in df_stk_f.iterrows()]
                sel_idx_stk = st.selectbox("Chọn GD để sửa/xóa", range(len(options_stk)), format_func=lambda i: options_stk[i], key="sel_stk")
                ce1, ce2 = st.columns(2)
                with ce1:
                    if st.button("✏️ SỬA", key="btn_edit_stk", use_container_width=True):
                        st.session_state.editing_stock = df_stk_f.iloc[sel_idx_stk].to_dict()
                with ce2:
                    if st.button("❌ XÓA", key="btn_del_stk", use_container_width=True):
                        supabase.table("stocks").delete().eq("id", df_stk_f.iloc[sel_idx_stk]['id']).execute()
                        st.toast("🗑️ Đã xóa!", icon="✅")
                        clear_cache_and_rerun()
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
                st.metric("📊 Tổng giá trị CCQ", f"{tong_ccq:,.0f} ₫")
                for _, row in summary_ccq.iterrows():
                    st.markdown(f'''
                    <div class="fintech-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="fintech-card-title">{row['ticker']}</div>
                                <div class="fintech-card-subtitle">SL: {row['SL tồn']:,.2f} • Giá TB: {row['Giá vốn TB']:,.0f} ₫</div>
                            </div>
                            <div class="fintech-card-amount text-green">
                                {row['Tổng vốn']:,.0f} ₫
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("Chưa có vị thế CCQ.")
        with ccq_hist_tab:
            if not df_ccq_f.empty:
                df_ccq_sorted = df_ccq_f.sort_values('trade_date', ascending=False)
                for _, row in df_ccq_sorted.iterrows():
                    act = str(row.get('action', ''))
                    color_cls = "text-green" if "Mua" in act else "text-yellow"
                    sign = "-" if "Mua" in act else "+"
                    vol = float(row.get('volume', 0) or 0)
                    prc = float(row.get('price', 0) or 0)
                    val = vol * prc
                    dt_val = row.get('trade_date')
                    dt_str = pd.to_datetime(dt_val).strftime('%d/%m/%Y') if pd.notna(dt_val) else ''
                    note_str = f"<div class='fintech-card-note'>{row.get('note', '')}</div>" if row.get('note') else ""
                    st.markdown(f'''
                    <div class="fintech-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="fintech-card-title">{row.get('ticker', '')} <span style="font-size:0.85rem; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.1); margin-left: 5px;">{act}</span></div>
                                <div class="fintech-card-subtitle">{dt_str} • SL: {vol:,.2f} • NAV: {prc:,.0f}</div>{note_str}
                            </div>
                            <div class="fintech-card-amount {color_cls}">
                                {sign}{val:,.0f} ₫
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                options_ccq = [f"{r.get('ticker','')} | {r.get('action','')} | {str(r.get('trade_date',''))[:10]}" for _, r in df_ccq_f.iterrows()]
                sel_idx_ccq = st.selectbox("Chọn GD để sửa/xóa", range(len(options_ccq)), format_func=lambda i: options_ccq[i], key="sel_ccq")
                ce1, ce2 = st.columns(2)
                with ce1:
                    if st.button("✏️ SỬA", key="btn_edit_ccq", use_container_width=True):
                        st.session_state.editing_ccq = df_ccq_f.iloc[sel_idx_ccq].to_dict()
                with ce2:
                    if st.button("❌ XÓA", key="btn_del_ccq", use_container_width=True):
                        supabase.table("ccq_funds").delete().eq("id", df_ccq_f.iloc[sel_idx_ccq]['id']).execute()
                        st.toast("🗑️ Đã xóa!", icon="✅")
                        clear_cache_and_rerun()
                if st.session_state.get("editing_ccq"):
                    modal_edit_ccq()
            else:
                st.info("Chưa có giao dịch CCQ.")

    # --- GOLD ---
    with inv_gld:
        gld_sum_tab, gld_hist_tab = st.tabs(["📊 Tổng hợp", "📋 Lịch sử GD"])
        with gld_sum_tab:
            summary_gld, _ = calc_investment_total(df_gold_f, 'gold_type')
            if not summary_gld.empty:
                st.metric("🥇 Tổng giá trị Vàng", f"{tong_vang:,.0f} ₫")
                for _, row in summary_gld.iterrows():
                    st.markdown(f'''
                    <div class="fintech-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="fintech-card-title">{row['gold_type']}</div>
                                <div class="fintech-card-subtitle">SL: {row['SL tồn']:,.2f} chỉ • Giá TB: {row['Giá vốn TB']:,.0f} ₫</div>
                            </div>
                            <div class="fintech-card-amount text-green">
                                {row['Tổng vốn']:,.0f} ₫
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("Chưa có vị thế Vàng.")
        with gld_hist_tab:
            if not df_gold_f.empty:
                df_gold_sorted = df_gold_f.sort_values('trade_date', ascending=False)
                for _, row in df_gold_sorted.iterrows():
                    act = str(row.get('action', ''))
                    color_cls = "text-green" if "Mua" in act else "text-yellow"
                    sign = "-" if "Mua" in act else "+"
                    qty = float(row.get('quantity', 0) or 0)
                    prc = float(row.get('price', 0) or 0)
                    val = qty * prc
                    dt_val = row.get('trade_date')
                    dt_str = pd.to_datetime(dt_val).strftime('%d/%m/%Y') if pd.notna(dt_val) else ''
                    note_str = f"<div class='fintech-card-note'>{row.get('note', '')}</div>" if row.get('note') else ""
                    st.markdown(f'''
                    <div class="fintech-card" style="border-left: 4px solid var(--accent-gold);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="fintech-card-title" style="color: var(--accent-gold);">{row.get('gold_type', '')} <span style="font-size:0.85rem; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.1); margin-left: 5px; color: #f8fafc;">{act}</span></div>
                                <div class="fintech-card-subtitle">{dt_str} • SL: {qty:,.2f} chỉ • Giá: {prc:,.0f} ₫</div>{note_str}
                            </div>
                            <div class="fintech-card-amount {color_cls}">
                                {sign}{val:,.0f} ₫
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                options_gld = [f"{r.get('gold_type','')} | {r.get('action','')} | {r.get('quantity','')} chỉ | {str(r.get('trade_date',''))[:10]}" for _, r in df_gold_f.iterrows()]
                sel_idx_gld = st.selectbox("Chọn GD để sửa/xóa", range(len(options_gld)), format_func=lambda i: options_gld[i], key="sel_gld")
                ce1, ce2 = st.columns(2)
                with ce1:
                    if st.button("✏️ SỬA", key="btn_edit_gld", use_container_width=True):
                        st.session_state.editing_gold = df_gold_f.iloc[sel_idx_gld].to_dict()
                with ce2:
                    if st.button("❌ XÓA", key="btn_del_gld", use_container_width=True):
                        supabase.table("gold").delete().eq("id", df_gold_f.iloc[sel_idx_gld]['id']).execute()
                        st.toast("🗑️ Đã xóa!", icon="✅")
                        clear_cache_and_rerun()
                if st.session_state.get("editing_gold"):
                    modal_edit_gold()
            else:
                st.info("Chưa có giao dịch Vàng.")

# =====================================================================
# TAB 3: TIẾT KIỆM
# =====================================================================
with tab_savings:
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">TIẾT KIỆM MỤC TIÊU{f" ({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)

    with st.expander("⚙️ CẤU HÌNH MỤC TIÊU TIẾT KIỆM", expanded=False):
        sg_cols = st.columns(len(FUNDS))
        for idx, fund_name in enumerate(FUNDS):
            with sg_cols[idx]:
                st.session_state.savings_goals[fund_name] = st.number_input(
                    f"Mục tiêu {fund_name}",
                    value=int(st.session_state.savings_goals.get(fund_name, 300_000_000)),
                    step=10_000_000,
                    format="%d",
                    key=f"sg_input_{idx}"
                )

    if st.button("➕ TẠO SỔ TIẾT KIỆM MỚI", key="btn_add_savings", type="primary", use_container_width=True):
        modal_add_savings()

    st.markdown("<br/>", unsafe_allow_html=True)

    # Summary cards
    sc1, sc2, sc3 = st.columns(3)
    cols_sv = [sc1, sc2, sc3]
    for i, fund_name in enumerate(FUNDS):
        if not fund_matches_member(fund_name, current_member):
            continue
        target = st.session_state.savings_goals.get(fund_name, 300_000_000)
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
                for _, row in fund_df.iterrows():
                    amt = safe_float(row.get('amount', 0))
                    rate = safe_float(row.get('interest_rate', 0))
                    trm = safe_float(row.get('term', 0))
                    bank = row.get('bank', '')
                    note = row.get('note', '')
                    dt_val = row.get('deposit_date')
                    dt_str = pd.to_datetime(dt_val).strftime('%d/%m/%Y') if pd.notna(dt_val) else ''
                    note_html = f"<div class='fintech-card-note'>{note}</div>" if note else ""
                    st.markdown(f'''
                    <div class="fintech-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="fintech-card-title">🏦 {bank}</div>
                                <div class="fintech-card-subtitle">Lãi suất: {rate}%/năm • Kỳ hạn: {trm:,.0f} tháng • Ngày gửi: {dt_str}</div>{note_html}
                            </div>
                            <div class="fintech-card-amount text-green">
                                {amt:,.0f} ₫
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
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
                        st.toast("🗑️ Đã tất toán!", icon="✅")
                        clear_cache_and_rerun()
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
    
    # RE Due Date Alert
    if not df_re.empty and 'status' in df_re.columns and 'due_date' in df_re.columns:
        unpaid = df_re[df_re['status'].astype(str).str.strip() == 'Chưa thanh toán'].copy()
        if not unpaid.empty:
            today_date = date.today()
            unpaid['due_date_dt'] = pd.to_datetime(unpaid['due_date'], errors='coerce').dt.date
            upcoming = unpaid[(unpaid['due_date_dt'] >= today_date) & (unpaid['due_date_dt'] <= today_date + pd.Timedelta(days=7))]
            for _, r in upcoming.iterrows():
                days_left = (r['due_date_dt'] - today_date).days
                st.warning(f"🚨 **Đến hạn thanh toán:** BĐS **{r.get('project_name','')} - {r.get('installment_name','')}** cần thanh toán **{safe_float(r.get('amount',0)):,.0f} ₫** trong **{days_left} ngày** tới!")

    st.subheader("🏠 Bất động sản đang sở hữu")
    df_re_f = df_re.copy()
    if not df_re_f.empty:
        total_contract = df_re_f.groupby('project_name')['contract_value'].first().sum()
        total_paid = df_re_f[df_re_f['status'].astype(str).str.strip() == 'Đã thanh toán']['amount'].sum()
        total_unpaid = df_re_f[df_re_f['status'].astype(str).str.strip() == 'Chưa thanh toán']['amount'].sum()

        rm1, rm2, rm3 = st.columns(3)
        with rm1:
            st.markdown(f'<div class="ios-card" style="padding:15px; border-left: 4px solid #38bdf8;">'
                        f'<div style="font-size:0.9rem; color:#94a3b8;">Tổng Giá Trị Hợp Đồng</div>'
                        f'<div style="font-size:1.5rem; font-weight:700;">{total_contract:,.0f} ₫</div></div>', unsafe_allow_html=True)
        with rm2:
            st.markdown(f'<div class="ios-card" style="padding:15px; border-left: 4px solid #4ade80;">'
                        f'<div style="font-size:0.9rem; color:#94a3b8;">Tổng Đã Thanh Toán</div>'
                        f'<div style="font-size:1.5rem; font-weight:700; color:#4ade80;">{total_paid:,.0f} ₫</div></div>', unsafe_allow_html=True)
        with rm3:
            st.markdown(f'<div class="ios-card" style="padding:15px; border-left: 4px solid #f87171;">'
                        f'<div style="font-size:0.9rem; color:#94a3b8;">Tổng Chưa Thanh Toán</div>'
                        f'<div style="font-size:1.5rem; font-weight:700; color:#f87171;">{total_unpaid:,.0f} ₫</div></div>', unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        display_cols = [c for c in ['project_name', 'contract_value', 'installment_name', 'amount', 'funding_source', 'due_date', 'status', 'note'] if c in df_re_f.columns]
        df_display = df_re_f[display_cols].copy()
        
        for _, row in df_display.iterrows():
            proj = row.get('project_name', '')
            inst = row.get('installment_name', '')
            amt = safe_float(row.get('amount', 0))
            stat = str(row.get('status', '')).strip()
            color_cls = "text-green" if stat == 'Đã thanh toán' else "text-red"
            dt_val = row.get('due_date')
            dt_str = pd.to_datetime(dt_val).strftime('%d/%m/%Y') if pd.notna(dt_val) else ''
            src = row.get('funding_source', '')
            note = row.get('note', '')
            note_html = f"<div class='fintech-card-note'>{note}</div>" if note else ""
            
            st.markdown(f'''
            <div class="fintech-card" style="border-left: 4px solid var(--accent-gold);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div class="fintech-card-title" style="color: var(--accent-gold);">🏢 {proj} - {inst} <span style="font-size:0.8rem; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.1); margin-left: 5px; color: #f8fafc;">{stat}</span></div>
                        <div class="fintech-card-subtitle">Hạn TT: {dt_str} • Nguồn: {src}</div>{note_html}
                    </div>
                    <div class="fintech-card-amount {color_cls}">
                        {amt:,.0f} ₫
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

        with st.expander("⚙️ Quản lý & Chỉnh sửa BĐS", expanded=False):
            options_re = [f"{r.get('project_name', 'BĐS')} | {r.get('installment_name', '')} | {safe_float(r.get('amount', 0)):,.0f}₫ ({r.get('status','')})" for _, r in df_re_f.iterrows()]
            sel_re = st.selectbox("Chọn đợt BĐS để sửa/xóa", range(len(options_re)), format_func=lambda i: options_re[i], key="sel_re")
            re_e1, re_e2 = st.columns(2)
            with re_e1:
                if st.button("✏️ SỬA BĐS", key="btn_edit_re", use_container_width=True):
                    st.session_state.editing_realestate = df_re_f.iloc[sel_re].to_dict()
            with re_e2:
                if st.button("❌ XÓA BĐS", key="btn_del_re", use_container_width=True):
                    supabase.table("realestate").delete().eq("id", df_re_f.iloc[sel_re]['id']).execute()
                    st.toast("🗑️ Đã xóa!", icon="✅")
                    clear_cache_and_rerun()
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
            start_dt = pd.to_datetime(row.get('start_date'), errors='coerce')
            if pd.isna(start_dt) or start_dt is pd.NaT:
                continue

            months_diff = (today_dt.year - start_dt.year) * 12 + (today_dt.month - start_dt.month)
            if today_dt.day < pay_day:
                months_diff -= 1
            months_elapsed = max(0, min(months_diff, months))
            effective_months = max(1, months - grace)
            monthly_principal = principal / effective_months
            balance = max(0, principal - (monthly_principal * max(0, months_elapsed - grace)))
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
            for row in debt_summary_rows:
                bank = row["Ngân hàng"]
                purp = row["Mục đích"]
                bal = float(row["Dư nợ hiện tại"])
                orig = float(row["Gốc ban đầu"])
                goc_t = float(row["Gốc/Tháng"])
                lai_t = float(row["Lãi/Tháng"])
                nxt = row["Ngày TT tiếp"]
                pct = float(row["Đã trả (%)"])
                
                st.markdown(f'''
                <div class="fintech-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1;">
                            <div class="fintech-card-title">🏦 {bank} - {purp}</div>
                            <div class="fintech-card-subtitle">Gốc/Tháng: {goc_t:,.0f} ₫ • Lãi: {lai_t:,.0f} ₫</div>
                            <div class="fintech-card-subtitle" style="color: #facc15; margin-top: 4px;">⏳ Trả nợ kỳ tới: {nxt}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.85rem; color: #94a3b8;">Dư nợ hiện tại</div>
                            <div class="fintech-card-amount text-red">
                                {bal:,.0f} ₫
                            </div>
                            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 2px;">/ {orig:,.0f} ₫</div>
                        </div>
                    </div>
                    <div class="progress-container" style="margin-top:12px;background-color:rgba(255,255,255,0.1);">
                        <div class="progress-bar-fill" style="width:{min(pct,100)}%;background-color:#4ade80;"></div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

        st.metric("💳 Tổng dư nợ hiện tại", f"{no_khoan_vay:,.0f} ₫")

        with st.expander("⚙️ Quản lý & Chỉnh sửa Khoản Vay", expanded=False):
            options_debt = [f"{r.get('purpose', 'Khoản vay')} | {r.get('bank', '')} | Gốc: {safe_float(r.get('original_principal')):,.0f}₫" for _, r in df_debts_f.iterrows()]
            sel_debt = st.selectbox("Chọn khoản vay để sửa/xóa", range(len(options_debt)), format_func=lambda i: options_debt[i], key="sel_debt")
            de1, de2 = st.columns(2)
            with de1:
                if st.button("✏️ SỬA KHOẢN VAY", key="btn_edit_debt", use_container_width=True):
                    st.session_state.editing_debt = df_debts_f.iloc[sel_debt].to_dict()
            with de2:
                if st.button("❌ XÓA KHOẢN VAY", key="btn_del_debt", use_container_width=True):
                    supabase.table("debts").delete().eq("id", df_debts_f.iloc[sel_debt]['id']).execute()
                    st.toast("🗑️ Đã xóa!", icon="✅")
                    clear_cache_and_rerun()
        if st.session_state.get("editing_debt"):
            modal_edit_debt()
    else:
        st.info("Chưa có khoản vay nào.")
