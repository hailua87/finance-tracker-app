import streamlit as st

def load_css(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Không tìm thấy file CSS tại: {file_path}")

def dashboard_card(title: str, value_str: str, value_color: str = "#f8fafc", icon: str = "", extra_classes: str = ""):
    """Creates a unified dashboard card with custom styling."""
    html = f"""
    <div class="ios-card {extra_classes}">
        <div class="metric-title">{icon} {title}</div>
        <div style="font-family: 'Inter', sans-serif; font-size: 1.5rem; font-weight: 700; color: {value_color};">
            {value_str}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def budget_card(title: str, budget_limit: float, spent: float):
    """Specialized card for budget progress."""
    percent_spent = spent / budget_limit if budget_limit > 0 else 0
    budget_remaining = budget_limit - spent
    bg_class = "budget-alert" if percent_spent > 0.8 else "budget-safe"
    
    html = f"""
    <div class="ios-card {bg_class}" style="margin-top: 10px;">
        <div class="metric-title">🎯 {title} ({(budget_limit/1000000):.1f}TR)</div>
        <div style="font-family: 'Inter', sans-serif; font-size: 2.2rem; font-weight: 700;">{budget_remaining:,.0f} ₫</div>
        <div style="font-size: 0.85rem; opacity: 0.8; margin-top: 5px;">Tiến độ sử dụng: {percent_spent*100:.1f}%</div>
        <div class="progress-container">
            <div class="progress-bar-fill" style="width: {min(percent_spent*100, 100)}%;"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def quick_action_button(icon: str, label: str, on_click=None, args=None, key=None):
    """Renders a styled quick action button in a grid."""
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
    html = f"""
    <div class="ios-card {theme_class}" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <div class="savings-goal-title">{name}</div>
            <div style="font-size: 1.8rem; font-weight: 700; font-family: 'Inter', sans-serif;">{current:,.0f} ₫</div>
            <div style="font-size: 0.85rem; opacity: 0.8; margin-top: 5px;">Mục tiêu: {target:,.0f} ₫ ({percent*100:.1f}%)</div>
        </div>
        <div class="progress-container" style="margin-top: 15px; margin-bottom: 15px; background-color: rgba(255,255,255,0.3);">
            <div class="progress-bar-fill" style="width: {min(percent*100, 100)}%; background-color: white;"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    st.button(f"⚡ Nạp {name}", key=deposit_key, on_click=on_deposit_click, use_container_width=True)

def net_worth_dashboard(total_assets: float, total_debts: float):
    net_worth = total_assets - total_debts
    html = f"""
    <div class="ios-card" style="margin-bottom: 20px; background: var(--primary-navy); border: 1px solid var(--accent-gold);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <div class="metric-title" style="color: #94a3b8;">💎 TÀI SẢN RÒNG (NET WORTH)</div>
                <div style="font-family: 'Inter', sans-serif; font-size: 3rem; font-weight: 700; color: var(--accent-gold);">{net_worth:,.0f} ₫</div>
            </div>
            <div style="display: flex; gap: 30px;">
                <div>
                    <div class="metric-title" style="color: #94a3b8;">📈 TỔNG TÀI SẢN</div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: #10b981;">+{total_assets:,.0f} ₫</div>
                </div>
                <div>
                    <div class="metric-title" style="color: #94a3b8;">📉 TỔNG NỢ</div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: #ef4444;">-{total_debts:,.0f} ₫</div>
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_amortization_table(df):
    """Render a styled HTML table for the amortization schedule."""
    html = '<div style="max-height: 400px; overflow-y: auto;"><table class="amortization-table">'
    html += '<thead><tr><th>Kỳ (Tháng)</th><th>Ngày trả</th><th>Gốc phải trả</th><th>Lãi phải trả</th><th>Tổng gốc + lãi</th><th>Dư nợ còn lại</th></tr></thead><tbody>'
    for _, row in df.iterrows():
        html += f"""
        <tr>
            <td style="text-align: left;">{int(row['Kỳ'])}</td>
            <td>{row['Ngày trả']}</td>
            <td>{row['Gốc']:,.0f}</td>
            <td>{row['Lãi']:,.0f}</td>
            <td style="color: #F87171; font-weight: bold;">{row['Tổng trả']:,.0f}</td>
            <td>{row['Dư nợ']:,.0f}</td>
        </tr>
        """
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)
