from enum import StrEnum


class UserType(StrEnum):
    superadmin = "superadmin"
    admin = "admin"
    user = "user"
    visitor = "visitor"


class CompanyType(StrEnum):
    master = "master"
    client = "client"
    partner = "partner"


class EquipmentRole(StrEnum):
    reference = "reference"
    working = "working"


class EquipmentMeasureType(StrEnum):
    temperature = "temperature"
    relative_humidity = "relative_humidity"
    pressure = "pressure"
    length = "length"
    weight = "weight"
    api = "api"
    percent_pv = "percent_pv"


class EquipmentStatus(StrEnum):
    stored = "stored"
    in_use = "in_use"
    maintenance = "maintenance"
    needs_review = "needs_review"
    lost = "lost"
    disposed = "disposed"
    unknown = "unknown"


class InspectionResponseType(StrEnum):
    boolean = "boolean"
    text = "text"
    number = "number"


class SampleAnalysisType(StrEnum):
    api_astm_1298 = "api_astm_1298"
    water_astm_4377 = "water_astm_4377"
