"""Observability and tracing utilities for the Co-Scientist system.

This module provides tracing decorators that integrate with LangSmith
when configured, or fall back to standard logging otherwise.
"""

import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar

from geospatial_co_scientist.config import get_settings

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _get_langsmith_traceable() -> Optional[Callable]:
    """Try to import the langsmith traceable decorator."""
    settings = get_settings()
    if not settings.langsmith_api_key:
        return None

    try:
        from langsmith import traceable
        return traceable
    except ImportError:
        logger.debug("LangSmith not available, using fallback tracing")
        return None


def traceable(
    name: Optional[str] = None,
    run_type: str = "chain",
    tags: Optional[list[str]] = None,
) -> Callable[[F], F]:
    """Decorator to add tracing to agent methods.

    When LangSmith is configured, this uses LangSmith's @traceable decorator.
    Otherwise, it falls back to local logging with timing information.

    Args:
        name: Name for the trace run (defaults to function name)
        run_type: Type of run (chain, llm, tool, etc.)
        tags: Additional tags to add to the trace

    Returns:
        Decorated function with tracing enabled

    Example:
        @traceable(name="hypothesis_generation", run_type="chain")
        async def generate_hypotheses(self, state):
            ...
    """
    def decorator(func: F) -> F:
        trace_name = name or func.__name__
        trace_tags = tags or []

        # Try to get LangSmith traceable
        langsmith_traceable = _get_langsmith_traceable()

        if langsmith_traceable:
            # Use LangSmith tracing
            return langsmith_traceable(
                name=trace_name,
                run_type=run_type,
                tags=trace_tags
            )(func)

        # Fallback to logging-based tracing
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            logger.info(
                f"[TRACE START] {trace_name} | type={run_type} | tags={trace_tags}"
            )

            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                logger.info(
                    f"[TRACE END] {trace_name} | duration={elapsed:.3f}s | status=success"
                )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(
                    f"[TRACE END] {trace_name} | duration={elapsed:.3f}s | "
                    f"status=error | error={type(e).__name__}: {str(e)}"
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            logger.info(
                f"[TRACE START] {trace_name} | type={run_type} | tags={trace_tags}"
            )

            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                logger.info(
                    f"[TRACE END] {trace_name} | duration={elapsed:.3f}s | status=success"
                )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(
                    f"[TRACE END] {trace_name} | duration={elapsed:.3f}s | "
                    f"status=error | error={type(e).__name__}: {str(e)}"
                )
                raise

        # Return appropriate wrapper based on function type
        if _is_async_function(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def _is_async_function(func: Callable) -> bool:
    """Check if a function is an async function."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


class TracingContext:
    """Context manager for tracing blocks of code.

    Example:
        with TracingContext("data_processing", run_type="chain"):
            # processing code
            pass
    """

    def __init__(
        self,
        name: str,
        run_type: str = "chain",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None
    ):
        self.name = name
        self.run_type = run_type
        self.tags = tags or []
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        logger.info(
            f"[TRACE START] {self.name} | type={self.run_type} | "
            f"tags={self.tags} | metadata={self.metadata}"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - (self.start_time or 0)
        if exc_type is None:
            logger.info(
                f"[TRACE END] {self.name} | duration={elapsed:.3f}s | status=success"
            )
        else:
            logger.error(
                f"[TRACE END] {self.name} | duration={elapsed:.3f}s | "
                f"status=error | error={exc_type.__name__}: {exc_val}"
            )
        return False  # Don't suppress exceptions

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


def log_agent_action(
    agent_type: str,
    action: str,
    details: Optional[dict[str, Any]] = None,
    level: int = logging.INFO
) -> None:
    """Log an agent action with consistent formatting.

    Args:
        agent_type: The type of agent performing the action
        action: Description of the action
        details: Optional additional details
        level: Logging level
    """
    msg = f"[{agent_type.upper()}] {action}"
    if details:
        details_str = " | ".join(f"{k}={v}" for k, v in details.items())
        msg = f"{msg} | {details_str}"

    logger.log(level, msg)
