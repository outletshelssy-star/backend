from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Temperature:
    """Temperature stored internally in Celsius."""

    celsius: float
    _ABSOLUTE_ZERO_C = -273.15

    def __post_init__(self) -> None:
        if not math.isfinite(self.celsius):
            raise ValueError("Temperature must be a finite real number.")
        if self.celsius < self._ABSOLUTE_ZERO_C:
            raise ValueError("Temperature cannot be below absolute zero (-273.15 C).")

    @classmethod
    def from_celsius(cls, value: float) -> Temperature:
        return cls(celsius=value)

    @classmethod
    def from_fahrenheit(cls, value: float) -> Temperature:
        return cls(celsius=(value - 32.0) * 5.0 / 9.0)

    @classmethod
    def from_kelvin(cls, value: float) -> Temperature:
        return cls(celsius=value - 273.15)

    @classmethod
    def from_rankine(cls, value: float) -> Temperature:
        return cls(celsius=(value - 491.67) * 5.0 / 9.0)

    @property
    def as_celsius(self) -> float:
        return self.celsius

    @property
    def as_fahrenheit(self) -> float:
        return (self.celsius * 9.0 / 5.0) + 32.0

    @property
    def as_kelvin(self) -> float:
        return self.celsius + 273.15

    @property
    def as_rankine(self) -> float:
        return (self.celsius + 273.15) * 9.0 / 5.0

    def to_unit(self, unit: str) -> float:
        key = unit.strip().lower()
        if key in {"c", "celsius"}:
            return self.as_celsius
        if key in {"f", "fahrenheit"}:
            return self.as_fahrenheit
        if key in {"k", "kelvin"}:
            return self.as_kelvin
        if key in {"r", "rankine"}:
            return self.as_rankine
        raise ValueError(f"Unsupported temperature unit: {unit}")

    def __add__(self, other: float) -> Temperature:
        if isinstance(other, (int, float)):
            return Temperature(self.celsius + float(other))
        return NotImplemented

    def __radd__(self, other: float) -> Temperature:
        return self.__add__(other)

    def __sub__(self, other: object) -> float | Temperature:
        if isinstance(other, (int, float)):
            return Temperature(self.celsius - float(other))
        if isinstance(other, Temperature):
            return self.celsius - other.celsius
        return NotImplemented

    def __rsub__(self, other: float) -> Temperature:
        if isinstance(other, (int, float)):
            return Temperature(float(other) - self.celsius)
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Temperature):
            return self.celsius < other.celsius
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Temperature):
            return self.celsius <= other.celsius
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Temperature):
            return self.celsius > other.celsius
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Temperature):
            return self.celsius >= other.celsius
        return NotImplemented
