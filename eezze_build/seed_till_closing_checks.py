import frappe
import shutil
import os
import sys
sys.path.insert(0, '/Users/ali/FrappeBench/frappeBench/apps/eezze_build')
from frappe.utils import getdate, now_datetime, flt

frappe.init(site='eezze.build')
frappe.connect()

company = 'EEZZE Build'
suspense_account = 'Till Suspense - EEZZE'

# 1. Create file attachments
files_dir = os.path.join(frappe.get_site_path(), 'private', 'files')
src_pdf = os.path.join(files_dir, 'Bank_POP_EFT-FNB-BW-990142.pdf')

def create_attachment(filename):
    dst = os.path.join(files_dir, filename)
    shutil.copyfile(src_pdf, dst)
    file_url = f'/private/files/{filename}'
    if not frappe.db.exists('File', {'file_url': file_url}):
        fdoc = frappe.new_doc('File')
        fdoc.file_name = filename
        fdoc.file_url = file_url
        fdoc.is_private = 1
        fdoc.insert(ignore_permissions=True)
    return file_url

pdf_incident = create_attachment('Incident_Report_Francistown_INC-FT-2026-081.pdf')
pdf_cashup_palapye = create_attachment('Daily_Cash_Up_Report_Palapye_Branch.pdf')

branches = [
    'Gaborone Central Store - EEZZE',
    'Francistown Branch - EEZZE',
    'Mogoditshane Branch - EEZZE',
    'Tlokweng Branch - EEZZE',
    'Palapye Branch - EEZZE'
]

# -------------------------------------------------------------------------
# RECORD 1: Clean Morning Routine (Zero Suspense & All Tills Closed)
# -------------------------------------------------------------------------
rec_1_name = 'TILL-CHK-2026-00001'
if frappe.db.exists('Daily Till Closing Check', rec_1_name):
    frappe.delete_doc('Daily Till Closing Check', rec_1_name, force=1)

doc1 = frappe.new_doc('Daily Till Closing Check')
doc1.name = rec_1_name
doc1.company = company
doc1.check_date = '2026-11-27'
doc1.target_date = '2026-11-26'
doc1.currency = 'BWP'
doc1.all_tills_closed = 1
doc1.unclosed_tills_count = 0
doc1.registers_summary = 'All 20 branch till registers verified: Tills 1 & 2 closed, Tills 10 & 100 reconciled across all 5 branches.'

for b in branches:
    b_short = b[:3].upper()
    doc1.append('till_registers', {
        'branch': b,
        'till_name': 'Till 1 (POS Main)',
        'till_type': 'POS Register (Till 1 & 2)',
        'status': 'Closed',
        'opening_amount': 2500.0,
        'expected_amount': 28500.0,
        'closing_amount': 28500.0,
        'variance': 0.0,
        'closing_doc_ref': f'POS-CLS-{b_short}-01'
    })
    doc1.append('till_registers', {
        'branch': b,
        'till_name': 'Till 2 (POS Express)',
        'till_type': 'POS Register (Till 1 & 2)',
        'status': 'Closed',
        'opening_amount': 1500.0,
        'expected_amount': 19200.0,
        'closing_amount': 19200.0,
        'variance': 0.0,
        'closing_doc_ref': f'POS-CLS-{b_short}-02'
    })
    doc1.append('till_registers', {
        'branch': b,
        'till_name': 'Till 10 (Branch Petty/Floats)',
        'till_type': 'Cash Book / Banking (Till 10 & 100)',
        'status': 'Reconciled',
        'opening_amount': 5000.0,
        'expected_amount': 4200.0,
        'closing_amount': 4200.0,
        'variance': 0.0,
        'closing_doc_ref': f'PETTY-{b_short}-10'
    })
    doc1.append('till_registers', {
        'branch': b,
        'till_name': 'Till 100 (Banking/Cash Book)',
        'till_type': 'Cash Book / Banking (Till 10 & 100)',
        'status': 'Reconciled',
        'opening_amount': 0.0,
        'expected_amount': 47700.0,
        'closing_amount': 47700.0,
        'variance': 0.0,
        'closing_doc_ref': f'BANK-{b_short}-100'
    })

