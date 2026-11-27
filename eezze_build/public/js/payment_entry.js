frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        if (frm.doc.payment_type !== 'Pay' || frm.doc.party_type !== 'Supplier') {
            return;
        }

        update_payment_banner(frm);

        // Action 1: Finance Manager Authorization (L2)
        if (frm.doc.docstatus === 0 && !frm.doc.custom_fm_authorized) {
            frm.add_custom_button(__('Authorise Remittance (FM L2)'), function() {
                frappe.call({
                    method: 'eezze_build.supplier_payment.authorize_by_fm',
                    args: { docname: frm.doc.name },
                    freeze: true,
                    callback: function() {
                        frm.reload_doc();
                    }
                });
            }, __('Dual Control'));
        }

        // Action 2: CEO / MD Release (L1)
        if (frm.doc.docstatus === 0 && frm.doc.custom_fm_authorized && !frm.doc.custom_ceo_released) {
            frm.add_custom_button(__('Release Payment (CEO L1)'), function() {
                frappe.prompt([
                    {
                        label: __('Bank EFT Transfer Ref / Cheque No'),
                        fieldname: 'transfer_ref',
                        fieldtype: 'Data',
                        default: frm.doc.custom_bank_transfer_ref || 'EFT-' + frappe.datetime.now_datetime().slice(0, 10).replace(/-/g, '') + '-01',
                        reqd: 1
                    }
                ], function(values) {
                    frappe.call({
                        method: 'eezze_build.supplier_payment.release_by_ceo',
                        args: { docname: frm.doc.name, transfer_ref: values.transfer_ref },
                        freeze: true,
                        callback: function() {
                            frm.reload_doc();
                        }
                    });
                }, __('Release Payment (Dual Control - CEO/MD)'), __('Authorize Release'));
            }, __('Dual Control'));
        }

        // Action 3: Send POP to Supplier (SOP-ACC-08)
        if (frm.doc.docstatus === 1 && !frm.doc.custom_pop_sent) {
            frm.add_custom_button(__('Send POP to Supplier (SOP-ACC-08)'), function() {
                frappe.call({
                    method: 'eezze_build.supplier_payment.send_pop_to_supplier',
                    args: { docname: frm.doc.name },
                    freeze: true,
                    freeze_message: __('Dispatching Proof of Payment & Remittance Advice...'),
                    callback: function() {
                        frm.reload_doc();
                    }
                });
            }, __('Filing & POP'));
        }
    }
});

function update_payment_banner(frm) {
    if (!frm.dashboard) return;

    if (frm.doc.custom_payment_process_status === 'Completed - POP Sent & Filed') {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-success" style="margin-bottom: 0px; padding: 8px 12px;">
                <strong>✅ Payment Completed & Filed:</strong> Recorded in cash book and Proof of Payment (POP) emailed to supplier.
                <div class="small" style="margin-top: 3px;">
                    Bank Transfer Ref: <b>${frm.doc.custom_bank_transfer_ref || 'N/A'}</b> &middot; Released by: <b>${frm.doc.custom_ceo_released_by || 'CEO'}</b>
                </div>
            </div>`
        );
    } else if (frm.doc.docstatus === 1) {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-info" style="margin-bottom: 0px; padding: 8px 12px;">
                <strong>💳 Recorded in Cash Book:</strong> Payment entry submitted. Next step: Click <b>Send POP to Supplier (SOP-ACC-08)</b>.
            </div>`
        );
    } else if (frm.doc.custom_ceo_released) {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-success" style="margin-bottom: 0px; padding: 8px 12px;">
                <strong>🔓 Dual Control Approved:</strong> Released by CEO / MD (L1). Ready to Submit & Record in Cash Book (SOP-ACC-07).
                <div class="small" style="margin-top: 3px;">Bank Transfer Ref: <b>${frm.doc.custom_bank_transfer_ref || ''}</b></div>
            </div>`
        );
    } else if (frm.doc.custom_fm_authorized) {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-warning" style="margin-bottom: 0px; padding: 8px 12px; background-color: #fff3cd; border-color: #ffeeba; color: #856404;">
                <strong>⏳ Dual Control: Pending CEO Release:</strong> Checked & authorised by Finance Manager (L2). Awaiting final release by CEO / MD (L1).
            </div>`
        );
    } else {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-warning" style="margin-bottom: 0px; padding: 8px 12px; background-color: #fff3cd; border-color: #ffeeba; color: #856404;">
                <strong>⚠️ Dual Control Required (P-FIN-12):</strong> Remittance loaded by AP&R (L3). Awaiting Finance Manager (L2) check & authorisation.
            </div>`
        );
    }
}
