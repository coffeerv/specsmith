from __future__ import annotations

from utils.hashing import hash_bytes, hash_envelope, hash_structured


def test_structured_hash_is_deterministic_and_key_order_independent():
    left = {"b": 2, "a": {"z": 1, "y": 0}}
    right = {"a": {"y": 0, "z": 1}, "b": 2}

    assert hash_structured(left) == hash_structured(right)
    assert hash_structured(left) != hash_structured({"b": 2, "a": {"z": 2, "y": 0}})


def test_byte_and_mixed_hashes_are_deterministic():
    assert hash_bytes(b"same") == hash_bytes(b"same")
    assert hash_bytes(b"same") != hash_bytes(b"different")

    first = hash_envelope(["hello"], [b"image-bytes"])
    second = hash_envelope(["hello"], [b"image-bytes"])

    assert first == second
