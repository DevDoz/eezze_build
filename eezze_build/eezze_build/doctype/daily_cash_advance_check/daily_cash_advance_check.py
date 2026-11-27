import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, flt

class DailyCashAdvanceCheck(Document):
    def validate(self):
        self.evaluate_line_statuses()
        self.evaluate_gl_reconciliation()
        self.update_status()

    def evaluate_line_statuses(self):
        """
        SOP-ACC-13 Steps 1-3:
        Review Cash Advance order lines.
        Decision: Lines on PIK (Picking) or SBO (Special Buy / Backorder)?
        Rule: Lines must be on PIK or SBO status.
        If NOT: Call Branch Manager to investigate.
        """
        lines = self.get("order_lines") or []
        total_orders = len(lines)
        invalid_count = 0
        total_advance = 0.0

        for line in lines:
            line_status = (line.line_status or "").strip()
            # Valid statuses are PIK or SBO
            if line_status in ["PIK (Picking)", "SBO (Special Buy / Backorder)"]:
                line.is_valid_status = 1
            else:
                line.is_valid_status = 0
                invalid_count += 1
            
            total_advance += flt(line.advance_amount)

        self.total_orders_count = total_orders
        self.invalid_lines_count = invalid_count
        self.report_total_amount = round(total_advance, 2)

        if total_orders > 0 and invalid_count == 0:
            self.all_lines_valid = 1
            self.line_status_summary = (
                f"✅ All {total_orders} order lines comply with SOP-ACC-13: "
                "Reserved stock is actively on PIK (Picking) or SBO (Special Buy Order)."
            )
        elif invalid_count > 0:
            self.all_lines_valid = 0
            self.line_status_summary = (
                f"⚠️ {invalid_count} of {total_orders} order lines have non-compliant status "
                "(not on PIK or SBO). Branch Manager investigation required."
            )
        else:
            self.all_lines_valid = 0
            self.line_status_summary = "No cash advance orders recorded for this branch today."

    def evaluate_gl_reconciliation(self):
        """
        SOP-ACC-13 Steps 4-5:
        Reconcile Cash Advance Control Account.
        Decision: Control equals report total?
        Key Rule: Closing balance must equal report total.
        If NO: Report difference to Finance Manager (L2).
        """
        report_total = round(flt(self.report_total_amount), 2)
        gl_balance = round(flt(self.gl_control_balance), 2)
        diff = round(report_total - gl_balance, 2)

        self.balance_difference = diff

        if abs(diff) < 0.01:
            self.control_agrees = 1
            self.gl_recon_summary = (
                f"✅ Cash Advance Control Account ({gl_balance:,.2f} BWP) exactly matches "
                f"Cash Advance Report Total ({report_total:,.2f} BWP). Zero variance."
            )
        else:
            self.control_agrees = 0
            self.gl_recon_summary = (
                f"❌ Discrepancy detected: Report total ({report_total:,.2f} BWP) differs from "
                f"GL Control balance ({gl_balance:,.2f} BWP) by {diff:,.2f} BWP. "
                "Escalation to Finance Manager required."
            )

    def update_status(self):
        if self.signed_off:
            self.status = "Verified & Signed Off"
            if not self.checked_at:
                self.checked_at = now_datetime()
            return

        if self.reported_to_fm:
            self.status = "Discrepancy Reported to Finance Manager"
            if not self.reported_to_fm_at:
                self.reported_to_fm_at = now_datetime()
            return

        if self.invalid_lines_count > 0:
            self.status = "Invalid Line Status Found"
        elif not self.control_agrees:
            self.status = "Control Discrepancy Found"
        elif self.all_lines_valid and self.control_agrees:
            self.status = "All Lines Valid & Balanced"
        else:
            self.status = "Draft"


@frappe.whitelist()
def fetch_gl_balance(account, company):
    """Returns current GL balance for the account"""
    gl_entries = frappe.db.sql(
        """
        SELECT SUM(credit - debit) as balance
        FROM `tabGL Entry`
        WHERE account = %s AND company = %s AND is_cancelled = 0
        """,
        (account, company),
        as_dict=True
    )
    if gl_entries and gl_entries[0].balance is not None:
        return flt(gl_entries[0].balance)
    return 0.0
