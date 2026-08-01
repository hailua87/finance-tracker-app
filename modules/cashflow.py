import streamlit as st
import pandas as pd
from datetime import date
import time
import plotly.express as px
from services.db import init_supabase
from components.ui import budget_card, dashboard_card
from utils.helpers import DEBIT_ACCOUNTS, CREDIT_CARDS, BROKER_ACCOUNTS, BANK_ACCOUNTS, parse_smart_amount

supabase = init_supabase()

def add_quick_amount_cf(val):
    current = parse_smart_amount(st.session_state.cf_amount_str)
    st.session_state.cf_amount_str = f"{current + val:,.0f}"

@st.dialog("NHẬP CHI TIÊU NHANH")
def modal_cashflow():
    with st.form("quick_cashflow_form", clear_on_submit=False):
        c1, c2 = st.columns([1, 1])
        with c1:
            amount_str = st.text_input("SỐ TIỀN (VND)", value=st.session_state.cf_amount_str, key="cf_amount_str", placeholder="Ví dụ: 50k, 1.2tr")
            b1, b2, b3 = st.columns(3)
            with b1: st.button("+50k", on_click=add_quick_amount_cf, args=(50000,), use_container_width=True)
            with b2: st.button("+100k", on_click=add_quick_amount_cf, args=(100000,), use_container_width=True)
            with b3: st.button("+500k", on_click=add_quick_amount_cf, args=(500000,), use_container_width=True)
        with c2:
            cats = list(st.session_state.cat_budgets.keys()) + ["Lương/Thu nhập"]
            category = st.selectbox("Phân loại", cats)
            account = st.selectbox("Tài khoản", BANK_ACCOUNTS, index=BANK_ACCOUNTS.index(st.session_state.last_account) if st.session_state.last_account in BANK_ACCOUNTS else 0)
        
        note = st.text_input("Ghi chú (Tùy chọn)")
        
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True, type="primary"):
            final_amount = parse_smart_amount(amount_str)
            if final_amount <= 0:
                st.error("⚠️ Vui lòng nhập số tiền hợp lệ!")
            else:
                try:
                    dt_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    supabase.table("cashflow").insert({"account": account, "amount": final_amount, "category": category, "note": note, "created_at": dt_str}).execute()
                    st.session_state.last_account = account
                    st.session_state.cf_amount_str = ""
                    st.toast("✅ Đã lưu giao dịch!", icon="🔥")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

def filter_by_member(df, current_member, col='fund_owner'):
    if current_member == "Tất cả" or df.empty or col not in df.columns:
        return df
    return df[df[col].str.contains(current_member, na=False, case=False)]

def render_cashflow_tab(current_member="Tất cả"):
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">DÒNG TIỀN THÁNG NÀY {f"({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)
    try: 
        res_all_cf = supabase.table("cashflow").select("*").execute()
        df_all = pd.DataFrame(res_all_cf.data) if res_all_cf and res_all_cf.data else pd.DataFrame()
    except: df_all = pd.DataFrame()
    
    df_all = filter_by_member(df_all, current_member)
        
    current_month_dt = date.today()
    start_date_val = current_month_dt.replace(day=1)
    
    if not df_all.empty:
        df_all['created_at_dt'] = pd.to_datetime(df_all['created_at'], errors='coerce')
        df_all = df_all.dropna(subset=['created_at_dt'])
        
        c_m_1, c_m_2 = st.columns(2)
        with c_m_1: m_start = st.date_input("Từ ngày", start_date_val)
        with c_m_2: m_end = st.date_input("Đến ngày", current_month_dt)
        
        df_filtered = df_all[(df_all['created_at_dt'].dt.date >= m_start) & (df_all['created_at_dt'].dt.date <= m_end)]
    else:
        df_filtered = pd.DataFrame()
        st.info("Chưa có dữ liệu dòng tiền.")

    tong_thu = df_filtered[df_filtered['category'] == 'Lương/Thu nhập']['amount'].sum() if not df_filtered.empty else 0
    tong_chi = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']['amount'].sum() if not df_filtered.empty else 0

    c1, c2 = st.columns(2)
    with c1: dashboard_card("ĐÃ CHI (THÁNG)", f"{tong_chi:,.0f} ₫", value_color="#f87171", icon="💸")
    with c2: dashboard_card("TỔNG THU", f"{tong_thu:,.0f} ₫", value_color="#4ade80", icon="🤑")

    st.markdown("<br/>", unsafe_allow_html=True)
    
    col_chart, col_budget = st.columns([1, 1])
    
    with col_chart:
        st.subheader("Phân bổ chi tiêu")
        if not df_filtered.empty:
            df_expenses = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']
            if not df_expenses.empty:
                df_pie = df_expenses.groupby('category')['amount'].sum().reset_index()
                modern_palette = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#1A535C', '#8b5cf6', '#F7FFF7', '#FF8C42', '#38bdf8']
                fig = px.pie(df_pie, names='category', values='amount', hole=0.55, color_discrete_sequence=modern_palette)
                fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#1E3A8A', width=2)))
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f8fafc", showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Chưa có khoản chi nào trong tháng.")
        else:
            st.info("Không có dữ liệu.")

    with col_budget:
        st.subheader("Ngân sách chi tiết")
        if not df_filtered.empty:
            df_expenses = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']
            if not df_expenses.empty:
                for cat, limit in st.session_state.cat_budgets.items():
                    spent = df_expenses[df_expenses['category'] == cat]['amount'].sum()
                    if spent > 0:
                        budget_card(cat, limit, spent)
