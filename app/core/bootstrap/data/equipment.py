from typing import NotRequired, TypedDict


class EquipmentTypeRefSeed(TypedDict):
    name: str
    role: str


class MeasureSpecSeed(TypedDict):
    measure: str
    min_unit: str
    max_unit: str
    resolution_unit: str
    min_value: float
    max_value: float
    resolution: float | None


class ComponentSerialSeed(TypedDict):
    component_name: str
    serial: str


class EquipmentSeed(TypedDict):
    equipment_type: EquipmentTypeRefSeed
    serial: str
    model: str
    brand: str
    status: str
    inspection_days_override: int | None
    measure_specs: list[MeasureSpecSeed]
    terminal: NotRequired[str]
    component_serials: NotRequired[list[ComponentSerialSeed]]
    weight_class: NotRequired[str]
    nominal_mass_value: NotRequired[float]
    nominal_mass_unit: NotRequired[str]
    emp_value: NotRequired[float]


DEFAULT_EQUIPMENT: list[EquipmentSeed] = [
    # {
    #     "equipment_type": {
    #         "name": "Termometro Electronico TL1",
    #         "role": "working",
    #     },
    #     "serial": "TL1-001",
    #     "model": "TL1-100",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "measure_specs": [
    #         {
    #             "measure": "temperature",
    #             "min_unit": "c",
    #             "max_unit": "c",
    #             "resolution_unit": "c",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Termometro Electronico TL-1",
    #         "role": "reference",
    #     },
    #     "serial": "TL1-P-001",
    #     "model": "TL1-100-P",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "measure_specs": [
    #         {
    #             "measure": "temperature",
    #             "min_unit": "c",
    #             "max_unit": "c",
    #             "resolution_unit": "c",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Termometro Electronico TL1",
    #         "role": "reference",
    #     },
    #     "serial": "TL1-PAT-001",
    #     "model": "TL1-100-P",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "measure_specs": [
    #         {
    #             "measure": "temperature",
    #             "min_unit": "c",
    #             "max_unit": "c",
    #             "resolution_unit": "c",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Termometro de Vidrio",
    #         "role": "working",
    #     },
    #     "serial": "TV-001",
    #     "model": "TV-100",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "measure_specs": [
    #         {
    #             "measure": "temperature",
    #             "min_unit": "c",
    #             "max_unit": "c",
    #             "resolution_unit": "c",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Termometro de Vidrio",
    #         "role": "reference",
    #     },
    #     "serial": "TV-PAT-001",
    #     "model": "TV-200-P",
    #     "brand": "Omega",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "measure_specs": [
    #         {
    #             "measure": "temperature",
    #             "min_unit": "c",
    #             "max_unit": "c",
    #             "resolution_unit": "c",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Fondo",
    #         "role": "working",
    #     },
    #     "serial": "CMPF-W-001",
    #     "model": "CMPF-W",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "component_serials": [
    #         {"component_name": "Cinta", "serial": "CINTA-CMPF-W-001"},
    #         {"component_name": "Plomada", "serial": "PLOM-CMPF-W-001"},
    #     ],
    #     "measure_specs": [
    #         {
    #             "measure": "length",
    #             "min_unit": "mm",
    #             "max_unit": "mm",
    #             "resolution_unit": "mm",
    #             "min_value": 0.0,
    #             "max_value": 50000.0,
    #             "resolution": 1.0,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Fondo",
    #         "role": "reference",
    #     },
    #     "serial": "CMPF-P-001",
    #     "model": "CMPF-P",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "component_serials": [
    #         {"component_name": "Cinta", "serial": "CINTA-CMPF-P-001"},
    #         {"component_name": "Plomada", "serial": "PLOM-CMPF-P-001"},
    #     ],
    #     "measure_specs": [
    #         {
    #             "measure": "length",
    #             "min_unit": "mm",
    #             "max_unit": "mm",
    #             "resolution_unit": "mm",
    #             "min_value": 0.0,
    #             "max_value": 50000.0,
    #             "resolution": 1.0,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Vacio",
    #         "role": "working",
    #     },
    #     "serial": "CMPV-W-001",
    #     "model": "CMPV-W",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "component_serials": [
    #         {"component_name": "Cinta", "serial": "CINTA-CMPV-W-001"},
    #         {"component_name": "Plomada", "serial": "PLOM-CMPV-W-001"},
    #     ],
    #     "measure_specs": [
    #         {
    #             "measure": "length",
    #             "min_unit": "mm",
    #             "max_unit": "mm",
    #             "resolution_unit": "mm",
    #             "min_value": 0.0,
    #             "max_value": 50000.0,
    #             "resolution": 1.0,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Vacio",
    #         "role": "reference",
    #     },
    #     "serial": "CMPV-P-001",
    #     "model": "CMPV-P",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "component_serials": [
    #         {"component_name": "Cinta", "serial": "CINTA-CMPV-P-001"},
    #         {"component_name": "Plomada", "serial": "PLOM-CMPV-P-001"},
    #     ],
    #     "measure_specs": [
    #         {
    #             "measure": "length",
    #             "min_unit": "mm",
    #             "max_unit": "mm",
    #             "resolution_unit": "mm",
    #             "min_value": 0.0,
    #             "max_value": 50000.0,
    #             "resolution": 1.0,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Fondo",
    #         "role": "working",
    #     },
    #     "serial": "09171943-50",
    #     "model": "CN1290SMEF590GME",
    #     "brand": "LUFKIN",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Greta Oto",
    #     "component_serials": [
    #         {"component_name": "Cinta", "serial": "09171943-50"},
    #         {"component_name": "Plomada", "serial": "09171943-50"},
    #     ],
    #     "measure_specs": [
    #         {
    #             "measure": "length",
    #             "min_unit": "mm",
    #             "max_unit": "mm",
    #             "resolution_unit": "mm",
    #             "min_value": 0.0,
    #             "max_value": 15000.0,
    #             "resolution": 1.0,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Hidrometro",
    #         "role": "reference",
    #     },
    #     "serial": "HID-PAT-001",
    #     "model": "HID-100-P",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "measure_specs": [
    #         {
    #             "measure": "api",
    #             "min_unit": "api",
    #             "max_unit": "api",
    #             "resolution_unit": "api",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         }
    #     ],
    # },
    {
        "equipment_type": {
            "name": "Termometro Electronico TP7 / TP9",
            "role": "working",
        },
        "serial": "7C-15055",
        "model": "TP7-C",
        "brand": "THERMOPROBE",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Greta Oto",
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "c",
                "max_unit": "c",
                "resolution_unit": "c",
                "min_value": 0.0,
                "max_value": 184.0,
                "resolution": 0.01,
            }
        ],
    },
    # {
    #     "equipment_type": {
    #         "name": "Hidrometro",
    #         "role": "working",
    #     },
    #     "serial": "HID-W-001",
    #     "model": "HID-200-W",
    #     "brand": "Omega",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "measure_specs": [
    #         {
    #             "measure": "api",
    #             "min_unit": "api",
    #             "max_unit": "api",
    #             "resolution_unit": "api",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         }
    #     ],
    # },
    {
        "equipment_type": {
            "name": "Balanza Analitica",
            "role": "working",
        },
        "serial": "B112122606",
        "model": "ML 204",
        "brand": "METTLER TOLEDO",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "measure_specs": [
            {
                "measure": "weight",
                "min_unit": "g",
                "max_unit": "g",
                "resolution_unit": "g",
                "min_value": 0.01,
                "max_value": 220.0,
                "resolution": 0.0001,
            }
        ],
    },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Fondo",
    #         "role": "reference",
    #     },
    #     "serial": "SN-1968",
    #     "model": "CN1290SMEN",
    #     "brand": "LUFKIN",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "component_serials": [
    #         {"component_name": "Cinta", "serial": "SN-1968"},
    #         {"component_name": "Plomada", "serial": "SN-1968"},
    #     ],
    #     "measure_specs": [
    #         {
    #             "measure": "length",
    #             "min_unit": "mm",
    #             "max_unit": "mm",
    #             "resolution_unit": "mm",
    #             "min_value": 0.0,
    #             "max_value": 15000.0,
    #             "resolution": 1.0,
    #         }
    #     ],
    # },
    {
        "equipment_type": {
            "name": "Hidrometro",
            "role": "reference",
        },
        "serial": "201366",
        "model": "3H",
        "brand": "ALLA FRANCE",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "measure_specs": [
            {
                "measure": "api",
                "min_unit": "api",
                "max_unit": "api",
                "resolution_unit": "api",
                "min_value": 19.0,
                "max_value": 31.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro de Vidrio",
            "role": "working",
        },
        "serial": "15999",
        "model": "ASTM 12F-98/ IP64F",
        "brand": "LSW",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "f",
                "max_unit": "f",
                "resolution_unit": "f",
                "min_value": -5.0,
                "max_value": 215.0,
                "resolution": 0.5,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro Electronico TL1",
            "role": "reference",
        },
        "serial": "1-21280",
        "model": "TL1-A",
        "brand": "THERMOPROBE",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "f",
                "max_unit": "f",
                "resolution_unit": "f",
                "min_value": -4.0,
                "max_value": 300.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro Electronico TP7 / TP9",
            "role": "working",
        },
        "serial": "7D-32833",
        "model": "TP7-D",
        "brand": "THERMOPROBE",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "measure_specs": [
            {
                "measure": "temperature",
                "min_unit": "f",
                "max_unit": "f",
                "resolution_unit": "f",
                "min_value": -40.0,
                "max_value": 400.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "Titulador Karl Fischer",
            "role": "working",
        },
        "serial": "10016694",
        "model": "TITROLINE 7500 KF",
        "brand": "SI ANALYTICS",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "measure_specs": [
            {
                "measure": "percent_pv",
                "min_unit": "%p/v",
                "max_unit": "%p/v",
                "resolution_unit": "%p/v",
                "min_value": 0.002,
                "max_value": 2.0,
                "resolution": 0.0001,
            }
        ],
    },
    # {
    #     "equipment_type": {
    #         "name": "TermoHigrometro",
    #         "role": "working",
    #     },
    #     "serial": "TH-HTZ-001",
    #     "model": "TH-200",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "measure_specs": [
    #         {
    #             "measure": "relative_humidity",
    #             "min_unit": "%",
    #             "max_unit": "%",
    #             "resolution_unit": "%",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         },
    #         {
    #             "measure": "temperature",
    #             "min_unit": "c",
    #             "max_unit": "c",
    #             "resolution_unit": "c",
    #             "min_value": -10.0,
    #             "max_value": 60.0,
    #             "resolution": 0.1,
    #         },
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Fondo",
    #         "role": "working",
    #     },
    #     "serial": "QM2024-104",
    #     "model": "CN1290SMEF/590GME",
    #     "brand": "LUFKIN",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "component_serials": [
    #         {"component_name": "Cinta", "serial": "QM2024-104"},
    #         {"component_name": "Plomada", "serial": "QM2024-104"},
    #     ],
    #     "measure_specs": [
    #         {
    #             "measure": "length",
    #             "min_unit": "mm",
    #             "max_unit": "mm",
    #             "resolution_unit": "mm",
    #             "min_value": 0.0,
    #             "max_value": 15000.0,
    #             "resolution": 1.0,
    #         }
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Titulador Karl Fischer",
    #         "role": "working",
    #     },
    #     "serial": "KF-001",
    #     "model": "KF-100",
    #     "brand": "Acme",
    #     "status": "in_use",
    #     "inspection_days_override": None,
    #     "terminal": "Hoatzin",
    #     "measure_specs": [
    #         {
    #             "measure": "percent_pv",
    #             "min_unit": "%p/v",
    #             "max_unit": "%p/v",
    #             "resolution_unit": "%p/v",
    #             "min_value": 0.0,
    #             "max_value": 100.0,
    #             "resolution": 0.1,
    #         }
    #     ],
    # },
    {
        "equipment_type": {
            "name": "Pesa",
            "role": "reference",
        },
        "serial": "20180419",
        "model": "CILINDRICAS - F1",
        "brand": "NO IDENTIFICADO",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "weight_class": "F1",
        "nominal_mass_value": 10.0,
        "nominal_mass_unit": "g",
        "measure_specs": [],
    },
    {
        "equipment_type": {
            "name": "Hidrometro",
            "role": "working",
        },
        "serial": "513528",
        "model": "3H",
        "brand": "CHASE USA",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "measure_specs": [
            {
                "measure": "api",
                "min_unit": "api",
                "max_unit": "api",
                "resolution_unit": "api",
                "min_value": 19.0,
                "max_value": 31.0,
                "resolution": 0.1,
            }
        ],
    },
    {
        "equipment_type": {
            "name": "TermoHigrometro",
            "role": "working",
        },
        "serial": "53451",
        "model": "445703",
        "brand": "EXTECH",
        "status": "in_use",
        "inspection_days_override": None,
        "terminal": "Hoatzin",
        "measure_specs": [
            {
                "measure": "relative_humidity",
                "min_unit": "%",
                "max_unit": "%",
                "resolution_unit": "%",
                "min_value": 20.0,
                "max_value": 99.0,
                "resolution": 1.0,
            },
            {
                "measure": "temperature",
                "min_unit": "c",
                "max_unit": "c",
                "resolution_unit": "c",
                "min_value": 10.0,
                "max_value": 40.0,
                "resolution": 0.1,
            },
        ],
    },
]
