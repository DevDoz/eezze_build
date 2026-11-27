import frappe
import os
import sys
sys.path.insert(0, '/Users/ali/FrappeBench/frappeBench/apps/eezze_build')
from frappe.utils import getdate, now_datetime, flt

frappe.init(site='eezze.build')
frappe.connect()

company = 'EEZZE Build'
cash_adv_account = 'Cash Advance Control - EEZZE'

# Ensure Currency Exchange BWP to PKR exists
if not frappe.db.exists('Currency Exchange', {'from_currency': 'BWP', 'to_currency': 'PKR'}):
    ce = frappe.new_doc('Currency Exchange')
    ce.from_currency = 'BWP'
    ce.to_currency = 'PKR'
    ce.exchange_rate = 1.0
    ce.insert(ignore_permissions=True)
if not frappe.db.exists('Currency Exchange', {'from_currency': 'PKR', 'to_currency': 'BWP'}):
    ce = frappe.new_doc('Currency Exchange')
    ce.from_currency = 'PKR'
    ce.to_currency = 'BWP'
    ce.exchange_rate = 1.0
    ce.insert(ignore_permissions=True)

# Ensure Botswana Territory exists
if not frappe.db.exists('Territory', 'Botswana'):
    t = frappe.new_doc('Territory')
    t.territory_name = 'Botswana'
    t.parent_territory = 'All Territories'
    t.is_group = 0
    t.insert(ignore_permissions=True)

# 1. Helper to create Customer
def ensure_customer(cust_name):
    if not frappe.db.exists('Customer', cust_name):
        c = frappe.new_doc('Customer')
        c.customer_name = cust_name
        c.customer_type = 'Company'
        c.customer_group = 'Commercial'
        c.territory = 'Botswana'
        c.insert(ignore_permissions=True)
    return cust_name

# 2. Helper to create Item
def ensure_item(item_code, item_name, standard_rate):
    if not frappe.db.exists('Item', item_code):
        it = frappe.new_doc('Item')
        it.item_code = item_code
        it.item_name = item_name
        it.item_group = 'Products'
        it.stock_uom = 'Nos'
        it.is_stock_item = 1
        it.standard_rate = standard_rate
        it.insert(ignore_permissions=True)
    return item_code

# Create master data
ensure_customer('Botho Construction (Pty) Ltd')
ensure_customer('Kgalagadi Mining Services')
ensure_customer('Kagisano Property Developers')
ensure_customer('Francistown General Contractors')
ensure_customer('Tati River Builders')
ensure_customer('Morupule Commercial Contractors')
ensure_customer('Palapye Urban Projects')

ensure_item('CEMENT-50KG', 'Dangote 42.5N Cement 50kg', 120.0)
ensure_item('STEEL-12MM', 'High Tensile Deformed Rebar Y12 6M', 123.33)
ensure_item('TIMBER-TRUSS-38X114', 'Structural Pine Timber 38x114mm 6.0M', 156.25)
ensure_item('BRICK-STOCK-MAXI', 'Cement Maxi Bricks (Load-Bearing)', 9.50)
ensure_item('ROOF-IBR-05MM', 'IBR Galvanised 0.5mm Roof Sheets 6M', 183.33)
ensure_item('PAVER-INTERLOCK-60', 'Interlocking Paving Blocks 60mm Grey', 15.0)

# Fetch existing Sales Orders mapped by customer
so_map = {}
for cust in [
    'Botho Construction (Pty) Ltd',
    'Kgalagadi Mining Services',
    'Kagisano Property Developers',
    'Francistown General Contractors',
    'Tati River Builders',
    'Morupule Commercial Contractors',
    'Palapye Urban Projects'
]:
    so_list = frappe.get_all('Sales Order', filters={'customer': cust}, pluck='name', order_by='creation desc')
    if so_list:
        so_map[cust] = so_list[0]

# -------------------------------------------------------------------------
# RECORD 1: Golden Path (Gaborone Central Store) - All Lines PIK/SBO & Zero GL Diff
# -------------------------------------------------------------------------
rec_1 = 'CSH-ADV-2026-00001'
if frappe.db.exists('Daily Cash Advance Check', rec_1):
    frappe.delete_doc('Daily Cash Advance Check', rec_1, force=1)

doc1 = frappe.new_doc('Daily Cash Advance Check')
doc1.name = rec_1
doc1.company = company
doc1.check_date = '2026-11-27'
doc1.branch = 'Gaborone Central Store - EEZZE'
doc1.currency = 'BWP'
doc1.cash_advance_control_account = cash_adv_account

