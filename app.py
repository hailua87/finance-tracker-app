import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

# 1. THIẾT LẬP CẤU HÌNH & KẾT NỐI SUPABASE
st.set_page_config(page_title="Nhà Quê Tập Chi Tiêu", layout="wide")

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_supabase()

# 2. HALLMARK CUSTOM CSS INJECTION
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
    
    .dashboard-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
    }
    
    .metric-title {
        font-size: 0.85rem;
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

BANK_ACCOUNTS = ["VCB chồng", "TCB chồng", "HSBC chồng", "UOB chồng", "UOB vợ", "TCB vợ"]
FUNDING_SOURCES = BANK_ACCOUNTS + ["Tiền mặt", "Giải ngân vốn vay", "Khác"]
TERMS = ["Không kỳ hạn", "1 Tháng", "2 Tháng", "3 Tháng", "6 Tháng", "7 Tháng", "8 Tháng", "9 Tháng", "10 Tháng", "11 Tháng", "12 Tháng", "13 Tháng", "18 Tháng", "24 Tháng", "36 Tháng"]
CATS = ["Ăn uống", "Mẹ & Bé", "Nhà cửa", "Đầu tư", "Lương/Thu nhập", "Khác"]

# 3. KHO MODAL (@st.dialog)
@st.dialog("GHI NHẬN DÒNG TIỀN")
def modal_cashflow():
    with st.form("cashflow_form", clear_on_submit=True):
        account = st.selectbox("Tài khoản nguồn", BANK_ACCOUNTS)
        category = st.selectbox("Phân loại", CATS)
        amount = st.number_input("Số tiền (VND)", min_value=0, step=50000)
        note = st.text_input("Ghi chú")
        
        if st.form_submit_button("LƯU GIAO DỊCH", use_container_width=True):
            try:
                data = {"account": account, "amount": amount, "category": category, "note": note}
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
        
        account = st.selectbox("Tài khoản nguồn", BANK_ACCOUNTS, index=idx_acc)
        category = st.selectbox("Phân loại", CATS, index=idx_cat)
        amount = st.number_input("Số tiền (VND)", min_value=0, step=50000, value=int(row_data['amount']))
        note = st.text_input("Ghi chú", value=row_data['note'] if row_data['note'] else "")
        
        if st.form_submit_button("CẬP NHẬT", use_container_width=True):
            try:
                data = {"account": account, "amount": amount, "category": category, "note": note}
                supabase.table("cashflow").update(data).eq("id", row_data['id']).execute()
                st.success("Đã cập nhật thành công!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

@st.dialog("THÊM ĐỢT THANH TOÁN BĐS")
def modal_realestate():
    # TRUY XUẤT DỮ LIỆU CŨ ĐỂ GỢI Ý
    try:
        res = supabase.table("realestate").select("project_name, contract_value").execute()
        existing_projects = {}
        if res.data:
            for row in res.data:
                existing_projects[row['project_name']] = row.get('contract_value', 0)
    except:
        existing_projects = {}
        
    project_opts = list(existing_projects.keys()) + ["➕ Thêm dự án mới..."]
    
    # Giao diện Động (Không dùng st.form)
    choice = st.selectbox("Chọn Dự án / Căn hộ", project_opts)
    
    if choice == "➕ Thêm dự án mới...":
        bds_name = st.text_input("Nhập tên dự án mới (VD: TT Avio B.30.05)")
        gia_tri_hd = st.number_input("Giá trị hợp đồng dự án (VND)", min_value=0, step=100000000)
    else:
        bds_name = choice
        gia_tri_hd = existing_projects[choice]
        st.info(f"💡 Giá trị hợp đồng của dự án này: **{gia_tri_hd:,.0f} ₫**")
        
    st.markdown("---")
    dot_tt = st.text_input("Tên đợt thanh toán (VD: Đợt 4 - Cất nóc)")
    so_tien_tt = st.number_input("Số tiền thanh toán đợt này (VND)", min_value=0, step=10000000)
    nguon_tien = st.selectbox("Nguồn tiền thanh toán", FUNDING_SOURCES)
    
    ngay_tt = st.date_input("Hạn thanh toán")
    trang_thai = st.selectbox("Trạng thái", ["Chưa thanh toán", "Đã thanh toán"])
    ghi_chu = st.text_input("Ghi chú (Tùy chọn)")
    
    # Nút bấm LƯU (Chạy độc lập không qua form)
    if st.button("LƯU TIẾN ĐỘ BĐS", use_container_width=True):
        if not bds_name.strip():
            st.error("Vui lòng nhập tên dự án!")
        elif not dot_tt.strip():
            st.error("Vui lòng nhập tên đợt thanh toán!")
        else:
            try:
                data = {
                    "project_name": bds_name,
                    "contract_value": gia_tri_hd,
                    "installment_name": dot_tt,
                    "amount": so_tien_tt,
                    "funding_source": nguon_tien,
                    "due_date": str(ngay_tt),
                    "status": trang_thai,
                    "note": ghi_chu
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
        
        cv_val = int(row_data['contract_value']) if 'contract_value' in row_data and pd.notna(row_data['contract_value']) else 0
        gia_tri_hd = st.number_input("Giá trị hợp đồng dự án (VND)", min_value=0, step=100000000, value=cv_val)
        
        st.markdown("---")
        dot_tt = st.text_input("Tên đợt", value=row_data['installment_name'])
        so_tien_tt = st.number_input("Số tiền thanh toán đợt này (VND)", min_value=0, step=10000000, value=int(row_data['amount']))
        
        fs_val = row_data['funding_source'] if 'funding_source' in row_data else "Tiền mặt"
        idx_fs = FUNDING_SOURCES.index(fs_val) if fs_val in FUNDING_SOURCES else 0
        nguon_tien = st.selectbox("Nguồn tiền thanh toán", FUNDING_SOURCES, index=idx_fs)
        
        try:
            due_dt = pd.to_datetime(row_data['due_date']).date()
        except:
            due_dt = date.today()
            
        ngay_tt = st.date_input("Hạn thanh toán", value=due_dt)
        
        status_opts = ["Chưa thanh toán", "Đã thanh toán"]
        idx_status = status_opts.index(row_data['status']) if row_data['status'] in status_opts else 0
        trang_thai = st.selectbox("Trạng thái", status_opts, index=idx_status)
        
        note_val = row_data['note'] if 'note' in row_data and pd.notna(row_data['note']) else ""
        ghi_chu = st.text_input("Ghi chú", value=note_val)
        
        if st.form_submit_button("CẬP NHẬT BĐS", use_container_width=True):
            try:
                data = {
                    "project_name": bds_name,
                    "contract_value": gia_tri_hd,
                    "installment_name": dot_tt,
                    "amount": so_tien_tt,
                    "funding_source": nguon_tien,
                    "due_date": str(ngay_tt),
                    "status": trang_thai,
                    "note": ghi_chu
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
        tien_vay_ban_dau = st.number_input("Tổng tiền vay BAN ĐẦU (VND)", min_value=0, step=10000000, value=1800000000)
        tong_thoi_gian = st.number_input("Tổng thời gian vay (Tháng)", min_value=1, step=1, value=180)
        ngay_giai_ngan = st.date_input("Ngày giải ngân / Bắt đầu vay")
        
        st.markdown("**Thông số biến động**")
        lai_suat = st.number_input("Lãi suất HIỆN HÀNH (%/năm)", min_value=0.0, format="%.2f", value=7.3)
        
        st.info("💡 Hệ thống tự động trừ lùi dư nợ. Chỉ sửa lại khoản vay này khi Lãi suất thay đổi hoặc Trả nợ trước hạn.")
        
        if st.form_submit_button("LƯU KHOẢN VAY", use_container_width=True):
            try:
                data = {
                    "purpose": muc_dich,
                    "bank": ngan_hang,
                    "original_principal": tien_vay_ban_dau,
                    "total_months": tong_thoi_gian,
                    "start_date": str(ngay_giai_ngan),
                    "interest_rate": lai_suat
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
        tien_vay_ban_dau = st.number_input("Tổng tiền vay BAN ĐẦU (VND)", min_value=0, step=10000000, value=int(row_data['original_principal']))
        tong_thoi_gian = st.number_input("Tổng thời gian vay (Tháng)", min_value=1, step=1, value=int(row_data['total_months']))
        
        try:
            start_dt = pd.to_datetime(row_data['start_date']).date()
        except:
            start_dt = date.today()
            
        ngay_giai_ngan = st.date_input("Ngày giải ngân / Bắt đầu vay", value=start_dt)
        
        st.markdown("**Thông số biến động**")
        lai_suat = st.number_input("Lãi suất HIỆN HÀNH (%/năm)", min_value=0.0, format="%.3f", value=float(row_data['interest_rate']))
        
        if st.form_submit_button("CẬP NHẬT KHOẢN VAY", use_container_width=True):
            try:
                data = {
                    "purpose": muc_dich,
                    "bank": ngan_hang,
                    "original_principal": tien_vay_ban_dau,
                    "total_months": tong_thoi_gian,
                    "start_date": str(ngay_giai_ngan),
                    "interest_rate": lai_suat
                }
                supabase.table("debts").update(data).eq("id", row_data['id']).execute()
                st.success("Đã cập nhật!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

@st.dialog("ĐẶT LỆNH CỔ PHIẾU")
def modal_stock():
    with st.form("invest_stock_form", clear_on_submit=True):
        broker = st.selectbox("Nơi lưu ký (CTCK)", ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Khác"])
        fund_owner_stock = st.selectbox("Thuộc Portfolio", ["Daddy Funding", "Mama Funding", "Tieu Boi Funding"])
        ticker = st.text_input("Mã cổ phiếu (VD: VIB, MBB, VCI...)").upper()
        action = st.radio("Lệnh", ["Mua", "Bán"], horizontal=True)
        volume = st.number_input("Khối lượng (CP)", min_value=100, step=100)
        price = st.number_input("Giá khớp (VND)", min_value=0)
        if st.form_submit_button("LƯU LỆNH", use_container_width=True):
            if ticker.strip() == "":
                st.error("Vui lòng nhập mã cổ phiếu!")
            else:
                st.success(f"Đã lưu lệnh {action} {volume} CP {ticker} qua {broker}!")

@st.dialog("GIAO DỊCH CHỨNG CHỈ QUỸ")
def modal_ccq():
    with st.form("invest_ccq_form", clear_on_submit=True):
        platform = st.selectbox("Nền tảng giao dịch", ["TCBS", "Fmarket", "DragonX", "VCB Digibank", "SSIAM"])
        fund_owner_ccq = st.selectbox("Thuộc Portfolio", ["Tieu Boi Funding", "Mama Funding", "Daddy Funding"])
        fund_ticker = st.text_input("Mã Quỹ (VD: DCDS, VESAF...)").upper()
        action_ccq = st.radio("Lệnh quỹ", ["Mua (SIP)", "Bán"], horizontal=True)
        volume_ccq = st.number_input("Số lượng CCQ", min_value=0.0, step=10.0, format="%.2f")
        nav_price = st.number_input("Giá NAV (VND)", min_value=0)
        if st.form_submit_button("LƯU GIAO DỊCH QUỸ", use_container_width=True):
            st.success(f"Đã lưu lệnh {fund_ticker} qua {platform}!")

@st.dialog("THÊM KHOẢN GỬI TIẾT KIỆM")
def modal_savings():
    with st.form("new_deposit_form", clear_on_submit=True):
        new_fund = st.selectbox("Chọn Portfolio", ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"])
        new_bank = st.selectbox("Ngân hàng", BANK_ACCOUNTS)
        new_amount = st.number_input("Số tiền (VND)", min_value=0, step=1000000)
        new_date = st.date_input("Ngày gửi")
        new_term = st.selectbox("Kỳ hạn", TERMS)
        new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, format="%.1f")
        
        if st.form_submit_button("LƯU KHOẢN GỬI", use_container_width=True):
            try:
                data = {
                    "fund_owner": new_fund,
                    "bank": new_bank,
                    "deposit_date": str(new_date),
                    "term": new_term,
                    "interest_rate": new_rate,
                    "amount": new_amount
                }
                supabase.table("savings").insert(data).execute()
                st.success("Đã lưu sổ tiết kiệm mới vào Database!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}")

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

    tong_ccq, tong_cp = 0, 0 
    tong_tai_san = tong_tiet_kiem + tong_ccq + tong_cp + bds_da_dong
    tai_san_rong = tong_tai_san - no_khoan_vay
    
    c_left, c_right = st.columns([1.6, 1])
    with c_left:
        st.markdown(f"""
        <div class="dashboard-card" style="border-left: 5px solid #10b981; background: linear-gradient(135deg, #111827 0%, #0f172a 100%);">
            <div class="metric-title">💰 TÀI SẢN RÒNG HIỆN TẠI (NET WORTH)</div>
            <div style="font-family: 'Space Grotesk'; font-size: 2.8rem; font-weight: 700; color: #10b981; margin: 5px 0;">
                {tai_san_rong:,.0f} ₫
            </div>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                Tổng tài sản: <b style="color: #f8fafc;">{tong_tai_san:,.0f} ₫</b> &nbsp;|&nbsp; Tổng dư nợ: <b style="color: #ef4444;">{no_khoan_vay:,.0f} ₫</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_right:
        ty_le_don_bay = (no_khoan_vay / (tong_tai_san if tong_tai_san > 0 else 1)) * 100
        st.markdown(f"""
        <div class="dashboard-card">
            <div class="metric-title">📊 TỶ LỆ ĐÒN BẨY TÀI CHÍNH</div>
            <div style="font-family: 'Space Grotesk'; font-size: 1.8rem; font-weight: 700; color: #f8fafc; margin: 10px 0;">
                {ty_le_don_bay:.1f}% <span style="font-size: 1rem; color: #94a3b8; font-weight: 400;">vốn vay</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.subheader("CƠ CẤU PHÂN BỔ TÀI SẢN")
    
    col_bar1, col_bar2, col_bar3, col_bar4 = st.columns(4)
    with col_bar1:
        st.metric("Tiết kiệm", f"{tong_tiet_kiem:,.0f} ₫")
    with col_bar2:
        st.metric("BĐS theo tiến độ", f"{bds_da_dong:,.0f} ₫")
    with col_bar3:
        st.metric("Chứng chỉ quỹ", f"{tong_ccq:,.0f} ₫")
    with col_bar4:
        st.metric("Cổ phiếu đầu tư", f"{tong_cp:,.0f} ₫")
    st.divider()

# --- TAB 1: DÒNG TIỀN ---
with tab_cashflow:
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("+ THÊM GIAO DỊCH MỚI", use_container_width=True):
            modal_cashflow()
            
    st.markdown("**LỊCH SỬ GIAO DỊCH (TỪ DATABASE)**")
    try:
        res_cf = supabase.table("cashflow").select("*").order("created_at", desc=True).limit(20).execute()
        if res_cf.data:
            df_cf = pd.DataFrame(res_cf.data)
            df_cf['created_at'] = pd.to_datetime(df_cf['created_at']).dt.strftime('%d/%m/%Y %H:%M')
            df_display = df_cf[['id', 'created_at', 'account', 'category', 'amount', 'note']].rename(
                columns={'created_at': 'Thời gian', 'account': 'Tài khoản', 'category': 'Phân loại', 'amount': 'Số tiền', 'note': 'Ghi chú'}
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
                df_cf['id'].tolist(), 
                format_func=lambda x: f"{df_cf[df_cf['id'] == x]['created_at'].values[0]} | {df_cf[df_cf['id'] == x]['category'].values[0]} | {df_cf[df_cf['id'] == x]['amount'].values[0]:,.0f} ₫",
                key="select_cf"
            )
            
            selected_row = df_cf[df_cf['id'] == action_id].iloc[0]
            
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
            st.info("Chưa có giao dịch nào được ghi nhận.")
    except Exception as e:
        st.error(f"Không thể tải dữ liệu dòng tiền: {e}")

# --- TAB 2: ĐẦU TƯ ---
with tab_invest:
    subtab_stock, subtab_ccq = st.tabs(["CỔ PHIẾU", "CHỨNG CHỈ QUỸ"])
    with subtab_stock:
        col_btn2, _ = st.columns([1, 3])
        with col_btn2:
            if st.button("+ LỆNH CỔ PHIẾU MỚI", use_container_width=True):
                modal_stock()
        st.info("Danh mục Cổ phiếu hiện đang trống.")

    with subtab_ccq:
        col_btn_ccq, _ = st.columns([1, 3])
        with col_btn_ccq:
            if st.button("+ GIAO DỊCH CCQ MỚI", use_container_width=True):
                modal_ccq()
        st.info("Danh mục Chứng chỉ quỹ hiện đang trống.")

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

    funds_info = [("Tieu Boi Funding", "Tieu Boi Funding"), ("Daddy Funding", "Daddy Funding"), ("Mama Funding", "Mama Funding")]
    for display_title, fund_name in funds_info:
        st.subheader(display_title)
        if not df_savings.empty and "fund_owner" in df_savings.columns:
            fund_data = df_savings[df_savings["fund_owner"] == fund_name].copy()
            total_goc = fund_data["amount"].sum() if not fund_data.empty else 0
        else:
            fund_data = pd.DataFrame()
            total_goc = 0
            
        st.markdown(f"**Tổng vốn:** <span style='color:#10b981; font-size:18px'>{total_goc:,.0f} ₫</span>", unsafe_allow_html=True)
        
        if not fund_data.empty:
            st.dataframe(
                fund_data[['bank', 'deposit_date', 'term', 'interest_rate', 'amount']].rename(
                    columns={'bank': 'Ngân hàng', 'deposit_date': 'Ngày gửi', 'term': 'Kỳ hạn', 'interest_rate': 'Lãi suất (%)', 'amount': 'Tiền gốc (VND)'}
                ),
                column_config={"Tiền gốc (VND)": st.column_config.NumberColumn("Tiền gốc (VND)", format="%,.0f ₫"), "Lãi suất (%)": st.column_config.NumberColumn("Lãi suất (%)", format="%.1f")},
                use_container_width=True, hide_index=True
            )
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
        if "funding_source" not in df_re.columns:
            df_re["funding_source"] = "N/A"
        if "note" not in df_re.columns:
            df_re["note"] = ""
            
        df_re_display = df_re[['id', 'project_name', 'contract_value', 'installment_name', 'amount', 'funding_source', 'due_date', 'status', 'note']].rename(
            columns={
                'project_name': 'Dự án', 
                'contract_value': 'Giá trị HĐ (VND)',
                'installment_name': 'Tên Đợt', 
                'amount': 'Thanh toán (VND)', 
                'funding_source': 'Nguồn tiền',
                'due_date': 'Hạn thanh toán', 
                'status': 'Trạng thái',
                'note': 'Ghi chú'
            }
        )
        st.dataframe(
            df_re_display,
            column_config={
                "id": None, 
                "Giá trị HĐ (VND)": st.column_config.NumberColumn("Giá trị HĐ (VND)", format="%,.0f ₫"),
                "Thanh toán (VND)": st.column_config.NumberColumn("Thanh toán (VND)", format="%,.0f ₫")
            },
            use_container_width=True, hide_index=True
        )
        
        # Action BĐS
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
        
        df_display_vay = df_vay.rename(columns={"purpose": "Mục đích", "bank": "Ngân hàng", "interest_rate": "Lãi suất (%/năm)", "total_months": "Tổng kỳ hạn"})
        cols_to_show = ['id', 'Mục đích', 'Ngân hàng', 'Dư nợ HIỆN TẠI', 'Tháng đã trả', 'Tổng kỳ hạn', 'Lãi suất (%/năm)', 'Gốc cố định/Tháng', 'Lãi tháng này', 'Tổng phải trả (Tháng này)']
        
        st.dataframe(
            df_display_vay[cols_to_show],
            column_config={
                "id": None,
                "Dư nợ HIỆN TẠI": st.column_config.NumberColumn("Dư nợ HIỆN TẠI", format="%,.0f ₫"),
                "Gốc cố định/Tháng": st.column_config.NumberColumn("Gốc cố định/Tháng", format="%,.0f ₫"),
                "Lãi tháng này": st.column_config.NumberColumn("Lãi tháng này", format="%,.0f ₫"),
                "Tổng phải trả (Tháng này)": st.column_config.NumberColumn("Tổng phải trả (Tháng)", format="%,.0f ₫"),
                "Lãi suất (%/năm)": st.column_config.NumberColumn("Lãi suất (%/năm)", format="%.2f%%")
            },
            use_container_width=True, hide_index=True
        )
        
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
