from enum import Enum


class UserType(str, Enum):
    superadmin = "superadmin"
    admin = "admin"
    user = "user"
    visitor = "visitor"


class CompanyType(str, Enum):
    master = "master"
    client = "client"
    partner = "partner"


class EquipmentRole(str, Enum):
    reference = "reference"
    working = "working"


class EquipmentMeasureType(str, Enum):
    temperature = "temperature"
    relative_humidity = "relative_humidity"
    pressure = "pressure"
    length = "length"
    weight = "weight"
    api = "api"
    percent_pv = "percent_pv"


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


class SampleAnalysisType(str, Enum):
    api_astm_1298 = "api_astm_1298"
    water_astm_4377 = "water_astm_4377"
