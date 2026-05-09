from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from time import perf_counter
from typing import Any, Awaitable, Callable, Optional, TypeVar
from uuid import UUID, uuid4

from models.trace import NodeName, TraceEntry, TraceMeta
from utils.hashing import hash_structured
from utils.trace_sink import InStateSink, TraceSink


StateUpdate = dict[str, Any]
NodeFunc = Callable[[dict[str, Any]], Awaitable[StateUpdate]]
F = TypeVar("F", bound=NodeFunc)


def traced_node(
    name: NodeName,
    hash_subject: Callable[[dict[str, Any]], Any],
    sink: Optional[TraceSink] = None,
) -> Callable[[F], F]:
    trace_sink = sink or InStateSink()

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(state: dict[str, Any]) -> StateUpdate:
            run_id = state.get("run_id")
            if run_id is None:
                raise RuntimeError(f"Missing run_id before node {name}")
            if not isinstance(run_id, UUID):
                raise RuntimeError(f"Invalid run_id before node {name}: {run_id!r}")

            started_at = datetime.now(timezone.utc)
            start = perf_counter()
            input_hash = hash_structured(hash_subject(state))
            update = await func(state)
            ended_at = datetime.now(timezone.utc)
            duration_ms = int((perf_counter() - start) * 1000)

            trace_meta = update.pop("_trace_meta", None)
            if trace_meta is None:
                trace_meta = TraceMeta()
            elif isinstance(trace_meta, dict):
                trace_meta = TraceMeta.model_validate(trace_meta)
            elif not isinstance(trace_meta, TraceMeta):
                raise RuntimeError(f"Invalid _trace_meta from node {name}: {trace_meta!r}")

            output_keys = sorted(update.keys())
            entry = TraceEntry(
                entry_id=uuid4(),
                run_id=run_id,
                node=name,
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
                input_hash=input_hash,
                output_keys=output_keys,
                model=trace_meta.model,
                token_usage=trace_meta.token_usage,
                prompts=trace_meta.prompts,
                status="success",
            )
            trace_update = trace_sink.emit(state, entry)
            if "trace" not in trace_update:
                raise RuntimeError(f"Trace sink did not emit trace for node {name}")
            return {
                **update,
                **trace_update,
            }

        return wrapper  # type: ignore[return-value]

    return decorator
