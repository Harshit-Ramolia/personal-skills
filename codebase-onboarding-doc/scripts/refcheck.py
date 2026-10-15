#!/usr/bin/env python3
"""Check every path:line reference in a markdown doc against a pinned checkout.

Usage:
    refcheck.py --doc DOC --repo PINNED_CHECKOUT [--alias NAME=GIT_DIR@REF ...]
                [--sample N] [--json OUT]

Reference forms recognised:
    path/to/file.py:120          path/to/file.py:120-180
    `path/to/file.py:120`        name@path/to/file.py:120   (file read from REF in GIT_DIR)
    name@`path/to/file.py:120`   (alias outside the backticks also works)
    `:300-320`                   shorthand for the last full ref on the same doc line

Results:
    OK         file found and the line range is inside it
    CONTEXT    valid, but resolved from context: a short path (e.g. runner.py) that matches
               several files, or a shorthand (`:120`) with no full ref on its own line (as in
               a table under a heading that names the file). Resolved to the file named
               nearest above it in the same section.
    BAD        file found but the line range is outside it (or reversed)
    MISSING    no such file (after a unique suffix match and any --extra-dir)
    AMBIGUOUS  short path that matches several files and no nearby full path settles it
    ORPHAN     backticked shorthand (`:120`) with no full path before it in its section
    WARN       range is valid but points at a blank line (single line) or is mostly blank

Exit status is 1 when any BAD or MISSING ref exists, else 0. The script only reads
files and runs `git ls-files` / `git show`; it never executes repo code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

EXTLESS = r"Dockerfile(?:\.[\w.\-]+)?|Makefile|Justfile|Procfile|Jenkinsfile|Gemfile|Rakefile|BUILD|WORKSPACE"
PATH = r"(?:[\w.\-]+/)*(?:[\w\-][\w.\-]*\.[A-Za-z][A-Za-z0-9]{0,9}|" + EXTLESS + r")"
FULL = re.compile(
    r"(?<![\w/.\-@:])(?:(?P<alias>[A-Za-z][\w\-]*)@`?)?(?P<path>" + PATH + r"):(?P<a>\d+)(?:-(?P<b>\d+))?(?![\d:])"
)
SHORT = re.compile(r"(?:(?<=[\s(,`])|^):(?P<a>\d+)(?:-(?P<b>\d+))?(?=[`\s),.;]|$)")
ORPHAN = re.compile(r"(?:(?P<alias>[A-Za-z][\w\-]*)@)?`:(?P<a>\d+)(?:-(?P<b>\d+))?`")
MENTION = re.compile(r"(?<![\w/.\-])(?:(?P<alias>[A-Za-z][\w\-]*)@`?)?(?P<path>(?:[\w.\-]+/)+[\w\-][\w.\-]*\.[A-Za-z][A-Za-z0-9]{0,9})")
HEADING = re.compile(r"^#{1,6}\s")
NOT_FILES = re.compile(r"^(?:[\w\-]+\.)+(?:com|org|net|io|ai|dev|co|app|cloud|local|internal)$", re.I)


def git(git_dir: str, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", git_dir, *argv], capture_output=True, text=True, check=False)


class Resolver:
    def __init__(self, repo: str, aliases: dict[str, tuple[str, str]], extra_dirs: list[str] | None = None):
        self.repo = os.path.realpath(repo)
        self.aliases = aliases
        self.extra_dirs = [os.path.realpath(d) for d in (extra_dirs or [])]
        self.cache: dict = {}
        r = git(self.repo, "ls-files", "-z")
        if r.returncode == 0:
            self.files = [p for p in r.stdout.split("\0") if p]
        else:
            self.files = []
            for root, dirs, names in os.walk(self.repo):
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".venv")]
                self.files += [os.path.relpath(os.path.join(root, n), self.repo) for n in names]
        self.fileset = set(self.files)
        self.alias_files: dict[str, set] = {}

    def _alias_listing(self, alias: str) -> set:
        if alias not in self.alias_files:
            git_dir, ref = self.aliases[alias]
            r = git(git_dir, "ls-tree", "-r", "--name-only", "-z", ref)
            self.alias_files[alias] = set(p for p in r.stdout.split("\0") if p) if r.returncode == 0 else set()
        return self.alias_files[alias]

    def resolve(self, alias: str | None, path: str, context: list[str] | None = None):
        """Return (status, resolved_path, lines|None, candidates).

        context: full paths mentioned above the ref in the same section, nearest first.
        """
        if path.startswith("/") or ".." in path.split("/"):
            return "MISSING", path, None, []
        listing = self._alias_listing(alias) if alias else self.fileset
        if path in listing:
            return "FOUND", path, self.lines(alias, path), []
        cands = [f for f in listing if f.endswith("/" + path)]
        if len(cands) == 1:
            return "FOUND", cands[0], self.lines(alias, cands[0]), []
        if len(cands) > 1:
            for mention in context or []:
                hit = [c for c in cands if c == mention or c.endswith("/" + mention) or mention.endswith("/" + c)]
                if len(hit) == 1:
                    return "CONTEXT", hit[0], self.lines(alias, hit[0]), []
            return "AMBIGUOUS", path, None, sorted(cands)[:5]
        if not alias:
            for d in self.extra_dirs:
                full = os.path.realpath(os.path.join(d, path))
                if full.startswith(d + os.sep) and os.path.isfile(full):
                    key = ("extra", full)
                    if key not in self.cache:
                        with open(full, errors="ignore") as fh:
                            self.cache[key] = fh.read().splitlines()
                    return "FOUND", full, self.cache[key], []
        return "MISSING", path, None, []

    def lines(self, alias: str | None, path: str):
        key = (alias, path)
        if key in self.cache:
            return self.cache[key]
        text = None
        if alias:
            git_dir, ref = self.aliases[alias]
            r = git(git_dir, "show", f"{ref}:{path}")
            if r.returncode == 0:
                text = r.stdout
        else:
            full = os.path.realpath(os.path.join(self.repo, path))
            if full.startswith(self.repo + os.sep) and os.path.isfile(full):
                with open(full, errors="ignore") as fh:
                    text = fh.read()
        lines = text.splitlines() if text is not None else None
        self.cache[key] = lines
        return lines


def parse_aliases(items: list[str]) -> dict[str, tuple[str, str]]:
    out = {}
    for it in items or []:
        m = re.fullmatch(r"([A-Za-z][\w\-]*)=(.+)@([^@\s]+)", it)
        if not m:
            sys.exit(f"bad --alias {it!r}; expected NAME=GIT_DIR@REF")
        name, git_dir, ref = m.groups()
        if ref.startswith("-"):
            sys.exit(f"bad ref in --alias {it!r}")
        out[name] = (os.path.realpath(git_dir), ref)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--repo", required=True, help="pinned checkout the refs were written against")
    ap.add_argument("--alias", action="append", default=[], help="NAME=GIT_DIR@REF for NAME@path:line refs")
    ap.add_argument("--extra-dir", action="append", default=[],
                    help="other local source roots to try for paths not in the repo (e.g. a second checkout)")
    ap.add_argument("--sample", type=int, default=0, help="print the cited code for N refs spread across the doc")
    ap.add_argument("--json", help="write all results as JSON here")
    a = ap.parse_args()

    aliases = parse_aliases(a.alias)
    res = Resolver(a.repo, aliases, a.extra_dir)
    with open(a.doc, errors="ignore") as fh:
        doc_lines = fh.read().splitlines()

    results = []
    section_mentions: list[tuple] = []  # (alias, path) seen in the current section, oldest first
    for ln, line in enumerate(doc_lines, 1):
        if HEADING.match(line):
            section_mentions = []
        context = [p for _, p in reversed(section_mentions)]
        spans = []
        for m in FULL.finditer(line):
            alias, path = m.group("alias"), m.group("path")
            if alias and alias not in aliases:
                # e.g. an email address or an alias you forgot to pass; check on the pinned repo instead
                alias = None
            if NOT_FILES.match(path):
                continue
            spans.append((m.start(), m.end(), alias, path, int(m.group("a")), m.group("b")))
        for i, (_, end, alias, path, lo, hi) in enumerate(spans):
            results.append(check(res, ln, line, alias, path, lo, int(hi) if hi else lo, short=False, context=context))
            # shorthand refs (`:300-320`) between this full ref and the next one belong to this file
            nxt = spans[i + 1][0] if i + 1 < len(spans) else len(line)
            for sm in SHORT.finditer(line, end, nxt):
                b = sm.group("b")
                results.append(check(res, ln, line, alias, path, int(sm.group("a")), int(b) if b else int(sm.group("a")),
                                     short=True, context=context))
        first = spans[0][0] if spans else len(line)
        line_mentions = [(m.group("alias") if m.group("alias") in aliases else None, m.group("path"))
                         for m in MENTION.finditer(line, 0, first)]
        for om in ORPHAN.finditer(line, 0, first):
            oalias = om.group("alias") if om.group("alias") in aliases else None
            lo, hi = int(om.group("a")), int(om.group("b") or om.group("a"))
            # try files named above it in this section, nearest first; keep the first one the range fits
            anchors = list(dict.fromkeys(p for al, p in reversed(section_mentions + line_mentions) if al == oalias))
            row = None
            for anchor in anchors:
                cand = check(res, ln, line, oalias, anchor, lo, hi, short=True, context=context)
                cand["ref"] = f"{om.group(0)} -> {anchor}"
                if cand["status"] == "OK":
                    row = cand
                    break
                if row is None or (cand["status"] == "WARN" and row["status"] != "WARN"):
                    row = cand  # fallback: first in-range (blank) hit, else the nearest anchor
            if row is not None:
                if row["status"] == "OK":
                    row["status"] = "CONTEXT"
                results.append(row)
            else:
                results.append({"doc_line": ln, "doc_text": line.strip(), "alias": oalias, "path": None,
                                "resolved": None, "lo": lo, "hi": hi, "ref": om.group(0), "candidates": [],
                                "file_lines": None, "status": "ORPHAN"})
        section_mentions += [(m.group("alias") if m.group("alias") in aliases else None, m.group("path"))
                             for m in MENTION.finditer(line)]

    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"refs: {len(results)}  " + "  ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for status in ("BAD", "MISSING", "AMBIGUOUS", "ORPHAN", "WARN", "CONTEXT"):
        rows = [r for r in results if r["status"] == status]
        if not rows:
            continue
        print(f"\n{status} ({len(rows)}):")
        for r in rows[:200]:
            extra = ""
            if status == "BAD":
                extra = f" (file has {r['file_lines']} lines)"
            elif status == "AMBIGUOUS":
                extra = f" candidates: {', '.join(r['candidates'])}"
            elif status == "CONTEXT" and "->" not in r["ref"]:
                extra = f"  -> {r['resolved']}"
            elif status == "ORPHAN":
                extra = "  (no full path before it in this section; write the full path)"
            print(f"  doc:{r['doc_line']}  {r['ref']}{extra}")

    if a.sample:
        ok = [r for r in results if r["status"] in ("OK", "CONTEXT", "WARN")]
        step = max(1, len(ok) // a.sample) if ok else 1
        print(f"\nSAMPLE ({min(a.sample, len(ok))} refs; check that the code shows what the doc claims):")
        for r in ok[::step][: a.sample]:
            lines = res.lines(r["alias"], r["resolved"]) or []
            lo, hi = r["lo"], r["hi"]
            show = list(range(lo, min(hi, lo + 4) + 1))
            if hi > lo + 6:
                show += [hi - 1, hi]
            print(f"\n- doc:{r['doc_line']}: {r['doc_text'][:220]}")
            print(f"  {r['ref']}")
            for k in show:
                if 1 <= k <= len(lines):
                    print(f"    {k:>6} | {lines[k - 1][:160]}")

    if a.json:
        with open(a.json, "w") as fh:
            json.dump(results, fh, indent=1)
    return 1 if counts.get("BAD") or counts.get("MISSING") else 0


def check(res: Resolver, ln: int, line: str, alias, path, lo: int, hi: int, short: bool,
          context: list[str] | None = None) -> dict:
    status, target, lines, cands = res.resolve(alias, path, context)
    ref = f"{alias + '@' if alias else ''}{path}:{lo}{'-' + str(hi) if hi != lo else ''}{' (shorthand)' if short else ''}"
    row = {"doc_line": ln, "doc_text": line.strip(), "alias": alias, "path": path, "resolved": target,
           "lo": lo, "hi": hi, "ref": ref, "candidates": cands, "file_lines": None}
    if status not in ("FOUND", "CONTEXT"):
        row["status"] = status
        return row
    if lines is None:
        row["status"] = "MISSING"
        return row
    n = len(lines)
    row["file_lines"] = n
    if lo < 1 or hi < lo or hi > n:
        row["status"] = "BAD"
        return row
    cited = lines[lo - 1:hi]
    blank = sum(1 for c in cited if not c.strip())
    if (hi == lo and blank) or (hi > lo and blank * 2 > len(cited)):
        row["status"] = "WARN"
    else:
        row["status"] = "CONTEXT" if status == "CONTEXT" else "OK"
    return row


if __name__ == "__main__":
    sys.exit(main())
