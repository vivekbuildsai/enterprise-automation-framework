from __future__ import annotations

from collections.abc import Callable
from typing import Any

from framework.exceptions import TestDataError


class CustomGeneratorRegistry:
    """Named registry for project-specific generators that don't belong in
    the framework's built-in set (`RandomData`, `TelecomIdentifierGenerator`)
    — e.g. a team-specific employee ID format, or a partner-system account
    number scheme. Register once, generate by name anywhere a builder or
    dataset needs it, instead of every caller reinventing the same
    ad hoc helper.
    """

    def __init__(self) -> None:
        self._generators: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, generator: Callable[..., Any]) -> None:
        self._generators[name] = generator

    def unregister(self, name: str) -> None:
        self._generators.pop(name, None)

    def is_registered(self, name: str) -> bool:
        return name in self._generators

    def generate(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if name not in self._generators:
            raise TestDataError(
                f"No custom generator registered as '{name}'. "
                f"Registered: {sorted(self._generators)}"
            )
        return self._generators[name](*args, **kwargs)


custom_generators = CustomGeneratorRegistry()
