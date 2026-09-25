from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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

    def display_p(self) -> Optional[float]:
        """Prefer adjusted P when supplied."""
        if self.p_adjusted is not None:
            return self.p_adjusted
        return self.p
