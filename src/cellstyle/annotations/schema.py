from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from numbers import Real
import math


@dataclass(frozen=True)
class ComparisonResult:
    """
    A statistical result supplied TO CellStyle.

    CellStyle renders this result.
    CellStyle does not choose or execute the statistical test.
    """

    group_a: str
    group_b: str

    p: Optional[float] = None
    p_adjusted: Optional[float] = None

    effect: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None

    test: Optional[str] = None
    observation_unit: Optional[str] = None

    label: Optional[str] = None

    def __post_init__(self):
        for group in (self.group_a, self.group_b):
            if not isinstance(group, str) or not group:
                raise ValueError("Comparison groups must be nonempty strings.")
        if self.group_a == self.group_b:
            raise ValueError("Comparison requires two distinct groups.")
        for field in ("p", "p_adjusted", "effect", "ci_low", "ci_high"):
            value = getattr(self, field)
            if value is not None and (not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value)):
                raise ValueError(f"{field} must be a finite number or None.")
        for field in ("p", "p_adjusted"):
            value = getattr(self, field)
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"{field} must be in [0, 1].")
        if (self.ci_low is None) != (self.ci_high is None):
            raise ValueError("Both confidence interval bounds must be supplied together.")
        if self.ci_low is not None and self.ci_low > self.ci_high:
            raise ValueError("Confidence interval bounds must be ordered.")
        if self.label is not None and not isinstance(self.label, str):
            raise ValueError("label must be a string or None.")

    def display_p(self) -> Optional[float]:
        """Prefer adjusted P when supplied."""
        if self.p_adjusted is not None:
            return self.p_adjusted
        return self.p
