from enum import Enum


class UserType(str, Enum):
    superadmin = "superadmin"
    admin = "admin"
    user = "user"


class CompanyType(str, Enum):
    master = "master"
    client = "client"
    partner = "partner"


class EquipmentRole(str, Enum):
    reference = "reference"
    working = "working"


class EquipmentMeasureType(str, Enum):
    temperature = "temperature"
    pressure = "pressure"
    length = "length"
    weight = "weight"


class EquipmentStatus(str, Enum):
    stored = "stored"
    in_use = "in_use"
    maintenance = "maintenance"
    needs_review = "needs_review"
    lost = "lost"
    disposed = "disposed"
    unknown = "unknown"


class InspectionResponseType(str, Enum):
    boolean = "boolean"
    text = "text"
    number = "number"
