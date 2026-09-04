from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from lxml import etree

from .model import Concept, Label

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
OWL = "http://www.w3.org/2002/07/owl#"
XML = "http://www.w3.org/XML/1998/namespace"


class VocabularyError(ValueError):
    """Le référentiel PACTOLS ne permet pas une résolution déterministe."""


class Vocabulary:
    def __init__(self, path: Path, *, all_concepts_deprecated: bool = False):
        self.path = path
        self.all_concepts_deprecated = all_concepts_deprecated
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        self.concepts: dict[str, Concept] = {}
        self.by_french_label: dict[str, list[Concept]] = defaultdict(list)
        self.by_typographic_label: dict[str, list[Concept]] = defaultdict(list)
        self.by_french_alt_label: dict[str, list[Concept]] = defaultdict(list)
        self.by_typographic_alt_label: dict[str, list[Concept]] = defaultdict(list)
        self.by_deprecated_french_label: dict[str, list[Concept]] = defaultdict(list)
        self.by_deprecated_typographic_label: dict[str, list[Concept]] = defaultdict(list)
        self.by_deprecated_french_alt_label: dict[str, list[Concept]] = defaultdict(list)
        self.by_deprecated_typographic_alt_label: dict[str, list[Concept]] = defaultdict(list)
        self._load()

    def _load(self) -> None:
        tree = etree.parse(str(self.path))
        for description in tree.iterfind(f".//{{{RDF}}}Description"):
            uri = description.get(f"{{{RDF}}}about")
            if not uri:
                continue
            is_concept = any(
                child.tag == f"{{{RDF}}}type"
                and child.get(f"{{{RDF}}}resource") == f"{SKOS}Concept"
                for child in description
            )
            if not is_concept:
                continue
            concept = Concept(uri=uri, deprecated=self.all_concepts_deprecated)
            for child in description:
                if child.tag == f"{{{SKOS}}}prefLabel" and child.text:
                    concept.labels.append(
                        Label(child.get(f"{{{XML}}}lang", ""), child.text)
                    )
                elif child.tag == f"{{{SKOS}}}altLabel" and child.text:
                    concept.alt_labels.append(
                        Label(child.get(f"{{{XML}}}lang", ""), child.text)
                    )
                elif child.tag == f"{{{SKOS}}}broader":
                    broader = child.get(f"{{{RDF}}}resource")
                    if broader:
                        concept.broader.append(broader)
                elif child.tag == f"{{{OWL}}}deprecated":
                    concept.deprecated = concept.deprecated or (
                        (child.text or "").strip().lower() == "true"
                    )
            self.concepts[uri] = concept

        for concept in self.concepts.values():
            if concept.deprecated:
                self._index_labels(
                    concept,
                    concept.french_labels,
                    self.by_deprecated_french_label,
                    self.by_deprecated_typographic_label,
                )
                self._index_labels(
                    concept,
                    concept.french_alt_labels,
                    self.by_deprecated_french_alt_label,
                    self.by_deprecated_typographic_alt_label,
                )
            else:
                self._index_labels(
                    concept,
                    concept.french_labels,
                    self.by_french_label,
                    self.by_typographic_label,
                )
                self._index_labels(
                    concept,
                    concept.french_alt_labels,
                    self.by_french_alt_label,
                    self.by_typographic_alt_label,
                )

    @staticmethod
    def _index_labels(
        concept: Concept,
        labels: list[str],
        exact_index: dict[str, list[Concept]],
        typographic_index: dict[str, list[Concept]],
    ) -> None:
        for label in labels:
            if concept not in exact_index[label]:
                exact_index[label].append(concept)
            key = _typographic_key(label)
            if concept not in typographic_index[key]:
                typographic_index[key].append(concept)

    def exact(self, label: str) -> list[Concept]:
        return self.by_french_label.get(label, [])

    def typographic_matches(self, label: str) -> list[Concept]:
        return self.by_typographic_label.get(_typographic_key(label), [])

    def exact_alt(self, label: str) -> list[Concept]:
        return self.by_french_alt_label.get(label, [])

    def typographic_alt_matches(self, label: str) -> list[Concept]:
        return self.by_typographic_alt_label.get(_typographic_key(label), [])

    def deprecated_exact(self, label: str) -> list[Concept]:
        return self.by_deprecated_french_label.get(label, [])

    def deprecated_typographic_matches(self, label: str) -> list[Concept]:
        return self.by_deprecated_typographic_label.get(_typographic_key(label), [])

    def deprecated_exact_alt(self, label: str) -> list[Concept]:
        return self.by_deprecated_french_alt_label.get(label, [])

    def deprecated_typographic_alt_matches(self, label: str) -> list[Concept]:
        return self.by_deprecated_typographic_alt_label.get(
            _typographic_key(label), []
        )

    def french_labels_for(self, concepts: list[Concept]) -> list[str]:
        return sorted({label for concept in concepts for label in concept.french_labels})

    def path_to(self, concept: Concept) -> list[Concept]:
        reverse_path = [concept]
        seen = {concept.uri}
        current = concept
        while current.broader:
            if len(current.broader) != 1:
                raise VocabularyError(
                    f"{current.uri} possède {len(current.broader)} concepts génériques"
                )
            parent_uri = current.broader[0]
            if parent_uri in seen:
                raise VocabularyError(f"cycle hiérarchique détecté à {parent_uri}")
            parent = self.concepts.get(parent_uri)
            if parent is None:
                raise VocabularyError(f"concept générique absent : {parent_uri}")
            reverse_path.append(parent)
            seen.add(parent_uri)
            current = parent
        return list(reversed(reverse_path))


def _typographic_key(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKC", value)
        .replace("’", "'")
        .replace("‘", "'")
        .replace("œ", "oe")
        .replace("Œ", "OE")
        .replace("\u00a0", " ")
        .casefold()
    )
    normalized = " ".join(normalized.split())
    # PACTOLS écrit par exemple « III a », tandis que la source peut porter « IIIa ».
    return re.sub(r"\b([ivxlcdm]+)\s+([a-z])\b", r"\1\2", normalized)
