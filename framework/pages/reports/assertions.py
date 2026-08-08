from __future__ import annotations

from framework.assertions import UIAssert


class ReportAssertions(UIAssert):
    """Reports has no domain-specific checks beyond the generic UI
    assertion set today — kept as a subclass (rather than a fresh empty
    class) so a module-specific check can be added here later without
    every existing caller needing to switch what it imports.
    """
