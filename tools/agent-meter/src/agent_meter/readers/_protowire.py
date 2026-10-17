"""Schema-less protobuf wire-format walker (stdlib only, ADR §3.1 / contracts §3.2).

Only the wire format is decoded; callers pick values by dotted field paths such as
``"1.4.2"`` (field 1 → field 4 → field 2). Every repeated occurrence is followed,
and branches that are not decodable sub-messages are skipped, so an unexpected
layout yields *no values* rather than wrong ones.
"""

from __future__ import annotations

import struct

__all__ = ["ProtoDecodeError", "duration_ms", "get_path", "kv_map", "parse"]

_WIRE_VARINT = 0
_WIRE_FIXED64 = 1
_WIRE_LEN = 2
_WIRE_FIXED32 = 5
_MAX_VARINT_BYTES = 10


class ProtoDecodeError(ValueError):
    """The buffer is not a well-formed protobuf message."""


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = 0
    for shift_index in range(_MAX_VARINT_BYTES):
        if pos >= len(buf):
            raise ProtoDecodeError("truncated varint")
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << (7 * shift_index)
        if byte < 0x80:
            return result, pos
    raise ProtoDecodeError("varint longer than 10 bytes")


def parse(buf: bytes) -> list[tuple[int, int, int | bytes]]:
    """Decode one message level into ``(field, wire_type, value)`` triples.

    Varint and fixed-width values are returned as unsigned ``int``; length-delimited
    values as ``bytes``. Groups (wire types 3/4) and truncation raise ``ProtoDecodeError``.
    """
    out: list[tuple[int, int, int | bytes]] = []
    pos = 0
    end = len(buf)
    while pos < end:
        key, pos = _read_varint(buf, pos)
        field, wire_type = key >> 3, key & 0x7
        if field == 0:
            raise ProtoDecodeError("field number 0")
        value: int | bytes
        if wire_type == _WIRE_VARINT:
            value, pos = _read_varint(buf, pos)
        elif wire_type == _WIRE_LEN:
            length, pos = _read_varint(buf, pos)
            if pos + length > end:
                raise ProtoDecodeError("length-delimited field exceeds buffer")
            value = bytes(buf[pos : pos + length])
            pos += length
        elif wire_type == _WIRE_FIXED64:
            if pos + 8 > end:
                raise ProtoDecodeError("truncated fixed64")
            (value,) = struct.unpack_from("<Q", buf, pos)
            pos += 8
        elif wire_type == _WIRE_FIXED32:
            if pos + 4 > end:
                raise ProtoDecodeError("truncated fixed32")
            (value,) = struct.unpack_from("<I", buf, pos)
            pos += 4
        else:
            raise ProtoDecodeError(f"unsupported wire type {wire_type}")
        out.append((field, wire_type, value))
    return out


def _parse_path(path: str) -> list[int]:
    try:
        numbers = [int(part) for part in path.split(".")]
    except ValueError as exc:
        raise ValueError(f"invalid field path {path!r}") from exc
    if not numbers or any(n <= 0 for n in numbers):
        raise ValueError(f"invalid field path {path!r}")
    return numbers


def get_path(buf: bytes, path: str) -> list[int | bytes]:
    """Return every value found at ``path`` (repeated-aware, depth-first order)."""
    numbers = _parse_path(path)
    current: list[bytes] = [buf]
    for depth, number in enumerate(numbers):
        is_last = depth == len(numbers) - 1
        found: list[int | bytes] = []
        for message in current:
            try:
                fields = parse(message)
            except ProtoDecodeError:
                continue  # not a sub-message on this branch: no values here
            found.extend(value for field, _wire, value in fields if field == number)
        if is_last:
            return found
        current = [value for value in found if isinstance(value, bytes)]
    return []


def kv_map(buf: bytes, path: str = "1.20") -> dict[str, str]:
    """Decode repeated ``{1: key, 2: value}`` entries; non-UTF-8 entries are skipped."""
    result: dict[str, str] = {}
    for entry in get_path(buf, path):
        if not isinstance(entry, bytes):
            continue
        try:
            fields = parse(entry)
        except ProtoDecodeError:
            continue
        key = next((v for f, _w, v in fields if f == 1 and isinstance(v, bytes)), None)
        value = next((v for f, _w, v in fields if f == 2 and isinstance(v, bytes)), b"")
        if key is None:
            continue
        try:
            result[key.decode("utf-8")] = value.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return result


def _first_varint(fields: list[tuple[int, int, int | bytes]], number: int) -> int:
    for field, _wire, value in fields:
        if field == number and isinstance(value, int):
            return value
    return 0


def duration_ms(buf: bytes, path: str) -> int | None:
    """Decode a ``{1: seconds, 2: nanos}`` duration at ``path`` into milliseconds.

    Returns ``None`` when the path is absent; absent sub-fields are proto3 zeros.
    """
    for value in get_path(buf, path):
        if not isinstance(value, bytes):
            continue
        try:
            fields = parse(value)
        except ProtoDecodeError:
            continue
        return _first_varint(fields, 1) * 1000 + _first_varint(fields, 2) // 1_000_000
    return None
