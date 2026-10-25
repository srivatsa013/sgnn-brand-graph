"""Independent check of FNSPID regions where the stream's row counter froze.

This file does not import phase1_csvstream. It counts timestamp record
starts and the stock-symbol field that follows each start, using the
standard-library regex engine on the raw HTTP bytes.
"""

from __future__ import annotations

import json
import re
import socket
import sys
import urllib.request
from collections import Counter

NAS = "https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/nasdaq_exteral_data.csv"
ALL = "https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/All_external.csv"

# Stalls are the log spans where rows_seen did not change. Recovery spans
# are the bytes between those stalls, where the counter moved again.
REGIONS = [
    ("nas_before_flat1", NAS, 17_786_013_640, 17_854_168_758),
    ("nas_flat1", NAS, 17_854_168_758, 19_886_310_087),
    ("nas_recovery", NAS, 19_886_310_087, 20_360_267_810),
    ("nas_flat2", NAS, 20_360_267_810, 23_232_979_597),
    ("all_before_flat1", ALL, 270_532_482, 338_689_211),
    ("all_flat1", ALL, 338_689_211, 2_370_830_120),
    ("all_recovery", ALL, 2_370_830_120, 2_842_689_396),
    ("all_flat2", ALL, 2_842_689_396, 5_731_397_037),
]

RECORD = re.compile(rb"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC),")
FOCUS = (b"AAPL", b"MSFT", b"GOOG", b"GOOGL", b"TSLA", b"AMZN", b"META", b"FB")


def prefer_ipv4() -> None:
    original = socket.getaddrinfo

    def ipv4(host, port, family=0, socktype=0, proto=0, flags=0):
        try:
            found = original(host, port, socket.AF_INET, socktype, proto, flags)
        except socket.gaierror:
            found = []
        return found or original(host, port, family, socktype, proto, flags)

    socket.getaddrinfo = ipv4


def symbol_after(buf: bytes, start: int) -> tuple[str, str]:
    """Return (class, symbol) for the field after a record's title.

    class is empty, ticker, unresolved, or no_url. A ticker is accepted
    only when the following field looks like an http URL, which is the
    column layout of both FNSPID news files.
    """
    n = len(buf)
    i = start
    if i >= n:
        return "unresolved", ""
    if buf[i] == 34:
        j = i + 1
        while j < n and j - i < 8000:
            if buf[j] == 34:
                if j + 1 < n and buf[j + 1] == 34:
                    j += 2
                    continue
                j += 1
                break
            j += 1
        else:
            return "unresolved", ""
        if j >= n or buf[j - 1] != 34 or j >= n or buf[j : j + 1] != b",":
            return "unresolved", ""
        sym_at = j + 1
    else:
        j = buf.find(b",", i, i + 800)
        if j < 0:
            return "unresolved", ""
        sym_at = j + 1
    k = buf.find(b",", sym_at, sym_at + 40)
    if k < 0:
        return "unresolved", ""
    symbol = buf[sym_at:k].strip()
    nxt = buf[k + 1 : k + 5]
    if nxt not in (b"http", b"HTTP"):
        return "no_url", symbol.decode("ascii", "replace")
    if not symbol:
        return "empty", ""
    if not re.fullmatch(rb"[A-Za-z][A-Za-z0-9.\-]{0,9}", symbol):
        return "other", symbol.decode("ascii", "replace")
    return "ticker", symbol.decode("ascii").upper()


def is_record_prefix(prefix: bytes) -> bool:
    return bool(
        prefix.endswith(b"\n")
        or prefix.endswith(b"\n,")
        or re.search(rb"(?:\n|\r)\d+\.\d+,$", prefix)
    )


