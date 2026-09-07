"""Forge dashboards — stdlib project + ecosystem health boards, NO AI, offline.

  project(roots_of_journal_tasks)   -> board of the Forge task journal + corpus
  ecosystem(roots)                  -> board across sibling repo checkouts,
                                       reading each repo's own CHANGELOG.md

Deterministic and fail-closed: a corrupt/missing journal refuses loudly rather
than guessing; a repo without its own CHANGELOG/README is reported in a
"missing" lane (documentation doctrine rule 5), not silently skipped.
Emits plain Markdown for humans and a JSON dict for machines.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field

from . import __version__
from .corpus import CorpusRefusal, load as load_corpus
from .journal import Journal
from .task import Status, StatusRefusal, Task


class DashRefusal(Exception):
    """Raised when a board cannot be built — callers surface it, never guess."""


_TASK_STATUS_ORDER = [s.value for s in Status]
_TOP_RELEASE = re.compile(r"^## \[(?P<v>[^\]]+)\]")

_RELEASE_SECTION = re.compile(r"^### (?P<name>[A-Za-z].*)$")


def _latest_per_id(journal: Journal) -> list[Task]:
    by_id: dict[str, Task] = {}
    for task in journal.read():
        by_id[task.task_id] = task
    return sorted(by_id.values(), key=lambda t: t.task_id)


def project_board(journal_path: str, corpus_path: str | None = None,
                  repo_root: str | None = None) -> dict:
    """Aggregate the Forge project board from the task journal + builder corpus."""
    journal = Journal(journal_path)
    try:
        tasks = _latest_per_id(journal)
    except StatusRefusal as exc:
        raise DashRefusal(str(exc)) from None

    counts = {s: 0 for s in _TASK_STATUS_ORDER}
    for task in tasks:
        counts[task.status.value] += 1
    merged = counts[Status.MERGED.value]
    blocked = [t.task_id for t in tasks if t.status == Status.BLOCKED]
    total = len(tasks)
    blocked_reasons = []
    for t in tasks:
        if t.status == Status.BLOCKED:
            note = (t.events[-1]["note"] if t.events and "note" in t.events[-1] else "")
            blocked_reasons.append({"id": t.task_id, "repo": t.repo, "reason": note or "unspecified"})

    corpus = {"loaded": False, "patterns": 0, "verified_citations": 0}
    if corpus_path is not None and os.path.exists(corpus_path):
        try:
            patterns = load_corpus(corpus_path)
            corpus = {
                "loaded": True,
                "patterns": len(patterns),
                "verified_citations": 0,
            }
            if repo_root is not None:
                try:
                    from .corpus import verify_citations
                    bad = verify_citations(patterns, repo_root)
                    corpus["verified_citations"] = len(patterns) - len(bad)
                except CorpusRefusal:
                    corpus["verified_citations"] = None  # could not proof-read
        except (CorpusRefusal, ValueError):
            raise DashRefusal(f"corpus at {corpus_path} is malformed — refusing to guess") from None

    integrity = journal.verify()
    return {
        "type": "project",
        "forge_version": __version__,
        "journal": journal_path,
        "tasks": {
            "total": total,
            "merged": merged,
            "merged_pct": round(100 * merged / total, 1) if total else 0.0,
            "by_status": counts,
            "blocked": [b["id"] for b in blocked_reasons],
            "blockeds_with_reason": blocked_reasons,
        },
        "corpus": corpus,
        "journal_integrity": integrity["ok"] if "ok" in integrity else integrity,
    }


@dataclass
class RepoRow:
    name: str
    path: str
    version: str = ""
    top_section_hint: str = ""
    head: str = ""
    signed: str = "?"
    has_changelog: bool = False
    has_readme: bool = False
    problems: list[str] = field(default_factory=list)


def _git(repo_root: str, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", repo_root, *args],
            capture_output=True, text=True, check=False, timeout=10,
        )
        return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _changelog_head(changelog_path: str) -> tuple[str, str, list[str]]:
    """Top release header, first feature-section names, and any doctype flags."""
    version, sections = "", []
    try:
        with open(changelog_path, "r", encoding="utf-8") as fh:
            for line in fh:
                m = _TOP_RELEASE.match(line)
                if m and not version:
                    version = m.group("v")
                s = _RELEASE_SECTION.match(line)
                if s and sections and version:
                    if len(sections) >= 3:
                        break
                if s:
                    sections.append(s.group("name"))
    except OSError as exc:
        return "", [], [f"unreadable: {exc}"]
    return version, sections, []


def ecosystem_board(roots: list[str]) -> dict:
    """Cross-repo board read from each repo's own pristine CHANGELOG.md."""
    rows: list[RepoRow] = []
    for root in roots:
        root = os.path.abspath(root)
        name = os.path.basename(root)
        row = RepoRow(name=name, path=root)
        cl_path = os.path.join(root, "CHANGELOG.md")
        row.has_changelog = os.path.isfile(cl_path)
        row.has_readme = os.path.isfile(os.path.join(root, "README.md"))
        if row.has_changelog:
            version, sections, problems = _changelog_head(cl_path)
            row.version = version
            row.top_section_hint = " / ".join(sections)
            row.problems.extend(problems)
        else:
            row.problems.append("missing CHANGELOG.md (doctrine rule 5)")
        if os.path.isdir(os.path.join(root, ".git")):
            row.head = _git(root, "rev-parse", "--short", "HEAD")
            row.signed = _git(root, "log", "-1", "--format=%G?")
        rows.append(row)

    return {
        "type": "ecosystem",
        "forge_version": __version__,
        "repos": [
            {
                "name": r.name,
                "version": r.version,
                "top_release_sections": r.top_section_hint,
                "head": r.head,
                "signed": r.signed,
                "has_changelog": r.has_changelog,
                "has_readme": r.has_readme,
                "problems": r.problems,
            }
            for r in rows
        ],
    }


