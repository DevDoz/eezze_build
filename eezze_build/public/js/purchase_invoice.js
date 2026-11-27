frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm) {
        update_dmn_banner(frm);

        if (frm.doc.docstatus === 0) {
            // Action button to run DMN Check
            frm.add_custom_button(__('Check Documents (DMN-ACC-01)'), function() {
                frappe.call({
                    method: 'eezze_build.supplier_invoice.run_dmn_check',
                    args: { docname: frm.doc.name },
                    freeze: true,
                    freeze_message: __('Evaluating DMN-ACC-01 Decision Rules...'),
                    callback: function(r) {
                        if (r.message) {
                            frm.reload_doc();
                            if (r.message.action === 'Register') {
                                frappe.show_alert({
                                    message: __('✅ DMN-ACC-01 Passed: Approved to Register (Zero Variance)'),
                                    indicator: 'green'
                                });
                            } else {
                                frappe.msgprint({
                                    title: __('DMN-ACC-01 Decision: Return to Procurement'),
                                    indicator: 'orange',
                                    message: __('<b>Action:</b> Return to Procurement<br><b>Reason:</b> ' + r.message.note)
                                });
                            }
                        }
                    }
                });
            }, __('Supplier Verification'));

            // Action button to Verify against GRV (SOP-ACC-02)
            if (frm.doc.custom_verification_action === 'Register' && !frm.doc.custom_grv_verified) {
                frm.add_custom_button(__('Verify Against GRV (SOP-ACC-02)'), function() {
                    frm.set_value('custom_grv_verified', 1);
                    frm.save().then(() => {
                        frappe.show_alert({
                            message: __('✅ SOP-ACC-02: Zero Variance Confirmed. Invoice Verified against GRV!'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    });
                }, __('Supplier Verification'));
            }

            // Quick action to Return to Procurement with note
            if (frm.doc.custom_verification_action === 'Return to Procurement') {
                frm.add_custom_button(__('Flag for Procurement Return'), function() {
                    frappe.prompt([
                        {
                            label: __('Return Reason / Notes for Procurement'),
                            fieldname: 'notes',
                            fieldtype: 'Small Text',
                            default: frm.doc.custom_action_note || ''
                        }
                    ], function(values) {
                        frm.set_value('custom_action_note', values.notes);
                        frm.set_value('custom_unpaid_filing_status', 'Returned to Procurement');
                        frm.save().then(() => {
                            frappe.msgprint(__('Invoice marked as Returned to Procurement.'));
                        });
                    }, __('Return Documents to Procurement'));
                }, __('Supplier Verification'));
            }
        }
    },

    custom_signed_pod_received: function(frm) {
        frm.trigger('calculate_dmn');
    },

    custom_tax_invoice_received: function(frm) {
        frm.trigger('calculate_dmn');
    },

    custom_grv_reference: function(frm) {
        if (frm.doc.custom_grv_reference) {
            frappe.db.get_value('Purchase Receipt', frm.doc.custom_grv_reference, ['grand_total', 'custom_signed_pod_attached'])
                .then(r => {
                    if (r && r.message) {
                        frm.set_value('custom_grv_total_amount', r.message.grand_total);
                        if (r.message.custom_signed_pod_attached) {
                            frm.set_value('custom_signed_pod_received', 1);
                        }
                        frm.trigger('calculate_dmn');
                    }
                });
        }
    },

    calculate_dmn: function(frm) {
        const grv_total = flt(frm.doc.custom_grv_total_amount || 0);
        const inv_total = flt(frm.doc.grand_total || 0);
        const variance = Math.round((inv_total - grv_total) * 100) / 100;
        frm.set_value('custom_amount_variance', variance);

        // Client-side quick preview of DMN rules
        if (!frm.doc.custom_tax_invoice_received || !frm.doc.bill_no) {
            frm.set_value('custom_verification_action', 'Return to Procurement');
            frm.set_value('custom_action_note', 'Ask supplier for tax invoice (Tax Invoice missing)');
        } else if (!frm.doc.custom_signed_pod_received) {
            frm.set_value('custom_verification_action', 'Return to Procurement');
            frm.set_value('custom_action_note', 'POD must be signed (Signed delivery note missing from branch)');
        } else if (!frm.doc.custom_grv_reference) {
            frm.set_value('custom_verification_action', 'Return to Procurement');
            frm.set_value('custom_action_note', 'Branch to capture GRV (Goods Received Voucher missing in system)');
        } else if (Math.abs(variance) > 0.01) {
            frm.set_value('custom_verification_action', 'Return to Procurement');
            frm.set_value('custom_action_note', 'GRV correction (Price and Margin Control) - Variance: ' + variance);
        } else {
            frm.set_value('custom_verification_action', 'Register');
            frm.set_value('custom_action_note', 'All documents present and GRV matches invoice with zero variance. Approved to register & verify.');
        }

        update_dmn_banner(frm);
    }
});

function update_dmn_banner(frm) {
    if (!frm.dashboard) return;

    if (frm.doc.custom_verification_action === 'Register') {
        const verified_badge = frm.doc.custom_grv_verified 
            ? ' &middot; <span class="text-success font-weight-bold">Verified against GRV (Zero Variance)</span>' 
            : ' &middot; <span class="text-warning">Ready for Verification</span>';
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-success" style="margin-bottom: 0px; padding: 8px 12px;">
                <strong>✅ DMN-ACC-01 Passed:</strong> Approved to Register ${verified_badge}
                <div class="text-muted small">${frm.doc.custom_action_note || ''}</div>
            </div>`
        );
    } else if (frm.doc.custom_verification_action === 'Return to Procurement') {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-warning" style="margin-bottom: 0px; padding: 8px 12px; background-color: #fff3cd; border-color: #ffeeba; color: #856404;">
                <strong>⚠️ DMN-ACC-01 Incomplete:</strong> Return to Procurement
                <div style="margin-top: 4px;"><strong>Reason:</strong> ${frm.doc.custom_action_note || ''}</div>
            </div>`
        );
    }
}