def scan(url: str, start: int, end: int, label: str) -> dict:
    counts: Counter = Counter()
    symbols: Counter = Counter()
    focus: Counter = Counter()
    raw = Counter()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "sgnn-csp-phase1", "Range": f"bytes={start}-{end - 1}"},
    )
    hold = b""
    got = 0
    last_report = 0
    with urllib.request.urlopen(req, timeout=180) as response:
        while got < end - start:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            blob = hold + chunk
            hold_n = len(hold)
            # Count only this chunk. The hold exists so a timestamp that
            # began in the previous chunk is still visible once.
            searchable = blob if got + len(chunk) >= end - start else blob[: len(blob) - 256]
            for match in RECORD.finditer(searchable):
                if match.start() < hold_n:
                    continue
                prefix = searchable[max(0, match.start() - 24) : match.start()]
                if not is_record_prefix(prefix):
                    counts["timestamp_not_at_line_start"] += 1
                    continue
                counts["record_starts"] += 1
                kind, symbol = symbol_after(searchable, match.end())
                counts[kind] += 1
                if kind == "ticker":
                    symbols[symbol] += 1
                    if symbol.encode() in FOCUS:
                        focus[symbol] += 1
            fresh = chunk if got + len(chunk) >= end - start else searchable[hold_n:]
            for token in FOCUS:
                raw[token.decode()] += fresh.count(b"," + token + b",")
            got += len(chunk)
            if got + len(chunk) >= end - start:
                hold = b""
            else:
                hold = blob[len(searchable) - 256 :]
            if got - last_report >= 64 * 1024 * 1024:
                print(
                    f"{label} {got}/{end - start} starts {counts['record_starts']} "
                    f"empty {counts['empty']} ticker {counts['ticker']} unresolved {counts['unresolved']}",
                    flush=True,
                )
                last_report = got
    return {
        "bytes": got,
        "record_starts": counts["record_starts"],
        "empty_symbol": counts["empty"],
        "ticker_symbol": counts["ticker"],
        "other_symbol": counts["other"],
        "no_url_after_symbol": counts["no_url"],
        "unresolved": counts["unresolved"],
        "timestamp_not_at_line_start": counts["timestamp_not_at_line_start"],
        "top_symbols": symbols.most_common(8),
        "focus_symbols": dict(focus),
        "raw_comma_ticker_comma": dict(raw),
    }


SAMPLES = [
    ("nas_before_flat1", NAS, 17_840_000_000, 17_842_000_000),
    ("nas_flat1_start", NAS, 17_860_000_000, 17_862_000_000),
    ("nas_flat1_mid", NAS, 18_800_000_000, 18_802_000_000),
    ("nas_flat1_end", NAS, 19_850_000_000, 19_852_000_000),
    ("nas_recovery", NAS, 20_000_000_000, 20_002_000_000),
    ("nas_flat2_start", NAS, 20_400_000_000, 20_402_000_000),
    ("nas_flat2_mid", NAS, 22_000_000_000, 22_002_000_000),
    ("nas_flat2_end", NAS, 23_230_000_000, 23_232_000_000),
    ("all_before_flat1", ALL, 300_000_000, 302_000_000),
    ("all_flat1_start", ALL, 400_000_000, 402_000_000),
    ("all_flat1_mid", ALL, 1_300_000_000, 1_302_000_000),
    ("all_flat1_end", ALL, 2_300_000_000, 2_302_000_000),
    ("all_recovery", ALL, 2_500_000_000, 2_502_000_000),
    ("all_flat2_start", ALL, 2_900_000_000, 2_902_000_000),
    ("all_flat2_mid", ALL, 4_200_000_000, 4_202_000_000),
    ("all_flat2_end", ALL, 5_700_000_000, 5_702_000_000),
]


def main() -> None:
    prefer_ipv4()
    chosen = SAMPLES if "--sample" in sys.argv else REGIONS
    out = {}
    for name, url, start, end in chosen:
        print(f"scan {name} {start}-{end}", flush=True)
        out[name] = scan(url, start, end, name)
        print(json.dumps({name: out[name]}), flush=True)
    path = "eval/results/phase1_fnspid_stall_check.json"
    with open(path, "w") as handle:
        json.dump(out, handle, indent=2)
    print("wrote", path, flush=True)


if __name__ == "__main__":
    main()
