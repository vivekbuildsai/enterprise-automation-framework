from framework.discovery.ai_recommendations import ElementRecommendation, recommend_for_report
from framework.discovery.api_discovery import discover_from_openapi
from framework.discovery.code_generator import (
    DomainModelGenerator,
    PageObjectGenerator,
    write_generated_file,
)
from framework.discovery.db_discovery import DatabaseDiscoveryEngine
from framework.discovery.models import (
    DiscoveredColumn,
    DiscoveredElement,
    DiscoveredEndpoint,
    DiscoveredLocator,
    DiscoveredPage,
    DiscoveredTable,
    DiscoveryReport,
)
from framework.discovery.ui_discovery import UIDiscoveryEngine

__all__ = [
    "DatabaseDiscoveryEngine",
    "DiscoveredColumn",
    "DiscoveredElement",
    "DiscoveredEndpoint",
    "DiscoveredLocator",
    "DiscoveredPage",
    "DiscoveredTable",
    "DiscoveryReport",
    "DomainModelGenerator",
    "ElementRecommendation",
    "PageObjectGenerator",
    "UIDiscoveryEngine",
    "discover_from_openapi",
    "recommend_for_report",
    "write_generated_file",
]
