import frappe
import shutil
import os
import sys
sys.path.insert(0, '/Users/ali/FrappeBench/frappeBench/apps/eezze_build')
from frappe.utils import getdate, now_datetime, flt
from erpnext.controllers.sales_and_purchase_return import make_return_doc

frappe.init(site='eezze.build')
frappe.connect()

company = 'EEZZE Build'
income_account = 'Service - EEZZE'
debtors_account = 'Debtors - EEZZE'
cost_center = 'Main - EEZZE'

# 1. Create file attachments by copying existing valid PDF
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

pdf_bank_fnb = create_attachment('Bank_Confirmation_Palmer_Productions_FNB.pdf')
pdf_pop_fnb = create_attachment('Customer_Refund_POP_Palmer_Productions_449102.pdf')
pdf_bank_absa = create_attachment('Bank_Confirmation_West_View_Software_Absa.pdf')
pdf_pod_palmer = create_attachment('Customer_Return_Goods_Receipt_Palmer.pdf')
pdf_pod_westview = create_attachment('Customer_Return_Goods_Receipt_WestView.pdf')

# -------------------------------------------------------------------------
# Customer 1: Palmer Productions Ltd. (Gaborone Central Store)
# -------------------------------------------------------------------------
customer_1 = 'Palmer Productions Ltd.'
si1_name = 'ACC-SINV-2026-00006'
crn1_name = 'ACC-SINV-2026-00007'

if not frappe.db.exists('Sales Invoice', si1_name):
    si1 = frappe.new_doc('Sales Invoice')
    si1.company = company
    si1.currency = 'PKR'
    si1.conversion_rate = 1.0
    si1.customer = customer_1
    si1.posting_date = '2026-11-15'
    si1.debit_to = debtors_account
    si1.append('items', {
        'item_code': 'CEMENT-50KG',
        'qty': 40,
        'rate': 850.0,
        'income_account': income_account,
        'cost_center': cost_center
    })
    si1.insert(ignore_permissions=True)
    si1.submit()
    si1_name = si1.name

    crn1 = make_return_doc('Sales Invoice', si1_name)
    crn1.posting_date = '2026-11-20'
    crn1.items[0].qty = -14.705882
    crn1.insert(ignore_permissions=True)
    crn1.submit()
    crn1_name = crn1.name

# -------------------------------------------------------------------------
# Customer 2: Grant Plastics Ltd. (Francistown Branch)
# -------------------------------------------------------------------------
customer_2 = 'Grant Plastics Ltd.'
si2_name = frappe.db.get_value('Sales Invoice', {'customer': customer_2, 'company': company, 'is_return': 0}, 'name')
if not si2_name:
    si2 = frappe.new_doc('Sales Invoice')
    si2.company = company
    si2.currency = 'PKR'
    si2.conversion_rate = 1.0
    si2.customer = customer_2
    si2.posting_date = '2026-11-16'
    si2.debit_to = debtors_account
    si2.append('items', {
        'item_code': 'STEEL-12MM',
        'qty': 80,
        'rate': 200.0,
        'income_account': income_account,
        'cost_center': cost_center
    })
    si2.insert(ignore_permissions=True)
    si2.submit()
    si2_name = si2.name
    print('Created Original Sales Invoice 2:', si2_name)

crn2_name = frappe.db.get_value('Sales Invoice', {'customer': customer_2, 'company': company, 'is_return': 1}, 'name')
if not crn2_name:
    crn2 = make_return_doc('Sales Invoice', si2_name)
    crn2.posting_date = '2026-11-22'
    crn2.items[0].qty = -21
    crn2.insert(ignore_permissions=True)
    crn2.submit()
    crn2_name = crn2.name
    print('Created Credit Note 2:', crn2_name, 'Total:', crn2.grand_total)

# -------------------------------------------------------------------------
# Customer 3: West View Software Ltd. (Palapye Branch)
# -------------------------------------------------------------------------
customer_3 = 'West View Software Ltd.'
si3_name = frappe.db.get_value('Sales Invoice', {'customer': customer_3, 'company': company, 'is_return': 0}, 'name')
if not si3_name:
    si3 = frappe.new_doc('Sales Invoice')
    si3.company = company
    si3.currency = 'PKR'
    si3.conversion_rate = 1.0
    si3.customer = customer_3
    si3.posting_date = '2026-11-18'
    si3.debit_to = debtors_account
    si3.append('items', {
        'item_code': 'CEMENT-50KG',
        'qty': 30,
        'rate': 875.0,
        'income_account': income_account,
        'cost_center': cost_center
    })
    si3.insert(ignore_permissions=True)
    si3.submit()
    si3_name = si3.name
    print('Created Original Sales Invoice 3:', si3_name)

