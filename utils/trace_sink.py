from __future__ import annotations

from typing import Any, Protocol

from models.trace import TraceEntry


class TraceSink(Protocol):
    def emit(self, state: dict[str, Any], entry: TraceEntry) -> dict[str, Any]:
        ...


class InStateSink:
    def emit(self, state: dict[str, Any], entry: TraceEntry) -> dict[str, Any]:
        return {
            "trace": [
                *state.get("trace", []),
                entry,
            ]
        }
