import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, flt, getdate

class CustomerRefundRequest(Document):
    def validate(self):
        self.evaluate_dmn_acc_09()
        self.update_status()

    def evaluate_dmn_acc_09(self):
        """
        DMN-ACC-09: Refund can be paid?
        Inputs:
        1. Credit note approved by branch manager? (Yes / No)
        2. Original payment received in bank? (Yes / No - "Do not refund money not yet received")
        3. Customer bank details confirmed? (Yes / No)
        Rules:
        - If any is No -> Return to branch
        - If all are Yes -> Pay
        """
        if self.credit_note_approved and self.original_payment_received and self.bank_details_confirmed:
            self.dmn_decision = "Pay"
        elif self.status == "Returned to Branch":
            self.dmn_decision = "Return to Branch"
        elif not (self.credit_note_approved or self.original_payment_received or self.bank_details_confirmed):
            self.dmn_decision = "Pending Verification"
        else:
            self.dmn_decision = "Return to Branch"

    def update_status(self):
        if self.status == "Returned to Branch":
            return
        
        if self.pop_sent and self.payment_entry:
            self.status = "Refund Paid & Filed"
        elif self.ceo_released and self.payment_entry:
            self.status = "Refund Paid & Filed" if self.pop_sent else "Pending CEO Release"
        elif self.loaded_on_banking:
            self.status = "Pending CEO Release"
        elif self.fm_authorized:
            self.status = "Pending Online Banking Load"
        elif self.dmn_decision == "Pay":
            self.status = "Pending FM Authorization"
        elif self.dmn_decision == "Return to Branch":
            self.status = "Returned to Branch"
        else:
            self.status = "Pending Verification"


@frappe.whitelist()
def return_request_to_branch(refund_request_name, reason):
    """
    P-FIN-14 Hand-off: Return request to branch / Customer Returns
    """
    doc = frappe.get_doc("Customer Refund Request", refund_request_name)
    doc.return_reason = reason
    doc.return_notified = 1
    doc.return_notified_at = now_datetime()
    doc.dmn_decision = "Return to Branch"
    doc.status = "Returned to Branch"
    doc.save()

    # Log in timeline
    doc.add_comment(
        "Comment",
        _("<b>DMN-ACC-09 Return to Branch:</b> Request returned to Branch ({0}) by AP&R.<br><b>Reason:</b> {1}").format(
            doc.branch, reason
        )
    )
    return doc


@frappe.whitelist()
def authorize_refund_by_fm(refund_request_name):
    """
    P-FIN-14 Step: Authorize refund - Finance Manager (L2)
    """
    doc = frappe.get_doc("Customer Refund Request", refund_request_name)
    
    if doc.dmn_decision != "Pay":
        frappe.throw(_("Cannot authorise refund: DMN-ACC-09 conditions not met (Decision must be 'Pay')."))

    doc.fm_authorized = 1
    doc.fm_authorized_by = frappe.session.user
    doc.fm_authorized_at = now_datetime()
    doc.status = "Pending Online Banking Load"
    doc.save()

    doc.add_comment(
        "Comment",
        _("<b>P-FIN-14 Authorized:</b> Refund of BWP {0} authorized by Finance Manager ({1}). Ready for AP&R to load on online banking.").format(
            doc.refund_amount, frappe.session.user
        )
    )
    return doc


@frappe.whitelist()
def load_refund_on_banking(refund_request_name, bank_transfer_ref=None):
    """
    P-FIN-14 Part 2: Load refund on online banking - AP&R (L3) (SOP-ACC-07)
    Creates / links the Payment Entry in Draft state.
    """
    doc = frappe.get_doc("Customer Refund Request", refund_request_name)
    
    if not doc.fm_authorized:
        frappe.throw(_("Cannot load refund on online banking without Finance Manager (L2) authorization."))

    doc.loaded_on_banking = 1
    doc.loaded_by = frappe.session.user
    doc.loaded_at = now_datetime()
    if bank_transfer_ref:
        doc.bank_transfer_ref = bank_transfer_ref

    # Create Payment Entry if not already created
    if not doc.payment_entry:
        pe = create_customer_refund_payment_entry(doc)
        doc.payment_entry = pe.name

    doc.status = "Pending CEO Release"
    doc.save()

    doc.add_comment(
        "Comment",
        _("<b>SOP-ACC-07 Loaded on Banking:</b> Loaded by AP&R ({0}). Reference: {1}. Draft Payment Entry {2} generated. Awaiting CEO/MD release.").format(
            frappe.session.user, doc.bank_transfer_ref or "Pending", doc.payment_entry
        )
    )
    return doc


