import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, flt, getdate

class DailyTillClosingCheck(Document):
    def validate(self):
        self.evaluate_registers_status()
        self.evaluate_dmn_acc_06()
        self.evaluate_suspense_status()
        self.update_status()

    def evaluate_registers_status(self):
        unclosed = 0
        total = 0
        for item in self.get("till_registers") or []:
            total += 1
            if item.status in ["Unclosed / Open", "Discrepancy"]:
                unclosed += 1

        self.unclosed_tills_count = unclosed
        if unclosed == 0:
            self.all_tills_closed = 1
            self.registers_summary = f"All {total} branch till registers verified: Tills 1 & 2 closed, Tills 10 & 100 reconciled."
        else:
            self.all_tills_closed = 0
            self.registers_summary = f"⚠️ {unclosed} of {total} branch till registers are unclosed or have discrepancies."

    def evaluate_dmn_acc_06(self):
        """
        DMN-ACC-06: Valid reason given?
        Rules:
        1. Reason given = No -> Make incident report
        2. Reason given = Yes, Reason documented = No -> Make incident report (Reason must be documented)
        3. Reason given = Yes, Reason documented = Yes -> Accept and recheck next day
        """
        if self.unclosed_tills_count == 0:
            self.dmn_action = "Pending Check"
            self.incident_report_required = 0
            return

        if not self.manager_contacted:
            self.dmn_action = "Pending Check"
            self.incident_report_required = 0
        elif not self.reason_given_by_manager:
            self.dmn_action = "Make incident report"
            self.incident_report_required = 1
        elif not self.reason_documented:
            self.dmn_action = "Make incident report"
            self.incident_report_required = 1
        else:
            self.dmn_action = "Accept and recheck next day"
            self.incident_report_required = 0

    def evaluate_suspense_status(self):
        suspense = round(flt(self.previous_day_suspense_balance), 2)
        if abs(suspense) < 0.01:
            self.till_suspense_at_zero = 1
            self.previous_day_suspense_balance = 0.0
        else:
            self.till_suspense_at_zero = 0

    def update_status(self):
        if self.status == "Closed & Discrepancy Reported to FM" and self.reported_to_fm:
            return

        if self.incident_report_ref and self.unclosed_tills_count > 0:
            self.status = "Incident Report Raised"
        elif not self.all_tills_closed:
            self.status = "Unclosed Tills Found"
        elif not self.till_suspense_at_zero or self.discrepancy_amount:
            self.status = "Till Suspense Discrepancy Found"
        elif self.all_tills_closed and self.till_suspense_at_zero:
            self.status = "Verified & Cleared (Zero Suspense)"
        else:
            self.status = "Draft"


@frappe.whitelist()
def populate_all_branch_tills(check_name):
    """
    Populates standard 5 branches with standard registers:
    Till 1 (POS Main), Till 2 (POS Express), Till 10 (Float/Petty), Till 100 (Cash Book)
    """
    doc = frappe.get_doc("Daily Till Closing Check", check_name)
    branches = frappe.get_all(
        "Warehouse",
        filters={"company": doc.company, "name": ["like", "%Branch%"]},
        pluck="name"
    )
    if not branches:
        branches = [
            "Gaborone Central Store - EEZZE",
            "Francistown Branch - EEZZE",
            "Mogoditshane Branch - EEZZE",
            "Tlokweng Branch - EEZZE",
            "Palapye Branch - EEZZE"
        ]

    doc.set("till_registers", [])
    for b in branches:
        # Till 1: POS Main
        doc.append("till_registers", {
            "branch": b,
            "till_name": "Till 1 (POS Main)",
            "till_type": "POS Register (Till 1 & 2)",
            "status": "Closed",
            "closing_doc_ref": f"POS-CLS-{b[:3].upper()}-01"
        })
        # Till 2: POS Express
        doc.append("till_registers", {
            "branch": b,
            "till_name": "Till 2 (POS Express)",
            "till_type": "POS Register (Till 1 & 2)",
            "status": "Closed",
            "closing_doc_ref": f"POS-CLS-{b[:3].upper()}-02"
        })
        # Till 10: Floats / Petty
        doc.append("till_registers", {
            "branch": b,
            "till_name": "Till 10 (Branch Petty/Floats)",
            "till_type": "Cash Book / Banking (Till 10 & 100)",
            "status": "Reconciled",
            "closing_doc_ref": f"PETTY-{b[:3].upper()}-10"
        })
        # Till 100: Banking
        doc.append("till_registers", {
            "branch": b,
            "till_name": "Till 100 (Banking/Cash Book)",
            "till_type": "Cash Book / Banking (Till 10 & 100)",
            "status": "Reconciled",
            "closing_doc_ref": f"BANK-{b[:3].upper()}-100"
        })

    doc.save()
    return doc


@frappe.whitelist()
def raise_incident_report_entry(check_name, incident_ref, notes, file_url=None):
    """
    Part 2: Branch Manager makes Incident Report (DMN-ACC-06)
    """
    doc = frappe.get_doc("Daily Till Closing Check", check_name)
    doc.incident_report_ref = incident_ref
    doc.manager_reason_notes = notes
    if file_url:
        doc.incident_report_file = file_url
    doc.status = "Incident Report Raised"
    doc.save()

    doc.add_comment(
        "Comment",
        _("<b>DMN-ACC-06 Incident Report Raised:</b> Incident report form {0} submitted. Reason: {1}").format(
            incident_ref, notes
        )
    )
    return doc


@frappe.whitelist()
def report_discrepancy_to_fm_entry(check_name, discrepancy_details, discrepancy_amount=0.0):
    """
    Part 4: Report discrepancy to Finance Manager (L2) per SOP-ACC-12 Step 6
    """
    doc = frappe.get_doc("Daily Till Closing Check", check_name)
    doc.discrepancy_details = discrepancy_details
    doc.discrepancy_amount = flt(discrepancy_amount)
    doc.reported_to_fm = 1
    doc.reported_to_fm_at = now_datetime()
    doc.status = "Closed & Discrepancy Reported to FM"
    doc.save()

    doc.add_comment(
        "Comment",
        _("<b>SOP-ACC-12 Step 6 Reported to FM:</b> Discrepancy of BWP {0} formally reported to Finance Manager. Details: {1}").format(
            doc.discrepancy_amount, discrepancy_details
        )
    )
    return doc


@frappe.whitelist()
def signoff_till_closing_check(check_name, notes=None):
    """
    Final signoff by AP&R L3
    """
    doc = frappe.get_doc("Daily Till Closing Check", check_name)
    doc.checked_by = frappe.session.user
    doc.checked_at = now_datetime()
    if notes:
        doc.overall_notes = notes
    if doc.all_tills_closed and doc.till_suspense_at_zero:
        doc.status = "Verified & Cleared (Zero Suspense)"
    doc.save()
    return doc
