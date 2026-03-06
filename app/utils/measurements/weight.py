from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Weight:
    """Weight stored internally in grams."""

    grams: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.grams):
            raise ValueError("Weight must be a finite real number.")
        if self.grams < 0:
            raise ValueError("Weight cannot be negative.")

    @classmethod
    def from_kilograms(cls, value: float) -> Weight:
        return cls(grams=value * 1000.0)

    @classmethod
    def from_grams(cls, value: float) -> Weight:
        return cls(grams=value)

    @classmethod
    def from_pounds(cls, value: float) -> Weight:
        return cls(grams=value * 453.59237)

    @classmethod
    def from_ounces(cls, value: float) -> Weight:
        return cls(grams=value * 28.349523125)

    @property
    def as_kilograms(self) -> float:
        return self.grams / 1000.0

    @property
    def as_grams(self) -> float:
        return self.grams

    @property
    def as_pounds(self) -> float:
        return self.grams / 453.59237

    @property
    def as_ounces(self) -> float:
        return self.grams / 28.349523125

    def to_unit(self, unit: str) -> float:
        key = unit.strip().lower()
        if key in {"kg", "kilogram", "kilograms"}:
            return self.as_kilograms
        if key in {"g", "gram", "grams"}:
            return self.as_grams
        if key in {"lb", "lbs", "pound", "pounds"}:
            return self.as_pounds
        if key in {"oz", "ounce", "ounces"}:
            return self.as_ounces
        raise ValueError(f"Unsupported weight unit: {unit}")

    def __add__(self, other: float) -> Weight:
        if isinstance(other, (int, float)):
            return Weight(self.grams + float(other))
        return NotImplemented

    def __radd__(self, other: float) -> Weight:
        return self.__add__(other)

    def __sub__(self, other: object) -> float | Weight:
        if isinstance(other, (int, float)):
            return Weight(self.grams - float(other))
        if isinstance(other, Weight):
            return self.grams - other.grams
        return NotImplemented

    def __rsub__(self, other: float) -> Weight:
        if isinstance(other, (int, float)):
            return Weight(float(other) - self.grams)
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Weight):
            return self.grams < other.grams
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Weight):
            return self.grams <= other.grams
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Weight):
            return self.grams > other.grams
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Weight):
            return self.grams >= other.grams
        return NotImplemented
