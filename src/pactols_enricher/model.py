from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Label:
    language: str
    text: str


@dataclass
class Concept:
    uri: str
    labels: list[Label] = field(default_factory=list)
    alt_labels: list[Label] = field(default_factory=list)
    broader: list[str] = field(default_factory=list)
    deprecated: bool = False

    @property
    def french_labels(self) -> list[str]:
        return [label.text for label in self.labels if label.language == "fr"]

    @property
    def french_alt_labels(self) -> list[str]:
        return [label.text for label in self.alt_labels if label.language == "fr"]


@dataclass(frozen=True)
class ReportEntry:
    file: str
    notice: str
    paragraph_id: str
    zone: str
    label: str
    status: str
    candidate: str = ""
    concept_uri: str = ""
    detail: str = ""


INDEXED_STATUSES = frozenset(
    {
        "indexed_exact",
        "indexed_typographic",
        "indexed_altlabel",
        "indexed_altlabel_typographic",
    }
)

WARNING_STATUSES = frozenset(
    {"indexed_altlabel", "indexed_altlabel_typographic"}
)
