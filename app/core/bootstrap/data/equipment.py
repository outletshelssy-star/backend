DEFAULT_EQUIPMENT = [
    {
        "equipment_type": {
            "name": "Termometro Electronico TL1",
            "role": "working",
        },
        "serial": "TL1-001",
        "model": "TL1-100",
        "brand": "Acme",
        "status": "in_use",
        "inspection_days_override": None,
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "c",
                "max_unit": "c",
                "resolution_unit": "c",
                "min_value": 0.0,
                "max_value": 100.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro Electronico TL-1",
            "role": "reference",
        },
        "serial": "TL1-P-001",
        "model": "TL1-100-P",
        "brand": "Acme",
        "status": "in_use",
        "inspection_days_override": None,
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "c",
                "max_unit": "c",
                "resolution_unit": "c",
                "min_value": 0.0,
                "max_value": 100.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro Electronico TL1",
            "role": "reference",
        },
        "serial": "TL1-PAT-001",
        "model": "TL1-100-P",
        "brand": "Acme",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Sabanero",
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "c",
                "max_unit": "c",
                "resolution_unit": "c",
                "min_value": 0.0,
                "max_value": 100.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro de Vidrio",
            "role": "working",
        },
        "serial": "TV-001",
        "model": "TV-100",
        "brand": "Acme",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Sabanero",
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "c",
                "max_unit": "c",
                "resolution_unit": "c",
                "min_value": 0.0,
                "max_value": 100.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro de Vidrio",
            "role": "reference",
        },
        "serial": "TV-PAT-001",
        "model": "TV-200-P",
        "brand": "Omega",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Sabanero",
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "c",
                "max_unit": "c",
                "resolution_unit": "c",
                "min_value": 0.0,
                "max_value": 100.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Cinta Metrica Plomada Fondo",
            "role": "working",
        },
        "serial": "CMPF-W-001",
        "model": "CMPF-W",
        "brand": "Acme",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Sabanero",
        "component_serials": [
            {"component_name": "Cinta", "serial": "CINTA-CMPF-W-001"},
            {"component_name": "Plomada", "serial": "PLOM-CMPF-W-001"},
        ],
        "measure_specs": [
            {
                "measure": "length",
                "min_unit": "mm",
                "max_unit": "mm",
                "resolution_unit": "mm",
                "min_value": 0.0,
                "max_value": 50000.0,
                "resolution": 1.0,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Cinta Metrica Plomada Fondo",
            "role": "reference",
        },
        "serial": "CMPF-P-001",
        "model": "CMPF-P",
        "brand": "Acme",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Sabanero",
        "component_serials": [
            {"component_name": "Cinta", "serial": "CINTA-CMPF-P-001"},
            {"component_name": "Plomada", "serial": "PLOM-CMPF-P-001"},
        ],
        "measure_specs": [
            {
                "measure": "length",
                "min_unit": "mm",
                "max_unit": "mm",
                "resolution_unit": "mm",
                "min_value": 0.0,
                "max_value": 50000.0,
                "resolution": 1.0,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Cinta Metrica Plomada Vacio",
            "role": "working",
        },
        "serial": "CMPV-W-001",
        "model": "CMPV-W",
        "brand": "Acme",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Sabanero",
        "component_serials": [
            {"component_name": "Cinta", "serial": "CINTA-CMPV-W-001"},
            {"component_name": "Plomada", "serial": "PLOM-CMPV-W-001"},
        ],
        "measure_specs": [
            {
                "measure": "length",
                "min_unit": "mm",
                "max_unit": "mm",
                "resolution_unit": "mm",
                "min_value": 0.0,
                "max_value": 50000.0,
                "resolution": 1.0,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Cinta Metrica Plomada Vacio",
            "role": "reference",
        },
        "serial": "CMPV-P-001",
        "model": "CMPV-P",
        "brand": "Acme",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Sabanero",
        "component_serials": [
            {"component_name": "Cinta", "serial": "CINTA-CMPV-P-001"},
            {"component_name": "Plomada", "serial": "PLOM-CMPV-P-001"},
        ],
        "measure_specs": [
            {
                "measure": "length",
                "min_unit": "mm",
                "max_unit": "mm",
                "resolution_unit": "mm",
                "min_value": 0.0,
                "max_value": 50000.0,
                "resolution": 1.0,
            }
        ],
    },
]
