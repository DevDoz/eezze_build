import frappe
import shutil
import os
import sys
sys.path.insert(0, '/Users/ali/FrappeBench/frappeBench/apps/eezze_build')
from frappe.utils import getdate, now_datetime, flt

frappe.init(site='eezze.build')
frappe.connect()

company = 'EEZZE Build'
bank_account_name = 'FNB Gaborone Main - 1110'
gl_account = frappe.db.get_value('Bank Account', bank_account_name, 'account') or 'Cash - EEZZE'

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

pdf_fnb_stmt = create_attachment('FNB_Bank_Statement_November_2026.pdf')
pdf_recon_report = create_attachment('Bank_Reconciliation_Report_FNB_Gaborone_Main_2026-11-27.pdf')
pdf_midmonth_stmt = create_attachment('FNB_MidMonth_Statement_November_2026.pdf')

# -------------------------------------------------------------------------
# RECORD 1: The Golden Path (Balanced & Reconciled with Zero Variance)
# -------------------------------------------------------------------------
rec_1_name = 'BANK-REC-2026-00001'
if frappe.db.exists('Bank Reconciliation Statement', rec_1_name):
    frappe.delete_doc('Bank Reconciliation Statement', rec_1_name, force=1)

doc1 = frappe.new_doc('Bank Reconciliation Statement')
doc1.name = rec_1_name
doc1.company = company
doc1.bank_account = bank_account_name
doc1.gl_account = gl_account
doc1.statement_date = '2026-11-27'
doc1.posting_date = '2026-11-27'
doc1.currency = 'BWP'

# Step 1: Till 100 Reconciled
doc1.till_100_reconciled = 1
doc1.till_100_reconciled_by = 'Administrator'
doc1.till_100_reconciled_at = '2026-11-27 14:00:00'
doc1.till_100_notes = 'All branch Till 100 daily registers (Gaborone Central, Francistown, Mogoditshane, Tlokweng, Palapye) reconciled and posted into Central Cash Book.'

# Step 2 & 4: Bank Statement
doc1.statement_file = pdf_fnb_stmt
doc1.bank_statement_opening_balance = 500000.00
doc1.bank_statement_closing_balance = 404625.00
doc1.bank_statement_date = '2026-11-27'
doc1.bank_statement_ref = 'FNB-BW-STMT-2026-11'

# Step 3 & 5: Balances
doc1.gl_book_balance = 344625.00
doc1.total_unpresented_payments = 85000.00
doc1.total_deposits_in_transit = 25000.00
doc1.adjusted_bank_balance = 344625.00
doc1.reconcilable_balance = 0.00
doc1.variance_status = 'Balanced (Zero Variance)'
doc1.suspense_items_found = 0
doc1.suspense_amount = 0.00

# Reconciling items
doc1.append('reconciling_items', {
    'item_type': 'Reconciled Transaction',
    'reference_doctype': 'Payment Entry',
    'reference_name': 'ACC-PAY-2026-00006',
    'party_type': 'Supplier',
    'party': 'National Building Supplies Ltd.',
    'reference_no': 'EFT-FNB-BW-992014',
    'posting_date': '2026-11-27',
    'amount': 82875.00,
    'clearance_date': '2026-11-27',
    'reconciled': 1,
    'notes': 'Supplier payment cleared by bank'
})

doc1.append('reconciling_items', {
    'item_type': 'Reconciled Transaction',
    'reference_doctype': 'Payment Entry',
    'reference_name': 'ACC-PAY-2026-00008',
    'party_type': 'Customer',
    'party': 'Palmer Productions Ltd.',
    'reference_no': 'EFT-FNB-REF-449102',
    'posting_date': '2026-11-27',
    'amount': 12500.00,
    'clearance_date': '2026-11-27',
    'reconciled': 1,
    'notes': 'Customer refund cleared by bank'
})