doc1.append('order_lines', {
    'sales_order': so_map.get('Botho Construction (Pty) Ltd', 'SAL-ORD-2026-00006'),
    'customer': 'Botho Construction (Pty) Ltd',
    'order_date': '2026-11-25',
    'item_code': 'CEMENT-50KG',
    'item_name': 'Dangote 42.5N Cement 50kg',
    'qty': 200,
    'advance_amount': 24000.0,
    'line_status': 'PIK (Picking)',
    'is_valid_status': 1,
    'line_issue': 'None - Active Picking List Generated',
    'investigation_notes': 'Stock staged in Warehouse Bay 4. Client transport dispatch scheduled for today.'
})

doc1.append('order_lines', {
    'sales_order': so_map.get('Kgalagadi Mining Services', 'SAL-ORD-2026-00007'),
    'customer': 'Kgalagadi Mining Services',
    'order_date': '2026-11-25',
    'item_code': 'STEEL-12MM',
    'item_name': 'High Tensile Deformed Rebar Y12 6M',
    'qty': 150,
    'advance_amount': 18500.0,
    'line_status': 'SBO (Special Buy / Backorder)',
    'is_valid_status': 1,
    'line_issue': 'None - Special Buy Order Confirmed',
    'investigation_notes': 'Backorder confirmed with ArcelorMittal SA (PO-2026-0081). Stock in transit.'
})

doc1.append('order_lines', {
    'sales_order': so_map.get('Kagisano Property Developers', 'SAL-ORD-2026-00008'),
    'customer': 'Kagisano Property Developers',
    'order_date': '2026-11-26',
    'item_code': 'TIMBER-TRUSS-38X114',
    'item_name': 'Structural Pine Timber 38x114mm 6.0M',
    'qty': 80,
    'advance_amount': 12500.0,
    'line_status': 'PIK (Picking)',
    'is_valid_status': 1,
    'line_issue': 'None - Active Picking List Generated',
    'investigation_notes': 'Yard picking slip #PL-2026-114 issued. Collection arranged by client.'
})

doc1.total_orders_count = 3
doc1.invalid_lines_count = 0
doc1.all_lines_valid = 1
doc1.report_total_amount = 55000.0
doc1.gl_control_balance = 55000.0
doc1.balance_difference = 0.0
doc1.control_agrees = 1
doc1.signed_off = 1
doc1.checked_by = 'Administrator'
doc1.checked_at = '2026-11-27 09:30:00'
doc1.overall_notes = (
    'Morning Routine Verification (SOP-ACC-13): All 3 open customer prepayments verified with active stock reservation '
    'on PIK (Picking) or SBO (Special Buy Order). Cash Advance Control GL balance (BWP 55,000.00) matches Cash Advance Report total exactly. '
    'Zero variance. Reconciled and signed off.'
)

doc1.insert(ignore_permissions=True)
doc1.save()
print("Created record 1:", rec_1)

# -------------------------------------------------------------------------
# RECORD 2: Line Status Exception - Abandoned Order / Not PIK or SBO (Francistown Branch)
# -------------------------------------------------------------------------
rec_2 = 'CSH-ADV-2026-00002'
if frappe.db.exists('Daily Cash Advance Check', rec_2):
    frappe.delete_doc('Daily Cash Advance Check', rec_2, force=1)

doc2 = frappe.new_doc('Daily Cash Advance Check')
doc2.name = rec_2
doc2.company = company
doc2.check_date = '2026-11-27'
doc2.branch = 'Francistown Branch - EEZZE'
doc2.currency = 'BWP'
doc2.cash_advance_control_account = cash_adv_account

doc2.append('order_lines', {
    'sales_order': so_map.get('Francistown General Contractors', 'SAL-ORD-2026-00009'),
    'customer': 'Francistown General Contractors',
    'order_date': '2026-11-24',
    'item_code': 'BRICK-STOCK-MAXI',
    'item_name': 'Cement Maxi Bricks (Load-Bearing)',
    'qty': 3000,
    'advance_amount': 28500.0,
    'line_status': 'PIK (Picking)',
    'is_valid_status': 1,
    'line_issue': 'Compliant',
    'investigation_notes': '3 pallets staged in yard ready for delivery.'
})

doc2.append('order_lines', {
    'sales_order': so_map.get('Tati River Builders', 'SAL-ORD-2026-00010'),
    'customer': 'Tati River Builders',
    'order_date': '2026-11-10',
    'item_code': 'ROOF-IBR-05MM',
    'item_name': 'IBR Galvanised 0.5mm Roof Sheets 6M',
    'qty': 120,
    'advance_amount': 22000.0,
    'line_status': 'ABN (Abandoned)',
    'is_valid_status': 0,
    'line_issue': 'Non-Compliant: Abandoned Order (Not on PIK or SBO for >14 days)',
    'investigation_notes': 'SOP-ACC-13 Step 3 Check: Line is NOT on PIK or SBO. Stock not reserved; client project cancelled.'
})

