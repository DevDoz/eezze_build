frappe.ui.form.on('Supplier Reconciliation', {
    refresh: function(frm) {
        update_recon_banner(frm);

        if (!frm.is_new()) {
            // Action 1: Pull Invoices
            if (frm.doc.status === 'Draft' || !frm.doc.items.length) {
                frm.add_custom_button(__('Fetch Invoices & Match (SOP-ACC-06)'), function() {
                    frappe.call({
                        method: 'eezze_build.eezze_build.doctype.supplier_reconciliation.supplier_reconciliation.fetch_unpaid_invoices',
                        args: { docname: frm.doc.name },
                        freeze: true,
                        freeze_message: __('Matching Statement to Supplier Ledger Account...'),
                        callback: function() {
                            frm.reload_doc();
                        }
                    });
                }, __('Reconciliation'));
            }

            // Action 2: Apply Settlement Discount (SOP-ACC-05 Step 4)
            if (frm.doc.items.length && frm.doc.status !== 'Approved & Sent for Payment') {
                frm.add_custom_button(__('Apply Settlement Discount (SOP-ACC-05)'), function() {
                    frappe.prompt([
                        {
                            label: __('Settlement Discount %'),
                            fieldname: 'discount_pct',
                            fieldtype: 'Percent',
                            default: 2.5,
                            reqd: 1
                        }
                    ], function(values) {
                        frappe.call({
                            method: 'eezze_build.eezze_build.doctype.supplier_reconciliation.supplier_reconciliation.apply_settlement_discount',
                            args: { docname: frm.doc.name, discount_pct: values.discount_pct },
                            freeze: true,
                            callback: function() {
                                frm.reload_doc();
                            }
                        });
                    }, __('Apply Settlement Discount (SOP-ACC-05)'), __('Calculate Discount'));
                }, __('Reconciliation'));
            }

            // Action 3: Inform Supplier of Discrepancies (SOP-ACC-06 Step 5)
            if (frm.doc.has_discrepancies && frm.doc.status !== 'Approved & Sent for Payment') {
                frm.add_custom_button(__('Inform Supplier of Discrepancies'), function() {
                    frappe.prompt([
                        {
                            label: __('Discrepancy Details / Supplier Action Required'),
                            fieldname: 'notes',
                            fieldtype: 'Small Text',
                            default: frm.doc.discrepancy_details || 'Differences identified between statement and verified account. Missing invoices / PODs requested.'
                        }
                    ], function(values) {
                        frappe.call({
                            method: 'eezze_build.eezze_build.doctype.supplier_reconciliation.supplier_reconciliation.inform_supplier_of_discrepancies',
                            args: { docname: frm.doc.name, notes: values.notes },
                            freeze: true,
                            callback: function() {
                                frm.reload_doc();
                            }
                        });
                    }, __('Discrepancy Notice (SOP-ACC-06 Step 5)'), __('Send Notice'));
                }, __('Reconciliation'));
            }

            // Action 4: Prepare Remittance & Payment Entry (SOP-ACC-05 Step 6 & 7)
            if (frm.doc.items.length && !frm.doc.payment_entry) {
                frm.add_custom_button(__('Prepare Remittance & Send for Payment (SOP-ACC-05)'), function() {
                    frappe.confirm(
                        __('Are you sure you want to finalize this reconciliation and prepare the payment remittance of {0} {1}?', [frm.doc.currency, frappe.format(frm.doc.net_remittance_amount, {fieldtype: 'Currency'})]),
                        function() {
                            frappe.call({
                                method: 'eezze_build.eezze_build.doctype.supplier_reconciliation.supplier_reconciliation.create_remittance_and_payment_entry',
                                args: { docname: frm.doc.name },
                                freeze: true,
                                freeze_message: __('Generating Remittance & Payment Entry...'),
                                callback: function(r) {
                                    if (r.message) {
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }
                    );
                }, __('Reconciliation'));
            }
        }
    },

    supplier_statement_balance: function(frm) {
        frm.trigger('recalculate_totals');
    },

    recalculate_totals: function(frm) {
        let gross = 0.0;
        let discount = 0.0;
        let net = 0.0;

        (frm.doc.items || []).forEach(item => {
            if (item.matched) {
                const amt = flt(item.erp_amount || item.statement_amount);
                const disc_pct = flt(item.discount_percentage || 0);
                const disc_amt = Math.round(amt * disc_pct) / 100;
                item.discount_amount = disc_amt;
                item.net_payable = Math.round((amt - disc_amt) * 100) / 100;

                gross += amt;
                discount += disc_amt;
                net += item.net_payable;
            }
        });

        frm.set_value('reconciled_invoices_total', gross);
        frm.set_value('total_settlement_discount', discount);
        frm.set_value('net_remittance_amount', net);

        const stmt = flt(frm.doc.supplier_statement_balance || 0);
        frm.set_value('unreconciled_variance', Math.round((stmt - gross) * 100) / 100);
        update_recon_banner(frm);
    }
});

frappe.ui.form.on('Supplier Reconciliation Item', {
    matched: function(frm, cdt, cdn) {
        frm.trigger('recalculate_totals');
    },
    discount_percentage: function(frm, cdt, cdn) {
        frm.trigger('recalculate_totals');
    },
    erp_amount: function(frm, cdt, cdn) {
        frm.trigger('recalculate_totals');
    }
});

function update_recon_banner(frm) {
    if (!frm.dashboard) return;

    if (frm.doc.status === 'Approved & Sent for Payment') {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-success" style="margin-bottom: 0px; padding: 8px 12px;">
                <strong>💳 Remittance Processed & Sent for Payment:</strong> Payment Entry <b>${frm.doc.payment_entry || ''}</b> created for <b>${frm.doc.currency || 'BWP'} ${frappe.format(frm.doc.net_remittance_amount, {fieldtype: 'Currency'})}</b>.
                <div class="small" style="margin-top: 3px;">
                    Gross Invoices: <b>${frm.doc.currency || 'BWP'} ${frappe.format(frm.doc.reconciled_invoices_total, {fieldtype: 'Currency'})}</b> &middot; Settlement Discount: <b>${frm.doc.currency || 'BWP'} ${frappe.format(frm.doc.total_settlement_discount, {fieldtype: 'Currency'})}</b>
                </div>
            </div>`
        );
    } else if (frm.doc.has_discrepancies || frm.doc.status === 'Discrepancy Found - Sent to Supplier') {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-warning" style="margin-bottom: 0px; padding: 8px 12px; background-color: #fff3cd; border-color: #ffeeba; color: #856404;">
                <strong>⚠️ Statement Discrepancy Flagged:</strong> Unreconciled difference of <b>${frm.doc.currency || 'BWP'} ${frappe.format(frm.doc.unreconciled_variance, {fieldtype: 'Currency'})}</b>.
                <div class="small" style="margin-top: 3px;">Follow SOP-ACC-06: Inform supplier of discrepancies / request missing POD or invoice.</div>
            </div>`
        );
    } else if (frm.doc.items && frm.doc.items.length) {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-info" style="margin-bottom: 0px; padding: 8px 12px;">
                <strong>✅ Statement Agrees with Account (Zero Variance):</strong> Reconciled Gross: <b>${frm.doc.currency || 'BWP'} ${frappe.format(frm.doc.reconciled_invoices_total, {fieldtype: 'Currency'})}</b>.
                <div class="small" style="margin-top: 3px;">Ready to apply settlement discount and prepare remittance pack (SOP-ACC-05).</div>
            </div>`
        );
    }
}
