from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Brand:
    """Minimal example domain model demonstrating how a small business
    entity plugs into the repository/validation layers (see
    `BaseClickHouseRepository`, `ValidationService`). Replace with your
    own application's real domain models once GUI/schema evidence exists.
    """

    name: str
    code: str = ""
