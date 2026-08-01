import streamlit as st

def load_css(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Không tìm thấy file CSS tại: {file_path}")

def dashboard_card(title: str, value_str: str, value_color: str = "#333333", icon: str = "", extra_classes: str = ""):
    html = f'''
    <div class="ios-card {extra_classes}">
        <div class="metric-title">{icon} {title}</div>
        <div style="font-family: 'Inter', sans-serif; font-size: 1.5rem; font-weight: 700; color: {value_color};">
            {value_str}
        </div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)

def budget_card(title: str, budget_limit: float, spent: float):
    percent_spent = spent / budget_limit if budget_limit > 0 else 0
    budget_remaining = budget_limit - spent
    bg_class = "budget-alert" if percent_spent > 0.8 else "budget-safe"
    
    html = f'''
    <div class="ios-card {bg_class}" style="margin-top: 10px;">
        <div class="metric-title" style="margin-bottom: 2px;">🎯 {title} ({(budget_limit/1000000):.1f}TR)</div>
        <div style="font-family: 'Inter', sans-serif; font-size: 2.2rem; font-weight: 700; margin-bottom: 5px;">{budget_remaining:,.0f} ₫</div>
        <div style="font-size: 0.85rem; font-weight: 600; opacity: 0.8; margin-top: 5px;">Tiến độ sử dụng: {percent_spent*100:.1f}%</div>
        <div class="progress-container" style="background-color: rgba(0,0,0,0.1);">
            <div class="progress-bar-fill" style="width: {min(percent_spent*100, 100)}%; background-color: inherit;"></div>
        </div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)

def quick_action_button(icon: str, label: str, on_click=None, args=None, key=None):
    st.markdown('<div class="app-icon-btn">', unsafe_allow_html=True)
    clicked = st.button(f"{icon}\n{label}", use_container_width=True, key=key)
    st.markdown('</div>', unsafe_allow_html=True)
    if clicked and on_click:
        if args:
            on_click(*args)
        else:
            on_click()
    return clicked

def savings_goal_card(name: str, current: float, target: float, theme_class: str, on_deposit_click, deposit_key: str):
    percent = current / target if target > 0 else 0
    html = f'''
    <div class="ios-card {theme_class}" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <div class="savings-goal-title">{name}</div>
            <div style="font-size: 1.8rem; font-weight: 700; font-family: 'Inter', sans-serif; color: var(--text-main);">{current:,.0f} ₫</div>
            <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 5px;">Mục tiêu: {target:,.0f} ₫ ({percent*100:.1f}%)</div>
        </div>
        <div class="progress-container" style="margin-top: 15px; margin-bottom: 15px; background-color: #f3f4f6;">
            <div class="progress-bar-fill" style="width: {min(percent*100, 100)}%;"></div>
        </div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)
    st.button(f"⚡ Nạp {name}", key=deposit_key, on_click=on_deposit_click, use_container_width=True)

def net_worth_dashboard(total_assets: float, total_debts: float):
    net_worth = total_assets - total_debts
    html = f'''
    <div class="ios-card" style="margin-bottom: 20px; border-top: 4px solid var(--primary-green);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <div class="metric-title">💎 TÀI SẢN RÒNG (NET WORTH)</div>
                <div style="font-family: 'Inter', sans-serif; font-size: 3rem; font-weight: 700; color: var(--primary-green);">{net_worth:,.0f} ₫</div>
            </div>
            <div style="display: flex; gap: 30px;">
                <div>
                    <div class="metric-title">📈 TỔNG TÀI SẢN</div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--accent-blue);">+{total_assets:,.0f} ₫</div>
                </div>
                <div>
                    <div class="metric-title">📉 TỔNG NỢ</div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: var(--alert-red);">-{total_debts:,.0f} ₫</div>
                </div>
            </div>
        </div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)
