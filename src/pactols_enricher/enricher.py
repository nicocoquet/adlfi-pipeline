from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from .model import Concept, ReportEntry
from .vocabulary import Vocabulary, VocabularyError

TEI = "http://www.tei-c.org/ns/1.0"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"tei": TEI}
FIELDWORK_PREFIX = re.compile(r"^(Nature de l[’']opération(?:\u00a0| ):\s*)")

ZONES = {
    "archeo_keywords_subjects": ("subjects", "pactols:Sujets"),
    "archeo_keywords_subjects:chronology": ("chronology", "pactols:Chronologie"),
    "archeo_fieldwork_method": ("fieldwork_method", "pactols:Sujets"),
}


class Enricher:
    def __init__(self, subjects: Vocabulary, chronology: Vocabulary):
        self.vocabularies = {
            "subjects": subjects,
            "fieldwork_method": subjects,
            "chronology": chronology,
        }

    def enrich_file(self, input_path: Path) -> tuple[etree._ElementTree, list[ReportEntry]]:
        parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
        tree = etree.parse(str(input_path), parser)
        entries: list[ReportEntry] = []
        xpath = " | ".join(f'//tei:p[@rend="{rend}"]' for rend in ZONES)
        for paragraph in tree.xpath(xpath, namespaces=NS):
            entries.extend(self._enrich_paragraph(paragraph, input_path.name))
        return tree, entries

    def _enrich_paragraph(
        self, paragraph: etree._Element, filename: str
    ) -> list[ReportEntry]:
        rend = paragraph.get("rend", "")
        zone, index_name = ZONES[rend]
        metadata = self._metadata(paragraph, filename, zone)

        if paragraph.xpath("./tei:index", namespaces=NS):
            return [ReportEntry(**metadata, label="", status="already_indexed")]
        if len(paragraph):
            return [
                ReportEntry(
                    **metadata,
                    label="".join(paragraph.itertext()),
                    status="invalid_structure",
                    detail="balisage enfant inattendu",
                )
            ]

        original = paragraph.text or ""
        prefix = ""
        content = original
        if zone == "fieldwork_method":
            match = FIELDWORK_PREFIX.match(original)
            if not match:
                return [
                    ReportEntry(
                        **metadata,
                        label=original,
                        status="invalid_structure",
                        detail="préfixe de nature d’opération absent",
                    )
                ]
            prefix = match.group(1)
            content = original[match.end() :]

        vocabulary = self.vocabularies[zone]
        resolutions = []
        for label in content.split(", "):
            element, entry = self._resolve(vocabulary, label, index_name, metadata)
            resolutions.append((label, element, entry))

        paragraph.text = prefix
        for position, (label, element, _) in enumerate(resolutions):
            if position:
                _append_text(paragraph, ", ")
            if element is None:
                _append_text(paragraph, label)
            else:
                paragraph.append(element)
        return [entry for _, _, entry in resolutions]

    def _resolve(
        self,
        vocabulary: Vocabulary,
        label: str,
        index_name: str,
        metadata: dict[str, str],
    ) -> tuple[etree._Element | None, ReportEntry]:
        matches = vocabulary.exact(label)
        if len(matches) > 1:
            return None, ReportEntry(
                **metadata,
                label=label,
                status="ambiguous",
                detail="plusieurs prefLabel français identiques",
            )
        if not matches:
            candidates = vocabulary.typographic_candidates(label)
            status = "typographic_variant" if candidates else "not_found"
            return None, ReportEntry(
                **metadata,
                label=label,
                status=status,
                candidate=" | ".join(candidates),
            )
        try:
            path = vocabulary.path_to(matches[0])
        except VocabularyError as error:
            return None, ReportEntry(
                **metadata,
                label=label,
                status="invalid_vocabulary",
                detail=str(error),
            )
        return (
            _build_index(label, path, index_name),
            ReportEntry(**metadata, label=label, status="indexed_exact"),
        )

    @staticmethod
    def _metadata(
        paragraph: etree._Element, filename: str, zone: str
    ) -> dict[str, str]:
        notices = paragraph.xpath(
            "ancestor::tei:div[@subtype='notice'][1]", namespaces=NS
        )
        notice = ""
        if notices:
            heads = notices[0].xpath("./tei:head[1]", namespaces=NS)
            if heads:
                notice = "".join(heads[0].itertext()).strip()
        return {
            "file": filename,
            "notice": notice,
            "paragraph_id": paragraph.get(f"{{{XML}}}id", ""),
            "zone": zone,
        }


def _build_index(label: str, path: list[Concept], index_name: str) -> etree._Element:
    outer = etree.Element(f"{{{TEI}}}index", indexName="Index")
    original = etree.SubElement(outer, f"{{{TEI}}}term", type="orig")
    original.text = label
    parent = outer
    for level, concept in enumerate(path, start=1):
        if level == 1:
            attributes = {
                "indexName": index_name,
                "n": str(level),
                "rendition": "oe",
                "source": _relative_ark(concept.uri),
            }
            attributes[f"{{{XML}}}base"] = "https://ark.frantiq.fr/ark:/"
        else:
            attributes = {
                "n": str(level),
                "rendition": "oe",
                "source": _relative_ark(concept.uri),
            }
        current = etree.SubElement(parent, f"{{{TEI}}}index", **attributes)
        for label_item in concept.labels:
            term = etree.SubElement(current, f"{{{TEI}}}term")
            if label_item.language:
                term.set(f"{{{XML}}}lang", label_item.language)
            term.text = label_item.text
        parent = current
    return outer


def _relative_ark(uri: str) -> str:
    marker = "ark:/"
    return uri.split(marker, 1)[1] if marker in uri else uri


def _append_text(parent: etree._Element, text: str) -> None:
    if len(parent):
        last = parent[-1]
        last.tail = (last.tail or "") + text
    else:
        parent.text = (parent.text or "") + text
