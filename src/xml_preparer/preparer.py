from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree


TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
TEI_GRAPHIC = f"{{{TEI_NAMESPACE}}}graphic"


@dataclass
class PreparationResult:
    figures_found: int = 0
    graphics_added: int = 0
    graphics_existing: int = 0
    figures_with_multiple_graphics: list[str] = field(default_factory=list)
    anchors_removed: int = 0
    referenced_anchor_ids: list[str] = field(default_factory=list)

    @property
    def warnings(self) -> int:
        return len(self.figures_with_multiple_graphics) + len(self.referenced_anchor_ids)


def _element_label(element: etree._Element, position: int) -> str:
    return element.get(XML_ID) or f"figure sans xml:id n°{position}"


def _external_anchor_references(root: etree._Element, anchor_ids: set[str]) -> list[str]:
    referenced: set[str] = set()
    if not anchor_ids:
        return []
    for element in root.iter():
        if etree.QName(element).localname == "anchor":
            continue
        for value in element.attrib.values():
            tokens = value.split()
            for anchor_id in anchor_ids:
                if f"#{anchor_id}" in tokens or value == f"#{anchor_id}":
                    referenced.add(anchor_id)
    return sorted(referenced)


def _remove_preserving_tail(element: etree._Element) -> None:
    """Retire un élément vide sans perdre le texte placé après lui."""

    parent = element.getparent()
    if parent is None:
        return
    previous = element.getprevious()
    # `anchor` est vide dans la TEI, mais conserver aussi un éventuel contenu
    # textuel permet de ne jamais perdre de texte face à une source non conforme.
    tail = "".join(element.itertext()) + (element.tail or "")
    if previous is None:
        parent.text = (parent.text or "") + tail
    else:
        previous.tail = (previous.tail or "") + tail
    parent.remove(element)


def prepare_tree(tree: etree._ElementTree) -> PreparationResult:
    root = tree.getroot()
    result = PreparationResult()

    figures = root.xpath(".//tei:figure", namespaces={"tei": TEI_NAMESPACE})
    result.figures_found = len(figures)
    for position, figure in enumerate(figures, 1):
        graphics = figure.xpath("./tei:graphic", namespaces={"tei": TEI_NAMESPACE})
        if graphics:
            result.graphics_existing += len(graphics)
            if len(graphics) > 1:
                result.figures_with_multiple_graphics.append(_element_label(figure, position))
            continue

        graphic = etree.Element(TEI_GRAPHIC, url="???")
        first_child = figure[0] if len(figure) else None
        if first_child is not None:
            graphic.tail = figure.text
        figure.insert(0, graphic)
        result.graphics_added += 1

    anchors = root.xpath(".//tei:anchor", namespaces={"tei": TEI_NAMESPACE})
    anchor_ids = {anchor.get(XML_ID) for anchor in anchors if anchor.get(XML_ID)}
    result.referenced_anchor_ids = _external_anchor_references(root, anchor_ids)
    for anchor in anchors:
        _remove_preserving_tail(anchor)
        result.anchors_removed += 1

    return result


def parse_xml(path: str) -> etree._ElementTree:
    parser = etree.XMLParser(
        remove_blank_text=False,
        resolve_entities=False,
        no_network=True,
        strip_cdata=False,
    )
    return etree.parse(path, parser)


def write_xml(tree: etree._ElementTree, path: str) -> None:
    doctype = tree.docinfo.doctype or None
    tree.write(
        path,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
        doctype=doctype,
    )
