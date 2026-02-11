from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Length:
    """Length stored internally in millimeters."""

    millimeters: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.millimeters):
            raise ValueError("Length must be a finite real number.")
        if self.millimeters < 0:
            raise ValueError("Length cannot be negative.")

    @classmethod
    def from_millimeters(cls, value: float) -> Length:
        return cls(millimeters=value)

    @classmethod
    def from_centimeters(cls, value: float) -> Length:
        return cls(millimeters=value * 10.0)

    @classmethod
    def from_meters(cls, value: float) -> Length:
        return cls(millimeters=value * 1000.0)

    @classmethod
    def from_inches(cls, value: float) -> Length:
        return cls(millimeters=value * 25.4)

    @classmethod
    def from_feet(cls, value: float) -> Length:
        return cls(millimeters=value * 304.8)

    @property
    def as_millimeters(self) -> float:
        return self.millimeters

    @property
    def as_centimeters(self) -> float:
        return self.millimeters / 10.0

    @property
    def as_meters(self) -> float:
        return self.millimeters / 1000.0

    @property
    def as_inches(self) -> float:
        return self.millimeters / 25.4

    @property
    def as_feet(self) -> float:
        return self.millimeters / 304.8

    def to_unit(self, unit: str) -> float:
        key = unit.strip().lower()
        if key in {"mm", "millimeter", "millimeters"}:
            return self.as_millimeters
        if key in {"cm", "centimeter", "centimeters"}:
            return self.as_centimeters
        if key in {"m", "meter", "meters"}:
            return self.as_meters
        if key in {"in", "inch", "inches"}:
            return self.as_inches
        if key in {"ft", "foot", "feet"}:
            return self.as_feet
        raise ValueError(f"Unsupported length unit: {unit}")
