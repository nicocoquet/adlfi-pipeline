from __future__ import annotations

import argparse
from pathlib import Path

from .enricher import Enricher
from .report import write_reports
from .vocabulary import Vocabulary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrichit récursivement un dossier de XML-TEI avec PACTOLS."
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--subjects", type=Path, required=True)
    parser.add_argument("--chronology", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--pactols-version", default="non renseignée")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inputs = sorted(args.input_dir.rglob("*.xml"))
    if not inputs:
        raise SystemExit(f"aucun fichier XML trouvé dans {args.input_dir}")

    subjects = Vocabulary(args.subjects)
    chronology = Vocabulary(args.chronology)
    enricher = Enricher(subjects, chronology)
    total_concepts = 0
    total_exceptions = 0

    for input_path in inputs:
        relative = input_path.relative_to(args.input_dir)
        output_path = args.output_dir / relative.with_name(
            f"{relative.stem}_enriched.xml"
        )
        report_base = args.reports_dir / relative.with_suffix("")
        text_path = report_base.with_name(f"{report_base.name}_report.txt")
        csv_path = report_base.with_name(f"{report_base.name}_report.csv")

        tree, entries = enricher.enrich_file(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(
            str(output_path),
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=False,
        )
        write_reports(
            entries,
            text_path,
            csv_path,
            input_path,
            subjects,
            chronology,
            args.pactols_version,
        )
        exceptions = sum(
            entry.status not in {"indexed_exact", "indexed_typographic"}
            for entry in entries
        )
        total_concepts += len(entries)
        total_exceptions += exceptions
        print(f"{relative}: {len(entries)} concept(s), {exceptions} exception(s)")

    print(
        f"Lot terminé : {len(inputs)} fichier(s), {total_concepts} concept(s), "
        f"{total_exceptions} exception(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
