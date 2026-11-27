app_name = "eezze_build"
app_title = "Eezze Build"
app_publisher = "Muhammad Ali Husnain"
app_description = "Custom App for EEZZE Build - Supplier Invoice Registration and Verification (P-FIN-09)"
app_email = "alihusnainmughal215@gmail.com"
app_license = "mit"

# Document Events
# ---------------
doc_events = {
    "Purchase Invoice": {
        "validate": "eezze_build.supplier_invoice.validate_purchase_invoice",
        "before_submit": "eezze_build.supplier_invoice.before_submit_purchase_invoice",
        "on_submit": "eezze_build.supplier_invoice.on_submit_purchase_invoice"
    }
}

# Client scripts in doctype views
# -------------------------------
doctype_js = {
    "Purchase Invoice": "public/js/purchase_invoice.js"
}

# Migration Hooks
# ---------------
after_migrate = "eezze_build.setup.setup_custom_fields"

# Fixtures
# --------
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "in", ["Purchase Invoice", "Purchase Receipt"]]
        ]
    }
]
