from __future__ import annotations

import argparse
from pathlib import Path

from .enricher import Enricher
from .model import INDEXED_STATUSES, WARNING_STATUSES
from .report import write_reports
from .vocabulary import Vocabulary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrichit trois zones XML-TEI avec un référentiel PACTOLS figé."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--subjects", type=Path, required=True)
    parser.add_argument("--chronology", type=Path, required=True)
    parser.add_argument("--deprecated", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-text", type=Path, required=True)
    parser.add_argument("--report-csv", type=Path, required=True)
    parser.add_argument("--pactols-version", default="non renseignée")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    subjects = Vocabulary(args.subjects)
    chronology = Vocabulary(args.chronology)
    deprecated = (
        Vocabulary(args.deprecated, all_concepts_deprecated=True)
        if args.deprecated
        else None
    )
    tree, entries = Enricher(subjects, chronology, deprecated).enrich_file(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(args.output),
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
    )
    write_reports(
        entries,
        args.report_text,
        args.report_csv,
        args.input,
        subjects,
        chronology,
        args.pactols_version,
        deprecated,
    )
    warnings = sum(entry.status in WARNING_STATUSES for entry in entries)
    unresolved = sum(entry.status not in INDEXED_STATUSES for entry in entries)
    print(
        f"{len(entries)} concept(s), {warnings} avertissement(s), "
        f"{unresolved} exception(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
