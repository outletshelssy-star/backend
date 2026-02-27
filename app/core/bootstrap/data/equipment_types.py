from typing import NotRequired, TypedDict


class VerificationTypeSeed(TypedDict):
    name: str
    frequency_days: int
    is_active: bool
    order: int


class MaxErrorSeed(TypedDict):
    measure: str
    max_error_value: float
    unit: str


class EquipmentTypeSeed(TypedDict):
    name: str
    role: str
    calibration_days: int
    maintenance_days: int
    inspection_days: int
    observations: str | None
    measures: list[str]
    max_errors: list[MaxErrorSeed]
    verification_types: list[VerificationTypeSeed]
    is_lab: NotRequired[bool]


class EquipmentTypeRefSeed(TypedDict):
    name: str
    role: str


class InspectionItemSeed(TypedDict):
    item: str
    response_type: str
    is_required: bool
    order: int
    expected_bool: NotRequired[bool]
    expected_text_options: NotRequired[list[str]]
    expected_number: NotRequired[float]
    expected_number_min: NotRequired[float]
    expected_number_max: NotRequired[float]


class InspectionItemsSeed(TypedDict):
    equipment_type: EquipmentTypeRefSeed
    items: list[InspectionItemSeed]


DEFAULT_EQUIPMENT_TYPES: list[EquipmentTypeSeed] = [
    {
        "name": "Termometro Electronico TP7 / TP9",
        "role": "working",
        "calibration_days": 365,
        "verification_types": [
            {
                "name": "Diaria",
                "frequency_days": 1,
                "is_active": True,
                "order": 0,
            },
            {
                "name": "Mensual",
                "frequency_days": 30,
                "is_active": True,
                "order": 1,
            },
        ],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": "Norma API MPMS Capitulo 7.",
        "measures": ["temperature"],
        "max_errors": [
            {
                "measure": "temperature",
                "max_error_value": 0.2,
                "unit": "c",
            }
        ],
    },
    {
        "name": "Termometro Electronico TL1",
        "role": "working",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [
            {
                "name": "Diaria",
                "frequency_days": 1,
                "is_active": True,
                "order": 0,
            },
            {
                "name": "Mensual",
                "frequency_days": 30,
                "is_active": True,
                "order": 1,
            },
        ],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": "Norma API MPMS Capitulo 7.",
        "measures": ["temperature"],
        "max_errors": [
            {
                "measure": "temperature",
                "max_error_value": 0.2,
                "unit": "c",
            }
        ],
    },
    {
        "name": "Termometro de Vidrio",
        "role": "working",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [
            {
                "name": "Diaria",
                "frequency_days": 1,
                "is_active": True,
                "order": 0,
            },
            {
                "name": "Mensual",
                "frequency_days": 30,
                "is_active": True,
                "order": 1,
            },
        ],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": "Norma API MPMS Capitulo 7.",
        "measures": ["temperature"],
        "max_errors": [
            {
                "measure": "temperature",
                "max_error_value": 0.2,
                "unit": "c",
            }
        ],
    },
    {
        "name": "Hidrometro",
        "role": "working",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [
            {
                "name": "Mensual",
                "frequency_days": 30,
                "is_active": True,
                "order": 0,
            },
        ],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": "Norma API.",
        "measures": ["api"],
        "max_errors": [
            {
                "measure": "api",
                "max_error_value": 0.2,
                "unit": "api",
            }
        ],
    },
    {
        "name": "Hidrometro",
        "role": "reference",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": "Norma API.",
        "measures": ["api"],
        "max_errors": [
            {
                "measure": "api",
                "max_error_value": 0.2,
                "unit": "api",
            }
        ],
    },
    {
        "name": "Termometro de Vidrio",
        "role": "reference",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": "Calibracion anual (pendiente metodo analitico).",
        "measures": ["temperature"],
        "max_errors": [
            {
                "measure": "temperature",
                "max_error_value": 0.2,
                "unit": "c",
            }
        ],
    },
    {
        "name": "Termometro Electronico TL1",
        "role": "reference",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": "Calibracion anual (pendiente metodo analitico).",
        "measures": ["temperature"],
        "max_errors": [
            {
                "measure": "temperature",
                "max_error_value": 0.2,
                "unit": "c",
            }
        ],
    },
    {
        "name": "Balanza Analitica",
        "role": "working",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [
            {
                "name": "Verificacion diaria",
                "frequency_days": 1,
                "is_active": True,
                "order": 0,
            },
        ],
        "maintenance_days": 365,
        "inspection_days": 1,
        "observations": "Calibrar de acuerdo a SIM MWG7-CG-01-V00-2009",
        "measures": ["weight"],
        "max_errors": [
            {
                "measure": "weight",
                "max_error_value": 1,
                "unit": "g",
            }
        ],
    },
    {
        "name": "Pesa",
        "role": "reference",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": None,
        "measures": [],
        "max_errors": [],
    },
    # {
    #     "name": "Cinta Metrica Plomada Fondo",
    #     "role": "working",
    #     "calibration_days": 365,
    #     "verification_types": [
    #         {
    #             "name": "Verificacion mensual",
    #             "frequency_days": 30,
    #             "is_active": True,
    #             "order": 0,
    #         }
    #     ],
    #     "maintenance_days": 0,
    #     "inspection_days": 1,
    #     "observations": (
    #         "Norma API MPMS Capitulo 3.1A, Numeral 3.1A8. La Cinta Patron "
    #         "debe estar certificada con un ente Certificado, con la cual "
    #         "se haran las verificaciones a la Cinta de Trabajo."
    #     ),
    #     "measures": ["length"],
    #     "max_errors": [
    #         {
    #             "measure": "length",
    #             "max_error_value": 1,
    #             "unit": "mm",
    #         }
    #     ],
    # },
    # {
    #     "name": "Cinta Metrica Plomada Vacio",
    #     "role": "working",
    #     "calibration_days": 365,
    #     "verification_types": [
    #         {
    #             "name": "Verificacion mensual",
    #             "frequency_days": 30,
    #             "is_active": True,
    #             "order": 0,
    #         }
    #     ],
    #     "maintenance_days": 0,
    #     "inspection_days": 1,
    #     "observations": (
    #         "Norma API MPMS Capitulo 3.1A, Numeral 3.1A8. La Cinta Patron "
    #         "debe estar certificada con un ente Certificado, con la cual "
    #         "se haran las verificaciones a la Cinta de Trabajo."
    #     ),
    #     "measures": ["length"],
    #     "max_errors": [
    #         {
    #             "measure": "length",
    #             "max_error_value": 1,
    #             "unit": "mm",
    #         }
    #     ],
    # },
    # {
    #     "name": "Cinta Metrica Plomada Fondo",
    #     "role": "reference",
    #     "calibration_days": 365,
    #     "verification_types": [],
    #     "maintenance_days": 0,
    #     "inspection_days": 1,
    #     "observations": (
    #         "Norma API MPMS Capitulo 3.1A, Numeral 3.1A8. La Cinta Patron "
    #         "debe estar certificada con un ente Certificado, con la cual "
    #         "se haran las verificaciones a la Cinta de Trabajo."
    #     ),
    #     "measures": ["length"],
    #     "max_errors": [
    #         {
    #             "measure": "length",
    #             "max_error_value": 1,
    #             "unit": "mm",
    #         }
    #     ],
    # },
    # {
    #     "name": "Cinta Metrica Plomada Vacio",
    #     "role": "reference",
    #     "calibration_days": 365,
    #     "verification_types": [],
    #     "maintenance_days": 0,
    #     "inspection_days": 1,
    #     "observations": (
    #         "Norma API MPMS Capitulo 3.1A, Numeral 3.1A8. La Cinta Patron "
    #         "debe estar certificada con un ente Certificado, con la cual "
    #         "se haran las verificaciones a la Cinta de Trabajo."
    #     ),
    #     "measures": ["length"],
    #     "max_errors": [
    #         {
    #             "measure": "length",
    #             "max_error_value": 1,
    #             "unit": "mm",
    #         }
    #     ],
    # },
    {
        "name": "TermoHigrometro",
        "role": "working",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": None,
        "measures": ["relative_humidity", "temperature"],
        "max_errors": [
            {
                "measure": "relative_humidity",
                "max_error_value": 5,
                "unit": "%",
            },
            {
                "measure": "temperature",
                "max_error_value": 0.5,
                "unit": "c",
            },
        ],
    },
    {
        "name": "Titulador Karl Fischer",
        "role": "working",
        "calibration_days": 365,
        "is_lab": True,
        "verification_types": [
            {
                "name": "Diaria",
                "frequency_days": 1,
                "is_active": True,
                "order": 0,
            }
        ],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": None,
        "measures": ["percent_pv"],
        "max_errors": [
            {
                "measure": "percent_pv",
                "max_error_value": 0.1,
                "unit": "%p/v",
            }
        ],
    },
]

