from framework.sync.ai_recommendations import MappingRecommendation, recommend_mappings
from framework.sync.analyzer import RepositoryAnalyzer
from framework.sync.compatibility import compute_compatibility_report
from framework.sync.detectors import (
    DEFAULT_ADAPTERS,
    CypressAdapter,
    FrameworkAdapter,
    JUnitAdapter,
    PlaywrightAdapter,
    PytestAdapter,
    SeleniumAdapter,
    TestNGAdapter,
)
from framework.sync.diff import diff_analyses
from framework.sync.models import (
    AnalysisDiff,
    CompatibilityReport,
    DetectedFramework,
    Finding,
    RepositoryAnalysis,
    RepositoryStructure,
    SupportLevel,
    SyncMode,
)
from framework.sync.scaffold import generate_migration_worksheet
from framework.sync.sources import GitRepositorySource, LocalDirectorySource, ZipArchiveSource

__all__ = [
    "DEFAULT_ADAPTERS",
    "AnalysisDiff",
    "CompatibilityReport",
    "CypressAdapter",
    "DetectedFramework",
    "Finding",
    "FrameworkAdapter",
    "GitRepositorySource",
    "JUnitAdapter",
    "LocalDirectorySource",
    "MappingRecommendation",
    "PlaywrightAdapter",
    "PytestAdapter",
    "RepositoryAnalysis",
    "RepositoryAnalyzer",
    "RepositoryStructure",
    "SeleniumAdapter",
    "SupportLevel",
    "SyncMode",
    "TestNGAdapter",
    "ZipArchiveSource",
    "compute_compatibility_report",
    "diff_analyses",
    "generate_migration_worksheet",
    "recommend_mappings",
]
