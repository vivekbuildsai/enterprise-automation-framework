"""Shared pytest fixtures for the runnable examples under `examples/` —
the same fixtures `tests/conftest.py` registers as plugins, so
`pytest examples/` works standalone. Examples live outside `tests/` on
purpose (`pyproject.toml`'s `testpaths = ["tests"]` never auto-collects
them) — they're demo code, not part of the CI-gated test suite.
"""

pytest_plugins = [
    "framework.fixtures.driver_fixtures",
]
