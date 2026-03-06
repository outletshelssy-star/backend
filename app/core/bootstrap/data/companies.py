from typing import NotRequired, TypedDict


class TerminalSeed(TypedDict):
    name: str
    block: str
    code: str
    has_lab: bool
    is_active: NotRequired[bool]
    lab_terminal: NotRequired[str]


class CompanySeed(TypedDict):
    name: str
    company_type: str


class UserSeed(TypedDict):
    name: str
    last_name: str
    email: str
    password: str
    user_type: str
    terminals: NotRequired[list[str]]
    company: NotRequired[str]


DEFAULT_BLOCKS: list[str] = [
    "Arrendajo",
    "Cachicamo",
    "Entrerrios",
    "Cravoviejo",
    "Casimena",
    "Cubiro",
    "CPE-6",
    "Quifa",
    "Corcel",
    "Guatiquia",
    "Canaguaro",
    "El Dificil",
    "Sabanero",
    "La Creciente",
    "Hamaca",
]

DEFAULT_INACTIVE_BLOCKS: set[str] = {
    "Canaguaro",
    "La Creciente",
    "Entrerrios",
}

DEFAULT_TERMINALS: list[TerminalSeed] = [
    {
        "name": "Azor",
        "block": "Arrendajo",
        "code": "AZOR",
        "has_lab": True,
    },
    {
        "name": "Yaguazo",
        "block": "Arrendajo",
        "code": "YGZO",
        "has_lab": False,
        "lab_terminal": "Azor",
    },
    {
        "name": "Sabanero",
        "block": "Sabanero",
        "code": "SAB",
        "has_lab": True,
    },
    {
        "name": "El Dificil",
        "block": "El Dificil",
        "code": "DIF",
        "has_lab": True,
    },
    {
        "name": "Hamaca",
        "block": "CPE-6",
        "code": "CPE6",
        "has_lab": True,
    },
    {
        "name": "Quifa",
        "block": "Quifa",
        "code": "QUI",
        "is_active": True,
        "has_lab": True,
    },
    {
        "name": "Cajua",
        "block": "Quifa",
        "code": "CAJ",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Quifa",
    },
    {
        "name": "Jaspe",
        "block": "Quifa",
        "code": "JAS",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Quifa",
    },
    {
        "name": "Corcel Unificado",
        "block": "Corcel",
        "code": "CORC",
        "is_active": True,
        "has_lab": True,
    },
    {
        "name": "Caruto",
        "block": "Corcel",
        "code": "CARU",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Corcel Unificado",
    },
    {
        "name": "Espardarte",
        "block": "Corcel",
        "code": "ESPA",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Corcel Unificado",
    },
    {
        "name": "Ceibo Unificado",
        "block": "Guatiquia",
        "code": "CEIB",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Corcel Unificado",
    },
    {
        "name": "Yatay",
        "block": "Guatiquia",
        "code": "YAT",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Corcel Unificado",
    },
    {
        "name": "Candelilla",
        "block": "Guatiquia",
        "code": "CAND",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Corcel Unificado",
    },
    {
        "name": "Canaguay",
        "block": "Canaguaro",
        "code": "CNG",
        "is_active": False,
        "has_lab": True,
    },
    {
        "name": "Tapity",
        "block": "Canaguaro",
        "code": "TAPI",
        "is_active": False,
        "has_lab": False,
        "lab_terminal": "Canaguay",
    },
    {
        "name": "La Creciente",
        "block": "La Creciente",
        "code": "CREC",
        "is_active": False,
        "has_lab": True,
    },
    {
        "name": "Entrerrios",
        "block": "Entrerrios",
        "code": "ERIO",
        "is_active": False,
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
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Hoatzin",
    },
    {
        "name": "Guacharaca",
        "block": "Cachicamo",
        "code": "GUA",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Hoatzin",
    },
    {
        "name": "Ciriguelo",
        "block": "Cachicamo",
        "code": "CIR",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Hoatzin",
    },
    {
        "name": "Andarrios",
        "block": "Cachicamo",
        "code": "ANDA",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Hoatzin",
    },
    {
        "name": "Greta Oto",
        "block": "Cachicamo",
        "code": "GOTO",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Hoatzin",
    },
    {
        "name": "CPF Carrizales",
        "block": "Cravoviejo",
        "code": "CPFC",
        "has_lab": True,
    },
    {
        "name": "Saimiri",
        "block": "Cravoviejo",
        "code": "SAIM",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "CPF Carrizales",
    },
    {
        "name": "Matemarrano",
        "block": "Cravoviejo",
        "code": "MATE",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "CPF Carrizales",
    },
    {
        "name": "Zopilote",
        "block": "Cravoviejo",
        "code": "ZOP",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "CPF Carrizales",
    },
    {
        "name": "Bastidas",
        "block": "Cravoviejo",
        "code": "BAST",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "CPF Carrizales",
    },
    {
        "name": "Yenac",
        "block": "Casimena",
        "code": "YEN",
        "has_lab": True,
    },
    {
        "name": "Mantis",
        "block": "Casimena",
        "code": "MANT",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Yenac",
    },
    {
        "name": "Pisingo",
        "block": "Casimena",
        "code": "PIS",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Yenac",
    },
    {
        "name": "Copa",
        "block": "Cubiro",
        "code": "COPA",
        "has_lab": True,
    },
    {
        "name": "Copa Unificado",
        "block": "Cubiro",
        "code": "COPU",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Copa",
    },
    {
        "name": "Tijereto",
        "block": "Cubiro",
        "code": "TIJ",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Copa",
    },
    {
        "name": "Careto",
        "block": "Cubiro",
        "code": "CART",
        "is_active": True,
        "has_lab": False,
        "lab_terminal": "Copa",
    },
    {
        "name": "Cernicalo",
        "block": "Cubiro",
        "code": "CERN",
        "is_active": False,
        "has_lab": False,
        "lab_terminal": "Copa",
    },
    {
        "name": "Petirrojo Unificado",
        "block": "Cubiro",
        "code": "PETU",
        "is_active": False,
        "has_lab": False,
        "lab_terminal": "Copa",
    },
]

DEFAULT_PRIMARY_COMPANY_NAME: str = "Frontera Energy"

DEFAULT_COMPANIES: list[CompanySeed] = [
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
    {
        "name": "Applus Colombia",
        "company_type": "partner",
    },
    {
        "name": "Metrología Analítica SAS",
        "company_type": "partner",
    },
    {
        "name": "Set y Gad Metrología",
        "company_type": "partner",
    },
    {
        "name": "Unión Metrológica",
        "company_type": "partner",
    },
    {
        "name": "Metrological Center",
        "company_type": "partner",
    },
    {
        "name": "Atlas Metrologia de Colombias SAS",
        "company_type": "partner",
    },
]

DEFAULT_USERS: list[UserSeed] = [
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
    {
        "name": "Willy",
        "last_name": "Corzo",
        "email": "willy@gmail.com",
        "password": "12345678",
        "user_type": "superadmin",
        "company": "Applus Colombia",
    },
]
