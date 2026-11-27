frappe.ui.form.on('Daily Till Closing Check', {
    refresh: function(frm) {
        render_status_banner(frm);
        add_workflow_buttons(frm);
    },

    manager_contacted: function(frm) {
        frm.trigger('eval_dmn');
    },

    reason_given_by_manager: function(frm) {
        frm.trigger('eval_dmn');
    },

    reason_documented: function(frm) {
        frm.trigger('eval_dmn');
    },

    eval_dmn: function(frm) {
        if (!frm.doc.manager_contacted) {
            frm.set_value('dmn_action', 'Pending Check');
            frm.set_value('incident_report_required', 0);
        } else if (!frm.doc.reason_given_by_manager || !frm.doc.reason_documented) {
            frm.set_value('dmn_action', 'Make incident report');
            frm.set_value('incident_report_required', 1);
        } else {
            frm.set_value('dmn_action', 'Accept and recheck next day');
            frm.set_value('incident_report_required', 0);
        }
    }
});

function render_status_banner(frm) {
    if (frm.doc.status === 'Verified & Cleared (Zero Suspense)') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-success">
                <b>✅ P-FIN-16 Verified & Cleared: All Tills Closed & Reconciled (Zero Suspense)</b> — All branch registers closed. Till suspense balance is <b>0.00 BWP</b>.
            </div>`,
            'green'
        );
    } else if (frm.doc.status === 'Incident Report Raised' || frm.doc.incident_report_required) {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-danger">
                <b>⚠️ DMN-ACC-06 Incident Report Required:</b> Unclosed till identified without accepted written documentation. Incident report <b>${frm.doc.incident_report_ref || 'Pending'}</b> raised.
            </div>`,
            'red'
        );
    } else if (frm.doc.status === 'Unclosed Tills Found') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-warning">
                <b>⚠️ SOP-ACC-12 Step 3: ${frm.doc.unclosed_tills_count || 1} Unclosed Till(s) Found</b> — Call branch manager to obtain reason and evaluate DMN-ACC-06.
            </div>`,
            'orange'
        );
    } else if (frm.doc.status === 'Till Suspense Discrepancy Found') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-danger">
                <b>⚠️ SOP-ACC-12 Step 5: Key Rule Violated — Till Suspense is Not Zero (${frm.doc.previous_day_suspense_balance || 0} BWP)</b> — Compare cash-up reports to GL posting items and report discrepancy to Finance Manager.
            </div>`,
            'red'
        );
    } else if (frm.doc.status === 'Closed & Discrepancy Reported to FM') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-info">
                <b>ℹ️ Discrepancy Formally Reported to Finance Manager (L2):</b> Audit investigation completed and logged.
            </div>`,
            'blue'
        );
    }
}

function add_workflow_buttons(frm) {
    if (frm.is_new()) return;

    // 1. Populate standard 5-branch registers
    if (!frm.doc.till_registers || frm.doc.till_registers.length === 0) {
        frm.add_custom_button(__('Populate 5-Branch Tills (Step 1)'), function() {
            frappe.call({
                method: 'eezze_build.eezze_build.doctype.daily_till_closing_check.daily_till_closing_check.populate_all_branch_tills',
                args: { check_name: frm.doc.name },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Loaded registers for all 5 branches.'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Actions')).addClass('btn-secondary');
    }

    // 2. Raise Incident Report (Part 2)
    if (frm.doc.incident_report_required && !frm.doc.incident_report_ref) {
        frm.add_custom_button(__('Raise Incident Report (DMN-ACC-06)'), function() {
            frappe.prompt([
                {
                    fieldname: 'incident_ref',
                    fieldtype: 'Data',
                    label: __('Incident Report Reference'),
                    reqd: 1,
                    default: 'INC-' + frappe.datetime.nowdate().replace(/-/g, '') + '-01'
                },
                {
                    fieldname: 'notes',
                    fieldtype: 'Small Text',
                    label: __('Branch Manager Incident Details / Reason'),
                    reqd: 1,
                    default: frm.doc.manager_reason_notes || 'Cashier departed without performing POS closing.'
                }
            ], function(values) {
                frappe.call({
                    method: 'eezze_build.eezze_build.doctype.daily_till_closing_check.daily_till_closing_check.raise_incident_report_entry',
                    args: {
                        check_name: frm.doc.name,
                        incident_ref: values.incident_ref,
                        notes: values.notes
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Incident report raised and logged.'),
                                indicator: 'red'
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Make Incident Report (Branch Manager L3)'), __('Submit Incident'));
        }, __('Actions')).addClass('btn-danger');
    }

    // 3. Report Discrepancy to Finance Manager (Part 4)
    if (!frm.doc.till_suspense_at_zero && !frm.doc.reported_to_fm) {
        frm.add_custom_button(__('Report Discrepancy to FM (Step 6)'), function() {
            frappe.prompt([
                {
                    fieldname: 'discrepancy_amount',
                    fieldtype: 'Currency',
                    label: __('Discrepancy Amount (BWP)'),
                    reqd: 1,
                    default: Math.abs(frm.doc.previous_day_suspense_balance || 0)
                },
                {
                    fieldname: 'discrepancy_details',
                    fieldtype: 'Small Text',
                    label: __('Cash-Up vs Posting Variance Details'),
                    reqd: 1,
                    default: `Till Suspense balance of BWP ${Math.abs(frm.doc.previous_day_suspense_balance || 0).toFixed(2)} identified between physical cash-up and GL posting.`
                }
            ], function(values) {
                frappe.call({
                    method: 'eezze_build.eezze_build.doctype.daily_till_closing_check.daily_till_closing_check.report_discrepancy_to_fm_entry',
                    args: {
                        check_name: frm.doc.name,
                        discrepancy_details: values.discrepancy_details,
                        discrepancy_amount: values.discrepancy_amount
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Discrepancy formally reported to Finance Manager.'),
                                indicator: 'green'
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Report Discrepancy to Finance Manager (SOP-ACC-12 Step 6)'), __('Send Report'));
        }, __('Actions')).addClass('btn-warning');
    }

    // 4. Sign-Off & Clear Check
    if (frm.doc.status !== 'Verified & Cleared (Zero Suspense)') {
        frm.add_custom_button(__('Sign-Off Morning Check'), function() {
            frappe.call({
                method: 'eezze_build.eezze_build.doctype.daily_till_closing_check.daily_till_closing_check.signoff_till_closing_check',
                args: {
                    check_name: frm.doc.name,
                    notes: 'Morning till closing and posting check completed by AP&R.'
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Check signed off.'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Actions')).addClass('btn-primary');
    }

    // Standard ERPNext POS Closings Shortcut
    frm.add_custom_button(__('View POS Closings'), function() {
        frappe.set_route('List', 'POS Closing Entry');
    }, __('ERP Tools'));
}
