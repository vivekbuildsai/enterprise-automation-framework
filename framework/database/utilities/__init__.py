from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from framework.database.utilities.cleanup_manager import CleanupManager
    from framework.database.utilities.comparison import (
        ComparisonResult,
        DataComparator,
        FieldComparison,
        FieldDiff,
        Tolerance,
    )
    from framework.database.utilities.query_executor import QueryExecutor
    from framework.database.utilities.result_mapper import ExecutionResult, ResultMapper
    from framework.database.utilities.schema_manager import SchemaManager
    from framework.database.utilities.secrets import CredentialResolver
    from framework.database.utilities.transaction_manager import TransactionManager

__all__ = [
    "CleanupManager",
    "ComparisonResult",
    "CredentialResolver",
    "DataComparator",
    "ExecutionResult",
    "FieldComparison",
    "FieldDiff",
    "QueryExecutor",
    "ResultMapper",
    "SchemaManager",
    "Tolerance",
    "TransactionManager",
]

# Lazy re-exports (PEP 562): importing this package used to eagerly pull in
# every submodule regardless of which symbol a caller actually wanted —
# `from framework.database.utilities import DataComparator` (no SQLAlchemy/
# cryptography dependency at all) paid for `query_executor`'s SQLAlchemy
# import and `secrets`' cryptography import anyway, since Python always
# runs a package's __init__ before any of its submodules. Each name is now
# imported only on first access and then cached on this module, so the
# public API (every name in __all__) is unchanged but a caller only pays
# for the transitive imports of the symbols it actually uses.
_SOURCE_MODULES = {
    "CleanupManager": "framework.database.utilities.cleanup_manager",
    "ComparisonResult": "framework.database.utilities.comparison",
    "DataComparator": "framework.database.utilities.comparison",
    "FieldComparison": "framework.database.utilities.comparison",
    "FieldDiff": "framework.database.utilities.comparison",
    "Tolerance": "framework.database.utilities.comparison",
    "QueryExecutor": "framework.database.utilities.query_executor",
    "ExecutionResult": "framework.database.utilities.result_mapper",
    "ResultMapper": "framework.database.utilities.result_mapper",
    "SchemaManager": "framework.database.utilities.schema_manager",
    "CredentialResolver": "framework.database.utilities.secrets",
    "TransactionManager": "framework.database.utilities.transaction_manager",
}


def __getattr__(name: str) -> object:
    module_name = _SOURCE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
