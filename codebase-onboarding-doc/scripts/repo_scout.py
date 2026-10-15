#!/usr/bin/env python3
"""Read-only inventory of a repository, used to plan an onboarding doc.

Usage:
    repo_scout.py <repo_path> [--out scout.json] [--top 25]

Prints a short human summary to stdout and, with --out, writes the full JSON.
It never executes repo code and makes no network calls. It only reads files
and runs read-only git commands (ls-files, rev-parse, log, remote, shortlog).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

SKIP_PARTS = {
    "node_modules", "vendor", "vendored", "third_party", "thirdparty", "dist", "build",
    ".venv", "venv", "__pycache__", ".git", "site-packages", ".next", "target",
    "coverage", ".tox", ".mypy_cache", ".pytest_cache", ".gradle", "Pods",
}
LOCKFILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
    "Cargo.lock", "go.sum", "Gemfile.lock", "composer.lock", "Pipfile.lock",
}
GENERATED_SUFFIXES = (".min.js", ".min.css", ".map", ".snap", ".pb.go", "_pb2.py", ".lock")
LANG = {
    ".py": "Python", ".pyi": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".c": "C", ".h": "C/C++ header", ".hpp": "C/C++ header", ".swift": "Swift",
    ".scala": "Scala", ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".sql": "SQL",
    ".vue": "Vue", ".svelte": "Svelte", ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir",
    ".lua": "Lua", ".r": "R", ".jl": "Julia", ".m": "Objective-C", ".clj": "Clojure",
    ".hs": "Haskell", ".ml": "OCaml", ".zig": "Zig", ".tf": "Terraform", ".proto": "Protobuf",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".json": "JSON", ".ini": "INI",
    ".md": "Markdown", ".rst": "reStructuredText", ".ipynb": "Notebook",
}
NON_CODE = {"YAML", "TOML", "JSON", "INI", "Markdown", "reStructuredText", "Notebook", "HTML", "CSS", "SCSS"}
MAX_BYTES = 2_000_000
MARKER_SCAN_LIMIT = 30_000
MARKERS = {
    "python __main__": re.compile(r"""if __name__ == ['"]__main__['"]"""),
    "argparse": re.compile(r"argparse\.ArgumentParser\("),
    "click": re.compile(r"@click\.(command|group)"),
    "typer": re.compile(r"typer\.Typer\("),
    "fastapi": re.compile(r"FastAPI\("),
    "flask": re.compile(r"Flask\(__name__"),
    "django": re.compile(r"django\.(setup|core\.management)"),
    "modal app": re.compile(r"modal\.App\("),
    "temporal": re.compile(r"from temporalio|@workflow\.defn"),
    "celery": re.compile(r"Celery\("),
    "express": re.compile(r"express\(\)"),
    "next.js page/route": re.compile(r"export default function (Page|Layout)|export async function (GET|POST)\("),
    "go main": re.compile(r"^package main\b", re.M),
    "rust main": re.compile(r"^fn main\(", re.M),
    "pydantic models": re.compile(r"\(BaseModel\)"),
    "sqlalchemy": re.compile(r"declarative_base\(|DeclarativeBase\b"),
    "abstract base classes": re.compile(r"\(ABC\)|metaclass=ABCMeta"),
}
TEST_DIR_NAMES = {"tests", "test", "spec", "specs", "__tests__", "e2e", "testing"}
TEST_FILE = re.compile(r"(^test_.*\.py$|.*_test\.(py|go)$|.*\.(test|spec)\.(t|j)sx?$|.*Test\.(java|kt)$)")


def git(repo: str, *argv: str, timeout: int = 120) -> str | None:
    try:
        r = subprocess.run(["git", "-C", repo, *argv], capture_output=True, text=True,
                           timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def list_files(repo: str) -> tuple[list[str], bool]:
    out = git(repo, "ls-files", "-z")
    if out is not None:
        return [p for p in out.split("\0") if p], True
    files = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_PARTS and not d.startswith(".")]
        for n in names:
            files.append(os.path.relpath(os.path.join(root, n), repo))
    return files, False


def lang_of(path: str) -> str | None:
    base = os.path.basename(path)
    if base == "Dockerfile" or base.startswith("Dockerfile."):
        return "Docker"
    if base in ("Makefile", "Justfile", "justfile"):
        return "Make"
    return LANG.get(os.path.splitext(base)[1].lower())


def is_vendored(path: str) -> bool:
    parts = path.split("/")
    base = parts[-1]
    return (any(p in SKIP_PARTS for p in parts[:-1]) or base in LOCKFILES
            or base.endswith(GENERATED_SUFFIXES))


