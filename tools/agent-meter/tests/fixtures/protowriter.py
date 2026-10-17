"""Tiny protobuf wire-format *writer* used to build synthetic Antigravity blobs.

A message is described as a sequence of ``(field_number, value)`` pairs where the
value is an ``int`` (varint), ``bytes``/``str`` (length-delimited), a nested
``Msg`` (length-delimited sub-message) or a ``Fixed32``/``Fixed64`` wrapper.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

__all__ = ["Fixed32", "Fixed64", "Msg", "encode", "kv_entries", "varint"]


@dataclass(frozen=True, slots=True)
class Fixed32:
    value: int


@dataclass(frozen=True, slots=True)
class Fixed64:
    value: int


@dataclass(frozen=True, slots=True)
class Msg:
    fields: tuple[tuple[int, Value], ...]

    @classmethod
    def of(cls, *fields: tuple[int, Value]) -> Msg:
        return cls(tuple(fields))


Value = int | bytes | str | Msg | Fixed32 | Fixed64


def varint(value: int) -> bytes:
    """Encode an unsigned (or two's-complement 64-bit) varint."""
    if value < 0:
        value += 1 << 64
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _tag(field: int, wire_type: int) -> bytes:
    return varint((field << 3) | wire_type)


def encode(fields: Iterable[tuple[int, Value]] | Msg) -> bytes:
    """Serialize a message given as field pairs or a ``Msg``."""
    pairs = fields.fields if isinstance(fields, Msg) else fields
    out = bytearray()
    for field, value in pairs:
        if isinstance(value, bool):
            out += _tag(field, 0) + varint(int(value))
        elif isinstance(value, int):
            out += _tag(field, 0) + varint(value)
        elif isinstance(value, Fixed64):
            out += _tag(field, 1) + struct.pack("<Q", value.value)
        elif isinstance(value, Fixed32):
            out += _tag(field, 5) + struct.pack("<I", value.value)
        else:
            payload = (
                encode(value)
                if isinstance(value, Msg)
                else value.encode("utf-8")
                if isinstance(value, str)
                else value
            )
            out += _tag(field, 2) + varint(len(payload)) + payload
    return bytes(out)


def kv_entries(
    field: int, mapping: Mapping[str, str | bytes]
) -> list[tuple[int, Value]]:
    """Repeated ``{1: key, 2: value}`` entries as used by ``gen_metadata`` field ``1.20``."""
    return [(field, Msg.of((1, key), (2, value))) for key, value in mapping.items()]
