PRODUCTION_SECTIONS = [
    {
        "section": "fabric_sourcing",
        "required_role": "FABRIC_SUPPLIER",
        "form_fields": ["fabric_type", "fabric_composition", "fabric_weight_gsm"],
    },
    {
        "section": "trims_sourcing",
        "required_role": "TRIM_SUPPLIER",
        "form_fields": ["trim_requirement", "label_requirement"],
    },
    {
        "section": "packaging_sourcing",
        "required_role": "PACKAGING_SUPPLIER",
        "form_fields": ["packaging_requirement"],
    },
    {
        "section": "garment_manufacturing",
        "required_role": "MANUFACTURER",
        "form_fields": ["product_type", "quantity", "pattern_or_cutting_requirement"],
    },
    {
        "section": "qc_inspection",
        "required_role": "QC_INSPECTOR",
        "form_fields": ["qc_standard"],
    },
    {
        "section": "logistics",
        "required_role": "LOGISTICS_PROVIDER",
        "form_fields": ["trade_term", "destination"],
    },
]
