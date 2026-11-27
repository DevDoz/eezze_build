frappe.ui.form.on('Daily Cash Advance Check', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Recalculate Status & Totals'), function() {
                frm.save();
            });

            if (!frm.doc.reported_to_fm && (frm.doc.invalid_lines_count > 0 || !frm.doc.control_agrees)) {
                frm.add_custom_button(__('Escalate to Finance Manager'), function() {
                    frappe.prompt([
                        {
                            label: 'Investigation / Escalation Notes for Finance Manager',
                            fieldname: 'notes',
                            fieldtype: 'Small Text',
                            reqd: 1,
                            default: frm.doc.branch_manager_notes || 'Cash advance variance / invalid line status reported per SOP-ACC-13.'
                        }
                    ], function(values) {
                        frm.set_value('reported_to_fm', 1);
                        frm.set_value('reported_to_fm_at', frappe.datetime.now_datetime());
                        frm.set_value('fm_decision_notes', values.notes);
                        frm.save();
                        frappe.msgprint(__('Discrepancy reported to Finance Manager (L2). Status updated.'));
                    }, __('Report to Finance Manager (SOP-ACC-13)'), __('Submit Report'));
                }).addClass('btn-danger');
            }

            if (!frm.doc.signed_off && frm.doc.control_agrees && frm.doc.all_lines_valid) {
                frm.add_custom_button(__('Sign Off Cash Advance Check'), function() {
                    frm.set_value('signed_off', 1);
                    frm.set_value('checked_by', frappe.session.user);
                    frm.set_value('checked_at', frappe.datetime.now_datetime());
                    frm.save();
                    frappe.msgprint(__('Daily Cash Advance Check verified and signed off.'));
                }).addClass('btn-primary');
            }
        }
    },

    branch: function(frm) {
        if (!frm.doc.cash_advance_control_account) {
            frm.set_value('cash_advance_control_account', 'Cash Advance Control - EEZZE');
        }
    }
});
