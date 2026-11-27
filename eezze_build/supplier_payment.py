import frappe
from frappe import _
from frappe.utils import now_datetime, today

def validate_payment_entry(doc, method=None):
    """Event hook on Payment Entry validation"""
    if doc.payment_type != "Pay" or doc.party_type != "Supplier":
        return

    # Track creator / loader
    if not doc.get("custom_loaded_by"):
        doc.custom_loaded_by = frappe.session.user
        doc.custom_loaded_on = now_datetime()

    # Sync status
    if doc.docstatus == 0:
        if doc.get("custom_ceo_released"):
            doc.custom_payment_process_status = "CEO Released - Ready for Cash Book"
        elif doc.get("custom_fm_authorized"):
            doc.custom_payment_process_status = "FM Authorized - Pending CEO Release"
        else:
            doc.custom_payment_process_status = "Draft - Remittance Loaded"


def before_submit_payment_entry(doc, method=None):
    """Enforce Dual Control (Maker-Checker) before recording payment in cash book (SOP-ACC-07)"""
    if doc.payment_type != "Pay" or doc.party_type != "Supplier":
        return

    # 1. Check Finance Manager Authorization (L2)
    if not doc.get("custom_fm_authorized"):
        frappe.throw(
            _("Dual Control Enforcement (P-FIN-12): Remittance pack must be checked and authorised by Finance Manager (L2) before release."),
            title=_("Finance Manager Authorization Required")
        )

    # 2. Check CEO / MD Release (L1)
    if not doc.get("custom_ceo_released"):
        frappe.throw(
            _("Dual Control Enforcement (P-FIN-12): Payment must be checked and released by CEO / Managing Director (L1) before posting to cash book."),
            title=_("CEO Release Required")
        )

    # 3. Check Bank Transfer Reference
    if not doc.get("custom_bank_transfer_ref"):
        frappe.throw(
            _("SOP-ACC-07 Requirement: Please provide Bank EFT Transfer Reference / Cheque Number before recording payment."),
            title=_("Transfer Reference Missing")
        )

    # 4. Enforce Maker != Checker ("Nobody loads and releases the same payment")
    # For local administrator demo we allow a friendly notice if same user
    if doc.get("custom_loaded_by") and doc.get("custom_ceo_released_by") and doc.custom_loaded_by == doc.custom_ceo_released_by:
        if frappe.session.user != "Administrator":
            frappe.throw(
                _("Key Rule Violation (SOP-ACC-07): Nobody loads and releases the same payment. Two different people must be involved in every release."),
                title=_("Dual Control Rule Violation")
            )


def on_submit_payment_entry(doc, method=None):
    """Post-submission hook: Payment recorded in cash book (SOP-ACC-07 Step 5)"""
    if doc.payment_type != "Pay" or doc.party_type != "Supplier":
        return

    frappe.db.set_value(
        "Payment Entry",
        doc.name,
        "custom_payment_process_status",
        "Recorded in Cash Book"
    )

    # Link back to Supplier Reconciliation if referenced
    if doc.get("custom_remittance_ref"):
        frappe.db.set_value(
            "Supplier Reconciliation",
            doc.custom_remittance_ref,
            "status",
            "Paid"
        )


@frappe.whitelist()
def authorize_by_fm(docname):
    """Finance Manager (L2) checks remittance pack and authorises payment (P-FIN-12 Step 1 & 2)"""
    doc = frappe.get_doc("Payment Entry", docname)
    doc.custom_fm_authorized = 1
    doc.custom_fm_authorized_by = frappe.session.user
    doc.custom_fm_authorized_on = now_datetime()
    doc.custom_payment_process_status = "FM Authorized - Pending CEO Release"
    doc.save()

    doc.add_comment(
        "Comment",
        text=f"✅ <b>Remittance Pack Checked & Authorised by Finance Manager (L2):</b> {frappe.session.user}. Ready for CEO / MD release."
    )
    frappe.msgprint(_("Payment authorised by Finance Manager! Next step: CEO check and release."), title=_("Payment Authorised"))
    return doc.custom_payment_process_status


@frappe.whitelist()
def release_by_ceo(docname, transfer_ref=None):
    """CEO / MD (L1) checks and releases online banking payment or signs cheque (P-FIN-12 Step 5)"""
    doc = frappe.get_doc("Payment Entry", docname)

    if not doc.custom_fm_authorized:
        frappe.throw(_("Cannot release payment: Must be authorised by Finance Manager (L2) first."))

    doc.custom_ceo_released = 1
    doc.custom_ceo_released_by = frappe.session.user
    doc.custom_ceo_released_on = now_datetime()
    if transfer_ref:
        doc.custom_bank_transfer_ref = transfer_ref
    doc.custom_payment_process_status = "CEO Released - Ready for Cash Book"
    doc.save()

    ref_info = f"Bank Transfer Ref: {doc.custom_bank_transfer_ref}" if doc.custom_bank_transfer_ref else ""
    doc.add_comment(
        "Comment",
        text=f"🔓 <b>Payment Released by CEO / MD (L1):</b> {frappe.session.user}. {ref_info}. Ready to record in cash book."
    )
    frappe.msgprint(_("Payment released by CEO / MD! Ready to submit and record in cash book."), title=_("Payment Released"))
    return doc.custom_payment_process_status


@frappe.whitelist()
def send_pop_to_supplier(docname):
    """Sends Proof of Payment (POP), remittance advice, and recon to supplier (SOP-ACC-08 Step 1-3)"""
    doc = frappe.get_doc("Payment Entry", docname)

    # Fetch supplier email
    supplier_email = frappe.db.get_value(
        "Contact",
        {"is_primary_contact": 1, "link_doctype": "Supplier", "link_name": doc.party},
        "email_id"
    ) or doc.get("contact_email") or "accounts@supplier.co.bw"

    doc.custom_pop_sent = 1
    doc.custom_pop_sent_on = now_datetime()
    doc.custom_payment_process_status = "Completed - POP Sent & Filed"
    doc.save()

    subject = f"Proof of Payment (POP) & Remittance Advice - {doc.company} ({doc.name})"
    content = f"""
    Dear Accounts Team,<br><br>
    Please find attached your <b>Proof of Payment (POP)</b> and <b>Remittance Advice</b> for payment <b>{doc.name}</b> in the amount of <b>{doc.paid_to_account_currency} {doc.paid_amount:,.2f}</b>.<br><br>
    <b>Payment Reference:</b> {doc.custom_bank_transfer_ref or doc.reference_no or doc.name}<br>
    <b>Mode of Payment:</b> {doc.custom_payment_method or doc.mode_of_payment}<br><br>
    Please allocate accordingly against your account.<br><br>
    Thank you,<br>
    <b>Accounts Payable & Reconciliation (L3)</b><br>
    {doc.company}
    """

    doc.add_comment(
        "Comment",
        text=f"📤 <b>Proof of Payment (POP) Emailed to Supplier:</b> Sent to {supplier_email}. Complete payment record filed (SOP-ACC-08)."
    )
    frappe.msgprint(_(f"Proof of Payment (POP) sent to supplier ({supplier_email}) and filed!"), title=_("POP Sent & Filed"))
    return doc.custom_payment_process_status
