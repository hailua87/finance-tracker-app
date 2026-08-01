import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client
import plotly.express as px

# 1. THIẾT LẬP CẤU HÌNH & KẾT NỐI SUPABASE
st.set_page_config(page_title="Nhà Quê Tập Chi Tiêu", layout="wide")

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_supabase()

# 2. HALLMARK CUSTOM CSS INJECTION & MODERN UI ENHANCEMENTS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, .stMetricValue {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.03em;
    }
    
    .hallmark-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #f8fafc;
        border-left: 6px solid #10b981;
        padding-left: 15px;
        margin-bottom: 25px;
        margin-top: -10px;
    }
    
    .metric-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        font-weight: 600;
    }

    #stHeader { display: none; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hallmark-header">NHÀ QUÊ TẬP CHI TIÊU.</div>', unsafe_allow_html=True)

def color_profit_loss(val):
    color = '#10b981' if val > 0 else '#ef4444' if val < 0 else '#94a3b8'
    return f'color: {color}; font-weight: bold; font-family: "Space Grotesk";'

DEBIT_ACCOUNTS = ["VCB chồng", "TCB chồng", "TCB vợ"]
CREDIT_CARDS = ["UOB vợ", "UOB chồng", "HSBC chồng"]
BROKER_ACCOUNTS = ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Mirae Asset"]

BANK_ACCOUNTS = DEBIT_ACCOUNTS + CREDIT_CARDS + BROKER_ACCOUNTS
FUNDING_SOURCES = BANK_ACCOUNTS + ["Tiền mặt", "Giải ngân vốn vay", "Khác"]
TERMS = ["Không kỳ hạn", "1 Tháng", "2 Tháng", "3 Tháng", "6 Tháng", "7 Tháng", "8 Tháng", "9 Tháng", "10 Tháng", "11 Tháng", "12 Tháng", "13 Tháng", "18 Tháng", "24 Tháng", "36 Tháng"]

CATS = [
    "Lương/Thu nhập", 
    "Ăn uống & Sinh hoạt", 
    "Giáo dục (Con cái)", 
    "Nhà cửa & Tiện ích", 
    "Sức khỏe & Y tế", 
    "Đi lại & Phương tiện", 
    "Hiếu hỉ & Mua sắm", 
    "Đầu tư & Trả nợ", 
    "Khác"
]
FUNDS = ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"]

# 3. KHO MODAL (@st.dialog)
@st.dialog("GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    with st.form("cashflow_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            account = st.selectbox("Tài khoản nguồn", BANK_ACCOUNTS)
        with c2:
            category = st.selectbox("Phân loại", CATS)
            
        amount = st.number_input("Số tiền (VND)", min_value=0.0, step=None)
        note = st.text_input("Ghi chú")
        
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True):
            try:
                data = {"account": account, "amount": int(amount), "category": category, "note": note}
                supabase.table("cashflow").insert(data).execute()
                st.success(f"Đã lưu thành công {amount:,.0f} VND!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}")

