@st.dialog("ĐẶT LỆNH MUA / BÁN CỔ PHIẾU")
def modal_stock():
    with st.form("invest_stock_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            broker = st.selectbox("Nơi lưu ký (CTCK)", BROKER_ACCOUNTS + ["Khác"])
        with c2:
            fund_owner_stock = st.selectbox("Thuộc Portfolio", FUNDS)
            
        ticker = st.text_input("Mã cổ phiếu (VD: VIB, MBB, VCI...)").upper()
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        
        c3, c4 = st.columns(2)
        with c3:
            volume = st.number_input("Khối lượng (CP)", min_value=1.0, step=None)
        with c4:
            price = st.number_input("Giá khớp / Giá vốn TB (VND)", min_value=0.0, step=None)
            
        c5, c6 = st.columns(2)
        with c5:
            trade_date = st.date_input("Ngày giao dịch")
        with c6:
            note = st.text_input("Ghi chú", placeholder="VD: Nhập danh mục ban đầu")
            
        if st.form_submit_button("LƯU LỆNH", use_container_width=True):
            if ticker.strip() == "":
                st.error("Vui lòng nhập mã cổ phiếu!")
            else:
                try:
                    data = {
                        "trade_date": str(trade_date),
                        "broker": broker,
                        "fund_owner": fund_owner_stock,
                        "ticker": ticker.strip(),
                        "action": action,
                        "volume": int(volume),
                        "price": float(price),
                        "note": note
                    }
                    supabase.table("stocks").insert(data).execute()
                    st.success(f"Đã lưu lệnh {action} {int(volume)} CP {ticker} thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu lệnh: {e}. Vui lòng tạo cột 'trade_date' (date) và 'note' (text) trong bảng 'stocks'.")

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("invest_ccq_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            platform = st.selectbox("Nền tảng giao dịch", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM"])
        with c2:
            fund_owner_ccq = st.selectbox("Thuộc Portfolio", FUNDS)
            
        fund_ticker = st.text_input("Mã Quỹ (VD: DCDS, VESAF...)").upper()
        action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
        
        c3, c4 = st.columns(2)
        with c3:
            volume_ccq = st.number_input("Số lượng CCQ", min_value=0.01, step=None, format="%.2f")
        with c4:
            nav_price = st.number_input("Giá NAV / Giá vốn TB (VND)", min_value=0.0, step=None)
            
        c5, c6 = st.columns(2)
        with c5:
            trade_date = st.date_input("Ngày giao dịch")
        with c6:
            note = st.text_input("Ghi chú", placeholder="VD: Khởi tạo số dư")
            
        if st.form_submit_button("LƯU GIAO DỊCH QUỸ", use_container_width=True):
            if not fund_ticker.strip():
                st.error("Vui lòng nhập mã quỹ!")
            else:
                try:
                    data = {
                        "trade_date": str(trade_date),
                        "platform": platform,
                        "fund_owner": fund_owner_ccq,
                        "ticker": fund_ticker.strip(),
                        "action": action_ccq,
                        "volume": float(volume_ccq),
                        "price": float(nav_price),
                        "note": note
                    }
                    supabase.table("ccq_funds").insert(data).execute()
                    st.success(f"Đã lưu lệnh {fund_ticker} qua {platform}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}. Vui lòng tạo cột 'trade_date' (date) và 'note' (text) trong bảng 'ccq_funds'.")

# ---------------------------------------------------------
# COPY PHẦN NÀY ĐỂ THAY THẾ TOÀN BỘ NỘI DUNG TAB 2 (ĐẦU TƯ)
# ---------------------------------------------------------

