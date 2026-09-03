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
    broader: list[str] = field(default_factory=list)

    @property
    def french_labels(self) -> list[str]:
        return [label.text for label in self.labels if label.language == "fr"]


@dataclass(frozen=True)
class ReportEntry:
    file: str
    notice: str
    paragraph_id: str
    zone: str
    label: str
    status: str
    candidate: str = ""
    detail: str = ""