@st.dialog("SỬA GIAO DỊCH DÒNG TIỀN")
def modal_edit_cashflow(row_data):
    with st.form("edit_cashflow_form", clear_on_submit=True):
        idx_acc = BANK_ACCOUNTS.index(row_data['account']) if row_data['account'] in BANK_ACCOUNTS else 0
        idx_cat = CATS.index(row_data['category']) if row_data['category'] in CATS else 0
        
        c1, c2 = st.columns(2)
        with c1:
            account = st.selectbox("Tài khoản nguồn", BANK_ACCOUNTS, index=idx_acc)
        with c2:
            category = st.selectbox("Phân loại", CATS, index=idx_cat)
            
        amount = st.number_input("Số tiền (VND)", min_value=0.0, step=None, value=float(row_data['amount']))
        note = st.text_input("Ghi chú", value=row_data['note'] if row_data['note'] else "")
        
        if st.form_submit_button("CẬP NHẬT", use_container_width=True):
            try:
                data = {"account": account, "amount": int(amount), "category": category, "note": note}
                supabase.table("cashflow").update(data).eq("id", row_data['id']).execute()
                st.success("Đã cập nhật thành công!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

@st.dialog("CẤU HÌNH SỐ DƯ GỐC BAN ĐẦU")
def modal_opening_balance():
    with st.form("opening_balance_form"):
        st.markdown("Nhập số dư gốc ban đầu tại mốc xuất phát lịch sử (Ví dụ: Chốt trước 01/08/2026):")
        
        try:
            res = supabase.table("opening_balances").select("*").execute()
            old_data = {row['account']: row['balance'] for row in res.data} if res.data else {}
        except:
            old_data = {}
            
        balances = {}
        tab_debit, tab_broker, tab_credit = st.tabs(["💳 Tài khoản thanh toán", "📈 Tài khoản CK", "💳 Thẻ tín dụng"])
        
        with tab_debit:
            st.markdown("##### Tài khoản thanh toán (Số dư dương)")
            for i in range(0, len(DEBIT_ACCOUNTS), 2):
                c1, c2 = st.columns(2)
                with c1:
                    acc1 = DEBIT_ACCOUNTS[i]
                    balances[acc1] = st.number_input(f"{acc1} (VND)", min_value=0.0, step=None, value=float(old_data.get(acc1, 0.0)), key=f"ob_{acc1}")
                with c2:
                    if i + 1 < len(DEBIT_ACCOUNTS):
                        acc2 = DEBIT_ACCOUNTS[i+1]
                        balances[acc2] = st.number_input(f"{acc2} (VND)", min_value=0.0, step=None, value=float(old_data.get(acc2, 0.0)), key=f"ob_{acc2}")
                        
        with tab_broker:
            st.markdown("##### Tài khoản Chứng khoán (Tiền mặt / Margin)")
            for i in range(0, len(BROKER_ACCOUNTS), 2):
                c1, c2 = st.columns(2)
                with c1:
                    acc1 = BROKER_ACCOUNTS[i]
                    balances[acc1] = st.number_input(f"{acc1} (VND)", step=None, value=float(old_data.get(acc1, 0.0)), key=f"ob_{acc1}")
                with c2:
                    if i + 1 < len(BROKER_ACCOUNTS):
                        acc2 = BROKER_ACCOUNTS[i+1]
                        balances[acc2] = st.number_input(f"{acc2} (VND)", step=None, value=float(old_data.get(acc2, 0.0)), key=f"ob_{acc2}")
                        
        with tab_credit:
            st.markdown("##### Thẻ tín dụng (Dư nợ gốc cần trả)")
            for i in range(0, len(CREDIT_CARDS), 2):
                c1, c2 = st.columns(2)
                with c1:
                    acc1 = CREDIT_CARDS[i]
                    balances[acc1] = st.number_input(f"Dư nợ {acc1} (VND)", min_value=0.0, step=None, value=float(old_data.get(acc1, 0.0)), key=f"ob_{acc1}")
                with c2:
                    if i + 1 < len(CREDIT_CARDS):
                        acc2 = CREDIT_CARDS[i+1]
                        balances[acc2] = st.number_input(f"Dư nợ {acc2} (VND)", min_value=0.0, step=None, value=float(old_data.get(acc2, 0.0)), key=f"ob_{acc2}")
            
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.form_submit_button("LƯU SỐ DƯ GỐC", use_container_width=True):
            try:
                for acc, bal in balances.items():
                    supabase.table("opening_balances").upsert({"account": acc, "balance": int(bal)}, on_conflict="account").execute()
                st.success("Đã lưu số dư gốc thành công!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}. Đảm bảo bạn đã tạo bảng 'opening_balances' trên Supabase.")

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
            platform = st.selectbox("Nền tảng giao dịch", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM", "SSI", "VNDirect"])
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

@st.dialog("THÊM KHOẢN GỬI TIẾT KIỆM")
def modal_savings():
    with st.form("new_deposit_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_fund = st.selectbox("Chọn Portfolio", FUNDS)
        with c2:
            new_bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS)
            
        new_amount = st.number_input("Số tiền gốc (VND)", min_value=0.0, step=None)
        
        c3, c4 = st.columns(2)
        with c3:
            new_date = st.date_input("Ngày gửi")
        with c4:
            new_term = st.selectbox("Kỳ hạn", TERMS)
            
        new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=None, format="%.2f")
        
        if st.form_submit_button("LƯU KHOẢN GỬI", use_container_width=True):
            try:
                data = {
                    "fund_owner": new_fund, "bank": new_bank, "deposit_date": str(new_date),
                    "term": new_term, "interest_rate": new_rate, "amount": int(new_amount)
                }
                supabase.table("savings").insert(data).execute()
                st.success("Đã lưu sổ tiết kiệm mới!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}")

@st.dialog("SỬA KHOẢN GỬI TIẾT KIỆM")
def modal_edit_savings(row_data):
    with st.form("edit_deposit_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            idx_fund = FUNDS.index(row_data['fund_owner']) if row_data['fund_owner'] in FUNDS else 0
            new_fund = st.selectbox("Chọn Portfolio", FUNDS, index=idx_fund)
        with c2:
            idx_bank = BANK_ACCOUNTS.index(row_data['bank']) if row_data['bank'] in BANK_ACCOUNTS else 0
            new_bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS, index=idx_bank)
            
        new_amount = st.number_input("Số tiền gốc (VND)", min_value=0.0, step=None, value=float(row_data['amount']))
        
        c3, c4 = st.columns(2)
        with c3:
            try:
                dep_dt = pd.to_datetime(row_data['deposit_date']).date()
            except:
                dep_dt = date.today()
            new_date = st.date_input("Ngày gửi", value=dep_dt)
        with c4:
            idx_term = TERMS.index(row_data['term']) if row_data['term'] in TERMS else 0
            new_term = st.selectbox("Kỳ hạn", TERMS, index=idx_term)
            
        new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=None, format="%.2f", value=float(row_data['interest_rate']))
        
        if st.form_submit_button("CẬP NHẬT SỔ TIẾT KIỆM", use_container_width=True):
            try:
                data = {
                    "fund_owner": new_fund, "bank": new_bank, "deposit_date": str(new_date),
                    "term": new_term, "interest_rate": new_rate, "amount": int(new_amount)
                }
                supabase.table("savings").update(data).eq("id", row_data['id']).execute()
                st.success("Đã cập nhật!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}")

