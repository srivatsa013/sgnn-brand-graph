"""Quote-aware CSV splitter and a resumable SHA-256.

The splitter returns only complete records. Bytes that belong to an
unfinished record stay in the caller's buffer, so a resume offset is
always a record boundary.
"""

from __future__ import annotations

import hashlib
import json
import struct

_K = [
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
    0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3, 0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
    0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC, 0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
    0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
    0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13, 0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
    0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3, 0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
    0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
    0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208, 0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
]


def _rotr(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


class Sha256:
    """SHA-256 with a JSON state, so a multi-hour download can resume."""

    def __init__(self) -> None:
        self.h = [
            0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
            0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19,
        ]
        self.buf = b""
        self.nbits = 0

    def update(self, data: bytes) -> None:
        self.buf += data
        self.nbits += len(data) * 8
        while len(self.buf) >= 64:
            self._block(self.buf[:64])
            self.buf = self.buf[64:]

    def _block(self, block: bytes) -> None:
        w = list(struct.unpack(">16I", block))
        for i in range(16, 64):
            s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
            s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
            w.append((w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF)
        a, b, c, d, e, f, g, hh = self.h
        for i in range(64):
            s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
            ch = (e & f) ^ ((~e) & g)
            t1 = (hh + s1 + ch + _K[i] + w[i]) & 0xFFFFFFFF
            s0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
            maj = (a & b) ^ (a & c) ^ (b & c)
            t2 = (s0 + maj) & 0xFFFFFFFF
            hh, g, f, e, d, c, b, a = g, f, e, (d + t1) & 0xFFFFFFFF, c, b, a, (t1 + t2) & 0xFFFFFFFF
        self.h = [
            (self.h[0] + a) & 0xFFFFFFFF,
            (self.h[1] + b) & 0xFFFFFFFF,
            (self.h[2] + c) & 0xFFFFFFFF,
            (self.h[3] + d) & 0xFFFFFFFF,
            (self.h[4] + e) & 0xFFFFFFFF,
            (self.h[5] + f) & 0xFFFFFFFF,
            (self.h[6] + g) & 0xFFFFFFFF,
            (self.h[7] + hh) & 0xFFFFFFFF,
        ]

    def hexdigest(self) -> str:
        clone = Sha256()
        clone.h = list(self.h)
        clone.buf = self.buf
        clone.nbits = self.nbits
        length = clone.nbits.to_bytes(8, "big")
        clone.buf += b"\x80"
        clone.buf += b"\x00" * ((56 - len(clone.buf) % 64) % 64)
        clone.buf += length
        while len(clone.buf) >= 64:
            clone._block(clone.buf[:64])
            clone.buf = clone.buf[64:]
        return "".join(f"{word:08x}" for word in clone.h)

    def export_state(self) -> str:
        return json.dumps({"h": self.h, "buf": self.buf.hex(), "nbits": self.nbits})

    @classmethod
    def from_state(cls, raw: str | None) -> "Sha256":
        obj = cls()
        if not raw:
            return obj
        payload = json.loads(raw)
        obj.h = [int(word) for word in payload["h"]]
        obj.buf = bytes.fromhex(payload["buf"])
        obj.nbits = int(payload["nbits"])
        return obj


def assert_sha_matches_hashlib() -> None:
    samples = [b"", b"abc", b"a" * 1000, b"hello\n", bytes(range(256))]
    for sample in samples:
        ours = Sha256()
        ours.update(sample[:3])
        restored = Sha256.from_state(ours.export_state())
        restored.update(sample[3:])
        expect = hashlib.sha256(sample).hexdigest()
        if restored.hexdigest() != expect:
            raise SystemExit("SHA-256 resume check failed")


def feed_csv(buf: bytes) -> tuple[list[list[str]], int]:
    """Return complete rows and the number of leading bytes they occupy."""
    i = 0
    n = len(buf)
    rows: list[list[str]] = []
    field = bytearray()
    row: list[str] = []
    in_quotes = False
    last_good = 0
    while i < n:
        b = buf[i]
        if in_quotes:
            if b == 34:
                if i + 1 >= n:
                    break
                if buf[i + 1] == 34:
                    field.append(34)
                    i += 2
                    continue
                in_quotes = False
                i += 1
                continue
            field.append(b)
            i += 1
            continue
        if b == 34:
            in_quotes = True
            i += 1
            continue
        if b == 44:
            row.append(field.decode("utf-8", "replace"))
            field = bytearray()
            i += 1
            continue
        if b in (10, 13):
            if b == 13 and i + 1 >= n:
                break
            row.append(field.decode("utf-8", "replace"))
            field = bytearray()
            rows.append(row)
            row = []
            if b == 13 and buf[i + 1] == 10:
                i += 2
            else:
                i += 1
            last_good = i
            continue
        field.append(b)
        i += 1
    return rows, last_good
