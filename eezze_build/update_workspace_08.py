import frappe
import json
import os
import sys
sys.path.insert(0, '/Users/ali/FrappeBench/frappeBench/apps/eezze_build')

workspace_file = '/Users/ali/FrappeBench/frappeBench/apps/eezze_build/eezze_build/eezze_build/workspace/eezze_build/eezze_build.json'
fixture_file = '/Users/ali/FrappeBench/frappeBench/apps/eezze_build/eezze_build/fixtures/workspace.json'

with open(workspace_file, 'r') as f:
    ws_data = json.load(f)

# Update content header
content = json.loads(ws_data["content"])
for block in content:
    if block.get("id") == "h_overview":
        block["data"]["text"] = (
            "<span class=\"h3\"><b>Eezze Build — Accounts Payable & Cash Operations</b></span><br>"
            "<span class=\"text-muted small\">Comprehensive 8-Stage End-to-End Suite | Gaborone, Francistown, Mogoditshane, Tlokweng, Palapye</span>"
        )
    elif block.get("id") == "h_cards":
        block["data"]["text"] = (
            "<span class=\"h4\"><b>Accounts Payable & Cash Operations Lifecycle (Stages 01 – 08)</b></span>"
        )

# Add shortcuts to content if not already present
shortcut_ids = [b.get("id") for b in content if b.get("type") == "shortcut"]
if "sc_08_cash_advanc" not in shortcut_ids:
    # insert before sp_2
    sp_2_idx = next(i for i, b in enumerate(content) if b.get("id") == "sp_2")
    content.insert(sp_2_idx, {
        "id": "sc_08_cash_advanc",
        "type": "shortcut",
        "data": {"shortcut_name": "08. Cash Advance Checks (P-FIN-17)", "col": 3}
    })
    content.insert(sp_2_idx + 1, {
        "id": "sc_cash_adv_discr",
        "type": "shortcut",
        "data": {"shortcut_name": "Cash Advance Discrepancies", "col": 3}
    })

# Add card to content if not already present
card_ids = [b.get("id") for b in content if b.get("type") == "card"]
if "c_08_cash_advanc" not in card_ids:
    # insert after c_07_daily_till_
    c07_idx = next(i for i, b in enumerate(content) if b.get("id") == "c_07_daily_till_")
    content.insert(c07_idx + 1, {
        "id": "c_08_cash_advanc",
        "type": "card",
        "data": {"card_name": "08. Daily Cash Advance Check (P-FIN-17)", "col": 6}
    })

ws_data["content"] = json.dumps(content)