DEFAULT_EQUIPMENT_TYPE_INSPECTION_ITEMS: list[InspectionItemsSeed] = [
    {
        "equipment_type": {
            "name": "Pesa",
            "role": "reference",
        },
        "items": [
            {
                "item": "Presenta Corrosion?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": False,
            },
            {
                "item": "Presenta Golpes o Rayones profundos?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": False,
            },
            {
                "item": "Se encuentra limpia?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": True,
            },
        ],
    },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Fondo",
    #         "role": "working",
    #     },
    #     "items": [
    #         {
    #             "item": "Cable y pinza de conexion a tierra en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 1,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Escala Visible en la Cinta?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 2,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Presenta elongaciones, dobleces o torceduras?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 3,
    #             "expected_bool": False,
    #         },
    #         {
    #             "item": "Presenta Tramos Oxidados?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 4,
    #             "expected_bool": False,
    #         },
    #         {
    #             "item": "Camara Metalica en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 5,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Mango y Rodillo en buen Estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 6,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Argolla de la plomada en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 7,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Escala Visible en la Plomada?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 8,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Punta de plomada desgastada?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 9,
    #             "expected_bool": False,
    #         },
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Fondo",
    #         "role": "reference",
    #     },
    #     "items": [
    #         {
    #             "item": "Cable y pinza de conexion a tierra en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 1,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Escala Visible en la Cinta?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 2,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Presenta elongaciones, dobleces o torceduras?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 3,
    #             "expected_bool": False,
    #         },
    #         {
    #             "item": "Presenta Tramos Oxidados?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 4,
    #             "expected_bool": False,
    #         },
    #         {
    #             "item": "Camara Metalica en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 5,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Mango y Rodillo en buen Estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 6,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Argolla de la plomada en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 7,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Escala Visible en la Plomada?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 8,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Punta de plomada desgastada?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 9,
    #             "expected_bool": False,
    #         },
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Vacio",
    #         "role": "working",
    #     },
    #     "items": [
    #         {
    #             "item": "Cable y pinza de conexion a tierra en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 1,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Escala Visible en la Cinta?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 2,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Presenta elongaciones, dobleces o torceduras?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 3,
    #             "expected_bool": False,
    #         },
    #         {
    #             "item": "Presenta Tramos Oxidados?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 4,
    #             "expected_bool": False,
    #         },
    #         {
    #             "item": "Camara Metalica en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 5,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Mango y Rodillo en buen Estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 6,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Argolla de la plomada en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 7,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Escala Visible en la Plomada?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 8,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Punta de plomada desgastada?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 9,
    #             "expected_bool": False,
    #         },
    #     ],
    # },
    # {
    #     "equipment_type": {
    #         "name": "Cinta Metrica Plomada Vacio",
    #         "role": "reference",
    #     },
    #     "items": [
    #         {
    #             "item": "Cable y pinza de conexion a tierra en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 1,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Escala Visible en la Cinta?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 2,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Presenta elongaciones, dobleces o torceduras?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 3,
    #             "expected_bool": False,
    #         },
    #         {
    #             "item": "Presenta Tramos Oxidados?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 4,
    #             "expected_bool": False,
    #         },
    #         {
    #             "item": "Camara Metalica en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 5,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Mango y Rodillo en buen Estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 6,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Argolla de la plomada en buen estado?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 7,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Escala Visible en la Plomada?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 8,
    #             "expected_bool": True,
    #         },
    #         {
    #             "item": "Punta de plomada desgastada?",
    #             "response_type": "boolean",
    #             "is_required": True,
    #             "order": 9,
    #             "expected_bool": False,
    #         },
    #     ],
    # },
    {
        "equipment_type": {
            "name": "Termometro Electronico TP7 / TP9",
            "role": "working",
        },
        "items": [
            {
                "item": "Se cuenta con Cable y conexion a tierra?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "Se encuentra el Cable roto?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": False,
            },
            {
                "item": "Bateria Cargada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": True,
            },
            {
                "item": "El Sensor esta en Buen Estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 4,
                "expected_bool": True,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro Electronico TL1",
            "role": "working",
        },
        "items": [
            {
                "item": "Bateria Cargada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "El Sensor esta en Buen Estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro de Vidrio",
            "role": "working",
        },
        "items": [
            {
                "item": "Escala Borrosa?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": False,
            },
            {
                "item": "Columna Mercurio Fraccionada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": False,
            },
            {
                "item": "Almacenado Verticalmente?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": True,
            },
            {
                "item": "Fisuras?",
                "response_type": "boolean",
                "is_required": True,
                "order": 4,
                "expected_bool": False,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro de Vidrio",
            "role": "reference",
        },
        "items": [
            {
                "item": "Escala Borrosa?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": False,
            },
            {
                "item": "Columna Mercurio Fraccionada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": False,
            },
            {
                "item": "Almacenado Verticalmente?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": True,
            },
            {
                "item": "Fisuras?",
                "response_type": "boolean",
                "is_required": True,
                "order": 4,
                "expected_bool": False,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro Electronico TL1",
            "role": "reference",
        },
        "items": [
            {
                "item": "Bateria Cargada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "El Sensor esta en Buen Estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Hidrometro",
            "role": "working",
        },
        "items": [
            {
                "item": "Presenta Rotura?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": False,
            },
            {
                "item": "Escala Visible?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
            {
                "item": "Lastre Suelto?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": False,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Hidrometro",
            "role": "reference",
        },
        "items": [
            {
                "item": "Presenta Rotura?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": False,
            },
            {
                "item": "Escala Visible?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
            {
                "item": "Lastre Suelto?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": False,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Balanza Analitica",
            "role": "working",
        },
        "items": [
            {
                "item": "Enciende correctamente y sin errores?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "Presenta Corrosion o partes sueltas?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": False,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Termometro Electronico TL1",
            "role": "reference",
        },
        "items": [
            {
                "item": "Bateria Cargada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "El Sensor esta en Buen Estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "TermoHigrometro",
            "role": "working",
        },
        "items": [
            {
                "item": "Baterias Descargadas?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": False,
            },
            {
                "item": "Pantalla Funcionando?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Titulador Karl Fischer",
            "role": "working",
        },
        "items": [
            {
                "item": "Pantalla Funcional?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            }
        ],
    },
]
