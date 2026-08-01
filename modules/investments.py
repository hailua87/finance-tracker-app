import streamlit as st
import pandas as pd
from services.db import init_supabase

supabase = init_supabase()

def filter_by_member(df, current_member, col='fund_owner'):
    if current_member == "Tất cả" or df.empty or col not in df.columns:
        return df
    return df[df[col].str.contains(current_member, na=False, case=False)]

def render_investments_tab(current_member="Tất cả"):
    st.markdown(f'<div class="metric-title" style="margin-bottom:10px;">DANH MỤC ĐẦU TƯ ĐA KÊNH {f"({current_member})" if current_member != "Tất cả" else ""}</div>', unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📈 Chứng khoán", "📊 Chứng chỉ quỹ", "🥇 Vàng tích sản"])
    
    def calculate_wa_profit(df_grp, mock_price):
        buys = df_grp[df_grp['action'].str.contains('Mua', na=False, case=False)]
        sells = df_grp[df_grp['action'].str.contains('Bán', na=False, case=False)]
        
        buy_vol = buys['volume'].sum() if not buys.empty else 0
        sell_vol = sells['volume'].sum() if not sells.empty else 0
        current_vol = buy_vol - sell_vol
        
        if current_vol > 0:
            buy_val = (buys['volume'] * buys['price']).sum()
            avg_price = buy_val / buy_vol if buy_vol > 0 else 0
            profit = (mock_price - avg_price) * current_vol
            profit_pct = (mock_price - avg_price) / avg_price * 100 if avg_price > 0 else 0
            return current_vol, avg_price, mock_price, profit, profit_pct
        return 0, 0, 0, 0, 0

    with t1:
        try:
            res_stk = supabase.table("stocks").select("*").execute()
            if res_stk and res_stk.data:
                df = filter_by_member(pd.DataFrame(res_stk.data), current_member)
                if not df.empty:
                    summary = []
                    for ticker, grp in df.groupby("ticker"):
                        # Mocking current price logic
                        buy_val_temp = (grp[grp['action'].str.contains('Mua', na=False, case=False)]['volume'] * grp[grp['action'].str.contains('Mua', na=False, case=False)]['price']).sum()
                        buy_vol_temp = grp[grp['action'].str.contains('Mua', na=False, case=False)]['volume'].sum()
                        mock_price = (buy_val_temp / buy_vol_temp * 1.05) if buy_vol_temp > 0 else 0
                        
                        vol, avg, cur, prof, pct = calculate_wa_profit(grp, mock_price)
                        if vol > 0:
                            summary.append({
                                "Mã CP": f"🏢 {ticker}",
                                "Khối lượng": vol,
                                "Giá vốn WAC": avg,
                                "Giá TT (Giả lập)": cur,
                                "Lợi nhuận": prof,
                                "% Lãi/Lỗ": pct
                            })
                    if summary:
                        df_sum = pd.DataFrame(summary)
                        def color_profit(val):
                            color = '#10b981' if val > 0 else '#ef4444' if val < 0 else 'white'
                            return f'color: {color}; font-weight: bold;'
                            
                        st.dataframe(
                            df_sum.style.map(color_profit, subset=['Lợi nhuận', '% Lãi/Lỗ']),
                            hide_index=True, use_container_width=True, 
                            column_config={
                                "Khối lượng": st.column_config.NumberColumn(format="%d"),
                                "Giá vốn WAC": st.column_config.NumberColumn(format="%,.0f ₫"),
                                "Giá TT (Giả lập)": st.column_config.NumberColumn(format="%,.0f ₫"),
                                "Lợi nhuận": st.column_config.NumberColumn(format="%,.0f ₫"),
                                "% Lãi/Lỗ": st.column_config.NumberColumn(format="%+.2f%%")
                            }
                        )
                    else: st.info("Không có cổ phiếu nào đang nắm giữ.")
                else: st.info("Chưa có giao dịch chứng khoán (hoặc không phù hợp bộ lọc).")
            else: st.info("Chưa có giao dịch chứng khoán.")
        except Exception as e: st.error(f"Lỗi tải dữ liệu chứng khoán: {e}")

    with t2:
        try:
            res_ccq = supabase.table("ccq_funds").select("*").execute()
            if res_ccq and res_ccq.data:
                df = filter_by_member(pd.DataFrame(res_ccq.data), current_member)
                if not df.empty:
                    summary = []
                    for ticker, grp in df.groupby("ticker"):
                        buy_val_temp = (grp[grp['action'].str.contains('Mua', na=False, case=False)]['volume'] * grp[grp['action'].str.contains('Mua', na=False, case=False)]['price']).sum()
                        buy_vol_temp = grp[grp['action'].str.contains('Mua', na=False, case=False)]['volume'].sum()
                        mock_price = (buy_val_temp / buy_vol_temp * 1.03) if buy_vol_temp > 0 else 0
                        
                        vol, avg, cur, prof, pct = calculate_wa_profit(grp, mock_price)
                        if vol > 0:
                            summary.append({"Mã Quỹ": f"📈 {ticker}", "Số lượng": vol, "Giá vốn WAC": avg, "Giá TT": cur, "Lợi nhuận": prof, "% Lãi/Lỗ": pct})
                    if summary:
                        df_sum = pd.DataFrame(summary)
                        st.dataframe(df_sum.style.map(lambda v: f"color: {'#10b981' if v>0 else '#ef4444'}; font-weight: bold;", subset=['Lợi nhuận', '% Lãi/Lỗ']), hide_index=True, use_container_width=True, column_config={"Số lượng": st.column_config.NumberColumn(format="%.2f"), "Giá vốn WAC": st.column_config.NumberColumn(format="%,.0f ₫"), "Giá TT": st.column_config.NumberColumn(format="%,.0f ₫"), "Lợi nhuận": st.column_config.NumberColumn(format="%,.0f ₫"), "% Lãi/Lỗ": st.column_config.NumberColumn(format="%+.2f%%")})
                    else: st.info("Không có CCQ nào đang nắm giữ.")
                else: st.info("Chưa có giao dịch chứng chỉ quỹ (hoặc bộ lọc).")
            else: st.info("Chưa có giao dịch chứng chỉ quỹ.")
        except Exception as e: st.error(f"Lỗi: {e}")
    
    with t3:
        st.markdown('**Giá vàng tham khảo (Mockup API)**')
        df_gold_prices = pd.DataFrame({
            "Loại Vàng": ["SJC Miếng", "Nhẫn trơn 9999", "PNJ", "DOJI"],
            "Mua vào (₫/Chỉ)": [8_000_000, 7_500_000, 7_550_000, 7_950_000],
            "Bán ra (₫/Chỉ)": [8_200_000, 7_650_000, 7_700_000, 8_150_000],
        })
        st.dataframe(df_gold_prices, hide_index=True, use_container_width=True, column_config={"Mua vào (₫/Chỉ)": st.column_config.NumberColumn(format="%,.0f"), "Bán ra (₫/Chỉ)": st.column_config.NumberColumn(format="%,.0f")})
        
        st.markdown('**Số dư Vàng của bạn**')
        try:
            res_gold = supabase.table("gold").select("*").execute()
            if res_gold and res_gold.data:
                df = filter_by_member(pd.DataFrame(res_gold.data), current_member)
                if not df.empty:
                    summary = []
                    for gtype, grp in df.groupby("gold_type"):
                        buys = grp[grp['action'].str.contains('Mua', na=False, case=False)]
                        sells = grp[grp['action'].str.contains('Bán', na=False, case=False)]
                        buy_qty = buys['quantity'].sum() if not buys.empty else 0
                        sell_qty = sells['quantity'].sum() if not sells.empty else 0
                        current_qty = buy_qty - sell_qty
                        if current_qty > 0:
                            buy_val = (buys['quantity'] * buys['price']).sum()
                            avg_price = buy_val / buy_qty if buy_qty > 0 else 0
                            current_price = 8200000 if "SJC" in gtype else 7650000
                            profit = (current_price - avg_price) * current_qty
                            summary.append({"Loại Vàng": f"🥇 {gtype}", "Số lượng (Chỉ)": current_qty, "Giá vốn/Chỉ": avg_price, "Lợi nhuận (Tạm tính)": profit})
                    if summary:
                        df_sum = pd.DataFrame(summary)
                        st.dataframe(df_sum.style.map(lambda v: f"color: {'#10b981' if v>0 else '#ef4444'}; font-weight: bold;", subset=['Lợi nhuận (Tạm tính)']), hide_index=True, use_container_width=True, column_config={"Số lượng (Chỉ)": st.column_config.NumberColumn(format="%.2f"), "Giá vốn/Chỉ": st.column_config.NumberColumn(format="%,.0f ₫"), "Lợi nhuận (Tạm tính)": st.column_config.NumberColumn(format="%,.0f ₫")})
                    else: st.info("Bạn chưa nắm giữ vàng.")
                else: st.info("Không có dữ liệu Vàng (hoặc bộ lọc không khớp).")
            else: st.info("Chưa có dữ liệu Vàng.")
        except Exception as e: st.error(f"Lỗi: {e}")
