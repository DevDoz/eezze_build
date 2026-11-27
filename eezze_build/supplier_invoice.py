import frappe
from frappe import _

def evaluate_dmn_acc_01(doc):
    """
    Evaluates DMN-ACC-01 Supplier documents complete?
    Decision Table:
    1. Tax invoice missing -> Return to Procurement ('Ask supplier for tax invoice')
    2. Signed delivery note (POD) missing -> Return to Procurement ('POD must be signed')
    3. GRV missing -> Return to Procurement ('Branch to capture GRV')
    4. Purchase order missing -> Return to Procurement ('Missing Purchase Order')
    5. GRV amount vs invoice is Different -> Return to Procurement ('GRV correction (Price and Margin Control)')
    6. All Present and GRV amount == Invoice amount -> Register ('All documents present and GRV matches invoice with zero variance')
    """
    # 1. Infer GRV reference if not set
    if not doc.get("custom_grv_reference"):
        for item in doc.get("items", []):
            if item.get("purchase_receipt"):
                doc.custom_grv_reference = item.purchase_receipt
                break

    # 2. Infer PO reference if not set
    if not doc.get("custom_po_reference"):
        for item in doc.get("items", []):
            if item.get("purchase_order"):
                doc.custom_po_reference = item.purchase_order
                break

    # 3. Calculate GRV Total & Variance
    grv_total = 0.0
    if doc.get("custom_grv_reference"):
        grv = frappe.db.get_value(
            "Purchase Receipt",
            doc.custom_grv_reference,
            ["grand_total", "custom_signed_pod_attached"],
            as_dict=True
        )
        if grv:
            grv_total = float(grv.grand_total or 0.0)
            doc.custom_grv_total_amount = grv_total
            # If signed POD was noted on GRV and not yet checked on PI, sync it
            if grv.custom_signed_pod_attached and not doc.get("custom_signed_pod_received"):
                doc.custom_signed_pod_received = 1
    else:
        doc.custom_grv_total_amount = 0.0

    invoice_total = float(doc.get("grand_total") or 0.0)
    variance = round(invoice_total - grv_total, 2)
    doc.custom_amount_variance = variance

    # 4. Check Attachments to see if scanned document exists
    if not doc.get("custom_scanned_invoice_attached") and doc.name and not doc.is_new():
        files = frappe.get_all("File", filters={"attached_to_doctype": "Purchase Invoice", "attached_to_name": doc.name})
        if files:
            doc.custom_scanned_invoice_attached = 1

    # 5. Evaluate Decision Rules
    # Rule 1: Tax Invoice Missing
    has_tax_invoice = bool(doc.get("custom_tax_invoice_received") and (doc.get("bill_no") or doc.name))
    if not has_tax_invoice:
        doc.custom_verification_action = "Return to Procurement"
        doc.custom_action_note = "Ask supplier for tax invoice (Tax Invoice missing)"
        return

    # Rule 2: Signed POD Missing
    if not doc.get("custom_signed_pod_received"):
        doc.custom_verification_action = "Return to Procurement"
        doc.custom_action_note = "POD must be signed (Signed delivery note missing from branch)"
        return

    # Rule 3: GRV Missing
    if not doc.get("custom_grv_reference"):
        doc.custom_verification_action = "Return to Procurement"
        doc.custom_action_note = "Branch to capture GRV (Goods Received Voucher missing in system)"
        return

    # Rule 4: Purchase Order Missing
    if not doc.get("custom_po_reference"):
        doc.custom_verification_action = "Return to Procurement"
        doc.custom_action_note = "Missing Purchase Order (Cannot verify against unauthorized order)"
        return

    # Rule 5: Amount Variance between GRV and Invoice
    if abs(variance) > 0.01:
        doc.custom_verification_action = "Return to Procurement"
        doc.custom_action_note = f"GRV correction (Price and Margin Control) - Variance: {variance:.2f} {doc.currency or ''}"
        return

    # Rule 6: All Present & Zero Variance -> Register
    doc.custom_verification_action = "Register"
    doc.custom_action_note = "All documents present and GRV matches invoice with zero variance. Approved to register & verify."


def validate_purchase_invoice(doc, method=None):
    """Event hook on Purchase Invoice validation"""
    evaluate_dmn_acc_01(doc)

    # Sync filing status
    if doc.docstatus == 0:
        if doc.custom_verification_action == "Return to Procurement":
            doc.custom_unpaid_filing_status = "Returned to Procurement"
        elif doc.custom_grv_verified:
            doc.custom_unpaid_filing_status = "Pending Verification"
        else:
            doc.custom_unpaid_filing_status = "Draft"


def before_submit_purchase_invoice(doc, method=None):
    """Enforce SOP-ACC-02 before submitting invoice into Unpaid status"""
    evaluate_dmn_acc_01(doc)

    if doc.custom_verification_action != "Register":
        frappe.throw(
            _(f"Cannot post/submit invoice: DMN-ACC-01 Rule triggered '{doc.custom_verification_action}'. Reason: {doc.custom_action_note}"),
            title=_("DMN-ACC-01 Document Check Failed")
        )

    if not doc.custom_grv_verified:
        # Auto-verify if zero variance
        if abs(doc.custom_amount_variance or 0.0) <= 0.01:
            doc.custom_grv_verified = 1
        else:
            frappe.throw(
                _("SOP-ACC-02 Violation: Invoice cannot be accepted with a non-zero variance. Must be zero variance."),
                title=_("SOP-ACC-02 Zero Variance Required")
            )


def on_submit_purchase_invoice(doc, method=None):
    """Once submitted, invoice is filed as Unpaid (ready for payment run)"""
    frappe.db.set_value(
        "Purchase Invoice",
        doc.name,
        "custom_unpaid_filing_status",
        "Verified & Filed Unpaid (Ready for Payment)"
    )


@frappe.whitelist()
def run_dmn_check(docname):
    """Whitelisted method for desk UI quick evaluation"""
    doc = frappe.get_doc("Purchase Invoice", docname)
    evaluate_dmn_acc_01(doc)
    doc.save()
    return {
        "action": doc.custom_verification_action,
        "note": doc.custom_action_note,
        "variance": doc.custom_amount_variance,
        "grv_total": doc.custom_grv_total_amount,
        "grv_verified": doc.custom_grv_verified,
        "status": doc.custom_unpaid_filing_status
    }
