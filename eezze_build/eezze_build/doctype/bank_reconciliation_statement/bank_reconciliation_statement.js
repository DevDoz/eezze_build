frappe.ui.form.on('Bank Reconciliation Statement', {
    refresh: function(frm) {
        render_status_banner(frm);
        add_workflow_buttons(frm);
    },

    bank_statement_closing_balance: function(frm) {
        frm.trigger('calculate_balances');
    },

    gl_book_balance: function(frm) {
        frm.trigger('calculate_balances');
    },

    calculate_balances: function(frm) {
        let unpresented = 0.0;
        let deposits = 0.0;

        (frm.doc.reconciling_items || []).forEach(row => {
            if (!row.reconciled) {
                if ((row.item_type || '').includes('Unpresented') || (row.item_type || '').includes('Direct Debit')) {
                    unpresented += flt(row.amount);
                } else if ((row.item_type || '').includes('Deposit')) {
                    deposits += flt(row.amount);
                }
            }
        });

        frm.set_value('total_unpresented_payments', unpresented);
        frm.set_value('total_deposits_in_transit', deposits);

        let adjusted = flt(frm.doc.bank_statement_closing_balance) - unpresented + deposits;
        frm.set_value('adjusted_bank_balance', adjusted);

        let variance = Math.round((adjusted - flt(frm.doc.gl_book_balance)) * 100) / 100;
        frm.set_value('reconcilable_balance', variance);

        if (Math.abs(variance) < 0.01) {
            frm.set_value('variance_status', 'Balanced (Zero Variance)');
            frm.set_value('suspense_items_found', 0);
            frm.set_value('suspense_amount', 0.0);
        } else {
            frm.set_value('variance_status', `Variance: ${variance.toFixed(2)} BWP (Investigate Suspense)`);
            frm.set_value('suspense_items_found', 1);
            frm.set_value('suspense_amount', Math.abs(variance));
        }
    }
});

