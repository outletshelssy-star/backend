DEFAULT_BLOCKS = [
    "Sabanero",
    "El Dificil",
    "Hamaca",
    "Quifa",
]

DEFAULT_TERMINALS = [
    {
        "name": "Sabanero",
        "block": "Sabanero",
    },
    {
        "name": "El Dificil",
        "block": "El Dificil",
    },
    {
        "name": "CPE-6",
        "block": "Hamaca",
    },
    {
        "name": "Quifa",
        "block": "Quifa",
    },
]

DEFAULT_PRIMARY_COMPANY_NAME = "Frontera Energy"

DEFAULT_COMPANIES = [
    {
        "name": "Frontera Energy",
        "company_type": "master",
    },
    {
        "name": "Intertek Colombia",
        "company_type": "partner",
    },
    {
        "name": "Confipetrol",
        "company_type": "partner",
    },
]

DEFAULT_USERS = [
    {
        "name": "Admin",
        "last_name": "User",
        "email": "admin.user@local.dev",
        "password": "admin12345",
        "user_type": "admin",
        "terminals": ["Sabanero"],
    },
    {
        "name": "Normal",
        "last_name": "User",
        "email": "user@local.dev",
        "password": "user12345",
        "user_type": "user",
        "terminals": ["Sabanero"],
    },
]
