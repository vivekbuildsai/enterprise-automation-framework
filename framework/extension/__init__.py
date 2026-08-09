from framework.extension.ai_recommendations import (
    ExtensionMappingRecommendation,
    recommend_for_ambiguous_items,
)
from framework.extension.auth_detection import detect_login_page, detect_login_pages
from framework.extension.correlation import (
    correlate_database_usage,
    correlate_network_call,
    correlate_network_calls,
)
from framework.extension.discovery_quality import compute_discovery_quality
from framework.extension.gap_analysis import (
    build_extension_items,
    build_test_opportunities,
    format_reuse_matrix,
)
from framework.extension.models import (
    ClassifiedNetworkCall,
    DiscoveryQualityLevel,
    DiscoveryQualityScore,
    ExtensionClassification,
    ExtensionItem,
    ExtensionReport,
    ExtensionSubjectType,
    LoginPageSignal,
    NetworkCallClassification,
    NetworkClassificationResult,
    NetworkClassificationSummary,
    RelationshipStatus,
    ScaffoldFile,
    ScaffoldFileKind,
    ScaffoldManifest,
    ScaffoldTarget,
    TestOpportunity,
    UIAPICorrelation,
)
from framework.extension.network_classification import classify_network_calls, page_host_from_url
from framework.extension.paths import resolve_scaffold_output_dir, safe_scaffold_target
from framework.extension.scaffold import build_scaffold_plan, write_scaffold_plan
from framework.extension.target import detect_scaffold_target

__all__ = [
    "ClassifiedNetworkCall",
    "DiscoveryQualityLevel",
    "DiscoveryQualityScore",
    "ExtensionClassification",
    "ExtensionItem",
    "ExtensionMappingRecommendation",
    "ExtensionReport",
    "ExtensionSubjectType",
    "LoginPageSignal",
    "NetworkCallClassification",
    "NetworkClassificationResult",
    "NetworkClassificationSummary",
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
    "classify_network_calls",
    "compute_discovery_quality",
    "correlate_database_usage",
    "correlate_network_call",
    "correlate_network_calls",
    "detect_login_page",
    "detect_login_pages",
    "detect_scaffold_target",
    "format_reuse_matrix",
    "page_host_from_url",
    "recommend_for_ambiguous_items",
    "resolve_scaffold_output_dir",
    "safe_scaffold_target",
    "write_scaffold_plan",
]
