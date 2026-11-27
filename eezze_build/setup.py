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
        ]
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()
    print("Custom fields successfully configured for Eezze Build!")
