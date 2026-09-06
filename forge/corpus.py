"""Forge Builder corpus — the feeding base for the Builder agent role.

Sprint-24 (2026-09-06) extracted the first real pattern slice from the VERIFIED
Daftari production-readiness diffs (dmuhoro/Daftari, 4ea952c..36eaf82); every
pattern entry cites the real file:line boundary it protects (see
docs/corpus/builder-corpus.json). The Builder consumes this corpus BEFORE
touching code so its first pass is grounded on what already worked on the same
class of problem.

The matcher is deterministic, offline, stdlib-only, and FAIL-CLOSED: no usable
keywords means no result — it never guesses. This is feedstock for build-brief
step 2 ("Wire in Builder — low-risk tasks only"); the Docker sandbox and the
Planner->Reviewer loop remain separate phases (kickoff.md dependency table).

Alignment: ShrinkMedia ADR-014 (EcosystemIndex behaviour) adapted to a parsed,
citable pattern catalog instead of a free-text corpus; skills-workbench S-style
unit shape (name, one-line trigger, sequence, completion criteria) mirrored in
the JSON schema.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
from typing import Any

Pattern = dict[str, Any]


class CorpusRefusal(Exception):
    """Raised when the corpus is missing or malformed — fail closed, never skip."""


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

REQUIRED_FIELDS = (
    "id",
    "name",
    "trigger",
    "source",
    "boundary",
    "recipe",
    "acceptance",
    "guardrail",
)

_TOKEN = re.compile(r"[a-z0-9]+")
_TERMS = re.compile(r"[a-z0-9][a-z0-9 -]*[a-z0-9]|[a-z0-9]+")

# Tiny deterministic stemmer: strips a fixed suffix set so related forms
# (orphan/orphans/orphaned, adopt/adoption) land on the same search token.
# Deliberately crude and order-safe — matching is a RANKER, not a filter; the
# fail-closed guarantee (empty overlap => []) comes from the score floor, not
# from clustering precision.
_STEM_SUFFIXES = ("ions", "ing", "es", "ed", "ion", "s")


def _stem(token: str) -> str:
    for suffix in _STEM_SUFFIXES:
        if len(token) - len(suffix) >= 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _tokenize(text: str) -> set[str]:
    return {_stem(t) for t in _TOKEN.findall(text.lower())}


def corpus_path() -> str:
    """Resolve the corpus file: FORGE_CORPUS env override or the repo default."""
    env = os.environ.get("FORGE_CORPUS")
    if env:
        return env
    default = REPO_ROOT / "docs" / "corpus" / "builder-corpus.json"
    return str(default)


def load(corpus_file: str | None = None) -> list[Pattern]:
    """Load and validate the corpus; raise CorpusRefusal on any malformed entry."""
    path = corpus_file or corpus_path()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise CorpusRefusal(f"corpus not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CorpusRefusal(f"corpus not valid json: {exc}") from exc

    if not isinstance(data, dict) or "patterns" not in data:
        raise CorpusRefusal("corpus root must be an object with a 'patterns' list")

    patterns = data["patterns"]
    if not isinstance(patterns, list):
        raise CorpusRefusal("'patterns' must be a list")

    errors = validate(patterns)
    if errors:
        raise CorpusRefusal("corpus invalid: " + " | ".join(errors))
    return patterns


def validate(patterns: list[Pattern]) -> list[str]:
    """Return a list of problems, or an empty list for a valid corpus."""
    errors: list[str] = []
    seen: set[str] = set()
    for i, p in enumerate(patterns):
        where = f"pattern[{i}]"
        if not isinstance(p, dict):
            errors.append(f"{where} must be an object")
            continue
        p_id = p.get("id")
        if not p_id:
            errors.append(f"{where} missing 'id'")
        elif not isinstance(p_id, str):
            errors.append(f"{where} 'id' must be a string")
        elif p_id in seen:
            errors.append(f"{where} duplicate id {p_id}")
        seen.add(str(p_id))

        for field in REQUIRED_FIELDS:
            value = p.get(field)
            if field in ("recipe", "acceptance", "boundary"):
                if not (isinstance(value, list) and value):
                    errors.append(f"{where}.{field} must be a non-empty list")
            else:
                if not (isinstance(value, str) and value.strip()):
                    errors.append(f"{where}.{field} must be a non-empty string")

        boundary = p.get("boundary") or []
        for b in boundary:
            if not _looks_like_citation(str(b)):
                errors.append(f"{where}.boundary entry not a file:line citation: {b!r}")
    return errors


def _looks_like_citation(text: str) -> bool:
    parts = text.rsplit(":", 1)
    if len(parts) != 2:
        return False
    return bool(parts[0]) and parts[1].isdigit() and int(parts[1]) > 0


def match(patterns: list[Pattern], keywords: str, top: int = 5) -> list[dict[str, Any]]:
    """Deterministically rank patterns against a task's title + acceptance criteria.

    Score = overlapping keyword tokens plus a bonus for multiword trigger phrases
    that appear verbatim. Fail-closed: empty keywords or zero overlap => [].
    """
    if not keywords or not keywords.strip():
        return []

    query = keywords.lower()
    query_tokens = _TOKEN.findall(query)

    scored: list[tuple[int, str, dict[str, Any]]] = []
    for p in patterns:
        searchable = _tokenize(p["name"]) | _tokenize(p["trigger"])
        score = len(searchable & set(query_tokens))
        for term in _TERMS.findall(p["trigger"].lower()):
            if " " in term and term in query:
                score += 2
        if score > 0:
            scored.append((score, str(p.get("id", "")), p))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {
            "score": score,
            "id": p["id"],
            "name": p["name"],
            "boundary": p["boundary"],
            "guardrail": p["guardrail"],
        }
        for score, _, p in scored[:top]
    ]


def verify_citations(patterns: list[Pattern], repo_root: str | os.PathLike[str]) -> list[dict[str, str]]:
    """Check every boundary citation 'file:line' against a real checkout.

    Returns a list of problems; an empty list means every cited file:line EXISTS
    in the given repository root at the claimed line. This is the boundary proof
    that a corpus entry is not a paraphrase.
    """
    root = pathlib.Path(repo_root)
    problems: list[dict[str, str]] = []
    for p in patterns:
        for citation in p.get("boundary", []):
            file_rel, _, line_str = str(citation).rpartition(":")
            candidate = root / file_rel
            if not candidate.is_file():
                problems.append({"id": p["id"], "citation": citation, "error": f"file not found: {file_rel}"})
                continue
            with open(candidate, encoding="utf-8") as fh:
                line_count = sum(1 for _ in fh)
            if int(line_str) > line_count:
                problems.append({"id": p["id"], "citation": citation, "error": f"line {line_str} exceeds {line_count}"})
    return problems