# Add Links under links list
# Check if Card Break already exists
has_card_08 = any(l.get("label") == "08. Daily Cash Advance Check (P-FIN-17)" for l in ws_data["links"])
if not has_card_08:
    new_links = [
        {
            "dependencies": None,
            "description": None,
            "hidden": 0,
            "icon": None,
            "is_query_report": 0,
            "label": "08. Daily Cash Advance Check (P-FIN-17)",
            "link_count": 0,
            "link_to": None,
            "link_type": "DocType",
            "onboard": 0,
            "only_for": None,
            "parent": "Eezze Build",
            "parentfield": "links",
            "parenttype": "Workspace",
            "report_ref_doctype": None,
            "type": "Card Break"
        },
        {
            "dependencies": None,
            "description": "Daily routine (SOP-ACC-13): Check order lines on PIK or SBO and reconcile Control GL",
            "hidden": 0,
            "icon": None,
            "is_query_report": 0,
            "label": "Daily Cash Advance Checks (SOP-ACC-13)",
            "link_count": 0,
            "link_to": "Daily Cash Advance Check",
            "link_type": "DocType",
            "onboard": 0,
            "only_for": None,
            "parent": "Eezze Build",
            "parentfield": "links",
            "parenttype": "Workspace",
            "report_ref_doctype": None,
            "type": "Link"
        },
        {
            "dependencies": None,
            "description": "Review sales orders with active customer advances and stock reservation",
            "hidden": 0,
            "icon": None,
            "is_query_report": 0,
            "label": "Sales Orders (Customer Advances)",
            "link_count": 0,
            "link_to": "Sales Order",
            "link_type": "DocType",
            "onboard": 0,
            "only_for": None,
            "parent": "Eezze Build",
            "parentfield": "links",
            "parenttype": "Workspace",
            "report_ref_doctype": None,
            "type": "Link"
        },
        {
            "dependencies": None,
            "description": "Audit Cash Advance Control Account (2150) against branch advance report total",
            "hidden": 0,
            "icon": None,
            "is_query_report": 0,
            "label": "Cash Advance Control Ledger",
            "link_count": 0,
            "link_to": "General Ledger",
            "link_type": "Report",
            "onboard": 0,
            "only_for": None,
            "parent": "Eezze Build",
            "parentfield": "links",
            "parenttype": "Workspace",
            "report_ref_doctype": "GL Entry",
            "type": "Link"
        },
        {
            "dependencies": None,
            "description": "Customer prepayment receipts & advance deposits",
            "hidden": 0,
            "icon": None,
            "is_query_report": 0,
            "label": "Customer Advance Receipts",
            "link_count": 0,
            "link_to": "Payment Entry",
            "link_type": "DocType",
            "onboard": 0,
            "only_for": None,
            "parent": "Eezze Build",
            "parentfield": "links",
            "parenttype": "Workspace",
            "report_ref_doctype": None,
            "type": "Link"
        }
    ]
    # find where to insert: before Branch Receiving & Warehouses Card Break
    insert_idx = len(ws_data["links"])
    for idx, l in enumerate(ws_data["links"]):
        if l.get("label") == "Branch Receiving & Warehouses":
            insert_idx = idx
            break
    for offset, item in enumerate(new_links):
        ws_data["links"].insert(insert_idx + offset, item)

# Add shortcuts
existing_sc_labels = [s.get("label") for s in ws_data["shortcuts"]]
if "08. Cash Advance Checks (P-FIN-17)" not in existing_sc_labels:
    ws_data["shortcuts"].append({
        "color": "Blue",
        "doc_view": "",
        "format": "{} Checks",
        "icon": None,
        "kanban_board": None,
        "label": "08. Cash Advance Checks (P-FIN-17)",
        "link_to": "Daily Cash Advance Check",
        "parent": "Eezze Build",
        "parentfield": "shortcuts",
        "parenttype": "Workspace",
        "report_ref_doctype": None,
        "restrict_to_domain": None,
        "stats_filter": None,
        "type": "DocType",
        "url": None
    })

if "Cash Advance Discrepancies" not in existing_sc_labels:
    ws_data["shortcuts"].append({
        "color": "Red",
        "doc_view": "",
        "format": "{} Discrepant",
        "icon": None,
        "kanban_board": None,
        "label": "Cash Advance Discrepancies",
        "link_to": "Daily Cash Advance Check",
        "parent": "Eezze Build",
        "parentfield": "shortcuts",
        "parenttype": "Workspace",
        "report_ref_doctype": None,
        "restrict_to_domain": None,
        "stats_filter": json.dumps({"status": ["in", ["Invalid Line Status Found", "Control Discrepancy Found", "Discrepancy Reported to Finance Manager"]]}),
        "type": "DocType",
        "url": None
    })

# Write back to workspace json
with open(workspace_file, 'w') as f:
    json.dump(ws_data, f, indent=1)

print("Updated workspace file:", workspace_file)

# Update database workspace
frappe.init(site='eezze.build')
frappe.connect()

if frappe.db.exists('Workspace', 'Eezze Build'):
    ws_doc = frappe.get_doc('Workspace', 'Eezze Build')
    ws_doc.content = ws_data["content"]
    ws_doc.set("links", [])
    for l in ws_data["links"]:
        ws_doc.append("links", l)
    ws_doc.set("shortcuts", [])
    for s in ws_data["shortcuts"]:
        ws_doc.append("shortcuts", s)
    ws_doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Database Workspace Eezze Build updated successfully!")
