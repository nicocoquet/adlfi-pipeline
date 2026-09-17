from __future__ import annotations

from pathlib import Path

from .preparer import PreparationResult


def report_text(source_name: str, result: PreparationResult) -> str:
    lines = [
        "PRÉPARATION XML — RAPPORT",
        "",
        f"Fichier : {source_name}",
        f"Figures rencontrées : {result.figures_found}",
        f"Éléments graphic ajoutés : {result.graphics_added}",
        f"Éléments graphic déjà présents : {result.graphics_existing}",
        f"Éléments anchor supprimés : {result.anchors_removed}",
        f"Références externes vers des anchor supprimés : {len(result.referenced_anchor_ids)}",
        f"Avertissements : {result.warnings}",
    ]
    if result.figures_with_multiple_graphics:
        lines.extend(["", "FIGURES AVEC PLUSIEURS GRAPHIC"])
        lines.extend(f"- {label}" for label in result.figures_with_multiple_graphics)
    if result.referenced_anchor_ids:
        lines.extend(["", "ANCHOR ENCORE RÉFÉRENCÉS APRÈS SUPPRESSION"])
        lines.extend(f"- {anchor_id}" for anchor_id in result.referenced_anchor_ids)
    lines.extend(
        [
            "",
            "Le texte éditorial est conservé. Les éléments graphic déjà présents ne sont pas modifiés.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(path: Path, source_name: str, result: PreparationResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text(source_name, result), encoding="utf-8")
