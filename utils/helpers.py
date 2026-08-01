import re
import streamlit as st

DEBIT_ACCOUNTS = ["VCB chồng", "TCB chồng", "TCB vợ"]
CREDIT_CARDS = ["UOB vợ", "UOB chồng", "HSBC chồng"]
BROKER_ACCOUNTS = ["TCBS", "SSI", "VPS", "VNDirect", "HSC", "Mirae Asset"]
BANK_ACCOUNTS = DEBIT_ACCOUNTS + CREDIT_CARDS + BROKER_ACCOUNTS
FUNDING_SOURCES = BANK_ACCOUNTS + ["Tiền mặt", "Giải ngân vốn vay", "Khác"]
TERMS = ["Không kỳ hạn", "1 Tháng", "2 Tháng", "3 Tháng", "6 Tháng", "7 Tháng", "12 Tháng", "24 Tháng", "36 Tháng"]
CATS = ["Lương/Thu nhập", "Ăn uống & Sinh hoạt", "Giáo dục (Con cái)", "Nhà cửa & Tiện ích", "Sức khỏe & Y tế", "Đi lại & Phương tiện", "Hiếu hỉ & Mua sắm", "Đầu tư & Trả nợ", "Khác"]
EXPENSE_CATS = [c for c in CATS if c != "Lương/Thu nhập"]
FUNDS = ["Tieu Boi Funding", "Daddy Funding", "Mama Funding"]
GOLD_TYPES = ["SJC Miếng", "Nhẫn trơn 9999", "PNJ", "DOJI", "Vàng trang sức", "Khác"]

def parse_smart_amount(input_str):
    if not input_str: return 0
    s = str(input_str).lower().strip().replace(' ', '')
    if s == '': return 0
    match = re.match(r'^([\d\,\.]+)(k|tr|triệu|tỷ|ty|m|b|e\d+)?$', s)
    if not match:
        try: return float(s)
        except: return -1
    num_part = match.group(1)
    unit_part = match.group(2)
    if '.' in num_part and ',' in num_part: num_part = num_part.replace('.', '').replace(',', '.')
    elif ',' in num_part:
        if num_part.count(',') > 1 or len(num_part.split(',')[-1]) == 3: num_part = num_part.replace(',', '')
        else: num_part = num_part.replace(',', '.')
    elif '.' in num_part:
        if num_part.count('.') > 1 or len(num_part.split('.')[-1]) == 3: num_part = num_part.replace('.', '')
    try:
        val = float(num_part)
        if unit_part == 'k': val *= 1_000
        elif unit_part in ['tr', 'triệu', 'm']: val *= 1_000_000
        elif unit_part in ['tỷ', 'ty', 'b']: val *= 1_000_000_000
        elif unit_part and unit_part.startswith('e'): val = float(num_part + unit_part)
        return val
    except: return -1

def add_quick_amount(val):
    current = parse_smart_amount(st.session_state.cf_amount_str)
    if current < 0: current = 0
    st.session_state.cf_amount_str = f"{int(current + val):,}"

def clear_quick_amount():
    st.session_state.cf_amount_str = ""
