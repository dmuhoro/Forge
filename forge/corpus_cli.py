"""Forge corpus CLI — inspect and verify the Builder corpus WITHOUT an AI.

Commands:
  forge corpus match "keywords from title + acceptance criteria"
       -> ranked patterns the Builder should consult before touching code
  forge corpus verify [--repo-root PATH]
       -> schema validity; with a repo root, also proves every reported
          file:line citation exists at that line in a real checkout

Exit codes: 0 ok, 1 refusal (missing/malformed corpus or bad citations),
2 usage/config error. Mirrors forge-task CLI conventions.
"""

from __future__ import annotations

import argparse
import os
import sys

from .corpus import CorpusRefusal, load, match, verify_citations


def cmd_match(args: argparse.Namespace) -> int:
    try:
        patterns = load(args.corpus)
    except CorpusRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    keywords = " ".join(args.keywords)
    results = match(patterns, keywords, top=args.top)
    if not results:
        print("no patterns matched (fail closed: no guess made)")
        return 0
    for r in results:
        print(f"[{r['score']}] {r['id']} {r['name']}")
        for b in r["boundary"]:
            print(f"    boundary: {b}")
        print(f"    guardrail: {r['guardrail']}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        patterns = load(args.corpus)
    except CorpusRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"corpus ok: {len(patterns)} patterns, schema valid")
    if args.repo_root:
        if not os.path.isdir(args.repo_root):
            print(f"REFUSED: repo root not a directory: {args.repo_root}", file=sys.stderr)
            return 2
        problems = verify_citations(patterns, args.repo_root)
        if problems:
            for p in problems:
                print(f"  FAIL {p['id']} {p['citation']}: {p['error']}", file=sys.stderr)
            print("references: FAIL (see above)", file=sys.stderr)
            return 1
        print(f"references: ok — all {sum(len(p['boundary']) for p in patterns)} citations exist at their cited lines")
    return 0


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="forge corpus", description="Forge Builder corpus CLI")
    parser.add_argument("--corpus", help="corpus file override (else FORGE_CORPUS or repo default)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("match", help="rank patterns for a task")
    p.add_argument("keywords", nargs="+", help="task title / acceptance criteria words")
    p.add_argument("--top", type=int, default=5)
    p.set_defaults(func=cmd_match)

    p = sub.add_parser("verify", help="validate corpus + optionally prove citations")
    p.add_argument("--repo-root", help="a real checkout to resolve file:line citations against")
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CorpusRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> None:
    sys.exit(run(argv))


if __name__ == "__main__":
    main()