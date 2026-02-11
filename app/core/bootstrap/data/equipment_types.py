DEFAULT_EQUIPMENT_TYPES = [
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
        "role": "reference",
        "calibration_days": 365,
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
        "verification_types": [
            {
                "name": "Verificacion diaria",
                "frequency_days": 1,
                "is_active": True,
                "order": 0,
            },
            {
                "name": "Verificacion mensual",
                "frequency_days": 30,
                "is_active": True,
                "order": 1,
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
        "name": "Cinta Metrica Plomada Fondo",
        "role": "working",
        "calibration_days": 365,
        "verification_types": [
            {
                "name": "Verificacion mensual",
                "frequency_days": 30,
                "is_active": True,
                "order": 0,
            }
        ],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": (
            "Norma API MPMS Capitulo 3.1A, Numeral 3.1A8. La Cinta Patron "
            "debe estar certificada con un ente Certificado, con la cual "
            "se haran las verificaciones a la Cinta de Trabajo."
        ),
        "measures": ["length"],
        "max_errors": [
            {
                "measure": "length",
                "max_error_value": 1,
                "unit": "mm",
            }
        ],
    },
    {
        "name": "Cinta Metrica Plomada Vacio",
        "role": "working",
        "calibration_days": 365,
        "verification_types": [
            {
                "name": "Verificacion mensual",
                "frequency_days": 30,
                "is_active": True,
                "order": 0,
            }
        ],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": (
            "Norma API MPMS Capitulo 3.1A, Numeral 3.1A8. La Cinta Patron "
            "debe estar certificada con un ente Certificado, con la cual "
            "se haran las verificaciones a la Cinta de Trabajo."
        ),
        "measures": ["length"],
        "max_errors": [
            {
                "measure": "length",
                "max_error_value": 1,
                "unit": "mm",
            }
        ],
    },
    {
        "name": "Cinta Metrica Plomada Fondo",
        "role": "reference",
        "calibration_days": 365,
        "verification_types": [],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": (
            "Norma API MPMS Capitulo 3.1A, Numeral 3.1A8. La Cinta Patron "
            "debe estar certificada con un ente Certificado, con la cual "
            "se haran las verificaciones a la Cinta de Trabajo."
        ),
        "measures": ["length"],
        "max_errors": [
            {
                "measure": "length",
                "max_error_value": 1,
                "unit": "mm",
            }
        ],
    },
    {
        "name": "Cinta Metrica Plomada Vacio",
        "role": "reference",
        "calibration_days": 365,
        "verification_types": [],
        "maintenance_days": 0,
        "inspection_days": 1,
        "observations": (
            "Norma API MPMS Capitulo 3.1A, Numeral 3.1A8. La Cinta Patron "
            "debe estar certificada con un ente Certificado, con la cual "
            "se haran las verificaciones a la Cinta de Trabajo."
        ),
        "measures": ["length"],
        "max_errors": [
            {
                "measure": "length",
                "max_error_value": 1,
                "unit": "mm",
            }
        ],
    },
]

DEFAULT_EQUIPMENT_TYPE_INSPECTION_ITEMS = [
    {
        "equipment_type": {
            "name": "Cinta Metrica Plomada Fondo",
            "role": "working",
        },
        "items": [
            {
                "item": "Cable y pinza de conexion a tierra en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "Escala Visible en la Cinta?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
            {
                "item": "Presenta elongaciones, dobleces o torceduras?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": False,
            },
            {
                "item": "Presenta Tramos Oxidados?",
                "response_type": "boolean",
                "is_required": True,
                "order": 4,
                "expected_bool": False,
            },
            {
                "item": "Camara Metalica en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 5,
                "expected_bool": True,
            },
            {
                "item": "Mango y Rodillo en buen Estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 6,
                "expected_bool": True,
            },
            {
                "item": "Argolla de la plomada en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 7,
                "expected_bool": True,
            },
            {
                "item": "Escala Visible en la Plomada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 8,
                "expected_bool": True,
            },
            {
                "item": "Punta de plomada desgastada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 9,
                "expected_bool": False,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Cinta Metrica Plomada Fondo",
            "role": "reference",
        },
        "items": [
            {
                "item": "Cable y pinza de conexion a tierra en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "Escala Visible en la Cinta?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
            {
                "item": "Presenta elongaciones, dobleces o torceduras?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": False,
            },
            {
                "item": "Presenta Tramos Oxidados?",
                "response_type": "boolean",
                "is_required": True,
                "order": 4,
                "expected_bool": False,
            },
            {
                "item": "Camara Metalica en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 5,
                "expected_bool": True,
            },
            {
                "item": "Mango y Rodillo en buen Estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 6,
                "expected_bool": True,
            },
            {
                "item": "Argolla de la plomada en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 7,
                "expected_bool": True,
            },
            {
                "item": "Escala Visible en la Plomada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 8,
                "expected_bool": True,
            },
            {
                "item": "Punta de plomada desgastada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 9,
                "expected_bool": False,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Cinta Metrica Plomada Vacio",
            "role": "working",
        },
        "items": [
            {
                "item": "Cable y pinza de conexion a tierra en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "Escala Visible en la Cinta?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
            {
                "item": "Presenta elongaciones, dobleces o torceduras?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": False,
            },
            {
                "item": "Presenta Tramos Oxidados?",
                "response_type": "boolean",
                "is_required": True,
                "order": 4,
                "expected_bool": False,
            },
            {
                "item": "Camara Metalica en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 5,
                "expected_bool": True,
            },
            {
                "item": "Mango y Rodillo en buen Estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 6,
                "expected_bool": True,
            },
            {
                "item": "Argolla de la plomada en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 7,
                "expected_bool": True,
            },
            {
                "item": "Escala Visible en la Plomada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 8,
                "expected_bool": True,
            },
            {
                "item": "Punta de plomada desgastada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 9,
                "expected_bool": False,
            },
        ],
    },
    {
        "equipment_type": {
            "name": "Cinta Metrica Plomada Vacio",
            "role": "reference",
        },
        "items": [
            {
                "item": "Cable y pinza de conexion a tierra en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 1,
                "expected_bool": True,
            },
            {
                "item": "Escala Visible en la Cinta?",
                "response_type": "boolean",
                "is_required": True,
                "order": 2,
                "expected_bool": True,
            },
            {
                "item": "Presenta elongaciones, dobleces o torceduras?",
                "response_type": "boolean",
                "is_required": True,
                "order": 3,
                "expected_bool": False,
            },
            {
                "item": "Presenta Tramos Oxidados?",
                "response_type": "boolean",
                "is_required": True,
                "order": 4,
                "expected_bool": False,
            },
            {
                "item": "Camara Metalica en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 5,
                "expected_bool": True,
            },
            {
                "item": "Mango y Rodillo en buen Estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 6,
                "expected_bool": True,
            },
            {
                "item": "Argolla de la plomada en buen estado?",
                "response_type": "boolean",
                "is_required": True,
                "order": 7,
                "expected_bool": True,
            },
            {
                "item": "Escala Visible en la Plomada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 8,
                "expected_bool": True,
            },
            {
                "item": "Punta de plomada desgastada?",
                "response_type": "boolean",
                "is_required": True,
                "order": 9,
                "expected_bool": False,
            },
        ],
    },
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
]





