from __future__ import annotations

import json

from framework.network.interceptor import CapturedExchange, NetworkInterceptor


class JsonRpcInterceptor(NetworkInterceptor):
    """`NetworkInterceptor` specialized for JSON-RPC-style APIs — a single
    endpoint receiving POST requests whose body carries a `method` (and
    usually `params`/`id`). Adds `calls_named()` to filter captured
    exchanges by RPC method name, on top of the generic URL-pattern
    capture `NetworkInterceptor` already provides. Applications that use
    plain REST/GraphQL endpoints instead should use the base
    `NetworkInterceptor` — nothing about the widget-matching pipeline
    (`WidgetDataExtractor`) requires JSON-RPC specifically.
    """

    @staticmethod
    def rpc_method(exchange: CapturedExchange) -> str | None:
        if not exchange.request_body:
            return None
        try:
            payload = json.loads(exchange.request_body)
        except ValueError:
            return None
        if isinstance(payload, dict):
            method = payload.get("method")
            return method if isinstance(method, str) else None
        return None

    def calls_named(self, method: str) -> list[CapturedExchange]:
        return [exc for exc in self.captured if self.rpc_method(exc) == method]
