from framework.extension.ai_recommendations import (
    ExtensionMappingRecommendation,
    recommend_for_ambiguous_items,
)
from framework.extension.correlation import (
    correlate_database_usage,
    correlate_network_call,
    correlate_network_calls,
)
from framework.extension.gap_analysis import (
    build_extension_items,
    build_test_opportunities,
    format_reuse_matrix,
)
from framework.extension.models import (
    ExtensionClassification,
    ExtensionItem,
    ExtensionReport,
    ExtensionSubjectType,
    RelationshipStatus,
    ScaffoldFile,
    ScaffoldFileKind,
    ScaffoldManifest,
    ScaffoldTarget,
    TestOpportunity,
    UIAPICorrelation,
)
from framework.extension.paths import resolve_scaffold_output_dir, safe_scaffold_target
from framework.extension.scaffold import build_scaffold_plan, write_scaffold_plan
from framework.extension.target import detect_scaffold_target

__all__ = [
    "ExtensionClassification",
    "ExtensionItem",
    "ExtensionMappingRecommendation",
    "ExtensionReport",
    "ExtensionSubjectType",
    "RelationshipStatus",
    "ScaffoldFile",
    "ScaffoldFileKind",
    "ScaffoldManifest",
    "ScaffoldTarget",
    "TestOpportunity",
    "UIAPICorrelation",
    "build_extension_items",
    "build_scaffold_plan",
    "build_test_opportunities",
    "correlate_database_usage",
    "correlate_network_call",
    "correlate_network_calls",
    "detect_scaffold_target",
    "format_reuse_matrix",
    "recommend_for_ambiguous_items",
    "resolve_scaffold_output_dir",
    "safe_scaffold_target",
    "write_scaffold_plan",
]