with tab_invest:
    subtab_stock, subtab_ccq = st.tabs(["📈 CỔ PHIẾU", "📊 CHỨNG CHỈ QUỸ (CCQ)"])
    
    with subtab_stock:
        col_btn2, _ = st.columns([1.5, 3])
        with col_btn2:
            if st.button("+ ĐẶT LỆNH MUA / BÁN CP", use_container_width=True):
                modal_stock()
                
        st.markdown("<br/>", unsafe_allow_html=True)
        stk_sub1, stk_sub2 = st.tabs(["Danh mục tồn kho hiện tại", "Lịch sử đặt lệnh"])
        
        try:
            res_stk = supabase.table("stocks").select("*").execute()
            df_stk = pd.DataFrame(res_stk.data) if res_stk.data else pd.DataFrame()
        except:
            df_stk = pd.DataFrame()
            
        with stk_sub1:
            if not df_stk.empty and 'ticker' in df_stk.columns:
                summary_list = []
                for ticker, grp in df_stk.groupby('ticker'):
                    buy_rows = grp[grp['action'] == 'Mua']
                    sell_rows = grp[grp['action'] == 'Bán']
                    
                    buy_vol = buy_rows['volume'].sum()
                    sell_vol = sell_rows['volume'].sum()
                    net_vol = buy_vol - sell_vol
                    
                    buy_val = (buy_rows['volume'] * buy_rows['price']).sum()
                    avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                    total_cost = net_vol * avg_price
                    broker_name = grp['broker'].iloc[0] if 'broker' in grp.columns else 'N/A'
                    
                    if net_vol > 0:
                        summary_list.append({
                            "Mã CK": ticker,
                            "Công ty CK": broker_name,
                            "Khối lượng tồn": net_vol,
                            "Giá vốn TB (VND)": avg_price,
                            "Tổng giá vốn (VND)": total_cost
                        })
                        
                if summary_list:
                    df_portfolio = pd.DataFrame(summary_list)
                    st.dataframe(
                        df_portfolio,
                        column_config={
                            "Khối lượng tồn": st.column_config.NumberColumn("Khối lượng tồn", format="%,.0f"),
                            "Giá vốn TB (VND)": st.column_config.NumberColumn("Giá vốn TB (VND)", format="%,.0f ₫"),
                            "Tổng giá vốn (VND)": st.column_config.NumberColumn("Tổng giá vốn (VND)", format="%,.0f ₫")
                        },
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.info("Hiện không có cổ phiếu nào trong danh mục (Khối lượng tồn = 0).")
            else:
                st.info("💡 Chưa có dữ liệu. Để cập nhật danh mục CŨ, hãy bấm '+ Đặt lệnh Mua/Bán CP', chọn 'Mua', nhập tổng khối lượng và giá vốn trung bình hiện tại.")

        with stk_sub2:
            if not df_stk.empty:
                df_stk['Ngày'] = pd.to_datetime(df_stk['trade_date']).dt.strftime('%d/%m/%Y') if 'trade_date' in df_stk.columns else ""
                df_stk_display = df_stk[['id', 'Ngày', 'broker', 'fund_owner', 'ticker', 'action', 'volume', 'price', 'note']].rename(columns={
                    'broker': 'CTCK', 'fund_owner': 'Portfolio', 'ticker': 'Mã CK', 'action': 'Lệnh', 'volume': 'Khối lượng', 'price': 'Giá khớp', 'note': 'Ghi chú'
                })
                st.dataframe(
                    df_stk_display,
                    column_config={
                        "id": None,
                        "Khối lượng": st.column_config.NumberColumn("Khối lượng", format="%,.0f"),
                        "Giá khớp": st.column_config.NumberColumn("Giá khớp", format="%,.0f ₫")
                    },
                    use_container_width=True, hide_index=True
                )
                
                st.markdown("---")
                del_stk_id = st.selectbox("Chọn ID lệnh để xóa nếu nhập sai:", df_stk['id'].tolist(), key="del_stk_id")
                if st.button("❌ XÓA LỆNH NÀY", key="btn_del_stk"):
                    supabase.table("stocks").delete().eq("id", del_stk_id).execute()
                    st.success("Đã xóa lệnh thành công!")
                    st.rerun()
            else:
                st.info("Chưa có lịch sử lệnh nào.")

    with subtab_ccq:
        col_btn_ccq, _ = st.columns([1.5, 3])
        with col_btn_ccq:
            if st.button("+ ĐẶT LỆNH MUA / BÁN CCQ", use_container_width=True):
                modal_ccq()
                
        st.markdown("<br/>", unsafe_allow_html=True)
        ccq_sub1, ccq_sub2 = st.tabs(["Danh mục CCQ tồn kho", "Lịch sử lệnh quỹ"])
        
        try:
            res_fund = supabase.table("ccq_funds").select("*").execute()
            df_fund = pd.DataFrame(res_fund.data) if res_fund.data else pd.DataFrame()
        except:
            df_fund = pd.DataFrame()
            
        with ccq_sub1:
            if not df_fund.empty and 'ticker' in df_fund.columns:
                fund_summary = []
                for ticker, grp in df_fund.groupby('ticker'):
                    buy_rows = grp[grp['action'] == 'Mua']
                    sell_rows = grp[grp['action'] == 'Bán']
                    
                    buy_vol = buy_rows['volume'].sum()
                    sell_vol = sell_rows['volume'].sum()
                    net_vol = buy_vol - sell_vol
                    
                    buy_val = (buy_rows['volume'] * buy_rows['price']).sum()
                    avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                    total_cost = net_vol * avg_price
                    platform_name = grp['platform'].iloc[0] if 'platform' in grp.columns else 'N/A'
                    
                    if net_vol > 0:
                        fund_summary.append({
                            "Mã Quỹ": ticker,
                            "Nền tảng": platform_name,
                            "Số lượng tồn": net_vol,
                            "Giá NAV TB (VND)": avg_price,
                            "Tổng giá trị (VND)": total_cost
                        })
                        
                if fund_summary:
                    df_fund_port = pd.DataFrame(fund_summary)
                    st.dataframe(
                        df_fund_port,
                        column_config={
                            "Số lượng tồn": st.column_config.NumberColumn("Số lượng tồn", format="%,.2f"),
                            "Giá NAV TB (VND)": st.column_config.NumberColumn("Giá NAV TB (VND)", format="%,.0f ₫"),
                            "Tổng giá trị (VND)": st.column_config.NumberColumn("Tổng giá trị (VND)", format="%,.0f ₫")
                        },
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.info("Hiện không có chứng chỉ quỹ nào trong danh mục.")
            else:
                st.info("💡 Chưa có dữ liệu. Để cập nhật danh mục CCQ CŨ, hãy bấm '+ Đặt lệnh Mua/Bán CCQ', chọn 'Mua', nhập tổng khối lượng và giá NAV trung bình hiện tại.")

        with ccq_sub2:
            if not df_fund.empty:
                df_fund['Ngày'] = pd.to_datetime(df_fund['trade_date']).dt.strftime('%d/%m/%Y') if 'trade_date' in df_fund.columns else ""
                df_fund_display = df_fund[['id', 'Ngày', 'platform', 'fund_owner', 'ticker', 'action', 'volume', 'price', 'note']].rename(columns={
                    'platform': 'Nền tảng', 'fund_owner': 'Portfolio', 'ticker': 'Mã Quỹ', 'action': 'Lệnh', 'volume': 'Số lượng', 'price': 'Giá NAV', 'note': 'Ghi chú'
                })
                st.dataframe(
                    df_fund_display,
                    column_config={
                        "id": None,
                        "Số lượng": st.column_config.NumberColumn("Số lượng", format="%,.2f"),
                        "Giá NAV": st.column_config.NumberColumn("Giá NAV", format="%,.0f ₫")
                    },
                    use_container_width=True, hide_index=True
                )
                
                st.markdown("---")
                del_ccq_id = st.selectbox("Chọn ID lệnh để xóa nếu nhập sai:", df_fund['id'].tolist(), key="del_ccq_id")
                if st.button("❌ XÓA LỆNH NÀY", key="btn_del_ccq"):
                    supabase.table("ccq_funds").delete().eq("id", del_ccq_id).execute()
                    st.success("Đã xóa lệnh thành công!")
                    st.rerun()
            else:
                st.info("Chưa có lịch sử lệnh quỹ nào.")
