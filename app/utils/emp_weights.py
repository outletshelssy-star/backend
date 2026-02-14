from __future__ import annotations

EMP_TABLE_MG = {
    200.0: {"E1": 0.10, "E2": 0.30, "F1": 1.00, "F2": 3.00, "M1": 10.00, "M2": 30.00, "M3": 100.00},
    100.0: {"E1": 0.05, "E2": 0.16, "F1": 0.50, "F2": 1.60, "M1": 5.00, "M2": 16.00, "M3": 50.00},
    50.0: {"E1": 0.03, "E2": 0.10, "F1": 0.30, "F2": 1.00, "M1": 3.00, "M2": 10.00, "M3": 30.00},
    20.0: {"E1": 0.03, "E2": 0.08, "F1": 0.25, "F2": 0.80, "M1": 2.50, "M2": 8.00, "M3": 25.00},
    10.0: {"E1": 0.02, "E2": 0.06, "F1": 0.20, "F2": 0.60, "M1": 2.00, "M2": 6.00, "M3": 20.00},
    5.0: {"E1": 0.02, "E2": 0.05, "F1": 0.16, "F2": 0.50, "M1": 1.60, "M2": 5.00, "M3": 16.00},
    2.0: {"E1": 0.01, "E2": 0.04, "F1": 0.12, "F2": 0.40, "M1": 1.20, "M2": 4.00, "M3": 12.00},
    1.0: {"E1": 0.01, "E2": 0.03, "F1": 0.10, "F2": 0.30, "M1": 1.00, "M2": 3.00, "M3": 10.00},
}

ALLOWED_UNITS = {"g"}
ALLOWED_CLASSES = {"E1", "E2", "F1", "F2", "M1", "M2", "M3"}


def get_emp(weight_class: str, nominal_value: float, unit: str) -> float:
    if unit is None:
        raise ValueError("Unit is required")
    unit_key = str(unit).strip().lower()
    if unit_key not in ALLOWED_UNITS:
        raise ValueError("Unsupported unit for EMP")
    class_key = str(weight_class or "").strip().upper()
    if class_key not in ALLOWED_CLASSES:
        raise ValueError("Unsupported weight class")
    try:
        nominal = float(nominal_value)
    except (TypeError, ValueError):
        raise ValueError("Invalid nominal mass value")
    if nominal not in EMP_TABLE_MG:
        raise ValueError("Nominal mass not allowed for EMP table")
    emp_mg = EMP_TABLE_MG[nominal].get(class_key)
    if emp_mg is None:
        raise ValueError("EMP not defined for this class")
    emp = float(emp_mg) / 1000.0
    if emp is None:
        raise ValueError("EMP not defined for this class")
    return float(emp)
