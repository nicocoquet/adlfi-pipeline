from __future__ import annotations

import argparse
from pathlib import Path

from .preparer import parse_xml, prepare_tree, write_xml
from .report import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Préparer un lot de XML-TEI AdlFI.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources = sorted(args.input_dir.rglob("*.xml")) if args.input_dir.exists() else []
    if not sources:
        print(f"Aucun fichier XML à traiter dans {args.input_dir}.")
        return 0

    for source in sources:
        relative = source.relative_to(args.input_dir)
        base = relative.stem
        output = args.output_dir / relative.parent / f"{base}_prepared.xml"
        report = args.reports_dir / relative.parent / f"{base}_prepared_report.txt"
        tree = parse_xml(str(source))
        result = prepare_tree(tree)
        output.parent.mkdir(parents=True, exist_ok=True)
        write_xml(tree, str(output))
        write_report(report, source.name, result)
        print(f"Préparé : {source} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
