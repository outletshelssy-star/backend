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
        "code": "SAB",
    },
    {
        "name": "El Dificil",
        "block": "El Dificil",
        "code": "EDI",
    },
    {
        "name": "CPE-6",
        "block": "Hamaca",
        "code": "CPE",
    },
    {
        "name": "Quifa",
        "block": "Quifa",
        "code": "QUI",
    },
]

DEFAULT_PRIMARY_COMPANY_NAME = "Frontera Energy"

DEFAULT_COMPANIES = [
    {
        "name": "Frontera Energy",
        "company_type": "master",
    },
    {
        "name": "ANH",
        "company_type": "client",
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
    {
        "name": "Visitante",
        "last_name": "ANH",
        "email": "visitante@anh.com",
        "password": "visitante12345",
        "user_type": "visitor",
        "company": "ANH",
        "terminals": ["Sabanero"],
    },
]