doc1.append('reconciling_items', {
    'item_type': 'Unpresented Payment (Cheque/EFT)',
    'reference_doctype': 'Payment Entry',
    'reference_name': 'ACC-PAY-2026-00007',
    'party_type': 'Supplier',
    'party': 'PPC Cement Botswana Ltd.',
    'reference_no': 'EFT-PPC-2026-007',
    'posting_date': '2026-11-27',
    'amount': 85000.00,
    'reconciled': 0,
    'notes': 'EFT loaded on banking, unpresented/pending CEO release'
})

doc1.append('reconciling_items', {
    'item_type': 'Deposit in Transit',
    'reference_no': 'DEP-PALAPYE-0491',
    'posting_date': '2026-11-27',
    'amount': 25000.00,
    'reconciled': 0,
    'notes': 'Palapye Branch weekend cash deposit collected by courier, not yet credited by FNB'
})

# Step 6: Post and Print
doc1.status = 'Reconciled & Filed'
doc1.reconciled_by = 'Administrator'
doc1.reconciled_at = '2026-11-27 14:15:00'
doc1.reconciliation_report_file = pdf_recon_report
doc1.filing_notes = 'Bank Reconciliation Statement BANK-REC-2026-00001 balanced and posted into Eezze Build General Ledger. Bank Reconciliation Report generated and filed in physical & digital Bank Reconciliation File.'

doc1.insert(ignore_permissions=True)
print('Created Demo Record 1:', rec_1_name)


# -------------------------------------------------------------------------
# RECORD 2: Suspense Investigation Loop (SOP-ACC-10 Step 7)
# -------------------------------------------------------------------------
rec_2_name = 'BANK-REC-2026-00002'
if frappe.db.exists('Bank Reconciliation Statement', rec_2_name):
    frappe.delete_doc('Bank Reconciliation Statement', rec_2_name, force=1)

doc2 = frappe.new_doc('Bank Reconciliation Statement')
doc2.name = rec_2_name
doc2.company = company
doc2.bank_account = bank_account_name
doc2.gl_account = gl_account
doc2.statement_date = '2026-11-20'
doc2.posting_date = '2026-11-20'
doc2.currency = 'BWP'

# Step 1: Till 100 Reconciled
doc2.till_100_reconciled = 1
doc2.till_100_reconciled_by = 'Administrator'
doc2.till_100_reconciled_at = '2026-11-20 10:00:00'
doc2.till_100_notes = 'Branch Till 100 registers verified.'

# Step 2 & 4: Bank Statement
doc2.statement_file = pdf_midmonth_stmt
doc2.bank_statement_opening_balance = 500000.00
doc2.bank_statement_closing_balance = 480000.00
doc2.bank_statement_date = '2026-11-20'
doc2.bank_statement_ref = 'FNB-BW-STMT-MID-2026-11'

# Step 3 & 5: Balances with Suspense Variance
doc2.gl_book_balance = 481450.00
doc2.total_unpresented_payments = 0.00
doc2.total_deposits_in_transit = 0.00
doc2.adjusted_bank_balance = 480000.00
doc2.reconcilable_balance = -1450.00
doc2.variance_status = 'Variance: -1,450.00 BWP (Investigate Suspense)'
doc2.suspense_items_found = 1
doc2.suspense_amount = 1450.00
doc2.suspense_account = 'Bank Suspense Account - EEZZE'
doc2.status = 'Suspense Under Investigation'

doc2.investigation_notes = 'Per SOP-ACC-10 Step 7, investigating bank suspense under General Ledger > Posting. Bank statement reflects automated direct debit of BWP 1,450.00 for FNB Speedpoint POS terminal service charges across 5 branches. Action: Post adjusting entry to Bank Charges expense account.'
doc2.investigated_by = 'Administrator'

doc2.append('reconciling_items', {
    'item_type': 'Suspense Item',
    'reference_no': 'FNB-DEBIT-SERV-019',
    'posting_date': '2026-11-20',
    'amount': 1450.00,
    'reconciled': 0,
    'notes': 'Unrecorded bank service fee direct debit on statement. Under investigation per Step 7.'
})

doc2.insert(ignore_permissions=True)
print('Created Demo Record 2:', rec_2_name)

frappe.db.commit()
print('All Bank Reconciliation demo records successfully seeded!')
