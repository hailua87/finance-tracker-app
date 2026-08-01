import streamlit as st
import pandas as pd
from datetime import date
import time
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit_antd_components as sac

from services.db import init_supabase
from components.ui import load_css, quick_action_button, net_worth_dashboard
from utils.helpers import (
    BROKER_ACCOUNTS, BANK_ACCOUNTS, FUNDS, GOLD_TYPES, parse_smart_amount
)
from modules.cashflow import render_cashflow_tab, modal_cashflow
from modules.savings import render_savings_tab
from modules.investments import render_investments_tab
from modules.realestate import render_realestate_tab

# =====================================================================
# 1. THIẾT LẬP CẤU HÌNH & KẾT NỐI SUPABASE
# =====================================================================
st.set_page_config(
    page_title="Nhà Quê Tập Chi Tiêu", 
    page_icon="💰", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

supabase = init_supabase()

if "last_account" not in st.session_state:
    st.session_state.last_account = "VCB chồng"
if "cf_amount_str" not in st.session_state:
    st.session_state.cf_amount_str = ""
if "current_member" not in st.session_state:
    st.session_state.current_member = "Tất cả"
if "cat_budgets" not in st.session_state:
    st.session_state.cat_budgets = {
        "Ăn uống & Sinh hoạt": 8000000,
        "Nhà cửa & Tiện ích": 3000000,
        "Giáo dục (Con cái)": 3000000,
        "Đi lại & Phương tiện": 1500000,
        "Sức khỏe & Y tế": 1000000,
        "Hiếu hỉ & Mua sắm": 3000000,
        "Đầu tư & Trả nợ": 5000000,
        "Khác": 1000000
    }

# =====================================================================
# 2. LOAD CUSTOM CSS & SIDEBAR FILTER
# =====================================================================
load_css("assets/style.css")

with st.sidebar:
    st.markdown('<div class="hallmark-header" style="font-size: 1.5rem; margin-top: 20px;">THÀNH VIÊN</div>', unsafe_allow_html=True)
    st.session_state.current_member = sac.segmented(
        items=[
            sac.SegmentedItem(label='Tất cả', icon='people-fill'),
            sac.SegmentedItem(label='Daddy', icon='person-workspace'),
            sac.SegmentedItem(label='Mommy', icon='person-hearts'),
            sac.SegmentedItem(label='Baby', icon='person-arms-up'),
        ], label='', align='center', use_container_width=True, index=0
    )

st.markdown(f'<div class="hallmark-header">NHÀ QUÊ TẬP CHI TIÊU. {f"<span style=font-size:1.2rem;>({st.session_state.current_member})</span>" if st.session_state.current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)

# =====================================================================
# 3. KHO MODAL CHO CÁC MODULE KHÁC (@st.dialog)
# =====================================================================
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
# 4. APP ICON GRID (QUICK ACTION MENU)
# =====================================================================
st.markdown('<div class="metric-title" style="margin-bottom: 10px;">⚡ THAO TÁC NHANH</div>', unsafe_allow_html=True)
qa1, qa2, qa3, qa4 = st.columns(4)
with qa1: quick_action_button("💸", "Nhập Chi Tiêu", on_click=modal_cashflow, key="btn_cf")
with qa2: quick_action_button("📈", "Mã Cổ Phiếu", on_click=modal_stock, key="btn_stk")
with qa3: quick_action_button("📊", "GD Chứng Quỹ", on_click=modal_ccq, key="btn_ccq")
with qa4: quick_action_button("🥇", "GD Vàng", on_click=modal_gold, key="btn_gld")

st.markdown("<br/>", unsafe_allow_html=True)

# =====================================================================
# 5. TAB ĐIỀU HƯỚNG CHÍNH
# =====================================================================
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

current_member = st.session_state.current_member

# =====================================================================
# TAB 1: DÒNG TIỀN
# =====================================================================
with tab_cashflow:
    render_cashflow_tab(current_member)

# =====================================================================
# TAB 2: ĐẦU TƯ
# =====================================================================
with tab_invest:
    render_investments_tab(current_member)

# =====================================================================
# TAB 3: TIẾT KIỆM
# =====================================================================
with tab_savings:
    render_savings_tab(current_member)

# =====================================================================
# TAB 4: BĐS & TÍN DỤNG
# =====================================================================
with tab_realestate:
    render_realestate_tab(current_member)

# =====================================================================
# TAB 0: TỔNG QUAN
# =====================================================================
with tab_home:
    def filter_by_member(df, col='fund_owner'):
        if current_member == "Tất cả" or df.empty or col not in df.columns:
            return df
        return df[df[col].str.contains(current_member, na=False, case=False)]

    # 1. Opening Balances (Tiền gửi TT, Tiền mặt khác)
    tong_tien_mat = 0
    try:
        res_ob = supabase.table("opening_balances").select("*").execute()
        if res_ob and res_ob.data:
            df_ob = pd.DataFrame(res_ob.data)
            df_ob = filter_by_member(df_ob)
            tong_tien_mat = pd.to_numeric(df_ob['amount'], errors='coerce').fillna(0).sum() if not df_ob.empty and 'amount' in df_ob.columns else 0
    except: pass

    # 2. Savings
    tong_tiet_kiem = 0
    try: 
        res_savings = supabase.table("savings").select("*").execute()
        if res_savings and res_savings.data:
            df_sv = filter_by_member(pd.DataFrame(res_savings.data))
            tong_tiet_kiem = pd.to_numeric(df_sv["amount"], errors='coerce').fillna(0).sum() if not df_sv.empty and 'amount' in df_sv.columns else 0
    except: pass

    # 3. Real Estate
    bds_da_dong = 0
    try: 
        res_re = supabase.table("realestate").select("*").execute()
        if res_re and res_re.data:
            # Assumed columns: contract_value or amount
            df_re = filter_by_member(pd.DataFrame(res_re.data))
            if 'contract_value' in df_re.columns:
                bds_da_dong = pd.to_numeric(df_re['contract_value'], errors='coerce').fillna(0).sum()
            elif 'amount' in df_re.columns:
                bds_da_dong = pd.to_numeric(df_re['amount'], errors='coerce').fillna(0).sum()
    except: pass
        
    # 4. Debts
    no_khoan_vay, total_monthly_debt_payment = 0, 0
    try:
        res_debts = supabase.table("debts").select("*").execute()
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

    # 5. Stocks
    tong_cp = 0
    try:
        res_stk = supabase.table("stocks").select("*").execute()
        if res_stk and res_stk.data:
            df_stk = filter_by_member(pd.DataFrame(res_stk.data))
            if not df_stk.empty:
                df_stk['volume'] = pd.to_numeric(df_stk['volume'], errors='coerce').fillna(0)
                df_stk['price'] = pd.to_numeric(df_stk['price'], errors='coerce').fillna(0)
                for t, grp in df_stk.groupby('ticker'):
                    net_vol = grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum() - grp[grp['action'].str.contains('Bán', na=False)]['volume'].sum()
                    buy_val = (grp[grp['action'].str.contains('Mua', na=False)]['volume'] * grp[grp['action'].str.contains('Mua', na=False)]['price']).sum()
                    if net_vol > 0:
                        avg_price = buy_val / grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum()
                        tong_cp += net_vol * (avg_price * 1.05)
    except: pass

    # 6. CCQ
    tong_ccq = 0
    try:
        res_ccq = supabase.table("ccq_funds").select("*").execute()
        if res_ccq and res_ccq.data:
            df_ccq = filter_by_member(pd.DataFrame(res_ccq.data))
            if not df_ccq.empty:
                for t, grp in df_ccq.groupby('ticker'):
                    net_vol = grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum() - grp[grp['action'].str.contains('Bán', na=False)]['volume'].sum()
                    buy_val = (grp[grp['action'].str.contains('Mua', na=False)]['volume'] * grp[grp['action'].str.contains('Mua', na=False)]['price']).sum()
                    if net_vol > 0:
                        avg_price = buy_val / grp[grp['action'].str.contains('Mua', na=False)]['volume'].sum()
                        tong_ccq += net_vol * (avg_price * 1.03)
    except: pass
    
    # 7. Gold
    tong_vang = 0
    try:
        res_gold = supabase.table("gold").select("*").execute()
        if res_gold and res_gold.data:
            df_gold = filter_by_member(pd.DataFrame(res_gold.data))
            if not df_gold.empty:
                for t, grp in df_gold.groupby('gold_type'):
                    net_vol = grp[grp['action'].str.contains('Mua', na=False)]['quantity'].sum() - grp[grp['action'].str.contains('Bán', na=False)]['quantity'].sum()
                    if net_vol > 0:
                        mock_price = 8200000 if "SJC" in t else 7650000
                        tong_vang += net_vol * mock_price
    except: pass

    tong_tai_san = tong_tien_mat + tong_tiet_kiem + tong_ccq + tong_cp + bds_da_dong + tong_vang
    tai_san_rong = tong_tai_san - no_khoan_vay

    # HIỂN THỊ NET WORTH DASHBOARD
    net_worth_dashboard(tong_tai_san, no_khoan_vay)

    st.subheader("CƠ CẤU PHÂN BỔ TÀI SẢN & BIỂU ĐỒ TRỰC QUAN")
    col_bar1, col_bar2, col_bar3, col_bar4, col_bar5, col_bar6 = st.columns(6)
    with col_bar1: st.metric("Tiền mặt (Opening)", f"{tong_tien_mat:,.0f} ₫")
    with col_bar2: st.metric("Tiết kiệm", f"{tong_tiet_kiem:,.0f} ₫")
    with col_bar3: st.metric("BĐS", f"{bds_da_dong:,.0f} ₫")
    with col_bar4: st.metric("CCQ", f"{tong_ccq:,.0f} ₫")
    with col_bar5: st.metric("Cổ phiếu", f"{tong_cp:,.0f} ₫")
    with col_bar6: st.metric("Vàng", f"{tong_vang:,.0f} ₫")

    st.markdown("<br/>", unsafe_allow_html=True)

    if tong_tai_san > 0:
        df_chart = pd.DataFrame({
            "Danh mục": ["Tiền mặt", "Tiết kiệm", "BĐS", "CCQ", "Cổ phiếu", "Vàng"],
            "Giá trị": [tong_tien_mat, tong_tiet_kiem, bds_da_dong, tong_ccq, tong_cp, tong_vang]
        })
        df_chart = df_chart[df_chart["Giá trị"] > 0]
        fig = px.pie(df_chart, names="Danh mục", values="Giá trị", hole=0.55, color_discrete_sequence=["#10b981", "#38bdf8", "#f59e0b", "#8b5cf6", "#eab308", "#ef4444"])
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
