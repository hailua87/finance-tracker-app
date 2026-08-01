import streamlit as st
import pandas as pd
import time
from services.db import init_supabase
from components.ui import savings_goal_card
from utils.helpers import BANK_ACCOUNTS

supabase = init_supabase()

SAVINGS_GOALS = {
    "Baby Funding": 500_000_000,
    "Daddy Funding": 300_000_000,
    "Mama Funding": 300_000_000
}

def open_deposit_modal(fund_name):
    st.session_state.quick_deposit_fund = fund_name
    st.session_state.show_deposit_modal = True

@st.dialog("⚡ NẠP NHANH VÀO VÍ TIẾT KIỆM")
def deposit_modal():
    fund_name = st.session_state.get("quick_deposit_fund", "")
    st.write(f"Đang nạp tiền vào: **{fund_name}**")
    with st.form("deposit_form", clear_on_submit=False):
        amount = st.number_input("Số tiền (VND)", min_value=0, step=1000000, format="%d")
        source_account = st.selectbox("Nguồn tiền (Tài khoản/Thẻ)", BANK_ACCOUNTS)
        note = st.text_input("Ghi chú", value=f"Nạp ví {fund_name}")
        interest_rate = st.number_input("Lãi suất (%/năm) - Tuỳ chọn", min_value=0.0, step=0.1, format="%.1f")
        term = st.number_input("Kỳ hạn (Tháng) - Tuỳ chọn", min_value=0, step=1)
        
        if st.form_submit_button("XÁC NHẬN NẠP", use_container_width=True):
            if amount > 0:
                try:
                    dt_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    supabase.table("cashflow").insert({
                        "account": source_account, 
                        "amount": int(amount), 
                        "category": "Đầu tư & Trả nợ",
                        "note": note, 
                        "created_at": dt_str
                    }).execute()
                    
                    supabase.table("savings").insert({
                        "fund_owner": fund_name,
                        "amount": int(amount),
                        "note": note,
                        "interest_rate": float(interest_rate),
                        "term": int(term),
                        "created_at": dt_str
                    }).execute()
                    
                    st.session_state.show_deposit_modal = False
                    st.toast("✅ Nạp thành công!", icon="🎉")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi (có thể bảng savings chưa có cột interest_rate, term): {e}")
            else:
                st.error("⚠️ Vui lòng nhập số tiền hợp lệ!")

def filter_by_member(df, current_member, col='fund_owner'):
    if current_member == "Tất cả" or df.empty or col not in df.columns:
        return df
    return df[df[col].str.contains(current_member, na=False, case=False)]

def render_savings_tab(current_member="Tất cả"):
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">TIẾT KIỆM MỤC TIÊU GIA ĐÌNH {f"({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)
    
    if st.session_state.get("show_deposit_modal", False):
        deposit_modal()
        st.session_state.show_deposit_modal = False

    try: 
        res_savings = supabase.table("savings").select("*").execute()
        df_savings = pd.DataFrame(res_savings.data) if res_savings and res_savings.data else pd.DataFrame()
        if not df_savings.empty and 'amount' in df_savings.columns:
            df_savings['amount'] = pd.to_numeric(df_savings['amount'], errors='coerce').fillna(0)
    except: 
        df_savings = pd.DataFrame()

    def get_fund_current(fund_name):
        if df_savings.empty or 'fund_owner' not in df_savings.columns:
            return 0
        df = df_savings[df_savings['fund_owner'] == fund_name]
        if df.empty: return 0, 0
        total_amount = df['amount'].sum()
        
        expected_interest = 0
        if 'interest_rate' in df.columns and 'term' in df.columns:
            def safe_float(val):
                if pd.isna(val) or val is None:
                    return 0.0
                if isinstance(val, str):
                    val = val.replace('%', '').replace(',', '').strip()
                    if val == '': return 0.0
                try:
                    return float(val)
                except ValueError:
                    return 0.0

            for _, row in df.iterrows():
                amt = safe_float(row.get('amount'))
                rate = safe_float(row.get('interest_rate'))
                trm = safe_float(row.get('term'))
                if rate > 0 and trm > 0:
                    expected_interest += amt * (rate / 100.0) * (trm / 12.0)
                    
        return total_amount, expected_interest

    col1, col2, col3 = st.columns(3)
    
    def render_fund_card(name, target, theme_class):
        if current_member not in ["Tất cả", name.split(" ")[0]]:
            return # Hide if not matching filter
        
        current, interest = get_fund_current(name)
        
        percent = current / target if target > 0 else 0
        html = f"""
        <div class="ios-card {theme_class}" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div class="savings-goal-title">{name}</div>
                <div style="font-size: 1.8rem; font-weight: 700; font-family: 'Playfair Display';">{current:,.0f} ₫</div>
                <div style="font-size: 0.85rem; opacity: 0.8; margin-top: 5px;">Mục tiêu: {target:,.0f} ₫ ({percent*100:.1f}%)</div>
                """
        if interest > 0:
            html += f'<div style="font-size: 0.85rem; color: #4ade80; margin-top: 5px;">+ Lãi dự kiến: {interest:,.0f} ₫</div>'
                
        html += f"""
            </div>
            <div class="progress-container" style="margin-top: 15px; margin-bottom: 15px; background-color: rgba(255,255,255,0.3);">
                <div class="progress-bar-fill" style="width: {min(percent*100, 100)}%; background-color: white;"></div>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        st.button(f"⚡ Nạp {name}", key=f"dep_{name}", on_click=open_deposit_modal, args=(name,), use_container_width=True)

    with col1: render_fund_card("Baby Funding", SAVINGS_GOALS["Baby Funding"], "card-baby")
    with col2: render_fund_card("Daddy Funding", SAVINGS_GOALS["Daddy Funding"], "card-daddy")
    with col3: render_fund_card("Mama Funding", SAVINGS_GOALS["Mama Funding"], "card-mommy")
        
    df_display = filter_by_member(df_savings, current_member)
    if not df_display.empty:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown('<div class="metric-title">LỊCH SỬ NẠP GẦN ĐÂY</div>', unsafe_allow_html=True)
        if 'created_at' in df_display.columns:
            df_display['created_at'] = pd.to_datetime(df_display['created_at'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
        st.dataframe(df_display, use_container_width=True, hide_index=True)
