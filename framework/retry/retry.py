from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from tenacity import (
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity import retry as _tenacity_retry

from framework.constants.timeouts import Timeouts
from framework.exceptions import RetryExhaustedError
from framework.logger import get_logger

_logger = get_logger("retry")

P = ParamSpec("P")
T = TypeVar("T")


def retry_on(
    *exceptions: type[Exception],
    attempts: int = Timeouts.RETRY_MAX_ATTEMPTS,
    wait_multiplier: float = Timeouts.RETRY_WAIT_MULTIPLIER_SECONDS,
    wait_max: float = Timeouts.RETRY_WAIT_MAX_SECONDS,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator factory: retry a callable with exponential backoff when it
    raises any of `exceptions`. Wraps tenacity's `RetryError` in the
    framework's own `RetryExhaustedError` so callers only need to catch one
    exception type regardless of which library implements retries.

    Example:
        @retry_on(ApiRequestError, attempts=5)
        def fetch_subscriber(subscriber_id: str) -> dict: ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        wrapped = _tenacity_retry(
            reraise=False,
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=wait_multiplier, max=wait_max),
            retry=retry_if_exception_type(exceptions),
            before_sleep=lambda state: _logger.warning(
                f"{func.__qualname__} failed on attempt {state.attempt_number}; retrying..."
            ),
        )(func)

        def guarded(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return wrapped(*args, **kwargs)
            except RetryError as exc:
                raise RetryExhaustedError(
                    f"{func.__qualname__} did not succeed after {attempts} attempts"
                ) from exc

        return guarded

    return decorator