def create_customer_refund_payment_entry(refund_req):
    """
    Generates standard ERPNext Payment Entry:
    Payment Type: Pay
    Party Type: Customer
    Party: Customer
    Paid From: Bank/Cash
    Paid To: Debtors
    """
    company = refund_req.company or "EEZZE Build"
    
    # Get company bank or cash account
    bank_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Bank", "is_group": 0},
        "name"
    ) or frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Cash", "is_group": 0},
        "name"
    ) or "Cash - EEZZE"

    # Get customer receivable account
    debtors_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Receivable", "is_group": 0},
        "name"
    ) or "Debtors - EEZZE"

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Pay"
    pe.company = company
    pe.posting_date = getdate(refund_req.posting_date)
    pe.party_type = "Customer"
    pe.party = refund_req.customer
    pe.paid_from = bank_account
    pe.paid_to = debtors_account
    pe.paid_amount = flt(refund_req.refund_amount)
    pe.received_amount = flt(refund_req.refund_amount)
    pe.reference_no = refund_req.bank_transfer_ref or refund_req.name
    pe.reference_date = getdate(refund_req.posting_date)
    pe.remarks = f"Customer Refund: {refund_req.name} for {refund_req.customer_name}. Branch: {refund_req.branch}. Bank: {refund_req.bank_name} ({refund_req.bank_account_no})"
    
    # Custom fields if present
    if hasattr(pe, "custom_customer_refund_ref"):
        pe.custom_customer_refund_ref = refund_req.name
    if hasattr(pe, "custom_loaded_by_ap"):
        pe.custom_loaded_by_ap = 1
    if hasattr(pe, "custom_fm_authorized"):
        pe.custom_fm_authorized = 1
        pe.custom_fm_authorized_by = refund_req.fm_authorized_by
        pe.custom_fm_authorized_on = refund_req.fm_authorized_at
    if hasattr(pe, "custom_bank_transfer_ref"):
        pe.custom_bank_transfer_ref = refund_req.bank_transfer_ref

    # Link Credit Note in references if provided
    if refund_req.credit_note and frappe.db.exists("Sales Invoice", refund_req.credit_note):
        pe.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": refund_req.credit_note,
            "total_amount": flt(refund_req.refund_amount),
            "outstanding_amount": flt(refund_req.refund_amount),
            "allocated_amount": flt(refund_req.refund_amount)
        })

    pe.insert(ignore_permissions=True)
    return pe


@frappe.whitelist()
def release_refund_by_ceo(refund_request_name, bank_transfer_ref=None):
    """
    P-FIN-14 Part 2: Release refund payment - CEO / MD (L1) (SOP-ACC-07)
    Dual control maker-checker: Loaded by AP&R -> Released by CEO.
    Submits the Payment Entry into the Cash Book.
    """
    doc = frappe.get_doc("Customer Refund Request", refund_request_name)
    
    if not doc.loaded_on_banking:
        frappe.throw(_("Payment must be loaded on online banking by AP&R before CEO release."))

    doc.ceo_released = 1
    doc.ceo_released_by = frappe.session.user
    doc.ceo_released_at = now_datetime()
    if bank_transfer_ref:
        doc.bank_transfer_ref = bank_transfer_ref

    # Submit linked Payment Entry to Cash Book
    if doc.payment_entry:
        pe = frappe.get_doc("Payment Entry", doc.payment_entry)
        if pe.docstatus == 0:
            if hasattr(pe, "custom_ceo_released"):
                pe.custom_ceo_released = 1
                pe.custom_ceo_released_by = frappe.session.user
                pe.custom_ceo_released_on = now_datetime()
            if hasattr(pe, "custom_bank_transfer_ref") and doc.bank_transfer_ref:
                pe.custom_bank_transfer_ref = doc.bank_transfer_ref
            pe.save(ignore_permissions=True)
            pe.submit()

    doc.status = "Pending CEO Release" if not doc.pop_file else "Refund Paid & Filed"
    doc.save()

    doc.add_comment(
        "Comment",
        _("<b>Dual Control Release:</b> Payment released by CEO/MD ({0}). EFT Reference: {1}. Posted to Cash Book via Payment Entry {2}.").format(
            frappe.session.user, doc.bank_transfer_ref, doc.payment_entry
        )
    )
    return doc


@frappe.whitelist()
def send_refund_pop(refund_request_name):
    """
    P-FIN-14 Part 2: Send POP to branch and customer & File refund documents (SOP-ACC-08)
    """
    doc = frappe.get_doc("Customer Refund Request", refund_request_name)
    
    if not doc.pop_file:
        frappe.throw(_("Please attach the Bank Proof of Payment (POP) before sending."))

    doc.pop_sent = 1
    doc.pop_sent_at = now_datetime()
    doc.status = "Refund Paid & Filed"
    if not doc.filing_notes:
        doc.filing_notes = f"POP, Credit Note ({doc.credit_note}), and original payment filed in Customer Refunds Archive. Dispatched to customer ({doc.customer_email or 'on-file'}) and branch ({doc.branch})."
    doc.save()

    # If linked Payment Entry has pop fields, update them
    if doc.payment_entry:
        pe = frappe.get_doc("Payment Entry", doc.payment_entry)
        if hasattr(pe, "custom_pop_file") and not pe.custom_pop_file:
            pe.custom_pop_file = doc.pop_file
        if hasattr(pe, "custom_pop_sent"):
            pe.custom_pop_sent = 1
            pe.custom_pop_sent_on = now_datetime()
        pe.save(ignore_permissions=True)

    doc.add_comment(
        "Comment",
        _("<b>SOP-ACC-08 POP Dispatched & Filed:</b> Bank POP sent to Customer ({0}) and Branch ({1}). Filed in Customer Refunds Master File.").format(
            doc.customer_name, doc.branch
        )
    )
    return doc
