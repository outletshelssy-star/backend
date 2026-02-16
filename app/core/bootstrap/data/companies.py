DEFAULT_BLOCKS = [
    "Sabanero",
    "El Dificil",
    "Hamaca",
    "Quifa",
    "Cachicamo",
]

DEFAULT_TERMINALS = [
    {
        "name": "Sabanero",
        "block": "Sabanero",
        "code": "SAB",
        "has_lab": True,
    },
    {
        "name": "El Dificil",
        "block": "El Dificil",
        "code": "EDIF",
        "has_lab": True,
    },
    {
        "name": "CPE-6",
        "block": "Hamaca",
        "code": "CPE6",
        "has_lab": True,
    },
    {
        "name": "Quifa",
        "block": "Quifa",
        "code": "QUI",
        "has_lab": True,
    },
    {
        "name": "Hoatzin",
        "block": "Cachicamo",
        "code": "HTZ",
        "has_lab": True,
    },
    {
        "name": "Hoatzin Norte",
        "block": "Cachicamo",
        "code": "HTZN",
        "is_active": False,
        "has_lab": True,
    },
    {
        "name": "Guacharaca",
        "block": "Cachicamo",
        "code": "GUA",
        "is_active": False,
        "has_lab": True,
    },
    {
        "name": "Ciriguelo",
        "block": "Cachicamo",
        "code": "CIRI",
        "is_active": False,
        "has_lab": True,
    },
    {
        "name": "Andarrios",
        "block": "Cachicamo",
        "code": "ANDA",
        "is_active": False,
        "has_lab": True,
    },
    {
        "name": "Greta Oto",
        "block": "Cachicamo",
        "code": "GOTO",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Hoatzin",
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
    {
        "name": "PSL Proanalisis SAS BIC",
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
        "terminals": ["Hoatzin"],
    },
    {
        "name": "Normal",
        "last_name": "User",
        "email": "user@local.dev",
        "password": "user12345",
        "user_type": "user",
        "terminals": ["Hoatzin"],
    },
    {
        "name": "Visitante",
        "last_name": "ANH",
        "email": "visitante@anh.com",
        "password": "visitante12345",
        "user_type": "visitor",
        "company": "ANH",
        "terminals": ["Hoatzin"],
    },
    {
        "name": "Usuario",
        "last_name": "Greta Oto",
        "email": "usuario.gretaoto@local.dev",
        "password": "user12345",
        "user_type": "user",
        "terminals": ["Greta Oto"],
    },
]