# Till suspense is zero
doc1.till_suspense_account = suspense_account
doc1.previous_day_suspense_balance = 0.00
doc1.till_suspense_at_zero = 1

doc1.checked_by = 'Administrator'
doc1.checked_at = '2026-11-27 08:30:00'
doc1.overall_notes = 'Morning routine check completed. All branch tills closed and reconciled. Till suspense is zero.'
doc1.status = 'Verified & Cleared (Zero Suspense)'

doc1.insert(ignore_permissions=True)
print('Created Demo Record 1:', rec_1_name)


# -------------------------------------------------------------------------
# RECORD 2: Unclosed Till & DMN-ACC-06 Incident Report (Part 2 Exception)
# -------------------------------------------------------------------------
rec_2_name = 'TILL-CHK-2026-00002'
if frappe.db.exists('Daily Till Closing Check', rec_2_name):
    frappe.delete_doc('Daily Till Closing Check', rec_2_name, force=1)

doc2 = frappe.new_doc('Daily Till Closing Check')
doc2.name = rec_2_name
doc2.company = company
doc2.check_date = '2026-11-26'
doc2.target_date = '2026-11-25'
doc2.currency = 'BWP'
doc2.all_tills_closed = 0
doc2.unclosed_tills_count = 1
doc2.registers_summary = '⚠️ 1 of 4 branch till registers unclosed: Francistown Till 2 (POS Express) unclosed at close of business.'

# Francistown registers
doc2.append('till_registers', {
    'branch': 'Francistown Branch - EEZZE',
    'till_name': 'Till 1 (POS Main)',
    'till_type': 'POS Register (Till 1 & 2)',
    'status': 'Closed',
    'opening_amount': 2500.0,
    'expected_amount': 22000.0,
    'closing_amount': 22000.0,
    'variance': 0.0,
    'closing_doc_ref': 'POS-CLS-FRA-01'
})
doc2.append('till_registers', {
    'branch': 'Francistown Branch - EEZZE',
    'till_name': 'Till 2 (POS Express)',
    'till_type': 'POS Register (Till 1 & 2)',
    'status': 'Unclosed / Open',
    'opening_amount': 1500.0,
    'expected_amount': 14200.0,
    'closing_amount': 0.0,
    'variance': 14200.0,
    'notes': 'Unclosed at 17:30 closing. Cashier departed without performing POS close.'
})
doc2.append('till_registers', {
    'branch': 'Francistown Branch - EEZZE',
    'till_name': 'Till 10 (Branch Petty/Floats)',
    'till_type': 'Cash Book / Banking (Till 10 & 100)',
    'status': 'Reconciled',
    'opening_amount': 5000.0,
    'expected_amount': 4800.0,
    'closing_amount': 4800.0,
    'variance': 0.0
})
doc2.append('till_registers', {
    'branch': 'Francistown Branch - EEZZE',
    'till_name': 'Till 100 (Banking/Cash Book)',
    'till_type': 'Cash Book / Banking (Till 10 & 100)',
    'status': 'Reconciled',
    'opening_amount': 0.0,
    'expected_amount': 22000.0,
    'closing_amount': 22000.0,
    'variance': 0.0
})

# DMN-ACC-06 Evaluation
doc2.manager_contacted = 1
doc2.reason_given_by_manager = 1
doc2.reason_documented = 0  # Missing documentation -> Rule 2 applies!
doc2.dmn_action = 'Make incident report'
doc2.manager_reason_notes = 'Branch Manager stated cashier departed on emergency medical leave. However, no written documentation or cash-up handover was submitted.'
doc2.incident_report_required = 1
doc2.incident_report_ref = 'INC-FT-2026-081'
doc2.incident_report_file = pdf_incident
doc2.incident_outcome_followed_up = 1
doc2.incident_outcome_notes = 'Incident report INC-FT-2026-081 filed by Francistown BM. Cash counted the following morning under BM supervision; cash-up reconciled with zero variance.'

doc2.till_suspense_account = suspense_account
doc2.previous_day_suspense_balance = 0.00
doc2.till_suspense_at_zero = 1
doc2.checked_by = 'Administrator'
doc2.checked_at = '2026-11-26 09:00:00'
doc2.status = 'Incident Report Raised'

