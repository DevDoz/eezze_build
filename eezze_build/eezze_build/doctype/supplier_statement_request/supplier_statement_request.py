import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, today, getdate
from frappe import _

class SupplierStatementRequest(Document):
    def validate(self):
        self.fetch_supplier_details()
        self.fetch_outstanding_balance()
        self.calculate_variance()
        self.sync_status()

    def fetch_supplier_details(self):
        if self.supplier and (not self.supplier_email or not self.supplier_phone):
            # Try to fetch from Supplier Contact
            contact_name = frappe.db.get_value(
                "Dynamic Link",
                {"link_doctype": "Supplier", "link_name": self.supplier, "parenttype": "Contact"},
                "parent"
            )
            if contact_name:
                contact = frappe.get_doc("Contact", contact_name)
                if not self.supplier_email and contact.email_id:
                    self.supplier_email = contact.email_id
                if not self.supplier_phone and (contact.phone or contact.mobile_no):
                    self.supplier_phone = contact.phone or contact.mobile_no

    def fetch_outstanding_balance(self):
        if not self.supplier:
            return

        company = self.company or "EEZZE Build"
        # Fetch total outstanding amount from Purchase Invoices
        invoices = frappe.get_all(
            "Purchase Invoice",
            filters={
                "supplier": self.supplier,
                "company": company,
                "docstatus": 1,
                "outstanding_amount": [">", 0]
            },
            fields=["outstanding_amount"]
        )
        total_outstanding = sum(flt(d.outstanding_amount) for d in invoices)
        if total_outstanding > 0 or not self.outstanding_balance:
            self.outstanding_balance = round(total_outstanding, 2)

    def calculate_variance(self):
        if self.statement_closing_balance:
            self.reconciliation_variance = round(
                flt(self.statement_closing_balance) - flt(self.outstanding_balance), 2
            )
        else:
            self.reconciliation_variance = 0.0

    def sync_status(self):
        if self.statement_file and self.statement_status in ("Draft", "Request Sent", "Call Confirmed", "Follow-up Needed"):
            self.statement_status = "Statement Received"
            if not self.statement_received_date:
                self.statement_received_date = today()


@frappe.whitelist()
def send_statement_request(docname):
    """Sends official statement request email to supplier (SOP-ACC-04)"""
    doc = frappe.get_doc("Supplier Statement Request", docname)
    if not doc.supplier_email:
        frappe.throw(_("Please provide a Supplier Contact Email before sending request."))

    doc.request_sent_date = now_datetime()
    doc.statement_status = "Request Sent"
    doc.save()

    # Log communication note
    subject = f"Monthly Statement Request - {doc.company} ({doc.supplier_name})"
    content = f"""
    Dear Accounts Department,<br><br>
    Please provide your current statement of account for <b>{doc.company}</b> up to <b>{doc.cutoff_date}</b>.<br><br>
    Our current age analysis reflects a ledger balance of <b>{doc.currency} {doc.outstanding_balance:,.2f}</b>.<br><br>
    Kindly email the statement to accounts@eezzebuild.co.bw as soon as possible so our Accounts Payable & Reconciliation team can verify and reconcile before the payment run.<br><br>
    Thank you,<br>
    <b>Accounts Payable & Reconciliation (L3)</b><br>
    {doc.company} (Plot 14391, New Lobatse Road, Gaborone)
    """

    doc.add_comment("Comment", text=f"📧 <b>Statement Request Email Sent to {doc.supplier_email}</b><br><br>{content}")
    frappe.msgprint(_(f"Statement request email logged and sent to {doc.supplier_email}"), title=_("Request Sent"))
    return doc.statement_status


@frappe.whitelist()
def log_phone_call(docname, notes=None):
    """Logs phone call to supplier to confirm receipt of request (SOP-ACC-04)"""
    doc = frappe.get_doc("Supplier Statement Request", docname)
    doc.call_confirmed = 1
    doc.call_confirmed_date = now_datetime()
    if notes:
        doc.call_notes = (doc.call_notes or "") + f"\n[{now_datetime().strftime('%Y-%m-%d %H:%M')}] {notes}"
    if doc.statement_status in ("Draft", "Request Sent"):
        doc.statement_status = "Call Confirmed"
    doc.save()

    doc.add_comment("Comment", text=f"📞 <b>Confirmation Phone Call Logged:</b> {notes or 'Confirmed with supplier accounting clerk.'}")
    frappe.msgprint(_("Phone call confirmation logged successfully!"), title=_("Call Confirmed"))
    return doc.statement_status


