from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Scenario:
    """A named, reusable bundle of related test-data entities representing
    one business situation (e.g. "a roaming subscriber whose zone is
    leaking traffic") — built once by `ScenarioLibrary`, then usable
    unmodified by a UI test (reads `scenario.entities["subscriber"]` to
    fill a form), an API test (posts `scenario.entities["subscriber"]` as
    the request body), and a DB test (seeds `scenario.entities.values()`
    via the repository layer) alike. See docs/ScenarioLibrary.md.
    """

    name: str
    description: str
    entities: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def get(self, entity_name: str) -> Any:
        if entity_name not in self.entities:
            raise KeyError(
                f"Scenario '{self.name}' has no entity '{entity_name}'. "
                f"Available: {sorted(self.entities)}"
            )
        return self.entities[entity_name]

    def all_entities(self) -> list[Any]:
        """Every entity in insertion order — the order `ScenarioLibrary`
        methods build them in is already dependency-safe (tenant before
        network before subscriber, ...), so seeding code can iterate this
        directly without re-deriving the order itself.
        """
        return list(self.entities.values())