doc2.insert(ignore_permissions=True)
print('Created Demo Record 2:', rec_2_name)


# -------------------------------------------------------------------------
# RECORD 3: Till Suspense Discrepancy & Reporting to FM (Part 3 & 4)
# -------------------------------------------------------------------------
rec_3_name = 'TILL-CHK-2026-00003'
if frappe.db.exists('Daily Till Closing Check', rec_3_name):
    frappe.delete_doc('Daily Till Closing Check', rec_3_name, force=1)

doc3 = frappe.new_doc('Daily Till Closing Check')
doc3.name = rec_3_name
doc3.company = company
doc3.check_date = '2026-11-25'
doc3.target_date = '2026-11-24'
doc3.currency = 'BWP'
doc3.all_tills_closed = 1
doc3.unclosed_tills_count = 0
doc3.registers_summary = 'All Palapye branch registers closed, but General Ledger Till Suspense has an unreconciled balance.'

# Palapye registers with cash discrepancy
doc3.append('till_registers', {
    'branch': 'Palapye Branch - EEZZE',
    'till_name': 'Till 1 (POS Main)',
    'till_type': 'POS Register (Till 1 & 2)',
    'status': 'Discrepancy',
    'opening_amount': 2500.0,
    'expected_amount': 14500.0,
    'closing_amount': 14850.0,
    'variance': 350.0,
    'closing_doc_ref': 'POS-CLS-PAL-01',
    'notes': 'Physical cash count 14,850 BWP vs POS system total 14,500 BWP (+350 BWP variance)'
})
doc3.append('till_registers', {
    'branch': 'Palapye Branch - EEZZE',
    'till_name': 'Till 2 (POS Express)',
    'till_type': 'POS Register (Till 1 & 2)',
    'status': 'Closed',
    'opening_amount': 1500.0,
    'expected_amount': 9800.0,
    'closing_amount': 9800.0,
    'variance': 0.0,
    'closing_doc_ref': 'POS-CLS-PAL-02'
})
doc3.append('till_registers', {
    'branch': 'Palapye Branch - EEZZE',
    'till_name': 'Till 10 (Branch Petty/Floats)',
    'till_type': 'Cash Book / Banking (Till 10 & 100)',
    'status': 'Reconciled',
    'opening_amount': 5000.0,
    'closing_amount': 5000.0,
    'variance': 0.0
})
doc3.append('till_registers', {
    'branch': 'Palapye Branch - EEZZE',
    'till_name': 'Till 100 (Banking/Cash Book)',
    'till_type': 'Cash Book / Banking (Till 10 & 100)',
    'status': 'Reconciled',
    'opening_amount': 0.0,
    'closing_amount': 24650.0,
    'variance': 0.0
})

# Till Suspense Discrepancy
doc3.till_suspense_account = suspense_account
doc3.previous_day_suspense_balance = 350.00
doc3.till_suspense_at_zero = 0

# Part 4 Cash-Up Comparison
doc3.cash_up_comparison_done = 1
doc3.daily_cash_up_file = pdf_cashup_palapye
doc3.discrepancy_amount = 350.00
doc3.discrepancy_details = 'Per SOP-ACC-12 Step 6, cash-up report compared to General Ledger Till Suspense. Physical banking deposit was BWP 14,850 vs Till 1 POS posting of BWP 14,500 (+350 BWP surplus). Reported to Finance Manager for ledger adjustment.'
doc3.reported_to_fm = 1
doc3.reported_to_fm_at = '2026-11-25 09:15:00'

doc3.checked_by = 'Administrator'
doc3.checked_at = '2026-11-25 09:15:00'
doc3.overall_notes = 'Discrepancy identified in Palapye Till 1 cash-up. Formally escalated to Finance Manager.'
doc3.status = 'Closed & Discrepancy Reported to FM'

doc3.insert(ignore_permissions=True)
print('Created Demo Record 3:', rec_3_name)

frappe.db.commit()
print('All Daily Till Closing Check demo records successfully seeded!')
