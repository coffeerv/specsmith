from __future__ import annotations

from dataclasses import dataclass

from agents.nodes import _token_usage


@dataclass
class ResponseWithUsageMetadata:
    usage_metadata: dict[str, int]


@dataclass
class ResponseWithResponseMetadata:
    response_metadata: dict[str, dict[str, int]]


def test_token_usage_reads_langchain_usage_metadata():
    assert _token_usage(
        ResponseWithUsageMetadata(
            {
                "input_tokens": 12,
                "output_tokens": 7,
                "total_tokens": 19,
            }
        )
    ) == {
        "input_tokens": 12,
        "output_tokens": 7,
        "total_tokens": 19,
    }


def test_token_usage_normalizes_response_metadata_token_usage():
    assert _token_usage(
        ResponseWithResponseMetadata(
            {
                "token_usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 7,
                    "total_tokens": 19,
                }
            }
        )
    ) == {
        "input_tokens": 12,
        "output_tokens": 7,
        "total_tokens": 19,
    }