crn3_name = frappe.db.get_value('Sales Invoice', {'customer': customer_3, 'company': company, 'is_return': 1}, 'name')
if not crn3_name:
    crn3 = make_return_doc('Sales Invoice', si3_name)
    crn3.posting_date = '2026-11-23'
    crn3.items[0].qty = -10
    crn3.insert(ignore_permissions=True)
    crn3.submit()
    crn3_name = crn3.name
    print('Created Credit Note 3:', crn3_name, 'Total:', crn3.grand_total)


# -------------------------------------------------------------------------
# RECORD 1: The Golden Path (Paid & POP Sent)
# -------------------------------------------------------------------------
req_1_name = 'REF-REQ-2026-00001'
if frappe.db.exists('Customer Refund Request', req_1_name):
    frappe.delete_doc('Customer Refund Request', req_1_name, force=1)

req1 = frappe.new_doc('Customer Refund Request')
req1.name = req_1_name
req1.company = company
req1.branch = 'Gaborone Central Store - EEZZE'
req1.posting_date = '2026-11-27'
req1.customer = customer_1
req1.customer_name = customer_1
req1.customer_email = 'accounts@palmerproductions.co.bw'
req1.original_sales_invoice = si1_name
req1.credit_note = crn1_name
req1.refund_amount = 12500.00
req1.currency = 'BWP'
req1.proof_of_original_payment = pdf_pod_palmer
req1.bank_name = 'First National Bank Botswana'
req1.bank_account_no = '62019920101'
req1.bank_branch_code = '281467'
req1.bank_account_holder = 'Palmer Productions Ltd.'
req1.bank_confirmation_letter = pdf_bank_fnb

# DMN-ACC-09 checklist
req1.credit_note_approved = 1
req1.original_payment_received = 1
req1.bank_details_confirmed = 1
req1.dmn_decision = 'Pay'

# Dual Control
req1.fm_authorized = 1
req1.fm_authorized_by = 'Administrator'
req1.fm_authorized_at = '2026-11-27 13:10:00'
req1.loaded_on_banking = 1
req1.loaded_by = 'Administrator'
req1.loaded_at = '2026-11-27 13:15:00'
req1.bank_transfer_ref = 'EFT-FNB-REF-449102'
req1.ceo_released = 1
req1.ceo_released_by = 'Administrator'
req1.ceo_released_at = '2026-11-27 13:20:00'

req1.pop_file = pdf_pop_fnb
req1.pop_sent = 1
req1.pop_sent_at = '2026-11-27 13:25:00'
req1.filing_notes = f'POP and Credit Note {crn1_name} filed in Customer Refunds Master Archive. Sent to customer and Gaborone branch.'
req1.status = 'Refund Paid & Filed'

req1.insert(ignore_permissions=True)
print('Inserted Request 1:', req_1_name)

# Create and submit Payment Entry
pe_1_name = 'ACC-PAY-2026-00008'
if frappe.db.exists('Payment Entry', pe_1_name):
    frappe.delete_doc('Payment Entry', pe_1_name, force=1)

pe1 = frappe.new_doc('Payment Entry')
pe1.name = pe_1_name
pe1.payment_type = 'Pay'
pe1.company = company
pe1.posting_date = '2026-11-27'
pe1.party_type = 'Customer'
pe1.party = customer_1
pe1.paid_from = 'Cash - EEZZE'
pe1.paid_to = debtors_account
pe1.paid_amount = 12500.00
pe1.received_amount = 12500.00
pe1.reference_no = 'EFT-FNB-REF-449102'
pe1.reference_date = '2026-11-27'
pe1.remarks = f'Customer Refund for Credit Note {crn1_name}. Branch: Gaborone Central Store. FNB Ref: EFT-FNB-REF-449102'
pe1.custom_loaded_by_ap = 1
pe1.custom_fm_authorized = 1
pe1.custom_fm_authorized_by = 'Administrator'
pe1.custom_fm_authorized_on = '2026-11-27 13:10:00'
pe1.custom_ceo_released = 1
pe1.custom_ceo_released_by = 'Administrator'
pe1.custom_ceo_released_on = '2026-11-27 13:20:00'
pe1.custom_pop_file = pdf_pop_fnb
pe1.custom_pop_sent = 1
pe1.custom_pop_sent_on = '2026-11-27 13:25:00'
pe1.custom_customer_refund_ref = req_1_name

pe1.insert(ignore_permissions=True)
pe1.submit()

req1.payment_entry = pe_1_name
req1.save(ignore_permissions=True)
print('Created Demo Record 1:', req_1_name)


# -------------------------------------------------------------------------
# RECORD 2: DMN-ACC-09 Exception (Returned to Branch)
# -------------------------------------------------------------------------
req_2_name = 'REF-REQ-2026-00002'
if frappe.db.exists('Customer Refund Request', req_2_name):
    frappe.delete_doc('Customer Refund Request', req_2_name, force=1)

