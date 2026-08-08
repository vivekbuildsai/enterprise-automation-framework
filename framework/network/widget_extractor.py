from __future__ import annotations

from typing import Any

from framework.models.dashboard_config import WidgetExtractors, WidgetIdentify
from framework.network.interceptor import CapturedExchange


class WidgetDataExtractor:
    """Matches a captured network exchange against a widget's `identify`
    rule (`config/dashboards/*.json` — see `DashboardConfig`/`WidgetConfig`)
    and pulls dimension/metric rows out of its JSON response using the
    widget's `extractors` config. This is the piece that turns "a captured
    request/response" into "the same shape of data `DashboardRepository`
    produces from ClickHouse", so the two can be compared by a
    `ValidationEngine`/tolerance check without either side knowing about
    the other.
    """

    @staticmethod
    def find_matching(
        identify: WidgetIdentify, exchanges: list[CapturedExchange]
    ) -> CapturedExchange | None:
        for exchange in exchanges:
            haystack = f"{exchange.url} {exchange.request_body or ''}".lower()

            if identify.skip_if_request_contains and (
                identify.skip_if_request_contains.lower() in haystack
            ):
                continue
            if identify.require_if_request_contains and (
                identify.require_if_request_contains.lower() not in haystack
            ):
                continue
            if not all(token.lower() in haystack for token in identify.must_have):
                continue
            if any(token.lower() in haystack for token in identify.must_not_have):
                continue

            return exchange
        return None

    @staticmethod
    def extract_rows(
        exchange: CapturedExchange, extractors: WidgetExtractors
    ) -> list[dict[str, Any]]:
        """Extracts `{dimension: ..., <metric>: ...}` rows from a captured
        response's JSON body. Accepts either a bare list of row-objects or
        `{"rows": [...]}` — the two shapes real dashboard/JSON-RPC APIs
        commonly use.
        """
        body = exchange.response_json
        if isinstance(body, dict):
            body = body.get("rows", body.get("data", []))
        if not isinstance(body, list):
            return []

        metrics = extractors.metric if isinstance(extractors.metric, list) else [extractors.metric]
        rows: list[dict[str, Any]] = []
        for row in body:
            if not isinstance(row, dict):
                continue
            entry: dict[str, Any] = {"dimension": row.get(extractors.dimension)}
            for metric in metrics:
                entry[metric] = row.get(metric)
            rows.append(entry)
        return rows
