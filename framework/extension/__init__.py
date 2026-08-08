from framework.extension.ai_recommendations import (
    ExtensionMappingRecommendation,
    recommend_for_ambiguous_items,
)
from framework.extension.correlation import (
    correlate_database_usage,
    correlate_network_call,
    correlate_network_calls,
)
from framework.extension.gap_analysis import build_extension_items, build_test_opportunities
from framework.extension.models import (
    ExtensionClassification,
    ExtensionItem,
    ExtensionReport,
    ExtensionSubjectType,
    RelationshipStatus,
    TestOpportunity,
    UIAPICorrelation,
)

__all__ = [
    "ExtensionClassification",
    "ExtensionItem",
    "ExtensionMappingRecommendation",
    "ExtensionReport",
    "ExtensionSubjectType",
    "RelationshipStatus",
    "TestOpportunity",
    "UIAPICorrelation",
    "build_extension_items",
    "build_test_opportunities",
    "correlate_database_usage",
    "correlate_network_call",
    "correlate_network_calls",
    "recommend_for_ambiguous_items",
]