function render_status_banner(frm) {
    if (frm.doc.status === 'Reconciled & Filed') {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-success">
                <b>✅ P-FIN-15 Completed: Bank Account Fully Reconciled & Filed</b> — Reconciling items equal the posting with <b>Zero Variance</b>. Official Bank Reconciliation Report filed.
            </div>`,
            'green'
        );
    } else if (frm.doc.status === 'Suspense Under Investigation' || frm.doc.suspense_items_found) {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-danger">
                <b>⚠️ SOP-ACC-10 Step 7: Variance Found (${frm.doc.variance_status || ''})</b> — Post is strictly disabled until the reconcilable balance is zero. Investigate bank suspense account under General Ledger > Posting.
            </div>`,
            'red'
        );
    } else if (frm.doc.status === 'Balanced - Ready to Post' || frm.doc.reconcilable_balance === 0.0) {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-primary">
                <b>✅ Balanced (Zero Variance): Ready to Post</b> — Adjusted bank balance matches GL book balance. Click <b>Post and Print Reconciliation</b> per SOP-ACC-10 Step 6.
            </div>`,
            'blue'
        );
    } else if (!frm.doc.till_100_reconciled) {
        frm.dashboard.clear_headline();
        frm.dashboard.set_headline_alert(
            `<div class="text-warning">
                <b>Step 1 Required:</b> Reconcile and post Till 100 branch registers before bank statement reconciliation.
            </div>`,
            'orange'
        );
    }
}

function add_workflow_buttons(frm) {
    if (frm.is_new()) return;

    // 1. Reconcile Till 100 (Step 1)
    if (!frm.doc.till_100_reconciled) {
        frm.add_custom_button(__('Reconcile Till 100 (Step 1)'), function() {
            frappe.prompt([
                {
                    fieldname: 'notes',
                    fieldtype: 'Small Text',
                    label: __('Branch Till Reconciliation Notes'),
                    default: 'All Gaborone and branch Till 100 registers reconciled into central Cash Book.'
                }
            ], function(values) {
                frappe.call({
                    method: 'eezze_build.eezze_build.doctype.bank_reconciliation_statement.bank_reconciliation_statement.reconcile_till_100',
                    args: {
                        statement_name: frm.doc.name,
                        notes: values.notes
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Till 100 reconciled & confirmed.'),
                                indicator: 'green'
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Reconcile & Post Till 100 (SOP-ACC-10 Step 1)'), __('Confirm Post'));
        }, __('Process Steps')).addClass('btn-secondary');
    }

    // 2. Fetch Reconciling Items (Step 2 & 3)
    if (frm.doc.status !== 'Reconciled & Filed') {
        frm.add_custom_button(__('Fetch ERP Cash Book Entries'), function() {
            frappe.call({
                method: 'eezze_build.eezze_build.doctype.bank_reconciliation_statement.bank_reconciliation_statement.fetch_reconciling_entries',
                args: { statement_name: frm.doc.name },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('ERP Cash Book entries loaded for matching.'),
                            indicator: 'blue'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Process Steps'));
    }

    // 3. Investigate & Resolve Suspense (Step 7)
    if (frm.doc.suspense_items_found && frm.doc.status !== 'Reconciled & Filed') {
        frm.add_custom_button(__('Resolve Suspense Item (Step 7)'), function() {
            frappe.prompt([
                {
                    fieldname: 'correcting_account',
                    fieldtype: 'Link',
                    label: __('Correcting / Expense Account'),
                    options: 'Account',
                    reqd: 1,
                    default: 'Bank Charges - EEZZE'
                },
                {
                    fieldname: 'notes',
                    fieldtype: 'Small Text',
                    label: __('Investigation Findings / Correcting Notes'),
                    reqd: 1,
                    default: `Bank Service Charge of BWP ${frm.doc.suspense_amount.toFixed(2)} investigated. Adjusting entry posted.`
                }
            ], function(values) {
                frappe.call({
                    method: 'eezze_build.eezze_build.doctype.bank_reconciliation_statement.bank_reconciliation_statement.resolve_suspense_entry',
                    args: {
                        statement_name: frm.doc.name,
                        correcting_account: values.correcting_account,
                        notes: values.notes
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Suspense entry resolved and variance cleared.'),
                                indicator: 'green'
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Investigate Bank Suspense (SOP-ACC-10 Step 7)'), __('Post Correction'));
        }, __('Process Steps')).addClass('btn-warning');
    }

    // 4. Post and Print Reconciliation (Step 6)
    if (frm.doc.status !== 'Reconciled & Filed') {
        frm.add_custom_button(__('Post & Print Reconciliation (Step 6)'), function() {
            if (Math.abs(frm.doc.reconcilable_balance) > 0.01) {
                frappe.msgprint({
                    title: __('Cannot Post Reconciliation'),
                    indicator: 'red',
                    message: __('<b>Key Rule Violation:</b> Reconciling items must equal the posting (Variance must be 0.00 BWP). Current variance: <b>{0} BWP</b>.<br>Please investigate bank suspense under Step 7.', [frm.doc.reconcilable_balance])
                });
                return;
            }

            frappe.confirm(
                __('Are you sure you want to post the balanced Bank Reconciliation and generate the formal report?'),
                function() {
                    frappe.call({
                        method: 'eezze_build.eezze_build.doctype.bank_reconciliation_statement.bank_reconciliation_statement.post_and_print_reconciliation',
                        args: { statement_name: frm.doc.name },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __('Bank Reconciliation posted and report filed!'),
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

    // Interactive ERPNext Tool Shortcut
    frm.add_custom_button(__('Open Bank Reconciliation Tool'), function() {
        frappe.set_route('bank-reconciliation-tool');
    }, __('ERP Tools'));

    frm.add_custom_button(__('Open Bank Clearance'), function() {
        frappe.set_route('Form', 'Bank Clearance');
    }, __('ERP Tools'));
}
