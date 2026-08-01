import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from services.db import init_supabase
from components.ui import render_amortization_table

supabase = init_supabase()

def filter_by_member(df, current_member, col='fund_owner'):
    if current_member == "Tất cả" or df.empty or col not in df.columns:
        return df
    return df[df[col].str.contains(current_member, na=False, case=False)]

def calculate_amortization(principal, annual_rate, months, start_date_str):
    schedule = []
    current_balance = principal
    monthly_rate = (annual_rate / 100) / 12
    monthly_principal = principal / months if months > 0 else 0
    start_dt = pd.to_datetime(start_date_str)
    
    for i in range(1, months + 1):
        interest = current_balance * monthly_rate
        payment = monthly_principal + interest
        current_balance -= monthly_principal
        
        if current_balance < 1:
            current_balance = 0
            
        pay_date = start_dt + relativedelta(months=i)
        
        schedule.append({
            "Kỳ": i,
            "Ngày trả": pay_date.strftime("%d/%m/%Y"),
            "Gốc": monthly_principal,
            "Lãi": interest,
            "Tổng trả": payment,
            "Dư nợ": current_balance
        })
    return pd.DataFrame(schedule)

def render_realestate_tab(current_member="Tất cả"):
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">BẤT ĐỘNG SẢN & KHOẢN VAY {f"({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Bất động sản đang sở hữu")
        try:
            res_re = supabase.table("realestate").select("*").execute()
            if res_re and res_re.data:
                df_re = filter_by_member(pd.DataFrame(res_re.data), current_member)
                if not df_re.empty:
                    for _, row in df_re.iterrows():
                        contract_val = row.get('contract_value', row.get('amount', 0))
                        img_url = "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                        
                        st.markdown(f"""
                        <div class="ios-card" style="margin-bottom: 15px; padding: 0; overflow: hidden;">
                            <img src="{img_url}" style="width: 100%; height: 150px; object-fit: cover;" />
                            <div style="padding: 15px;">
                                <div style="font-size: 1.2rem; font-weight: bold;">🏢 {row.get('name', 'Dự án BĐS')}</div>
                                <div style="color: #4ECDC4; font-weight: bold; font-size: 1.1rem; margin-top: 5px;">Giá trị HĐ: {contract_val:,.0f} ₫</div>
                                <div style="font-size: 0.9rem; color: #94a3b8; margin-top: 5px;">Trạng thái: {row.get('status', 'N/A')}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        due_date = row.get('due_date')
                        inst_name = row.get('installment_name')
                        if due_date and inst_name:
                            try:
                                d_date = pd.to_datetime(due_date)
                                days_left = (d_date - pd.to_datetime('today')).days
                                if 0 <= days_left <= 30:
                                    st.warning(f"⚠️ **SẮP ĐẾN HẠN ĐÓNG TIỀN**: Bạn có đợt đóng tiền dự án **{row.get('name')}** ({inst_name}) vào ngày **{d_date.strftime('%d/%m/%Y')}** ({days_left} ngày nữa).")
                            except: pass
                else: st.info("Không có BĐS (hoặc không khớp bộ lọc).")
            else: st.info("Chưa có dữ liệu Bất động sản.")
        except Exception as e:
            st.error("Lỗi dữ liệu BĐS. Đảm bảo bảng 'realestate' tồn tại trên Supabase.")

    with col2:
        st.subheader("Quản lý Khoản Vay (Nợ)")
        try:
            res_debts = supabase.table("debts").select("*").execute()
            if res_debts and res_debts.data:
                df_debts = filter_by_member(pd.DataFrame(res_debts.data), current_member)
                if not df_debts.empty:
                    for _, row in df_debts.iterrows():
                        principal = row['original_principal']
                        rate = row['interest_rate']
                        months = row['total_months']
                        purpose = row.get('purpose', 'Khoản vay')
                        
                        with st.expander(f"🏦 {purpose} - {principal/1000000000:.1f} Tỷ ({rate}%/năm)", expanded=False):
                            st.markdown(f"**Ngân hàng:** {row.get('bank')} | **Thời hạn:** {months} tháng")
                            
                            df_schedule = calculate_amortization(principal, rate, months, row['start_date'])
                            
                            today = pd.to_datetime('today')
                            start_dt = pd.to_datetime(row['start_date'])
                            months_passed = (today.year - start_dt.year) * 12 + (today.month - start_dt.month)
                            current_period = max(1, min(months_passed, months))
                            
                            if months_passed < months:
                                current_balance = df_schedule.iloc[current_period-1]['Dư nợ'] if current_period > 0 else principal
                                paid_amount = principal - current_balance
                                paid_percent = paid_amount / principal * 100
                                
                                st.markdown(f"👉 Dư nợ hiện tại: **{current_balance:,.0f} ₫**")
                                st.markdown(f"Tiến độ trả nợ gốc: **{paid_percent:.1f}%**")
                                st.markdown(f'<div class="progress-container" style="background-color: rgba(239, 68, 68, 0.2);"><div class="progress-bar-fill" style="width: {paid_percent}%; background-color: #ef4444;"></div></div><br/>', unsafe_allow_html=True)
                                
                            st.markdown("**Lịch trả nợ dự kiến:**")
                            render_amortization_table(df_schedule)
                else: st.info("Không có khoản vay nào (hoặc không khớp bộ lọc).")
            else: st.info("Hiện không có khoản vay nào.")
        except Exception as e: st.error(f"Lỗi tải dữ liệu khoản vay: {e}")
