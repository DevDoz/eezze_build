import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, today, getdate
from frappe import _

class SupplierReconciliation(Document):
    def validate(self):
        self.fetch_ledger_balance()
        self.calculate_totals()
        self.check_discrepancies()

    def fetch_ledger_balance(self):
        if not self.supplier:
            return
        company = self.company or "EEZZE Build"
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
        self.erp_ledger_balance = round(sum(flt(d.outstanding_amount) for d in invoices), 2)

    def calculate_totals(self):
        gross_total = 0.0
        discount_total = 0.0
        net_total = 0.0

        for item in self.get("items", []):
            if item.matched:
                amt = flt(item.erp_amount or item.statement_amount)
                item.erp_amount = amt
                disc_pct = flt(item.discount_percentage or 0.0)
                disc_amt = round(amt * (disc_pct / 100.0), 2)
                item.discount_amount = disc_amt
                item.net_payable = round(amt - disc_amt, 2)

                gross_total += amt
                discount_total += disc_amt
                net_total += item.net_payable
            else:
                item.discount_amount = 0.0
                item.net_payable = 0.0

        self.reconciled_invoices_total = round(gross_total, 2)
        self.total_settlement_discount = round(discount_total, 2)
        self.net_remittance_amount = round(net_total, 2)

        stmt_bal = flt(self.supplier_statement_balance or 0.0)
        self.unreconciled_variance = round(stmt_bal - self.reconciled_invoices_total, 2)

    def check_discrepancies(self):
        has_disc = False
        notes = []

        if abs(self.unreconciled_variance) > 0.01:
            has_disc = True
            notes.append(f"Statement variance of {self.currency} {self.unreconciled_variance:,.2f} against reconciled invoices.")

        for item in self.get("items", []):
            if not item.matched or item.discrepancy_note:
                has_disc = True
                if item.discrepancy_note:
                    notes.append(f"Invoice {item.invoice_number}: {item.discrepancy_note}")

        self.has_discrepancies = 1 if has_disc else 0
        if notes and not self.discrepancy_details:
            self.discrepancy_details = "\n".join(notes)


@frappe.whitelist()
def fetch_unpaid_invoices(docname):
    """Pulls all outstanding purchase invoices for the supplier up to cutoff date (SOP-ACC-06 Step 1 & 2)"""
    doc = frappe.get_doc("Supplier Reconciliation", docname)
    company = doc.company or "EEZZE Build"

    # Fetch supplier statement request balance if linked
    if doc.statement_request:
        stmt_req = frappe.db.get_value(
            "Supplier Statement Request",
            doc.statement_request,
            ["statement_closing_balance", "outstanding_balance", "statement_file"],
            as_dict=True
        )
        if stmt_req:
            if stmt_req.statement_closing_balance:
                doc.supplier_statement_balance = flt(stmt_req.statement_closing_balance)
            elif stmt_req.outstanding_balance and not doc.supplier_statement_balance:
                doc.supplier_statement_balance = flt(stmt_req.outstanding_balance)

    # Pull outstanding purchase invoices
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "supplier": doc.supplier,
            "company": company,
            "docstatus": 1,
            "outstanding_amount": [">", 0]
        },
        fields=["name", "bill_no", "posting_date", "grand_total", "outstanding_amount"]
    )

    doc.items = []
    for inv in invoices:
        inv_ref = inv.bill_no or inv.name
        doc.append("items", {
            "invoice_number": inv_ref,
            "purchase_invoice": inv.name,
            "invoice_date": inv.posting_date,
            "statement_amount": inv.outstanding_amount,
            "erp_amount": inv.outstanding_amount,
            "matched": 1,
            "discount_percentage": 0.0,
            "discount_amount": 0.0,
            "net_payable": inv.outstanding_amount
        })

    doc.validate()
    doc.save()
    frappe.msgprint(_(f"Fetched {len(invoices)} outstanding invoices for matching."), title=_("Invoices Loaded"))
    return doc.as_dict()


@frappe.whitelist()
def apply_settlement_discount(docname, discount_pct=2.5):
    """Applies settlement discount across matched invoices (SOP-ACC-05 Step 4)"""
    doc = frappe.get_doc("Supplier Reconciliation", docname)
    pct = flt(discount_pct)

    for item in doc.items:
        if item.matched:
            item.discount_percentage = pct

    doc.validate()
    doc.save()
    frappe.msgprint(
        _(f"Applied {pct}% settlement discount. Total discount: {doc.currency} {doc.total_settlement_discount:,.2f}. Net Payable: {doc.currency} {doc.net_remittance_amount:,.2f}"),
        title=_("Settlement Discount Applied")
    )
    return doc.as_dict()


