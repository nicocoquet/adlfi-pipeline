from __future__ import annotations

import argparse
from pathlib import Path

from .preparer import parse_xml, prepare_tree, write_xml
from .report import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Préparer un XML-TEI AdlFI.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-text", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tree = parse_xml(str(args.source))
    result = prepare_tree(tree)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_xml(tree, str(args.output))
    write_report(args.report_text, args.source.name, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
