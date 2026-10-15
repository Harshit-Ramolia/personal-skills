#!/usr/bin/env python3
"""Lint an onboarding doc: secret leaks, unverified marks, structure, reading time.

Usage:
    doc_lint.py DOC [--careful-wpm 100] [--skim-wpm 200]

Secret-like matches are printed masked (first 4 characters plus length), never in
full. Exit status is 1 when any secret-like string is found, else 0.
"""
from __future__ import annotations

import argparse
import re
import sys

SECRETS = [
    ("aws access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai-style key", re.compile(r"\bsk-(?:proj-|live-|test-)?[A-Za-z0-9_\-]{24,}")),
    ("github token", re.compile(r"\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}")),
    ("slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("credentials in url", re.compile(r"[a-z][a-z0-9+.\-]*://[^/\s:@]+:[^/\s@]{3,}@")),
]
ASSIGN = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|pwd|access[_-]?key)\b\s*[:=]\s*['\"]?([A-Za-z0-9_\-/+=.]{16,})"
)
PLACEHOLDER = re.compile(r"^(?:[A-Z0-9_]+|x+|\*+|\.+|your[_\-].*|example.*|placeholder.*|changeme.*)$", re.I)
REF = re.compile(r"(?:[\w.\-]+/)*[\w\-][\w.\-]*\.[A-Za-z][A-Za-z0-9]{0,9}:\d+")
FENCE = re.compile(r"^\s*```")
LABEL = re.compile(r"\[(FREE|READS PROD|COSTS MONEY|TOUCHES PROD|NETWORK)\]")

STRUCTURE = [
    ("pinned header", re.compile(r"(?i)pinned to")),
    ("10-minute version", re.compile(r"(?i)10-minute version")),
    ("five-sentence box", re.compile(r"(?i)if you remember only")),
    ("repo tour", re.compile(r"(?im)^##\s.*repo tour")),
    ("life of one unit", re.compile(r"(?im)^##\s.*life of one")),
    ("recipes", re.compile(r"(?im)^##\s.*(recipe|how-to|how to)")),
    ("gotchas", re.compile(r"(?im)^##\s.*(gotcha|trap)")),
    ("first week", re.compile(r"(?im)^##\s.*first week")),
    ("glossary", re.compile(r"(?im)^##\s.*glossary")),
    ("stale docs", re.compile(r"(?im)^##\s.*stale")),
]


def mask(s: str) -> str:
    return f"{s[:4]}… ({len(s)} chars)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc")
    ap.add_argument("--careful-wpm", type=int, default=100, help="dense technical reading speed")
    ap.add_argument("--skim-wpm", type=int, default=200)
    a = ap.parse_args()

    text = open(a.doc, errors="ignore").read()
    lines = text.splitlines()

    hits = []
    for ln, line in enumerate(lines, 1):
        for name, rx in SECRETS:
            for m in rx.finditer(line):
                hits.append((ln, name, mask(m.group(0))))
        for m in ASSIGN.finditer(line):
            val = m.group(2)
            if not PLACEHOLDER.match(val) and not re.search(r"[<>${}]", line[m.start(2) - 2:m.end(2) + 1]):
                hits.append((ln, f"possible {m.group(1).lower()} value", mask(val)))

    # count every "unverified" mention except the header's explanation of the convention
    unverified = [ln for ln, l in enumerate(lines, 1)
                  if "unverified" in l.lower() and not re.search(r"(?i)marked \**\(unverified\)", l)]

    parts = []
    cur = {"title": "(header)", "words": 0, "code_words": 0}
    in_fence = False
    for line in lines:
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith("## "):
            parts.append(cur)
            cur = {"title": line[3:].strip(), "words": 0, "code_words": 0}
            continue
        w = len(line.split())
        cur["words"] += w
        if in_fence:
            cur["code_words"] += w
    parts.append(cur)

    total_words = sum(p["words"] for p in parts)
    refs = len(REF.findall(text))
    labels = len(LABEL.findall(text))

    print(f"doc: {a.doc}")
    print(f"size: {len(text):,} chars, {total_words:,} words, {len(lines):,} lines, ~{refs} path:line refs, {labels} cost labels")
    print(f"reading time: careful ~{total_words / a.careful_wpm / 60:.1f} h ({a.careful_wpm} wpm), skim ~{total_words / a.skim_wpm / 60:.1f} h ({a.skim_wpm} wpm)")
    print(f"unverified mentions: {len(unverified)}" + (f" at lines {', '.join(map(str, unverified[:30]))}" if unverified else ""))

    print("\nstructure:")
    for name, rx in STRUCTURE:
        print(f"  [{'x' if rx.search(text) else ' '}] {name}")

    print("\nparts (words, minutes careful):")
    for p in parts:
        if p["words"] == 0 and p["title"] == "(header)":
            continue
        print(f"  {p['words']:>6}  {p['words'] / a.careful_wpm:>5.1f} min  {p['title'][:70]}")

    if hits:
        print(f"\nSECRET-LIKE STRINGS ({len(hits)}): remove or replace with the env var / secret name")
        for ln, name, m in hits:
            print(f"  line {ln}: {name}: {m}")
        return 1
    print("\nsecret scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
