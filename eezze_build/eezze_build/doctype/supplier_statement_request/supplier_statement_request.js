frappe.ui.form.on('Supplier Statement Request', {
    refresh: function(frm) {
        update_statement_banner(frm);

        if (!frm.is_new()) {
            // Step 1 & 2: Send Statement Request Email
            if (frm.doc.statement_status === 'Draft' || !frm.doc.request_sent_date) {
                frm.add_custom_button(__('Send Statement Request (Email)'), function() {
                    frappe.call({
                        method: 'eezze_build.eezze_build.doctype.supplier_statement_request.supplier_statement_request.send_statement_request',
                        args: { docname: frm.doc.name },
                        freeze: true,
                        freeze_message: __('Dispatching Statement Request Email...'),
                        callback: function() {
                            frm.reload_doc();
                        }
                    });
                }, __('Process Actions'));
            }

            // Step 3: Log Call to Confirm Request
            if (frm.doc.statement_status === 'Request Sent' || (!frm.doc.call_confirmed && frm.doc.statement_status !== 'Filed for Reconciliation')) {
                frm.add_custom_button(__('Log Confirmation Call'), function() {
                    frappe.prompt([
                        {
                            label: __('Call Notes / Contact Name'),
                            fieldname: 'notes',
                            fieldtype: 'Small Text',
                            default: 'Spoke with accounts clerk. Statement will be sent by close of business.'
                        }
                    ], function(values) {
                        frappe.call({
                            method: 'eezze_build.eezze_build.doctype.supplier_statement_request.supplier_statement_request.log_phone_call',
                            args: { docname: frm.doc.name, notes: values.notes },
                            freeze: true,
                            callback: function() {
                                frm.reload_doc();
                            }
                        });
                    }, __('Confirm Request by Phone (SOP-ACC-04)'), __('Save Call Log'));
                }, __('Process Actions'));
            }

            // Step 4 (Decision No): Resend Request / Follow-up Loop
            if (['Request Sent', 'Call Confirmed', 'Follow-up Needed'].includes(frm.doc.statement_status) && !frm.doc.statement_file) {
                frm.add_custom_button(__('Resend Request (Follow-up)'), function() {
                    frappe.prompt([
                        {
                            label: __('Follow-up Notes / Reason'),
                            fieldname: 'notes',
                            fieldtype: 'Small Text',
                            default: 'Statement overdue. Second reminder sent and called supplier accounting team.'
                        }
                    ], function(values) {
                        frappe.call({
                            method: 'eezze_build.eezze_build.doctype.supplier_statement_request.supplier_statement_request.resend_follow_up',
                            args: { docname: frm.doc.name, notes: values.notes },
                            freeze: true,
                            callback: function() {
                                frm.reload_doc();
                            }
                        });
                    }, __('Resend Statement Request (SOP-ACC-04 Step 5)'), __('Record Follow-up'));
                }, __('Process Actions'));
            }

            // Step 5: File Statement for Reconciliation
            if (frm.doc.statement_file && frm.doc.statement_status !== 'Filed for Reconciliation') {
                frm.add_custom_button(__('File for Reconciliation'), function() {
                    frappe.prompt([
                        {
                            label: __('Supplier Statement Closing Balance'),
                            fieldname: 'closing_balance',
                            fieldtype: 'Currency',
                            default: frm.doc.statement_closing_balance || frm.doc.outstanding_balance
                        },
                        {
                            label: __('Filing Notes'),
                            fieldname: 'notes',
                            fieldtype: 'Small Text',
                            default: 'Current statement on file. Ready for Finance > Supplier Reconciliation.'
                        }
                    ], function(values) {
                        frappe.call({
                            method: 'eezze_build.eezze_build.doctype.supplier_statement_request.supplier_statement_request.file_statement',
                            args: {
                                docname: frm.doc.name,
                                closing_balance: values.closing_balance,
                                notes: values.notes
                            },
                            freeze: true,
                            callback: function() {
                                frm.reload_doc();
                            }
                        });
                    }, __('File Statement for Reconciliation'), __('Confirm & File'));
                }, __('Process Actions'));
            }
        }
    },

    statement_file: function(frm) {
        if (frm.doc.statement_file && !frm.doc.statement_received_date) {
            frm.set_value('statement_received_date', frappe.datetime.get_today());
            if (frm.doc.statement_status !== 'Filed for Reconciliation') {
                frm.set_value('statement_status', 'Statement Received');
            }
        }
    },

    statement_closing_balance: function(frm) {
        const bal = flt(frm.doc.statement_closing_balance || 0);
        const ledger = flt(frm.doc.outstanding_balance || 0);
        frm.set_value('reconciliation_variance', Math.round((bal - ledger) * 100) / 100);
    }
});

function update_statement_banner(frm) {
    if (!frm.dashboard) return;

    if (frm.doc.statement_status === 'Filed for Reconciliation') {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-success" style="margin-bottom: 0px; padding: 8px 12px;">
                <strong>✅ Statements Ready:</strong> Current supplier statement on file. Hand-off to <b>Finance &rsaquo; Supplier Reconciliation</b> is ready.
                <div class="small text-muted" style="margin-top: 3px;">
                    Statement Closing Balance: <b>${frm.doc.currency || 'BWP'} ${frappe.format(frm.doc.statement_closing_balance, {fieldtype: 'Currency'})}</b> | Variance with Ledger: <b>${frm.doc.currency || 'BWP'} ${frappe.format(frm.doc.reconciliation_variance, {fieldtype: 'Currency'})}</b>
                </div>
            </div>`
        );
    } else if (frm.doc.statement_status === 'Follow-up Needed') {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-warning" style="margin-bottom: 0px; padding: 8px 12px; background-color: #fff3cd; border-color: #ffeeba; color: #856404;">
                <strong>⚠️ Statement Overdue (Follow-up #${frm.doc.follow_up_count || 1}):</strong> Request resent. Please call supplier to confirm dispatch.
                <div class="small" style="margin-top: 3px;">Outstanding Balance: <b>${frm.doc.currency || 'BWP'} ${frappe.format(frm.doc.outstanding_balance, {fieldtype: 'Currency'})}</b></div>
            </div>`
        );
    } else if (frm.doc.statement_status === 'Call Confirmed') {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-info" style="margin-bottom: 0px; padding: 8px 12px; background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">
                <strong>📞 Call Confirmed:</strong> Verbal confirmation received from supplier. Awaiting statement upload.
            </div>`
        );
    } else if (frm.doc.statement_status === 'Request Sent') {
        frm.dashboard.set_headline_alert(
            `<div class="alert alert-info" style="margin-bottom: 0px; padding: 8px 12px;">
                <strong>📧 Request Dispatched:</strong> Statement request email sent. Next step: Call supplier to confirm request (SOP-ACC-04).
            </div>`
        );
    }
}