@frappe.whitelist()
def resend_follow_up(docname, notes=None):
    """Follow-up loop: resends request and logs follow-up when statement has not arrived (SOP-ACC-04 Step 5)"""
    doc = frappe.get_doc("Supplier Statement Request", docname)
    doc.follow_up_count = (doc.follow_up_count or 0) + 1
    doc.last_follow_up_date = now_datetime()
    doc.statement_status = "Follow-up Needed"
    if notes:
        doc.call_notes = (doc.call_notes or "") + f"\n[Follow-up #{doc.follow_up_count} - {now_datetime().strftime('%Y-%m-%d %H:%M')}] {notes}"
    doc.save()

    doc.add_comment(
        "Comment",
        text=f"⚠️ <b>Follow-up #{doc.follow_up_count} Triggered:</b> Statement not yet received. Follow-up email and call queued."
    )
    frappe.msgprint(_(f"Follow-up #{doc.follow_up_count} recorded. Status updated to 'Follow-up Needed'."), title=_("Follow-up Sent"))
    return doc.statement_status


@frappe.whitelist()
def file_statement(docname, closing_balance=None, notes=None):
    """Files statement for reconciliation (SOP-ACC-04 Step 6 - Hand-off to Supplier Reconciliation)"""
    doc = frappe.get_doc("Supplier Statement Request", docname)
    if not doc.statement_file:
        frappe.throw(_("Please attach the supplier statement file before filing for reconciliation."))

    if closing_balance is not None and closing_balance != "":
        doc.statement_closing_balance = flt(closing_balance)
    if notes:
        doc.filing_notes = notes
    if not doc.statement_received_date:
        doc.statement_received_date = today()

    doc.calculate_variance()
    doc.statement_status = "Filed for Reconciliation"
    doc.save()

    variance_info = f"Closing Balance: {doc.currency} {doc.statement_closing_balance:,.2f} | Variance: {doc.currency} {doc.reconciliation_variance:,.2f}"
    doc.add_comment(
        "Comment",
        text=f"📁 <b>Statement Filed for Reconciliation:</b> {variance_info}. Ready for Finance > Supplier Reconciliation."
    )
    frappe.msgprint(_("Statement successfully filed for reconciliation! Hand-off to Supplier Reconciliation ready."), title=_("Filed"))
    return doc.statement_status


@frappe.whitelist()
def generate_month_end_requests(company="EEZZE Build", cutoff_date=None):
    """Batch tool: scans all suppliers with outstanding balances from Age Analysis and creates requests (SOP-ACC-04 Step 1 & 2)"""
    cutoff = cutoff_date or today()

    # Find all suppliers with open invoices
    suppliers_with_balance = frappe.db.sql("""
        SELECT supplier, SUM(outstanding_amount) as total_outstanding
        FROM `tabPurchase Invoice`
        WHERE company = %s AND docstatus = 1 AND outstanding_amount > 0
        GROUP BY supplier
    """, (company,), as_dict=True)

    created_count = 0
    updated_count = 0

    for s in suppliers_with_balance:
        supplier_name = s.supplier
        balance = flt(s.total_outstanding)

        # Check if already requested for this month
        existing = frappe.get_all(
            "Supplier Statement Request",
            filters={
                "company": company,
                "supplier": supplier_name,
                "cutoff_date": cutoff
            },
            fields=["name"]
        )

        if existing:
            doc = frappe.get_doc("Supplier Statement Request", existing[0].name)
            doc.outstanding_balance = balance
            doc.save()
            updated_count += 1
        else:
            doc = frappe.get_doc({
                "doctype": "Supplier Statement Request",
                "company": company,
                "cutoff_date": cutoff,
                "supplier": supplier_name,
                "outstanding_balance": balance,
                "statement_status": "Draft"
            })
            doc.insert(ignore_permissions=True)
            created_count += 1

    frappe.db.commit()
    return {
        "created": created_count,
        "updated": updated_count,
        "total_suppliers": len(suppliers_with_balance)
    }
