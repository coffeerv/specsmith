from __future__ import annotations

import hashlib
import json
from typing import Any, List


def hash_structured(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_envelope(text_parts: List[str], binary_parts: List[bytes]) -> str:
    envelope = {
        "text": text_parts,
        "binary_hashes": [hash_bytes(part) for part in binary_parts],
    }
    return hash_structured(envelope)


def user_assets_envelope(assets: List[dict[str, Any]]) -> dict[str, Any]:
    text_parts: List[str] = []
    binary_parts: List[bytes] = []
    normalized_assets: List[dict[str, Any]] = []

    for asset in assets:
        normalized = {
            key: value
            for key, value in asset.items()
            if key not in {"bytes", "text"}
        }
        if "text" in asset:
            text = asset.get("text") or ""
            text_parts.append(text)
            normalized["text"] = text
        if "bytes" in asset:
            data = asset.get("bytes") or b""
            binary_parts.append(data)
            normalized["bytes_sha256"] = hash_bytes(data)
        normalized_assets.append(normalized)

    return {
        "assets": normalized_assets,
        "mixed_payload_hash": hash_envelope(text_parts, binary_parts),
    }


def hash_user_assets(assets: List[dict[str, Any]]) -> str:
    return hash_structured(user_assets_envelope(assets))
