from __future__ import annotations

import random as _random_module
from collections.abc import Iterator
from contextlib import contextmanager

from faker import Faker
from faker.generator import random as _faker_random

from framework.testdata.utilities.id_sequence import sequences


class DeterministicGenerator:
    """Makes test-data generation repeatable: seeds both Python's `random`
    module (used directly by `TelecomIdentifierGenerator`) and Faker's
    shared generator (used by `RandomData`/Faker-backed builders) from one
    value, so the same seed reproduces the same generated data across runs
    — for a dataset that must diff cleanly between CI runs, or reproducing
    the exact data behind a bug report.
    """

    @staticmethod
    def seed(value: int) -> None:
        _random_module.seed(value)
        Faker.seed(value)

    @staticmethod
    @contextmanager
    def seeded_context(value: int, *, reset_sequences: bool = True) -> Iterator[None]:
        """Seeds for the duration of the `with` block only, restoring
        whatever random state was active beforehand on exit — so one
        deterministic dataset generation doesn't make every later,
        unrelated `random()`/Faker call in the same test session
        predictable too.
        """
        py_state = _random_module.getstate()
        faker_state = _faker_random.getstate()
        if reset_sequences:
            sequences.reset_all()
        DeterministicGenerator.seed(value)
        try:
            yield
        finally:
            _random_module.setstate(py_state)
            _faker_random.setstate(faker_state)