@st.dialog("THÊM ĐỢT THANH TOÁN BĐS")
def modal_realestate():
    try:
        res = supabase.table("realestate").select("project_name, contract_value").execute()
        existing_projects = {}
        if res.data:
            for row in res.data:
                existing_projects[row['project_name']] = row.get('contract_value', 0)
    except:
        existing_projects = {}
        
    project_opts = list(existing_projects.keys()) + ["➕ Thêm dự án mới..."]
    choice = st.selectbox("Chọn Dự án / Căn hộ", project_opts)
    
    if choice == "➕ Thêm dự án mới...":
        bds_name = st.text_input("Nhập tên dự án mới (VD: TT Avio B.30.05)")
        gia_tri_hd = st.number_input("Giá trị hợp đồng dự án (VND)", min_value=0.0, step=None)
    else:
        bds_name = choice
        gia_tri_hd = existing_projects[choice]
        st.info(f"💡 Giá trị hợp đồng của dự án này: **{gia_tri_hd:,.0f} ₫**")
        
    st.markdown("---")
    dot_tt = st.text_input("Tên đợt thanh toán (VD: Đợt 4 - Cất nóc)")
    
    c1, c2 = st.columns(2)
    with c1:
        so_tien_tt = st.number_input("Số tiền thanh toán (VND)", min_value=0.0, step=None)
    with c2:
        nguon_tien = st.selectbox("Nguồn tiền", FUNDING_SOURCES)
        
    c3, c4 = st.columns(2)
    with c3:
        ngay_tt = st.date_input("Hạn thanh toán")
    with c4:
        trang_thai = st.selectbox("Trạng thái", ["Chưa thanh toán", "Đã thanh toán"])
        
    ghi_chu = st.text_input("Ghi chú (Tùy chọn)")
    
    if st.button("LƯU TIẾN ĐỘ BĐS", use_container_width=True):
        if not bds_name.strip() or not dot_tt.strip():
            st.error("Vui lòng nhập tên dự án và tên đợt thanh toán!")
        else:
            try:
                data = {
                    "project_name": bds_name, "contract_value": int(gia_tri_hd), "installment_name": dot_tt,
                    "amount": int(so_tien_tt), "funding_source": nguon_tien, "due_date": str(ngay_tt),
                    "status": trang_thai, "note": ghi_chu
                }
                supabase.table("realestate").insert(data).execute()
                st.success("Đã ghi nhận tiến độ BĐS mới!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

@st.dialog("SỬA TIẾN ĐỘ BĐS")
def modal_edit_realestate(row_data):
    with st.form("edit_realestate_form", clear_on_submit=True):
        bds_name = st.text_input("Tên dự án / Căn hộ", value=row_data['project_name'])
        cv_val = float(row_data['contract_value']) if 'contract_value' in row_data and pd.notna(row_data['contract_value']) else 0.0
        gia_tri_hd = st.number_input("Giá trị hợp đồng dự án (VND)", min_value=0.0, step=None, value=cv_val)
        st.markdown("---")
        dot_tt = st.text_input("Tên đợt", value=row_data['installment_name'])
        
        c1, c2 = st.columns(2)
        with c1:
            so_tien_tt = st.number_input("Số tiền thanh toán (VND)", min_value=0.0, step=None, value=float(row_data['amount']))
        with c2:
            fs_val = row_data['funding_source'] if 'funding_source' in row_data else "Tiền mặt"
            idx_fs = FUNDING_SOURCES.index(fs_val) if fs_val in FUNDING_SOURCES else 0
            nguon_tien = st.selectbox("Nguồn tiền", FUNDING_SOURCES, index=idx_fs)
            
        c3, c4 = st.columns(2)
        with c3:
            try:
                due_dt = pd.to_datetime(row_data['due_date']).date()
            except:
                due_dt = date.today()
            ngay_tt = st.date_input("Hạn thanh toán", value=due_dt)
        with c4:
            status_opts = ["Chưa thanh toán", "Đã thanh toán"]
            idx_status = status_opts.index(row_data['status']) if row_data['status'] in status_opts else 0
            trang_thai = st.selectbox("Trạng thái", status_opts, index=idx_status)
            
        note_val = row_data['note'] if 'note' in row_data and pd.notna(row_data['note']) else ""
        ghi_chu = st.text_input("Ghi chú", value=note_val)
        
        if st.form_submit_button("CẬP NHẬT BĐS", use_container_width=True):
            try:
                data = {
                    "project_name": bds_name, "contract_value": int(gia_tri_hd), "installment_name": dot_tt,
                    "amount": int(so_tien_tt), "funding_source": nguon_tien, "due_date": str(ngay_tt),
                    "status": trang_thai, "note": ghi_chu
                }
                supabase.table("realestate").update(data).eq("id", row_data['id']).execute()
                st.success("Đã cập nhật BĐS!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

@st.dialog("THÊM KHOẢN VAY")
def modal_debt():
    with st.form("debt_form", clear_on_submit=True):
        muc_dich = st.text_input("Mục đích vay (VD: Chung cư Q7 Riverside)")
        ngan_hang = st.selectbox("Ngân hàng cho vay", BANK_ACCOUNTS + ["Khác"])
        
        st.markdown("**Thông số khởi tạo gốc (Chỉ nhập 1 lần)**")
        c1, c2 = st.columns(2)
        with c1:
            tien_vay_ban_dau = st.number_input("Tổng tiền vay BAN ĐẦU (VND)", min_value=0.0, step=None, value=1800000000.0)
        with c2:
            tong_thoi_gian = st.number_input("Tổng thời gian (Tháng)", min_value=1.0, step=None, value=180.0)
            
        c3, c4 = st.columns(2)
        with c3:
            ngay_giai_ngan = st.date_input("Ngày giải ngân")
        with c4:
            lai_suat = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=None, format="%.2f", value=7.3)
            
        st.info("💡 Hệ thống tự động trừ lùi dư nợ. Chỉ sửa khi Lãi suất thay đổi hoặc Trả nợ trước hạn.")
        
        if st.form_submit_button("LƯU KHOẢN VAY", use_container_width=True):
            try:
                data = {
                    "purpose": muc_dich, "bank": ngan_hang, "original_principal": int(tien_vay_ban_dau),
                    "total_months": int(tong_thoi_gian), "start_date": str(ngay_giai_ngan), "interest_rate": lai_suat
                }
                supabase.table("debts").insert(data).execute()
                st.success("Đã ghi nhận khoản vay!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

@st.dialog("SỬA KHOẢN VAY")
def modal_edit_debt(row_data):
    with st.form("edit_debt_form", clear_on_submit=True):
        muc_dich = st.text_input("Mục đích vay", value=row_data['purpose'])
        bank_opts = BANK_ACCOUNTS + ["Khác"]
        idx_bank = bank_opts.index(row_data['bank']) if row_data['bank'] in bank_opts else 0
        ngan_hang = st.selectbox("Ngân hàng cho vay", bank_opts, index=idx_bank)
        
        st.markdown("**Thông số gốc**")
        c1, c2 = st.columns(2)
        with c1:
            tien_vay_ban_dau = st.number_input("Tổng tiền vay BAN ĐẦU (VND)", min_value=0.0, step=None, value=float(row_data['original_principal']))
        with c2:
            tong_thoi_gian = st.number_input("Tổng thời gian (Tháng)", min_value=1.0, step=None, value=float(row_data['total_months']))
            
        c3, c4 = st.columns(2)
        with c3:
            try:
                start_dt = pd.to_datetime(row_data['start_date']).date()
            except:
                start_dt = date.today()
            ngay_giai_ngan = st.date_input("Ngày giải ngân", value=start_dt)
        with c4:
            lai_suat = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=None, format="%.3f", value=float(row_data['interest_rate']))
            
        if st.form_submit_button("CẬP NHẬT KHOẢN VAY", use_container_width=True):
            try:
                data = {
                    "purpose": muc_dich, "bank": ngan_hang, "original_principal": int(tien_vay_ban_dau),
                    "total_months": int(tong_thoi_gian), "start_date": str(ngay_giai_ngan), "interest_rate": lai_suat
                }
                supabase.table("debts").update(data).eq("id", row_data['id']).execute()
                st.success("Đã cập nhật!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

# 4. TAB ĐIỀU HƯỚNG CHÍNH
tab_home, tab_cashflow, tab_invest, tab_savings, tab_realestate = st.tabs([
    "TỔNG QUAN", "DÒNG TIỀN", "ĐẦU TƯ", "TIẾT KIỆM", "BĐS & TÍN DỤNG"
])

# --- TAB 0: TỔNG QUAN ---
with tab_home:
    try:
        res_savings = supabase.table("savings").select("amount").execute()
        tong_tiet_kiem = sum([row["amount"] for row in res_savings.data]) if res_savings.data else 0
    except:
        tong_tiet_kiem = 0
        
    try:
        res_re_total = supabase.table("realestate").select("amount").eq("status", "Đã thanh toán").execute()
        bds_da_dong = sum([row["amount"] for row in res_re_total.data]) if res_re_total.data else 0
    except:
        bds_da_dong = 0
        
    try:
        res_debts = supabase.table("debts").select("*").execute()
        no_khoan_vay = 0
        if res_debts.data:
            df_overview_debts = pd.DataFrame(res_debts.data)
            today_dt = pd.to_datetime(date.today())
            for index, row in df_overview_debts.iterrows():
                start_dt = pd.to_datetime(row['start_date'])
                months_passed = (today_dt.year - start_dt.year) * 12 + (today_dt.month - start_dt.month)
                months_passed = max(0, min(months_passed, row['total_months']))
                goc_co_dinh = row['original_principal'] / row['total_months']
                du_no_thuc_te = row['original_principal'] - (goc_co_dinh * months_passed)
                no_khoan_vay += du_no_thuc_te
    except:
        no_khoan_vay = 0

    tong_cp = 0
    try:
        res_stk = supabase.table("stocks").select("*").execute()
        if res_stk.data:
            df_stk = pd.DataFrame(res_stk.data)
            for ticker, grp in df_stk.groupby('ticker'):
                buy_vol = grp[grp['action'] == 'Mua']['volume'].sum()
                sell_vol = grp[grp['action'] == 'Bán']['volume'].sum()
                net_vol = buy_vol - sell_vol
                buy_val = (grp[grp['action'] == 'Mua']['volume'] * grp[grp['action'] == 'Mua']['price']).sum()
                avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                tong_cp += net_vol * avg_price
    except:
        tong_cp = 0

    tong_ccq = 0
    try:
        res_fund = supabase.table("ccq_funds").select("*").execute()
        if res_fund.data:
            df_fund = pd.DataFrame(res_fund.data)
            for ticker, grp in df_fund.groupby('ticker'):
                buy_vol = grp[grp['action'] == 'Mua']['volume'].sum()
                sell_vol = grp[grp['action'] == 'Bán']['volume'].sum()
                net_vol = buy_vol - sell_vol
                buy_val = (grp[grp['action'] == 'Mua']['volume'] * grp[grp['action'] == 'Mua']['price']).sum()
                avg_price = (buy_val / buy_vol) if buy_vol > 0 else 0
                tong_ccq += net_vol * avg_price
    except:
        tong_ccq = 0

    tong_tai_san = tong_tiet_kiem + tong_ccq + tong_cp + bds_da_dong
    tai_san_rong = tong_tai_san - no_khoan_vay
    
    c_left, c_right = st.columns([1.6, 1])
    with c_left:
        with st.container(border=True):
            st.markdown('<div class="metric-title">💰 TÀI SẢN RÒNG HIỆN TẠI (NET WORTH)</div>', unsafe_allow_html=True)
            color_net_worth = "#ef4444" if tai_san_rong < 0 else "#10b981"
            st.markdown(f"""
            <div style="font-family: 'Space Grotesk'; font-size: 2.8rem; font-weight: 700; color: {color_net_worth}; margin: 5px 0;">
                {tai_san_rong:,.0f} ₫
            </div>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                Tổng tài sản: <b style="color: #f8fafc;">{tong_tai_san:,.0f} ₫</b> &nbsp;|&nbsp; Tổng dư nợ: <b style="color: #ef4444;">{no_khoan_vay:,.0f} ₫</b>
            </div>
            """, unsafe_allow_html=True)
        
    with c_right:
        with st.container(border=True):
            ty_le_don_bay = (no_khoan_vay / (tong_tai_san if tong_tai_san > 0 else 1)) * 100
            st.markdown('<div class="metric-title">📊 TỶ LỆ ĐÒN BẨY TÀI CHÍNH</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div style="font-family: 'Space Grotesk'; font-size: 1.8rem; font-weight: 700; color: #f8fafc; margin: 10px 0;">
                {ty_le_don_bay:.1f}% <span style="font-size: 1rem; color: #94a3b8; font-weight: 400;">vốn vay</span>
            </div>
            <div style="color: #38bdf8; font-size: 0.85rem;">
                💡 Ngưỡng an toàn khuyến nghị < 50%.
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("CƠ CẤU PHÂN BỔ TÀI SẢN & BIỂU ĐỒ TRỰC QUAN")
    
    col_bar1, col_bar2, col_bar3, col_bar4 = st.columns(4)
    with col_bar1:
        st.metric("Tiết kiệm", f"{tong_tiet_kiem:,.0f} ₫")
    with col_bar2:
        st.metric("BĐS theo tiến độ", f"{bds_da_dong:,.0f} ₫")
    with col_bar3:
        st.metric("Chứng chỉ quỹ", f"{tong_ccq:,.0f} ₫")
    with col_bar4:
        st.metric("Cổ phiếu đầu tư", f"{tong_cp:,.0f} ₫")

    st.markdown("<br/>", unsafe_allow_html=True)
    
    if tong_tai_san > 0:
        df_chart = pd.DataFrame({
            "Danh mục": ["Tiết kiệm ngân hàng", "BĐS theo tiến độ", "Chứng chỉ quỹ", "Cổ phiếu"],
            "Giá trị": [tong_tiet_kiem, bds_da_dong, tong_ccq, tong_cp]
        })
        df_chart = df_chart[df_chart["Giá trị"] > 0]
        
        fig = px.pie(
            df_chart, 
            names="Danh mục", 
            values="Giá trị", 
            hole=0.55,
            color_discrete_sequence=["#10b981", "#38bdf8", "#f59e0b", "#8b5cf6"]
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#f8fafc",
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=10, b=10, l=10, r=10)
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
        col_c1, col_c2, col_c3 = st.columns([0.5, 2, 0.5])
        with col_c2:
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu tài sản để trực quan hóa biểu đồ.")
        
    st.divider()

# --- TAB 1: DÒNG TIỀN ---
with tab_cashflow:
    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
        if st.button("+ THÊM GIAO DỊCH MỚI", use_container_width=True):
            modal_cashflow()
    with col_btn2:
        if st.button("⚙️ CẬP NHẬT SỐ DƯ ĐẦU KỲ", use_container_width=True):
            modal_opening_balance()
            
    st.markdown("<br/>", unsafe_allow_html=True)
    
    try:
        res_all_cf = supabase.table("cashflow").select("*").execute()
        df_all = pd.DataFrame(res_all_cf.data) if res_all_cf.data else pd.DataFrame()
    except:
        df_all = pd.DataFrame()
        
    default_start = date(2026, 8, 1)
    default_end = date.today()
    
    st.markdown("#### 🔍 Bộ lọc đa chiều (Drill-down Filter)")
    fc1, fc2, fc3 = st.columns([1, 1.5, 1.5])
    
    with fc1:
        start_date = st.date_input("Từ ngày", value=default_start)
        end_date = st.date_input("Đến ngày", value=default_end)
        
    with fc2:
        acc_groups = st.multiselect("1. Nhóm tài khoản", ["TK Thanh toán", "Thẻ tín dụng", "Tài khoản CK"], default=["TK Thanh toán", "Thẻ tín dụng", "Tài khoản CK"])
        available_accs = []
        if "TK Thanh toán" in acc_groups: available_accs.extend(DEBIT_ACCOUNTS)
        if "Thẻ tín dụng" in acc_groups: available_accs.extend(CREDIT_CARDS)
        if "Tài khoản CK" in acc_groups: available_accs.extend(BROKER_ACCOUNTS)
        selected_accounts = st.multiselect("↳ Tài khoản chi tiết", available_accs, default=available_accs)
        
    with fc3:
        cat_groups = st.multiselect("2. Nhóm dòng tiền", ["Thu nhập", "Chi tiêu"], default=["Thu nhập", "Chi tiêu"])
        available_cats_list = []
        if "Thu nhập" in cat_groups: available_cats_list.append("Lương/Thu nhập")
        if "Chi tiêu" in cat_groups: available_cats_list.extend([c for c in CATS if c != "Lương/Thu nhập"])
        selected_cats = st.multiselect("↳ Danh mục chi tiết", available_cats_list, default=available_cats_list)

    if not df_all.empty:
        df_filtered = df_all.copy()
        df_filtered['created_at_dt'] = pd.to_datetime(df_filtered['created_at'])
        df_filtered['date_only'] = df_filtered['created_at_dt'].dt.date
        df_filtered = df_filtered[(df_filtered['date_only'] >= start_date) & (df_filtered['date_only'] <= end_date)]
        df_filtered = df_filtered[df_filtered['account'].isin(selected_accounts)]
        df_filtered = df_filtered[df_filtered['category'].isin(selected_cats)]
    else:
        df_filtered = pd.DataFrame()

    try:
        res_ob = supabase.table("opening_balances").select("*").execute()
        base_opening = {row['account']: row['balance'] for row in res_ob.data} if res_ob.data else {}
    except:
        base_opening = {}

    try:
        res_prior = supabase.table("cashflow").select("*").lt("created_at", str(start_date)).execute()
        df_prior = pd.DataFrame(res_prior.data) if res_prior.data else pd.DataFrame()
    except:
        df_prior = pd.DataFrame()

    total_debit_opening = 0
    total_credit_opening = 0

    for acc in selected_accounts:
        base_val = base_opening.get(acc, 0.0)
        if not df_prior.empty and 'account' in df_prior.columns:
            acc_prior = df_prior[df_prior['account'] == acc]
            if not acc_prior.empty:
                thu_prior = acc_prior[acc_prior['category'] == 'Lương/Thu nhập']['amount'].sum()
                chi_prior = acc_prior[acc_prior['category'] != 'Lương/Thu nhập']['amount'].sum()
                base_val = base_val + thu_prior - chi_prior
                
        if acc in DEBIT_ACCOUNTS or acc in BROKER_ACCOUNTS:
            total_debit_opening += base_val
        elif acc in CREDIT_CARDS:
            total_credit_opening += base_val

    if not df_filtered.empty:
        total_thu = df_filtered[df_filtered['category'] == 'Lương/Thu nhập']['amount'].sum()
        total_chi = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']['amount'].sum()
        dong_tien_thuan = total_thu - total_chi
    else:
        total_thu, total_chi, dong_tien_thuan = 0, 0, 0

    tong_quy = (total_debit_opening + dong_tien_thuan) - total_credit_opening

    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    with kc1:
        with st.container(border=True):
            st.markdown('<div class="metric-title">🏦 TK THANH TOÁN & CK</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: #38bdf8;'>{total_debit_opening:,.0f} ₫</div>", unsafe_allow_html=True)
    with kc2:
        with st.container(border=True):
            st.markdown('<div class="metric-title">💳 DƯ NỢ TÍN DỤNG</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: #ef4444;'>-{total_credit_opening:,.0f} ₫</div>", unsafe_allow_html=True)
    with kc3:
        with st.container(border=True):
            st.markdown('<div class="metric-title">📈 TỔNG THU KỲ</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: #10b981;'>+{total_thu:,.0f} ₫</div>", unsafe_allow_html=True)
    with kc4:
        with st.container(border=True):
            st.markdown('<div class="metric-title">📉 TỔNG CHI KỲ</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: #ef4444;'>-{total_chi:,.0f} ₫</div>", unsafe_allow_html=True)
    with kc5:
        with st.container(border=True):
            st.markdown('<div class="metric-title">⚖️ TỔNG QUỸ RÒNG</div>', unsafe_allow_html=True)
            color_dt = "#10b981" if tong_quy >= 0 else "#ef4444"
            st.markdown(f"<div style='font-family: Space Grotesk; font-size: 1.3rem; font-weight: 700; color: {color_dt};'>{tong_quy:,.0f} ₫</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    if not df_filtered.empty:
        viz1, viz2 = st.columns(2)
        with viz1:
            st.markdown("##### 📊 Xu hướng Thu vs Chi theo thời gian")
            df_filtered['Ngay'] = df_filtered['created_at_dt'].dt.strftime('%d/%m/%Y')
            df_filtered['Loại giao dịch'] = df_filtered['category'].apply(lambda x: 'Thu nhập' if x == 'Lương/Thu nhập' else 'Chi tiêu')
            df_trend = df_filtered.groupby(['Ngay', 'Loại giao dịch'])['amount'].sum().reset_index()
            
            fig_trend = px.bar(
                df_trend, x='Ngay', y='amount', color='Loại giao dịch',
                barmode='group',
                color_discrete_map={'Thu nhập': '#10b981', 'Chi tiêu': '#ef4444'},
                template="plotly_dark"
            )
            fig_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        with viz2:
            st.markdown("##### 🍩 Tỷ trọng chi tiêu theo danh mục")
            df_chi = df_filtered[df_filtered['category'] != 'Lương/Thu nhập']
            if not df_chi.empty:
                df_cat = df_chi.groupby('category')['amount'].sum().reset_index()
                fig_donut = px.pie(
                    df_cat, names='category', values='amount', hole=0.5,
                    color_discrete_sequence=['#38bdf8', '#f59e0b', '#8b5cf6', '#ec4899', '#10b981'],
                    template="plotly_dark"
                )
                fig_donut.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu chi tiêu trong khoảng thời gian này.")
    st.divider()

    st.markdown("**LỊCH SỬ GIAO DỊCH (ĐÃ LỌC)**")
    if not df_filtered.empty:
        df_display = df_filtered[['id', 'created_at_dt', 'account', 'category', 'amount', 'note']].copy()
        df_display['created_at_dt'] = df_display['created_at_dt'].dt.strftime('%d/%m/%Y %H:%M')
        df_display = df_display.rename(
            columns={'created_at_dt': 'Thời gian', 'account': 'Tài khoản', 'category': 'Phân loại', 'amount': 'Số tiền', 'note': 'Ghi chú'}
        )
        
        st.dataframe(
            df_display,
            column_config={"id": None, "Số tiền": st.column_config.NumberColumn("Số tiền (VND)", format="%,.0f ₫")},
            use_container_width=True, hide_index=True
        )
        
        st.markdown("---")
        st.markdown("### ⚙️ QUẢN LÝ DỮ LIỆU BẢNG")
        
        action_id = st.selectbox(
            "Chọn giao dịch để cập nhật:", 
            df_filtered['id'].tolist(), 
            format_func=lambda x: f"{pd.to_datetime(df_filtered[df_filtered['id'] == x]['created_at'].values[0]).strftime('%d/%m/%Y %H:%M')} | {df_filtered[df_filtered['id'] == x]['category'].values[0]} | {df_filtered[df_filtered['id'] == x]['amount'].values[0]:,.0f} ₫",
            key="select_cf"
        )
        
        selected_row = df_filtered[df_filtered['id'] == action_id].iloc[0]
        
        col_a1, col_a2, _ = st.columns([1.5, 1.5, 3])
        with col_a1:
            if st.button("✏️ SỬA GIAO DỊCH NÀY", use_container_width=True, key="edit_cf"):
                modal_edit_cashflow(selected_row)
        with col_a2:
            if st.button("❌ XÓA GIAO DỊCH NÀY", use_container_width=True, key="del_cf"):
                supabase.table("cashflow").delete().eq("id", action_id).execute()
                st.success("Đã xóa giao dịch!")
                st.rerun()
    else:
        st.info("Không có giao dịch nào phù hợp với bộ lọc hiện tại.")

# --- TAB 2: ĐẦU TƯ ---
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

# --- TAB 3: TIẾT KIỆM ---
with tab_savings:
    col_btn3, _ = st.columns([1, 3])
    with col_btn3:
        if st.button("+ TẠO SỔ TIẾT KIỆM MỚI", use_container_width=True):
            modal_savings()
            
    try:
        res_sav = supabase.table("savings").select("*").execute()
        df_savings = pd.DataFrame(res_sav.data) if res_sav.data else pd.DataFrame()
    except:
        df_savings = pd.DataFrame()

    for fund_name in FUNDS:
        st.subheader(fund_name)
        if not df_savings.empty and "fund_owner" in df_savings.columns:
            fund_data = df_savings[df_savings["fund_owner"] == fund_name].copy()
            total_goc = fund_data["amount"].sum() if not fund_data.empty else 0
        else:
            fund_data = pd.DataFrame()
            total_goc = 0
            
        st.markdown(f"**Tổng vốn:** <span style='color:#10b981; font-size:18px'>{total_goc:,.0f} ₫</span>", unsafe_allow_html=True)
        
        if not fund_data.empty:
            fund_data['term_months'] = fund_data['term'].apply(lambda x: int(x.split()[0]) if "Tháng" in x else 0)
            fund_data['Ngày gửi'] = pd.to_datetime(fund_data['deposit_date']).dt.strftime('%d/%m/%Y')
            
            df_display_sav = fund_data[['id', 'bank', 'Ngày gửi', 'term', 'interest_rate', 'amount']].rename(
                columns={'bank': 'Ngân hàng', 'term': 'Kỳ hạn', 'interest_rate': 'Lãi suất (%/năm)', 'amount': 'Tiền gốc (VND)'}
            )
            
            st.dataframe(
                df_display_sav,
                column_config={
                    "id": None,
                    "Tiền gốc (VND)": st.column_config.NumberColumn("Tiền gốc (VND)", format="%,.0f ₫"), 
                    "Lãi suất (%/năm)": st.column_config.NumberColumn("Lãi suất (%/năm)", format="%.2f")
                },
                use_container_width=True, hide_index=True
            )
            
            st.markdown(f"**⚙️ TÙY CHỈNH DỮ LIỆU SỔ TIẾT KIỆM ({fund_name.upper()})**")
            action_id_sav = st.selectbox(
                "Chọn sổ tiết kiệm để cập nhật:", 
                fund_data['id'].tolist(), 
                format_func=lambda x: f"{fund_data[fund_data['id'] == x]['bank'].values[0]} | Gốc: {fund_data[fund_data['id'] == x]['amount'].values[0]:,.0f} ₫",
                key=f"select_sav_{fund_name}"
            )
            
            selected_sav_row = fund_data[fund_data['id'] == action_id_sav].iloc[0]
            
            col_s1, col_s2, _ = st.columns([1.5, 1.5, 3])
            with col_s1:
                if st.button("✏️ SỬA SỔ NÀY", use_container_width=True, key=f"edit_sav_{fund_name}"):
                    modal_edit_savings(selected_sav_row)
            with col_s2:
                if st.button("❌ TẤT TOÁN / XÓA SỔ NÀY", use_container_width=True, key=f"del_sav_{fund_name}"):
                    supabase.table("savings").delete().eq("id", action_id_sav).execute()
                    st.success("Đã xóa sổ tiết kiệm!")
                    st.rerun()
        else:
            st.caption("Chưa có sổ tiết kiệm nào trong quỹ này.")
        st.divider()

# --- TAB 4: BĐS & TÍN DỤNG ---
with tab_realestate:
    col_re_btn, col_debt_btn, _ = st.columns([1.2, 1.2, 2])
    with col_re_btn:
        if st.button("+ THÊM TIẾN ĐỘ BĐS", use_container_width=True):
            modal_realestate()
    with col_debt_btn:
        if st.button("+ THÊM KHOẢN VAY", use_container_width=True):
            modal_debt()
            
    st.markdown("<br/>", unsafe_allow_html=True)
    
    # ------------------ PHẦN BẤT ĐỘNG SẢN ------------------
    st.subheader("Bất động sản mua theo tiến độ")
    
    try:
        res_re = supabase.table("realestate").select("*").execute()
        df_re = pd.DataFrame(res_re.data) if res_re.data else pd.DataFrame()
    except:
        df_re = pd.DataFrame()

    if not df_re.empty and "project_name" in df_re.columns:
        if "contract_value" not in df_re.columns:
            df_re["contract_value"] = 0
            
        # BẢNG 1: TỔNG HỢP TIẾN ĐỘ BĐS VỚI PROGRESS BAR
        st.markdown("##### 📈 Tiến độ thanh toán tổng thể")
        df_re_paid = df_re[df_re['status'] == 'Đã thanh toán']
        summary_re = []
        
        for proj, grp in df_re.groupby('project_name'):
            contract_val = grp['contract_value'].iloc[0] if 'contract_value' in grp.columns else 0
            paid_val = grp[grp['status'] == 'Đã thanh toán']['amount'].sum()
            progress = (paid_val / contract_val * 100) if contract_val > 0 else 0
            
            summary_re.append({
                "Dự án": proj,
                "Giá trị HĐ (VND)": contract_val,
                "Đã thanh toán (VND)": paid_val,
                "Còn lại (VND)": contract_val - paid_val,
                "Tiến độ (%)": progress
            })
            
        if summary_re:
            df_re_summary = pd.DataFrame(summary_re)
            st.dataframe(
                df_re_summary,
                column_config={
                    "Giá trị HĐ (VND)": st.column_config.NumberColumn("Giá trị HĐ (VND)", format="%,.0f ₫"),
                    "Đã thanh toán (VND)": st.column_config.NumberColumn("Đã thanh toán (VND)", format="%,.0f ₫"),
                    "Còn lại (VND)": st.column_config.NumberColumn("Còn lại (VND)", format="%,.0f ₫"),
                    "Tiến độ (%)": st.column_config.ProgressColumn("Tiến độ (%)", format="%.1f%%", min_value=0, max_value=100)
                },
                use_container_width=True, hide_index=True
            )
            
        st.markdown("##### 📄 Chi tiết các đợt thanh toán")
        if "funding_source" not in df_re.columns:
            df_re["funding_source"] = "N/A"
        if "note" not in df_re.columns:
            df_re["note"] = ""
            
        # YÊU CẦU 1: Đổi thứ tự cột BĐS theo Cognitive Flow
        df_re_display = df_re[['id', 'project_name', 'installment_name', 'contract_value', 'amount', 'funding_source', 'due_date', 'status', 'note']].rename(
            columns={
                'project_name': 'Dự án', 
                'installment_name': 'Tên Đợt', 
                'contract_value': 'Giá trị HĐ (VND)',
                'amount': 'Thanh toán (VND)', 
                'funding_source': 'Nguồn tiền',
                'due_date': 'Hạn TT', 
                'status': 'Trạng thái',
                'note': 'Ghi chú'
            }
        )
        
        # YÊU CẦU 3: Conditional Formatting cho trạng thái thanh toán BĐS
        def style_bds(row):
            if row['Trạng thái'] == 'Đã thanh toán':
                # Nền xanh nhạt, chữ xanh lá nổi bật
                return ['background-color: rgba(16, 185, 129, 0.15); color: #34d399; font-weight: 500'] * len(row)
            else:
                # Nền đỏ nhạt, chữ đỏ
                return ['background-color: rgba(239, 68, 68, 0.1); color: #f87171'] * len(row)
                
        styled_re = df_re_display.style.apply(style_bds, axis=1)

        # YÊU CẦU 2: Căn lề & định dạng tiền tệ
        st.dataframe(
            styled_re,
            column_config={
                "id": None, 
                "Giá trị HĐ (VND)": st.column_config.NumberColumn("Giá trị HĐ (VND)", format="%,.0f ₫"),
                "Thanh toán (VND)": st.column_config.NumberColumn("Thanh toán (VND)", format="%,.0f ₫")
            },
            use_container_width=True, hide_index=True
        )
        
        st.markdown("---")
        st.markdown("### ⚙️ QUẢN LÝ DỮ LIỆU BĐS")
        action_id_re = st.selectbox(
            "Chọn tiến độ BĐS để cập nhật:", 
            df_re['id'].tolist(), 
            format_func=lambda x: f"{df_re[df_re['id'] == x]['project_name'].values[0]} | {df_re[df_re['id'] == x]['installment_name'].values[0]} | {df_re[df_re['id'] == x]['amount'].values[0]:,.0f} ₫",
            key="select_re"
        )
        
        selected_re_row = df_re[df_re['id'] == action_id_re].iloc[0]
        
        col_re1, col_re2, _ = st.columns([1.5, 1.5, 3])
        with col_re1:
            if st.button("✏️ SỬA TIẾN ĐỘ NÀY", use_container_width=True, key="edit_re"):
                modal_edit_realestate(selected_re_row)
        with col_re2:
            if st.button("❌ XÓA TIẾN ĐỘ NÀY", use_container_width=True, key="del_re"):
                supabase.table("realestate").delete().eq("id", action_id_re).execute()
                st.success("Đã xóa BĐS!")
                st.rerun()
    else:
        st.info("Dữ liệu tiến độ BĐS hiện đang trống. Vui lòng thêm đợt thanh toán mới.")
    
    st.divider()
    
    # ------------------ PHẦN KHOẢN VAY TÍN DỤNG ------------------
    st.subheader("Khoản vay tín dụng & Dư nợ")
    
    try:
        res_debt = supabase.table("debts").select("*").execute()
        df_vay = pd.DataFrame(res_debt.data) if res_debt.data else pd.DataFrame()
    except:
        df_vay = pd.DataFrame()

    if not df_vay.empty and "original_principal" in df_vay.columns:
        today = pd.to_datetime(date.today())
        df_vay['start_date'] = pd.to_datetime(df_vay['start_date'])
        
        df_vay['Tháng đã trả'] = (today.year - df_vay['start_date'].dt.year) * 12 + (today.month - df_vay['start_date'].dt.month)
        df_vay['Tháng đã trả'] = df_vay.apply(lambda x: max(0, min(x['Tháng đã trả'], x['total_months'])), axis=1)
        
        df_vay["Gốc cố định/Tháng"] = df_vay["original_principal"] / df_vay["total_months"]
        df_vay["Dư nợ HIỆN TẠI"] = df_vay["original_principal"] - (df_vay["Gốc cố định/Tháng"] * df_vay["Tháng đã trả"])
        df_vay["Lãi tháng này"] = df_vay["Dư nợ HIỆN TẠI"] * (df_vay["interest_rate"] / 100 / 12)
        df_vay["Tổng phải trả (Tháng này)"] = df_vay["Gốc cố định/Tháng"] + df_vay["Lãi tháng này"]
        df_vay["Đã trả (Gốc)"] = df_vay["original_principal"] - df_vay["Dư nợ HIỆN TẠI"]
        df_vay["Tiến độ (%)"] = (df_vay["Đã trả (Gốc)"] / df_vay["original_principal"]) * 100
        
        df_display_vay = df_vay.rename(columns={
            "purpose": "Mục đích", 
            "bank": "Ngân hàng", 
            "total_months": "Tổng kỳ hạn",
            "original_principal": "Vay ban đầu",
            "interest_rate": "Lãi suất (%/năm)"
        })
        
        # YÊU CẦU 1: Đổi thứ tự cột Khoản Vay theo Cognitive Flow
        cols_to_show = ['id', 'Mục đích', 'Ngân hàng', 'Tổng kỳ hạn', 'Tháng đã trả', 'Dư nợ HIỆN TẠI', 'Lãi suất (%/năm)', 'Vay ban đầu', 'Đã trả (Gốc)', 'Tiến độ (%)', 'Gốc cố định/Tháng', 'Lãi tháng này', 'Tổng phải trả (Tháng này)']
        
        # YÊU CẦU 3: Conditional Formatting cho dư nợ đã tất toán
        def style_debt(row):
            if row['Dư nợ HIỆN TẠI'] <= 0:
                # Nếu đã trả xong (dư nợ = 0), tô màu xanh lá đánh dấu hoàn thành
                return ['background-color: rgba(16, 185, 129, 0.15); color: #34d399; font-weight: 500'] * len(row)
            return [''] * len(row)
            
        styled_debt = df_display_vay[cols_to_show].style.apply(style_debt, axis=1)
        
        # YÊU CẦU 2: Định dạng số cho tất cả các cột
        st.dataframe(
            styled_debt,
            column_config={
                "id": None,
                "Tổng kỳ hạn": st.column_config.NumberColumn("Tổng kỳ hạn", format="%d Tháng"),
                "Tháng đã trả": st.column_config.NumberColumn("Đã trả", format="%d Tháng"),
                "Vay ban đầu": st.column_config.NumberColumn("Vay ban đầu", format="%,.0f ₫"),
                "Đã trả (Gốc)": st.column_config.NumberColumn("Đã trả (Gốc)", format="%,.0f ₫"),
                "Dư nợ HIỆN TẠI": st.column_config.NumberColumn("Dư nợ HIỆN TẠI", format="%,.0f ₫"),
                "Gốc cố định/Tháng": st.column_config.NumberColumn("Gốc/Tháng", format="%,.0f ₫"),
                "Lãi tháng này": st.column_config.NumberColumn("Lãi tháng", format="%,.0f ₫"),
                "Tổng phải trả (Tháng này)": st.column_config.NumberColumn("Tổng TT (Tháng)", format="%,.0f ₫"),
                "Lãi suất (%/năm)": st.column_config.NumberColumn("Lãi suất", format="%.2f%%"),
                "Tiến độ (%)": st.column_config.ProgressColumn("Tiến độ (%)", format="%.1f%%", min_value=0, max_value=100)
            },
            use_container_width=True, hide_index=True
        )
        
        st.markdown("---")
        st.markdown("### ⚙️ QUẢN LÝ DỮ LIỆU KHOẢN VAY")
        action_id_debt = st.selectbox(
            "Chọn khoản vay để cập nhật:", 
            df_vay['id'].tolist(), 
            format_func=lambda x: f"{df_vay[df_vay['id'] == x]['purpose'].values[0]} | {df_vay[df_vay['id'] == x]['bank'].values[0]} | Dư nợ: {df_vay[df_vay['id'] == x]['Dư nợ HIỆN TẠI'].values[0]:,.0f} ₫",
            key="select_debt"
        )
        
        selected_debt_row = df_vay[df_vay['id'] == action_id_debt].iloc[0]
        
        col_d1, col_d2, _ = st.columns([1.5, 1.5, 3])
        with col_d1:
            if st.button("✏️ SỬA KHOẢN VAY NÀY", use_container_width=True, key="edit_debt"):
                modal_edit_debt(selected_debt_row)
        with col_d2:
            if st.button("❌ XÓA KHOẢN VAY NÀY", use_container_width=True, key="del_debt"):
                supabase.table("debts").delete().eq("id", action_id_debt).execute()
                st.success("Đã xóa khoản vay!")
                st.rerun()

    else:
        st.info("Dữ liệu dư nợ hiện đang trống. Vui lòng thêm khoản vay mới.")
