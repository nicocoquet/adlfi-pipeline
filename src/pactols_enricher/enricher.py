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
    def __init__(
        self,
        subjects: Vocabulary,
        chronology: Vocabulary,
        deprecated: Vocabulary | None = None,
    ):
        self.vocabularies = {
            "subjects": subjects,
            "fieldwork_method": subjects,
            "chronology": chronology,
        }
        self.deprecated = deprecated

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
        stages = (
            (
                vocabulary.exact(label),
                "indexed_exact",
                "ambiguous",
                "plusieurs prefLabel français identiques",
            ),
            (
                vocabulary.exact_alt(label),
                "indexed_altlabel",
                "ambiguous_altlabel",
                "un même altLabel français désigne plusieurs concepts actifs",
            ),
            (
                vocabulary.typographic_matches(label),
                "indexed_typographic",
                "ambiguous_typographic",
                "la forme normalisée correspond à plusieurs prefLabel actifs",
            ),
            (
                vocabulary.typographic_alt_matches(label),
                "indexed_altlabel_typographic",
                "ambiguous_altlabel_typographic",
                "la forme normalisée correspond à plusieurs altLabel actifs",
            ),
        )
        matches: list[Concept] = []
        match_status = ""
        for stage_matches, stage_status, ambiguous_status, ambiguous_detail in stages:
            if len(stage_matches) > 1:
                return None, ReportEntry(
                    **metadata,
                    label=label,
                    status=ambiguous_status,
                    candidate=" | ".join(
                        vocabulary.french_labels_for(stage_matches)
                    ),
                    detail=ambiguous_detail,
                )
            if stage_matches:
                matches = stage_matches
                match_status = stage_status
                break

        if not matches:
            deprecated_entry = self._deprecated_entry(vocabulary, label, metadata)
            if deprecated_entry is not None:
                return None, deprecated_entry
            return None, ReportEntry(
                **metadata,
                label=label,
                status="not_found",
                detail=(
                    "aucun prefLabel ou altLabel français actif, exact ou "
                    "équivalent typographique unique ; XML laissé inchangé"
                ),
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
            ReportEntry(
                **metadata,
                label=label,
                status=match_status,
                candidate=(
                    matches[0].french_labels[0]
                    if match_status != "indexed_exact"
                    else ""
                ),
                concept_uri=matches[0].uri,
                detail=(
                    "enrichissement effectué depuis un skos:altLabel français"
                    if match_status.startswith("indexed_altlabel")
                    else ""
                ),
            ),
        )

    def _deprecated_entry(
        self,
        vocabulary: Vocabulary,
        label: str,
        metadata: dict[str, str],
    ) -> ReportEntry | None:
        vocabularies = [vocabulary]
        if self.deprecated is not None:
            vocabularies.append(self.deprecated)

        stages = (
            ("prefLabel", False, "deprecated_exact"),
            ("altLabel", False, "deprecated_exact_alt"),
            ("prefLabel", True, "deprecated_typographic_matches"),
            ("altLabel", True, "deprecated_typographic_alt_matches"),
        )
        for label_type, typographic, method_name in stages:
            matches = _unique_concepts(
                concept
                for item in vocabularies
                for concept in getattr(item, method_name)(label)
            )
            if len(matches) > 1:
                return ReportEntry(
                    **metadata,
                    label=label,
                    status="ambiguous_deprecated",
                    candidate=" | ".join(
                        sorted(
                            {
                                french_label
                                for concept in matches
                                for french_label in concept.french_labels
                            }
                        )
                    ),
                    detail=(
                        "plusieurs concepts dépréciés correspondent à cette forme ; "
                        "XML laissé inchangé"
                    ),
                )
            if matches:
                concept = matches[0]
                return ReportEntry(
                    **metadata,
                    label=label,
                    status=("deprecated_typographic" if typographic else "deprecated"),
                    candidate=(concept.french_labels[0] if concept.french_labels else ""),
                    concept_uri=concept.uri,
                    detail=(
                        f"correspondance avec un {label_type} français d’un concept "
                        "PACTOLS déprécié ; XML laissé inchangé"
                    ),
                )
        return None

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


def _unique_concepts(concepts) -> list[Concept]:
    return list({concept.uri: concept for concept in concepts}.values())
