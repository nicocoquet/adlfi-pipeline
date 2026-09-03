from __future__ import annotations

import hashlib
import unicodedata
from collections import defaultdict
from pathlib import Path

from lxml import etree

from .model import Concept, Label

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
XML = "http://www.w3.org/XML/1998/namespace"


class VocabularyError(ValueError):
    """Le référentiel PACTOLS ne permet pas une résolution déterministe."""


class Vocabulary:
    def __init__(self, path: Path):
        self.path = path
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        self.concepts: dict[str, Concept] = {}
        self.by_french_label: dict[str, list[Concept]] = defaultdict(list)
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
            concept = Concept(uri=uri)
            for child in description:
                if child.tag == f"{{{SKOS}}}prefLabel" and child.text:
                    concept.labels.append(
                        Label(child.get(f"{{{XML}}}lang", ""), child.text)
                    )
                elif child.tag == f"{{{SKOS}}}broader":
                    broader = child.get(f"{{{RDF}}}resource")
                    if broader:
                        concept.broader.append(broader)
            self.concepts[uri] = concept

        for concept in self.concepts.values():
            for label in concept.french_labels:
                self.by_french_label[label].append(concept)

    def exact(self, label: str) -> list[Concept]:
        return self.by_french_label.get(label, [])

    def typographic_candidates(self, label: str) -> list[str]:
        normalized = _typographic_key(label)
        return sorted(
            candidate
            for candidate in self.by_french_label
            if candidate != label and _typographic_key(candidate) == normalized
        )

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
    return (
        unicodedata.normalize("NFKC", value)
        .replace("’", "'")
        .replace("‘", "'")
        .replace("œ", "oe")
        .replace("Œ", "OE")
        .replace("\u00a0", " ")
        .casefold()
    )
