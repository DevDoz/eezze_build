import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_custom_fields():
    custom_fields = {
        "Purchase Invoice": [
            {
                "fieldname": "supplier_doc_section",
                "label": "Supplier Document Verification (SOP-ACC-01 & DMN-ACC-01)",
                "fieldtype": "Section Break",
                "insert_after": "bill_date",
                "collapsible": 0
            },
            {
                "fieldname": "custom_tax_invoice_received",
                "label": "Tax Invoice Received",
                "fieldtype": "Check",
                "default": "1",
                "insert_after": "supplier_doc_section",
                "description": "Physical / electronic Tax Invoice received from Supplier"
            },
            {
                "fieldname": "custom_signed_pod_received",
                "label": "Signed Delivery Note (POD) Received",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "custom_tax_invoice_received",
                "description": "Delivery note with valid signature from receiving branch"
            },
            {
                "fieldname": "custom_col_break_docs",
                "fieldtype": "Column Break",
                "insert_after": "custom_signed_pod_received"
            },
            {
                "fieldname": "custom_grv_reference",
                "label": "GRV (Purchase Receipt)",
                "fieldtype": "Link",
                "options": "Purchase Receipt",
                "insert_after": "custom_col_break_docs",
                "description": "Goods Received Voucher / Purchase Receipt"
            },
            {
                "fieldname": "custom_po_reference",
                "label": "Purchase Order (PO)",
                "fieldtype": "Link",
                "options": "Purchase Order",
                "insert_after": "custom_grv_reference",
                "description": "Originating Purchase Order"
            },
            {
                "fieldname": "custom_section_break_dmn",
                "label": "DMN-ACC-01 Completeness & Variance Check",
                "fieldtype": "Section Break",
                "insert_after": "custom_po_reference"
            },
            {
                "fieldname": "custom_grv_total_amount",
                "label": "GRV Total Amount",
                "fieldtype": "Currency",
                "options": "currency",
                "read_only": 1,
                "insert_after": "custom_section_break_dmn"
            },
            {
                "fieldname": "custom_amount_variance",
                "label": "GRV vs Invoice Variance",
                "fieldtype": "Currency",
                "options": "currency",
                "read_only": 1,
                "insert_after": "custom_grv_total_amount",
                "description": "Variance = Invoice Grand Total - GRV Total (Must be 0.00 to accept)"
            },
            {
                "fieldname": "custom_col_break_action",
                "fieldtype": "Column Break",
                "insert_after": "custom_amount_variance"
            },
            {
                "fieldname": "custom_verification_action",
                "label": "DMN Decision / Action",
                "fieldtype": "Select",
                "options": "Pending Check\nRegister\nReturn to Procurement",
                "read_only": 1,
                "default": "Pending Check",
                "insert_after": "custom_col_break_action"
            },
            {
                "fieldname": "custom_action_note",
                "label": "Decision Note / Procurement Return Reason",
                "fieldtype": "Small Text",
                "read_only": 1,
                "insert_after": "custom_verification_action"
            },
            {
                "fieldname": "custom_section_break_status",
                "label": "Verification & Filing Status (SOP-ACC-02 & SOP-ACC-03)",
                "fieldtype": "Section Break",
                "insert_after": "custom_action_note"
            },
            {
                "fieldname": "custom_grv_verified",
                "label": "GRV Verified (Zero Variance Confirmed - SOP-ACC-02)",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "custom_section_break_status"
            },
            {
                "fieldname": "custom_scanned_invoice_attached",
                "label": "Scanned Invoice Attached to Supplier Account (SOP-ACC-03)",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "custom_grv_verified"
            },
            {
                "fieldname": "custom_col_break_filing",
                "fieldtype": "Column Break",
                "insert_after": "custom_scanned_invoice_attached"
            },
            {
                "fieldname": "custom_unpaid_filing_status",
                "label": "AP Filing Status",
                "fieldtype": "Select",
                "options": "Draft\nPending Verification\nReturned to Procurement\nVerified & Filed Unpaid (Ready for Payment)\nPaid",
                "default": "Draft",
                "insert_after": "custom_col_break_filing"
            }
        ],
        "Purchase Receipt": [
            {
                "fieldname": "custom_signed_pod_attached",
                "label": "Signed Delivery Note (POD) Attached",
                "fieldtype": "Check",
                "default": "1",
                "insert_after": "title",
                "description": "Signed by Branch Receiving Clerk"
            },
            {
                "fieldname": "custom_supplier_invoice_no",
                "label": "Supplier Advice / Invoice No",
                "fieldtype": "Data",
                "insert_after": "custom_signed_pod_attached"
            }
        ],
        "Payment Entry": [
            {
                "fieldname": "payment_authorization_section",
                "label": "Supplier Payment Dual Control & POP (P-FIN-12)",
                "fieldtype": "Section Break",
                "insert_after": "remarks",
                "collapsible": 0
            },
            {
                "fieldname": "custom_remittance_ref",
                "label": "Remittance Reference (P-FIN-11)",
                "fieldtype": "Link",
                "options": "Supplier Reconciliation",
                "insert_after": "payment_authorization_section"
            },
            {
                "fieldname": "custom_payment_method",
                "label": "Payment Method (EFT / Cheque)",
                "fieldtype": "Select",
                "options": "EFT\nCheque\nCash",
                "default": "EFT",
                "insert_after": "custom_remittance_ref"
            },
            {
                "fieldname": "col_break_auth_1",
                "fieldtype": "Column Break",
                "insert_after": "custom_payment_method"
            },
            {
                "fieldname": "custom_payment_process_status",
                "label": "Payment Release Status",
                "fieldtype": "Select",
                "options": "Draft - Remittance Loaded\nFM Authorized - Pending CEO Release\nCEO Released - Ready for Cash Book\nRecorded in Cash Book\nCompleted - POP Sent & Filed",
                "default": "Draft - Remittance Loaded",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "col_break_auth_1"
            },
            {
                "fieldname": "custom_bank_transfer_ref",
                "label": "Bank EFT Transfer Ref / Cheque No",
                "fieldtype": "Data",
                "insert_after": "custom_payment_process_status"
            },
            {
                "fieldname": "section_dual_control",
                "label": "Dual Control Approvals (Two-person release rule: SOP-ACC-07)",
                "fieldtype": "Section Break",
                "insert_after": "custom_bank_transfer_ref"
            },
            {
                "fieldname": "custom_loaded_by",
                "label": "Loaded By (AP&R L3)",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                "insert_after": "section_dual_control"
            },
            {
                "fieldname": "custom_loaded_on",
                "label": "Loaded On",
                "fieldtype": "Datetime",
                "read_only": 1,
                "insert_after": "custom_loaded_by"
            },
            {
                "fieldname": "custom_fm_authorized",
                "label": "Finance Manager Authorized (L2)",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "custom_loaded_on"
            },
            {
                "fieldname": "custom_fm_authorized_by",
                "label": "FM Authorized By",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                "insert_after": "custom_fm_authorized"
            },
            {
                "fieldname": "custom_fm_authorized_on",
                "label": "FM Authorized On",
                "fieldtype": "Datetime",
                "read_only": 1,
                "insert_after": "custom_fm_authorized_by"
            },
            {
                "fieldname": "col_break_dual_2",
                "fieldtype": "Column Break",
                "insert_after": "custom_fm_authorized_on"
            },
            {
                "fieldname": "custom_ceo_released",
                "label": "CEO / MD Released (L1)",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "col_break_dual_2"
            },
            {
                "fieldname": "custom_ceo_released_by",
                "label": "CEO Released By",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                "insert_after": "custom_ceo_released"
            },
            {
                "fieldname": "custom_ceo_released_on",
                "label": "CEO Released On",
                "fieldtype": "Datetime",
                "read_only": 1,
                "insert_after": "custom_ceo_released_by"
            },
            {
                "fieldname": "section_pop",
                "label": "Proof of Payment (POP) & Filing (SOP-ACC-08)",
                "fieldtype": "Section Break",
                "insert_after": "custom_ceo_released_on"
            },
            {
                "fieldname": "custom_pop_file",
                "label": "Bank Proof of Payment (POP)",
                "fieldtype": "Attach",
                "insert_after": "section_pop"
            },
            {
                "fieldname": "col_break_pop",
                "fieldtype": "Column Break",
                "insert_after": "custom_pop_file"
            },
            {
                "fieldname": "custom_pop_sent",
                "label": "POP Emailed to Supplier (SOP-ACC-08)",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "col_break_pop"
            },
            {
                "fieldname": "custom_pop_sent_on",
                "label": "POP Sent On",
                "fieldtype": "Datetime",
                "read_only": 1,
                "insert_after": "custom_pop_sent"
            },
            {
                "fieldname": "custom_customer_refund_ref",
                "label": "Customer Refund Request (P-FIN-14)",
                "fieldtype": "Link",
                "options": "Customer Refund Request",
                "read_only": 1,
                "insert_after": "custom_pop_sent_on"
            }
        ]
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()

    # Ensure Cash Advance Control Account exists
    if not frappe.db.exists("Account", {"account_name": "Cash Advance Control", "company": "EEZZE Build"}):
        acc = frappe.new_doc("Account")
        acc.account_name = "Cash Advance Control"
        acc.company = "EEZZE Build"
        acc.parent_account = "Current Liabilities - EEZZE"
        acc.account_type = "Temporary"
        acc.account_currency = "BWP"
        acc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Cash Advance Control - EEZZE account")

    print("Custom fields successfully configured for Eezze Build!")