req2 = frappe.new_doc('Customer Refund Request')
req2.name = req_2_name
req2.company = company
req2.branch = 'Francistown Branch - EEZZE'
req2.posting_date = '2026-11-27'
req2.customer = customer_2
req2.customer_name = customer_2
req2.customer_email = 'finance@grantplastics.co.bw'
req2.original_sales_invoice = si2_name
req2.credit_note = crn2_name
req2.refund_amount = 4200.00
req2.currency = 'BWP'
req2.bank_name = 'Stanbic Bank Botswana'
req2.bank_account_no = '90600029381'
req2.bank_branch_code = '064967'
req2.bank_account_holder = 'Grant Plastics Ltd.'

# DMN-ACC-09: Fails on original payment and bank confirmation
req2.credit_note_approved = 1
req2.original_payment_received = 0
req2.bank_details_confirmed = 0
req2.dmn_decision = 'Return to Branch'
req2.status = 'Returned to Branch'
req2.return_reason = 'Per DMN-ACC-09 Rule 2, do not refund money not yet received (Customer original cheque payment #004921 has not cleared the bank account). In addition, official customer bank confirmation letter is missing from Francistown branch. Request returned to Branch / Customer Returns.'
req2.return_notified = 1
req2.return_notified_at = '2026-11-27 13:30:00'

req2.insert(ignore_permissions=True)
print('Created Demo Record 2:', req_2_name)


# -------------------------------------------------------------------------
# RECORD 3: Dual Control Maker-Checker Gatekeeping
# -------------------------------------------------------------------------
req_3_name = 'REF-REQ-2026-00003'
if frappe.db.exists('Customer Refund Request', req_3_name):
    frappe.delete_doc('Customer Refund Request', req_3_name, force=1)

req3 = frappe.new_doc('Customer Refund Request')
req3.name = req_3_name
req3.company = company
req3.branch = 'Palapye Branch - EEZZE'
req3.posting_date = '2026-11-27'
req3.customer = customer_3
req3.customer_name = customer_3
req3.customer_email = 'accounts@westview.co.bw'
req3.original_sales_invoice = si3_name
req3.credit_note = crn3_name
req3.refund_amount = 8750.00
req3.currency = 'BWP'
req3.proof_of_original_payment = pdf_pod_westview
req3.bank_name = 'Absa Bank Botswana'
req3.bank_account_no = '3004928172'
req3.bank_branch_code = '290167'
req3.bank_account_holder = 'West View Software Ltd.'
req3.bank_confirmation_letter = pdf_bank_absa

# DMN-ACC-09 checklist passed
req3.credit_note_approved = 1
req3.original_payment_received = 1
req3.bank_details_confirmed = 1
req3.dmn_decision = 'Pay'

# Dual Control in progress
req3.fm_authorized = 1
req3.fm_authorized_by = 'Administrator'
req3.fm_authorized_at = '2026-11-27 13:35:00'
req3.loaded_on_banking = 1
req3.loaded_by = 'Administrator'
req3.loaded_at = '2026-11-27 13:40:00'
req3.bank_transfer_ref = 'EFT-ABSA-REF-773190'
req3.ceo_released = 0

req3.status = 'Pending CEO Release'
req3.insert(ignore_permissions=True)
print('Inserted Request 3:', req_3_name)

# Draft Payment Entry created
pe_3_name = 'ACC-PAY-2026-00009'
if frappe.db.exists('Payment Entry', pe_3_name):
    frappe.delete_doc('Payment Entry', pe_3_name, force=1)

pe3 = frappe.new_doc('Payment Entry')
pe3.name = pe_3_name
pe3.payment_type = 'Pay'
pe3.company = company
pe3.posting_date = '2026-11-27'
pe3.party_type = 'Customer'
pe3.party = customer_3
pe3.paid_from = 'Cash - EEZZE'
pe3.paid_to = debtors_account
pe3.paid_amount = 8750.00
pe3.received_amount = 8750.00
pe3.reference_no = 'EFT-ABSA-REF-773190'
pe3.reference_date = '2026-11-27'
pe3.remarks = f'Customer Refund (Awaiting CEO Release): {req_3_name} for {customer_3}. Palapye Branch. Absa Ref: EFT-ABSA-REF-773190'
pe3.custom_loaded_by_ap = 1
pe3.custom_fm_authorized = 1
pe3.custom_fm_authorized_by = 'Administrator'
pe3.custom_fm_authorized_on = '2026-11-27 13:35:00'
pe3.custom_ceo_released = 0
pe3.custom_customer_refund_ref = req_3_name

pe3.insert(ignore_permissions=True)

req3.payment_entry = pe_3_name
req3.save(ignore_permissions=True)
print('Created Demo Record 3:', req_3_name)

frappe.db.commit()
print('All Customer Refund demo records successfully seeded!')