@frappe.whitelist()
def inform_supplier_of_discrepancies(docname, notes=None):
    """Logs discrepancy notification sent to supplier (SOP-ACC-06 Step 5)"""
    doc = frappe.get_doc("Supplier Reconciliation", docname)
    doc.discrepancy_communicated_to_supplier = 1
    doc.status = "Discrepancy Found - Sent to Supplier"
    if notes:
        doc.discrepancy_resolution_notes = (doc.discrepancy_resolution_notes or "") + f"\n[{now_datetime().strftime('%Y-%m-%d %H:%M')}] {notes}"
    doc.save()

    doc.add_comment(
        "Comment",
        text=f"⚠️ <b>Discrepancy Notice Sent to Supplier:</b><br>{doc.discrepancy_details or 'Unreconciled differences flagged'}<br><b>Notes:</b> {notes or 'Supplier asked to provide supporting POD/invoices.'}"
    )
    frappe.msgprint(_("Discrepancies flagged and communicated to supplier."), title=_("Discrepancy Logged"))
    return doc.status


@frappe.whitelist()
def create_remittance_and_payment_entry(docname):
    """Generates Remittance advice and creates draft Payment Entry in ERPNext (SOP-ACC-05 Step 6 & 7)"""
    doc = frappe.get_doc("Supplier Reconciliation", docname)

    if not doc.items:
        frappe.throw(_("No invoice items present to create remittance."))

    if doc.has_discrepancies and not doc.discrepancy_communicated_to_supplier:
        frappe.throw(_("Please communicate discrepancies to the supplier or resolve them before preparing payment remittance."))

    company = doc.company or "EEZZE Build"
    party_account = frappe.db.get_value("Company", company, "default_payable_account") or "Creditors - EEZZE"
    bank_account = doc.bank_account or frappe.db.get_value("Company", company, "default_cash_account") or "Cash - EEZZE"

    # Create Payment Entry
    pe = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Pay",
        "party_type": "Supplier",
        "party": doc.supplier,
        "company": company,
        "posting_date": doc.remittance_date or today(),
        "paid_from": bank_account,
        "paid_to": party_account,
        "paid_amount": doc.net_remittance_amount,
        "received_amount": doc.net_remittance_amount,
        "reference_no": doc.name,
        "reference_date": today(),
        "remarks": f"Remittance Payment per Reconciliation {doc.name}. Total Gross: {doc.reconciled_invoices_total:,.2f}, Discount: {doc.total_settlement_discount:,.2f}, Net: {doc.net_remittance_amount:,.2f}"
    })

    # Allocate against specific invoices
    for item in doc.items:
        if item.matched and item.purchase_invoice:
            pe.append("references", {
                "reference_doctype": "Purchase Invoice",
                "reference_name": item.purchase_invoice,
                "total_amount": item.erp_amount,
                "outstanding_amount": item.erp_amount,
                "allocated_amount": item.net_payable
            })

    # Deductions/Discounts if any
    if doc.total_settlement_discount > 0:
        discount_account = frappe.db.get_value("Company", company, "default_discount_account") or "Cost of Goods Sold - EEZZE"
        pe.append("deductions", {
            "account": discount_account,
            "cost_center": "Main - EEZZE",
            "amount": doc.total_settlement_discount,
            "description": f"Early Settlement Discount per SOP-ACC-05 ({doc.name})"
        })

    pe.insert(ignore_permissions=True)

    doc.payment_entry = pe.name
    doc.status = "Approved & Sent for Payment"
    doc.remittance_notes = f"Remittance prepared and linked to Payment Entry {pe.name}. Net Payment Value: {doc.currency} {doc.net_remittance_amount:,.2f}"
    doc.save()

    doc.add_comment(
        "Comment",
        text=f"💳 <b>Remittance Pack Generated:</b> Payment Entry <a href='/app/payment-entry/{pe.name}'><b>{pe.name}</b></a> created for {doc.currency} {doc.net_remittance_amount:,.2f}. Sent for Payment."
    )

    frappe.msgprint(
        _(f"Remittance successfully prepared! Payment Entry {pe.name} created and sent for payment."),
        title=_("Remittance Ready")
    )
    return {
        "payment_entry": pe.name,
        "status": doc.status
    }