def _md_project(board: dict) -> str:
    t, c = board["tasks"], board["corpus"]
    by = t["by_status"]
    lines = [
        f"# Forge Project Board (forge {board['forge_version']})",
        "",
        f"Journal: `{board['journal']}`  ·  integrity: {board['journal_integrity']}",
        "",
        "| metric | value |",
        "|--------|-------|",
        f"| tasks total | {t['total']} |",
        f"| merged | {t['merged']} ({t['merged_pct']}%) |",
        f"| queued | {by['queued']} · retrieving {by['retrieving']} · building {by['building']} · reviewing {by['reviewing']} |",
        f"| changes_requested | {by['changes_requested']} |",
        f"| blocked | {by['blocked']} |",
        "",
    ]
    if t["blockeds_with_reason"]:
        lines.append("Blocked (never resurrect, reason required):")
        lines.append("")
        for b in t["blockeds_with_reason"]:
            lines.append(f"- `{b['id']}` [{b['repo']}] — {b['reason']}")
    lines.append("")
    if c["loaded"]:
        vc = c["verified_citations"]
        vc_txt = "n/a (no repo-root)" if vc is None else str(vc)
        lines.append(f"Builder corpus: {c['patterns']} patterns, {vc_txt} citations proof-read")
    else:
        lines.append("Builder corpus: not loaded (path absent)")
    return "\n".join(lines) + "\n"


def _md_ecosystem(board: dict) -> str:
    lines = [
        f"# Forge Ecosystem Board (forge {board['forge_version']})",
        "",
        "Read from each repo's own pristine CHANGELOG.md (documentation doctrine).",
        "",
        "| repo | head | signed | version | top sections | problems |",
        "|------|------|--------|---------|--------------|----------|",
    ]
    for r in board["repos"]:
        problems = "; ".join(r["problems"]) or "none"
        signed = "" if r["signed"] == "G" else (r["signed"] or "n/a")
        lines.append(f"| {r['name']} | `{r['head'] or 'n/a'}` | {signed or 'G'} | "
                     f"{r['version'] or '—'} | {r['top_release_sections'] or '—'} | {problems} |")
    return "\n".join(lines) + "\n"