def read_text(full: str) -> str | None:
    try:
        if os.path.getsize(full) > MAX_BYTES:
            return None
        with open(full, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="ignore")


def mask_url(url: str) -> str:
    return re.sub(r"//[^/@\s]+@", "//***@", url)


def parse_entry_points(repo: str, files: list[str]) -> dict:
    eps: dict = {}
    fset = set(files)
    if "pyproject.toml" in fset and tomllib:
        try:
            with open(os.path.join(repo, "pyproject.toml"), "rb") as fh:
                pp = tomllib.load(fh)
            proj = pp.get("project", {})
            eps["pyproject"] = {
                "name": proj.get("name"),
                "requires_python": proj.get("requires-python"),
                "scripts": proj.get("scripts", {}) or pp.get("tool", {}).get("poetry", {}).get("scripts", {}),
                "optional_dependency_groups": sorted((proj.get("optional-dependencies") or {}).keys()),
                "tools_configured": sorted(pp.get("tool", {}).keys()),
            }
        except (OSError, ValueError) as exc:
            eps["pyproject"] = {"error": str(exc)}
    pkgs = [f for f in files if os.path.basename(f) == "package.json" and f.count("/") <= 2 and not is_vendored(f)]
    for f in pkgs[:15]:
        try:
            with open(os.path.join(repo, f)) as fh:
                pj = json.load(fh)
            eps.setdefault("package_json", {})[f] = {
                "name": pj.get("name"), "main": pj.get("main"), "bin": pj.get("bin"),
                "scripts": sorted((pj.get("scripts") or {}).keys()), "workspaces": pj.get("workspaces"),
            }
        except (OSError, ValueError):
            continue
    for f in [x for x in files if os.path.basename(x) == "Cargo.toml" and x.count("/") <= 2][:10]:
        txt = read_text(os.path.join(repo, f)) or ""
        eps.setdefault("cargo", {})[f] = re.findall(r'^name\s*=\s*"([^"]+)"', txt, re.M)[:5]
    mk = [f for f in files if os.path.basename(f) in ("Makefile", "Justfile", "justfile") and f.count("/") <= 1]
    for f in mk:
        txt = read_text(os.path.join(repo, f)) or ""
        targets = [t for t in re.findall(r"^([A-Za-z0-9_][A-Za-z0-9_.\-/]*)\s*:(?!=)", txt, re.M) if t != ".PHONY"]
        eps.setdefault("make_targets", {})[f] = targets[:40]
    eps["go_main_dirs"] = sorted({os.path.dirname(f) or "." for f in files if f.endswith("/main.go") or f == "main.go"})[:20]
    eps["dockerfiles"] = [f for f in files if lang_of(f) == "Docker" and not is_vendored(f)][:30]
    eps["compose_files"] = [f for f in files if re.search(r"(^|/)(docker-)?compose[\w.\-]*\.ya?ml$", f)][:10]
    eps["procfiles"] = [f for f in files if os.path.basename(f) == "Procfile"][:5]
    eps["helm_charts"] = [os.path.dirname(f) for f in files if os.path.basename(f) == "Chart.yaml"][:10]
    eps["terraform_files"] = sum(1 for f in files if f.endswith(".tf"))
    return eps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("--out", help="write full JSON here")
    ap.add_argument("--top", type=int, default=25, help="how many largest files to list")
    a = ap.parse_args()

    repo = os.path.realpath(a.repo)
    if not os.path.isdir(repo):
        print(f"not a directory: {repo}", file=sys.stderr)
        return 2
    files, is_git = list_files(repo)

    loc_by_lang: Counter = Counter()
    files_by_lang: Counter = Counter()
    top: dict = defaultdict(lambda: {"files": 0, "loc": 0, "code_loc": 0, "langs": Counter(), "vendored_files": 0})
    sub: dict = defaultdict(lambda: defaultdict(lambda: {"files": 0, "loc": 0}))
    sizes: list[tuple[int, str]] = []
    markers: dict = defaultdict(list)
    test_files = 0
    test_loc = 0
    test_dirs: Counter = Counter()
    test_by_top: Counter = Counter()
    scanned = 0

    for rel in files:
        full = os.path.join(repo, rel)
        if not os.path.isfile(full) or os.path.islink(full):
            continue
        parts = rel.split("/")
        tl = parts[0] if len(parts) > 1 else "(root files)"
        t = top[tl]
        t["files"] += 1
        if is_vendored(rel):
            t["vendored_files"] += 1
            continue
        lang = lang_of(rel)
        text = read_text(full) if lang else None
        loc = text.count("\n") + (1 if text and not text.endswith("\n") else 0) if text else 0
        if lang:
            loc_by_lang[lang] += loc
            files_by_lang[lang] += 1
            t["langs"][lang] += loc
        t["loc"] += loc
        if lang and lang not in NON_CODE:
            t["code_loc"] += loc
            sizes.append((loc, rel))
        if len(parts) > 2:
            s = sub[tl][parts[1]]
            s["files"] += 1
            s["loc"] += loc
        if TEST_FILE.match(parts[-1]) or any(p in TEST_DIR_NAMES for p in parts[:-1]):
            if lang and lang not in NON_CODE:
                test_files += 1
                test_loc += loc
                test_by_top[tl] += 1
                tdir = next((("/".join(parts[: i + 1])) for i, p in enumerate(parts[:-1]) if p in TEST_DIR_NAMES), os.path.dirname(rel))
                test_dirs[tdir] += 1
        if text and lang and lang not in NON_CODE and scanned < MARKER_SCAN_LIMIT:
            scanned += 1
            for name, rx in MARKERS.items():
                if rx.search(text):
                    markers[name].append(rel)

    code_loc = sum(v for k, v in loc_by_lang.items() if k not in NON_CODE)
    # size the doc by the code a reader must understand; tests are read selectively
    sizing_loc = max(code_loc - test_loc, 0)
    if sizing_loc < 15_000:
        tier, readers, target, claims = "small", "3-4", "25,000–45,000", 30
    elif code_loc < 150_000:
        tier, readers, target, claims = "medium", "5-6", "50,000–80,000", 45
    else:
        tier, readers, target, claims = "large", "7-8", "80,000–130,000", 60

    gitinfo: dict = {"is_git": is_git}
    if is_git:
        gitinfo["head"] = (git(repo, "rev-parse", "HEAD") or "").strip()
        gitinfo["branch"] = (git(repo, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
        gitinfo["head_commit"] = (git(repo, "log", "-1", "--format=%h %cs %s") or "").strip()
        gitinfo["remotes"] = sorted({mask_url(l.split()[1]) for l in (git(repo, "remote", "-v") or "").splitlines() if len(l.split()) > 1})
        gitinfo["dirty"] = bool((git(repo, "status", "--porcelain", "--untracked-files=no") or "").strip())
        log = git(repo, "log", "--since=90.days", "--name-only", "--format=@@%h", timeout=300) or ""
        commits = sum(1 for l in log.splitlines() if l.startswith("@@"))
        hot: Counter = Counter()
        for l in log.splitlines():
            if l and not l.startswith("@@"):
                p = l.split("/")
                hot["/".join(p[:2]) if len(p) > 2 else p[0]] += 1
        gitinfo["commits_last_90d"] = commits
        gitinfo["hot_paths_last_90d"] = hot.most_common(15)
        sl = git(repo, "shortlog", "-sn", "--since=90.days", "HEAD") or ""
        gitinfo["top_authors_last_90d"] = [l.strip() for l in sl.splitlines()[:8]]

    ci = [f for f in files if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))]
    ci_info = []
    for f in ci:
        txt = read_text(os.path.join(repo, f)) or ""
        m = re.search(r"^name:\s*(.+)$", txt, re.M)
        ci_info.append({"file": f, "name": m.group(1).strip().strip("'\"") if m else None})
    other_ci = [f for f in files if f in (".gitlab-ci.yml", ".circleci/config.yml", "Jenkinsfile", "azure-pipelines.yml", ".buildkite/pipeline.yml")]

    docs_names = re.compile(r"^(README|CLAUDE|AGENTS|CONTRIBUTING|ARCHITECTURE|DEVELOPMENT|HACKING|SECURITY|CODEOWNERS)(\.\w+)?$", re.I)
    docs = {
        "root_docs": [f for f in files if "/" not in f and docs_names.match(f)],
        "nested_agent_files": [f for f in files if os.path.basename(f) in ("CLAUDE.md", "AGENTS.md") and "/" in f][:30],
        "docs_dir_files": sum(1 for f in files if f.startswith(("docs/", "doc/"))),
        "adr_files": [f for f in files if re.search(r"(^|/)(adr|adrs|decisions)/", f, re.I)][:20],
        "pr_template": [f for f in files if "PULL_REQUEST_TEMPLATE" in f.upper()],
        "cursor_rules": [f for f in files if f.startswith(".cursor/") or f == ".cursorrules"][:10],
    }

    top_level = []
    for name, t in sorted(top.items(), key=lambda kv: -kv[1]["loc"]):
        top_level.append({
            "name": name, "files": t["files"], "loc": t["loc"], "code_loc": t["code_loc"],
            "vendored_files": t["vendored_files"],
            "langs": [f"{k}:{v}" for k, v in t["langs"].most_common(3)],
        })
    biggest_dirs = [x["name"] for x in top_level if x["name"] != "(root files)"][:6]
    second_level = {
        d: sorted(({"name": k, **v} for k, v in sub[d].items()), key=lambda x: -x["loc"])[:12]
        for d in biggest_dirs
    }

    result = {
        "repo": repo,
        "git": gitinfo,
        "totals": {"tracked_files": len(files), "code_loc": code_loc, "test_code_loc": test_loc,
                   "non_test_code_loc": sizing_loc, "all_loc": sum(loc_by_lang.values())},
        "suggested": {"tier": tier, "readers": readers, "target_chars": target, "claims_to_check": claims},
        "languages": [{"lang": k, "loc": v, "files": files_by_lang[k]} for k, v in loc_by_lang.most_common(15)],
        "top_level": top_level,
        "second_level": second_level,
        "largest_files": [{"path": p, "loc": n} for n, p in sorted(sizes, reverse=True)[: a.top]],
        "entry_points": parse_entry_points(repo, files),
        "framework_markers": {k: {"count": len(v), "examples": v[:8]} for k, v in sorted(markers.items(), key=lambda kv: -len(kv[1]))},
        "ci": {"github_workflows": ci_info, "other": other_ci},
        "tests": {"test_files": test_files, "test_code_loc": test_loc,
                  "test_files_by_top_level": test_by_top.most_common(10),
                  "test_dirs_with_5plus_files": [(d, c) for d, c in test_dirs.most_common(15) if c >= 5]},
        "docs": docs,
    }

    if a.out:
        with open(a.out, "w") as fh:
            json.dump(result, fh, indent=1)

    g = gitinfo
    print(f"repo: {repo}")
    if is_git:
        print(f"git: {g.get('branch') if g.get('branch') != 'HEAD' else '(detached)'} @ {g.get('head_commit')}{'  (DIRTY working tree: uncommitted changes are not covered)' if g.get('dirty') else ''}")
        print(f"remotes: {', '.join(g.get('remotes') or []) or '-'}")
        print(f"activity (90d): {g.get('commits_last_90d')} commits; hot: {', '.join(p for p, _ in g.get('hot_paths_last_90d', [])[:8])}")
    print(f"size: {len(files)} tracked files, {code_loc:,} code lines ({test_loc:,} of them tests) -> tier {tier} by {sizing_loc:,} non-test lines (readers {readers}, target {target} chars, check {claims} claims)")
    print("languages: " + ", ".join(f"{x['lang']} {x['loc']:,}" for x in result["languages"][:8]))
    print("top-level (by lines):")
    for x in top_level[:20]:
        print(f"  {x['name']:<28} {x['files']:>6} files {x['loc']:>9,} lines  {' '.join(x['langs'])}{'  (+%d vendored)' % x['vendored_files'] if x['vendored_files'] else ''}")
    print("largest files: " + ", ".join(f"{x['path']} ({x['loc']:,})" for x in result["largest_files"][:8]))
    ep = result["entry_points"]
    if ep.get("pyproject", {}).get("scripts"):
        print("python scripts: " + ", ".join(f"{k}={v}" for k, v in ep["pyproject"]["scripts"].items()))
    for f, pj in (ep.get("package_json") or {}).items():
        print(f"package.json {f}: scripts={pj['scripts'][:12]} bin={pj['bin']}")
    for f, t in (ep.get("make_targets") or {}).items():
        print(f"make targets ({f}): {', '.join(t[:20])}")
    if ep.get("dockerfiles"):
        print("dockerfiles: " + ", ".join(ep["dockerfiles"][:8]))
    print("markers: " + ", ".join(f"{k}={v['count']}" for k, v in list(result["framework_markers"].items())[:10]))
    print(f"ci: {', '.join(c['file'] for c in ci_info) or '-'} {' '.join(other_ci)}")
    print(f"tests: {test_files} test files ({test_loc:,} lines); by top-level: {', '.join(f'{d} {c}' for d, c in test_by_top.most_common(5))}")
    print(f"docs: {', '.join(docs['root_docs']) or '-'}; docs/ files: {docs['docs_dir_files']}; nested agent files: {len(docs['nested_agent_files'])}")
    if a.out:
        print(f"full JSON: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
