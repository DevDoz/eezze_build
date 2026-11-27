frappe.ui.form.on('Customer Refund Request', {
    refresh: function(frm) {
        render_status_banner(frm);
        add_workflow_buttons(frm);
    },

    credit_note_approved: function(frm) {
        evaluate_dmn(frm);
    },

    original_payment_received: function(frm) {
        evaluate_dmn(frm);
    },

    bank_details_confirmed: function(frm) {
        evaluate_dmn(frm);
    }
});

function evaluate_dmn(frm) {
    if (frm.doc.credit_note_approved && frm.doc.original_payment_received && frm.doc.bank_details_confirmed) {
        frm.set_value('dmn_decision', 'Pay');
    } else if (frm.doc.credit_note_approved || frm.doc.original_payment_received || frm.doc.bank_details_confirmed) {
        frm.set_value('dmn_decision', 'Return to Branch');
    } else {
        frm.set_value('dmn_decision', 'Pending Verification');
    }
}

function render_status_banner(frm) {
    if (frm.doc.status === 'Returned to Branch') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-danger">
                <b>⚠️ DMN-ACC-09 Decision: Returned to Branch</b> — Request rejected and returned to branch/customer returns.
                <br><small><b>Reason:</b> ${frm.doc.return_reason || 'Missing required compliance documentation or uncleared funds.'}</small>
            </div>`,
            'red'
        );
    } else if (frm.doc.status === 'Refund Paid & Filed') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-success">
                <b>✅ P-FIN-14 Completed: Refund Paid & POP Dispatched</b> — Payment posted to Cash Book (Payment Entry: <b>${frm.doc.payment_entry || ''}</b>). POP emailed to customer & branch and archived in Refunds File.
            </div>`,
            'green'
        );
    } else if (frm.doc.status === 'Pending CEO Release') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-warning">
                <b>⚠️ SOP-ACC-07 Dual Control: Pending CEO / MD Release</b> — Payment loaded on online banking by AP&R (L3). Awaiting Executive release before Cash Book posting.
            </div>`,
            'orange'
        );
    } else if (frm.doc.status === 'Pending Online Banking Load') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-info">
                <b>ℹ️ Authorized by FM (L2):</b> Ready for AP&R (L3) to load EFT on online banking (SOP-ACC-07).
            </div>`,
            'blue'
        );
    } else if (frm.doc.dmn_decision === 'Pay') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-primary">
                <b>✅ DMN-ACC-09 Passed: Ready for FM Authorization</b> — Credit note approved, payment received in bank, and customer bank details confirmed.
            </div>`,
            'blue'
        );
    } else {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-muted">
                <b>🔍 DMN-ACC-09 Verification:</b> Verify credit note approval, bank receipt, and customer bank details before payment.
            </div>`,
            'yellow'
        );
    }
}

function add_workflow_buttons(frm) {
    if (frm.is_new()) return;

    // 1. Return to Branch Button (if not already returned or paid)
    if (frm.doc.status !== 'Returned to Branch' && frm.doc.status !== 'Refund Paid & Filed' && !frm.doc.ceo_released) {
        frm.add_custom_button(__('Return Request to Branch'), function() {
            frappe.prompt([
                {
                    fieldname: 'reason',
                    fieldtype: 'Small Text',
                    label: __('Reason for Returning to Branch (What is missing / uncleared)'),
                    reqd: 1,
                    default: frm.doc.return_reason || ''
                }
            ], function(values) {
                frappe.call({
                    method: 'eezze_build.eezze_build.doctype.customer_refund_request.customer_refund_request.return_request_to_branch',
                    args: {
                        refund_request_name: frm.doc.name,
                        reason: values.reason
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Refund request returned to branch.'),
                                indicator: 'red'
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Return Request to Branch (DMN-ACC-09)'), __('Confirm Return'));
        }, __('Process Actions'));
    }

    // 2. Authorise Refund (FM L2)
    if (frm.doc.dmn_decision === 'Pay' && !frm.doc.fm_authorized && frm.doc.status !== 'Returned to Branch') {
        frm.add_custom_button(__('Authorise Refund (FM L2)'), function() {
            frappe.confirm(
                __('Are you sure you want to authorize payment of BWP {0} to customer {1}?', [frm.doc.refund_amount, frm.doc.customer_name]),
                function() {
                    frappe.call({
                        method: 'eezze_build.eezze_build.doctype.customer_refund_request.customer_refund_request.authorize_refund_by_fm',
                        args: { refund_request_name: frm.doc.name },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __('Refund authorized by Finance Manager.'),
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            }
                        }
                    });
                }
            );
        }).addClass('btn-primary');
    }

    // 3. Load on Online Banking (AP&R L3)
    if (frm.doc.fm_authorized && !frm.doc.loaded_on_banking && frm.doc.status !== 'Returned to Branch') {
        frm.add_custom_button(__('Load on Online Banking (AP&R L3)'), function() {
            frappe.prompt([
                {
                    fieldname: 'bank_transfer_ref',
                    fieldtype: 'Data',
                    label: __('Bank EFT Reference / Batch Ref'),
                    reqd: 1,
                    default: frm.doc.bank_transfer_ref || 'EFT-' + frm.doc.name
                }
            ], function(values) {
                frappe.call({
                    method: 'eezze_build.eezze_build.doctype.customer_refund_request.customer_refund_request.load_refund_on_banking',
                    args: {
                        refund_request_name: frm.doc.name,
                        bank_transfer_ref: values.bank_transfer_ref
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Refund loaded on banking and draft Payment Entry created.'),
                                indicator: 'blue'
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Load Refund on Online Banking (SOP-ACC-07)'), __('Confirm Loaded'));
        }).addClass('btn-primary');
    }

    // 4. Release Refund Payment (CEO L1)
    if (frm.doc.loaded_on_banking && !frm.doc.ceo_released && frm.doc.status !== 'Returned to Branch') {
        frm.add_custom_button(__('Release Refund Payment (CEO L1)'), function() {
            frappe.confirm(
                __('Dual Control Maker-Checker: Release payment of BWP {0} (Ref: {1}) and post to Cash Book?', [frm.doc.refund_amount, frm.doc.bank_transfer_ref]),
                function() {
                    frappe.call({
                        method: 'eezze_build.eezze_build.doctype.customer_refund_request.customer_refund_request.release_by_ceo',
                        args: {
                            refund_request_name: frm.doc.name,
                            bank_transfer_ref: frm.doc.bank_transfer_ref
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __('Payment released by CEO and posted to Cash Book!'),
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            }
                        }
                    });
                }
            );
        }).addClass('btn-danger');
    }

    // 5. Send POP to Branch & Customer (SOP-ACC-08)
    if (frm.doc.ceo_released && !frm.doc.pop_sent) {
        frm.add_custom_button(__('Send POP to Branch & Customer (SOP-ACC-08)'), function() {
            if (!frm.doc.pop_file) {
                frappe.msgprint(__('Please attach the Bank Proof of Payment (POP) in the Proof of Payment section before sending.'));
                return;
            }
            frappe.call({
                method: 'eezze_build.eezze_build.doctype.customer_refund_request.customer_refund_request.send_refund_pop',
                args: { refund_request_name: frm.doc.name },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('POP emailed to Customer & Branch, and archived in Refunds File.'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }).addClass('btn-success');
    }

    // Shortcut to view Payment Entry if generated
    if (frm.doc.payment_entry) {
        frm.add_custom_button(__('View Cash Book Payment Entry'), function() {
            frappe.set_route('Form', 'Payment Entry', frm.doc.payment_entry);
        }, __('Links'));
    }
}
