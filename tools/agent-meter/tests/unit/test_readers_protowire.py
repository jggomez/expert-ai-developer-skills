"""Tests for the allowlist-driven protobuf wire walker (contracts §3.2)."""

from __future__ import annotations

import pytest

from agent_meter.readers._protowire import (
    ProtoDecodeError,
    duration_ms,
    get_path,
    kv_map,
    parse,
)
from tests.fixtures.protowriter import Fixed32, Fixed64, Msg, encode, kv_entries


def test_parse_returns_field_wire_type_and_value_for_every_wire_type() -> None:
    buf = encode([(1, 150), (2, b"abc"), (3, Fixed64(7)), (4, Fixed32(9)), (5, -1)])

    result = parse(buf)

    assert result == [
        (1, 0, 150),
        (2, 2, b"abc"),
        (3, 1, 7),
        (4, 5, 9),
        (5, 0, (1 << 64) - 1),
    ]


def test_parse_empty_buffer_is_empty_list() -> None:
    assert parse(b"") == []


@pytest.mark.parametrize(
    "buf",
    [
        b"\x08",  # tag without varint value
        b"\x12\x05ab",  # length longer than buffer
        b"\x0b",  # wire type 3 (start group) is unsupported
        b"\x08" + b"\xff" * 11,  # varint longer than 10 bytes
        b"\x19\x00\x00",  # truncated fixed64
        b"\x00",  # field number 0 is invalid
    ],
)
def test_parse_rejects_malformed_input(buf: bytes) -> None:
    with pytest.raises(ProtoDecodeError):
        parse(buf)


def test_get_path_walks_nested_messages_and_is_repeated_aware() -> None:
    inner_a = Msg.of((2, 10), (3, 20))
    inner_b = Msg.of((2, 11))
    buf = encode([(1, Msg.of((4, inner_a), (4, inner_b), (19, "gemini-3.8-flash")))])

    assert get_path(buf, "1.4.2") == [10, 11]
    assert get_path(buf, "1.4.3") == [20]
    assert get_path(buf, "1.19") == [b"gemini-3.8-flash"]
    assert get_path(buf, "1.4.9") == []
    assert get_path(buf, "7") == []


def test_get_path_skips_branches_that_are_not_messages() -> None:
    # Field 1 holds a varint in one occurrence and a message in the other.
    buf = encode([(1, 5), (1, Msg.of((2, 42))), (1, b"\xff\xff")])

    assert get_path(buf, "1.2") == [42]


def test_get_path_rejects_invalid_path() -> None:
    with pytest.raises(ValueError):
        get_path(b"", "1..2")


def test_kv_map_reads_repeated_pairs_and_skips_non_utf8() -> None:
    entries = kv_entries(20, {"trajectory_id": "t-1", "last_step_index": "41"})
    entries.append((20, Msg.of((1, "bad"), (2, b"\xff\xfe"))))
    buf = encode([(1, Msg(tuple(entries)))])

    assert kv_map(buf) == {"trajectory_id": "t-1", "last_step_index": "41"}


def test_kv_map_custom_path_and_missing_path() -> None:
    buf = encode([(3, Msg.of((9, Msg.of((1, "k"), (2, "v")))))])

    assert kv_map(buf, "3.9") == {"k": "v"}
    assert kv_map(buf, "1.20") == {}


def test_duration_ms_combines_seconds_and_nanos() -> None:
    buf = encode([(1, Msg.of((11, Msg.of((1, 3), (2, 206_912_875)))))])

    assert duration_ms(buf, "1.11") == 3_206


def test_duration_ms_absent_is_none_and_empty_message_is_zero() -> None:
    nanos_only = encode([(1, Msg.of((12, Msg.of((2, 43_072_541)))))])
    empty = encode([(1, Msg.of((11, b"")))])

    assert duration_ms(nanos_only, "1.11") is None
    assert duration_ms(nanos_only, "1.12") == 43
    assert duration_ms(empty, "1.11") == 0