doc2.total_orders_count = 2
doc2.invalid_lines_count = 1
doc2.all_lines_valid = 0
doc2.report_total_amount = 50500.0
doc2.gl_control_balance = 50500.0
doc2.balance_difference = 0.0
doc2.control_agrees = 1

doc2.branch_manager_contacted = 1
doc2.branch_manager_contacted_by = 'Administrator'
doc2.branch_manager_contacted_at = '2026-11-27 10:15:00'
doc2.branch_manager_notes = (
    'Contacted Francistown Branch Manager per SOP-ACC-13 Step 3: Branch Manager confirmed Tati River Builders halted work '
    'due to site licensing dispute. Order is abandoned. Branch requested customer refund initiation and cancellation of Sales Order.'
)
doc2.order_remedy_action = 'Process Customer Refund & Cancel SO'

doc2.reported_to_fm = 1
doc2.reported_to_fm_at = '2026-11-27 10:45:00'
doc2.fm_decision_notes = (
    'Reported abandoned cash advance line to Finance Manager (L2). FM instructed AP team to raise Customer Refund Request '
    'under P-FIN-14 / SOP-ACC-07 for BWP 22,000.00 and cancel the underlying Sales Order line upon refund clearance.'
)
doc2.overall_notes = 'Escalated to Finance Manager due to non-compliant abandoned order line status (SOP-ACC-13).'

doc2.insert(ignore_permissions=True)
doc2.save()
print("Created record 2:", rec_2)

# -------------------------------------------------------------------------
# RECORD 3: GL Control Discrepancy - Control != Report Total (Palapye Branch)
# -------------------------------------------------------------------------
rec_3 = 'CSH-ADV-2026-00003'
if frappe.db.exists('Daily Cash Advance Check', rec_3):
    frappe.delete_doc('Daily Cash Advance Check', rec_3, force=1)

doc3 = frappe.new_doc('Daily Cash Advance Check')
doc3.name = rec_3
doc3.company = company
doc3.check_date = '2026-11-27'
doc3.branch = 'Palapye Branch - EEZZE'
doc3.currency = 'BWP'
doc3.cash_advance_control_account = cash_adv_account

doc3.append('order_lines', {
    'sales_order': so_map.get('Morupule Commercial Contractors', 'SAL-ORD-2026-00011'),
    'customer': 'Morupule Commercial Contractors',
    'order_date': '2026-11-25',
    'item_code': 'CEMENT-50KG',
    'item_name': 'Dangote 42.5N Cement 50kg',
    'qty': 150,
    'advance_amount': 18000.0,
    'line_status': 'PIK (Picking)',
    'is_valid_status': 1,
    'line_issue': 'Compliant',
    'investigation_notes': 'Picking slip active in warehouse.'
})

doc3.append('order_lines', {
    'sales_order': so_map.get('Palapye Urban Projects', 'SAL-ORD-2026-00012'),
    'customer': 'Palapye Urban Projects',
    'order_date': '2026-11-26',
    'item_code': 'PAVER-INTERLOCK-60',
    'item_name': 'Interlocking Paving Blocks 60mm Grey',
    'qty': 1000,
    'advance_amount': 15000.0,
    'line_status': 'SBO (Special Buy / Backorder)',
    'is_valid_status': 1,
    'line_issue': 'Compliant',
    'investigation_notes': 'Backorder placed on supplier ROCLA Palapye.'
})

doc3.total_orders_count = 2
doc3.invalid_lines_count = 0
doc3.all_lines_valid = 1

# Variance: Report Total 33,000 vs GL Control Balance 30,500 = Variance of +2,500
doc3.report_total_amount = 33000.0
doc3.gl_control_balance = 30500.0
doc3.balance_difference = 2500.0
doc3.control_agrees = 0

doc3.reported_to_fm = 1
doc3.reported_to_fm_at = '2026-11-27 11:20:00'
doc3.fm_decision_notes = (
    'SOP-ACC-13 Step 5 Check Failed: Control account (BWP 30,500.00) does NOT equal Report Total (BWP 33,000.00). '
    'Discrepancy of BWP +2,500.00 reported to Finance Manager (L2). Audit trail showed Palapye branch cashier erroneously '
    'credited General Debtors (1310) instead of Cash Advance Control (2150) for a BWP 2,500 deposit on SO-2026-00107. '
    'FM instructed Senior Accountant to pass adjusting Journal Entry to reclassify BWP 2,500 to Cash Advance Control.'
)
doc3.overall_notes = 'Control vs Report variance (+2,500.00 BWP) reported to Finance Manager for ledger adjustment.'

doc3.insert(ignore_permissions=True)
doc3.save()
print("Created record 3:", rec_3)

frappe.db.commit()
print("All 3 Cash Advance Check seed records created successfully!")
