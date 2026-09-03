from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path

from .model import ReportEntry
from .vocabulary import Vocabulary


def write_reports(
    entries: list[ReportEntry],
    text_path: Path,
    csv_path: Path,
    input_path: Path,
    subjects: Vocabulary,
    chronology: Vocabulary,
    pactols_version: str,
) -> None:
    text_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(entry.status for entry in entries)
    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    lines = [
        "Rapport d’enrichissement PACTOLS",
        "",
        f"Fichier : {input_path.name}",
        f"SHA-256 du fichier : {input_hash}",
        f"Référentiel PACTOLS : {pactols_version}",
        f"SHA-256 Sujets : {subjects.sha256}",
        f"SHA-256 Chronologie : {chronology.sha256}",
        "",
        f"Concepts rencontrés : {len(entries)}",
    ]
    lines.extend(f"{status} : {count}" for status, count in sorted(counts.items()))
    exceptions = [entry for entry in entries if entry.status != "indexed_exact"]
    lines.extend(["", f"Exceptions : {len(exceptions)}"])
    for entry in exceptions:
        lines.extend(
            [
                "",
                f"NOTICE : {entry.notice}",
                f"PARAGRAPHE : {entry.paragraph_id}",
                f"ZONE : {entry.zone}",
                f"VALEUR : {entry.label}",
                f"STATUT : {entry.status}",
                f"CANDIDAT : {entry.candidate}",
                f"DÉTAIL : {entry.detail}",
            ]
        )
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fields = list(ReportEntry.__dataclass_fields__)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for entry in entries:
            writer.writerow({field: getattr(entry, field) for field in fields})
