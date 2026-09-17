from pathlib import Path

from lxml import etree

from xml_preparer.batch import main
from xml_preparer.preparer import TEI_NAMESPACE, prepare_tree


NS = {"tei": TEI_NAMESPACE}


def parse(value: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(value.encode("utf-8")))


def test_adds_graphic_first_and_removes_anchor_without_losing_text():
    tree = parse(
        """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
        <p>Avant <anchor type="crossref" xml:id="_Toc1"/>Après</p>
        <figure xml:id="figure01"><head>Légende</head><p rend="credits">Crédit</p></figure>
        </body></text></TEI>"""
    )

    result = prepare_tree(tree)

    figure = tree.xpath("//tei:figure", namespaces=NS)[0]
    assert [etree.QName(child).localname for child in figure] == ["graphic", "head", "p"]
    assert figure[0].get("url") == "???"
    assert not tree.xpath("//tei:anchor", namespaces=NS)
    paragraph = tree.xpath("//tei:p[not(@rend)]", namespaces=NS)[0]
    assert "".join(paragraph.itertext()) == "Avant Après"
    assert result.figures_found == 1
    assert result.graphics_added == 1
    assert result.anchors_removed == 1


def test_is_idempotent_and_reports_multiple_existing_graphics():
    tree = parse(
        """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
        <figure xml:id="figure01"><graphic url="a"/><graphic url="b"/><head>Légende</head></figure>
        </body></text></TEI>"""
    )

    first = prepare_tree(tree)
    second = prepare_tree(tree)

    assert len(tree.xpath("//tei:graphic", namespaces=NS)) == 2
    assert first.graphics_added == 0
    assert first.graphics_existing == 2
    assert first.figures_with_multiple_graphics == ["figure01"]
    assert second.graphics_added == 0


def test_reports_external_reference_to_removed_anchor():
    tree = parse(
        """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
        <p><anchor xml:id="place"/>Texte</p><ref target="#place">Renvoi</ref>
        </body></text></TEI>"""
    )
    result = prepare_tree(tree)
    assert result.referenced_anchor_ids == ["place"]
    assert result.warnings == 1


def test_malformed_nonempty_anchor_does_not_lose_its_text():
    tree = parse(
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><p>A<anchor>milieu</anchor>Z</p></body></text></TEI>'
    )
    prepare_tree(tree)
    paragraph = tree.xpath("//tei:p", namespaces=NS)[0]
    assert "".join(paragraph.itertext()) == "AmilieuZ"


def test_batch_writes_xml_and_text_report(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "notice.xml").write_text(
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><figure><head>Fig.</head></figure></body></text></TEI>',
        encoding="utf-8",
    )
    result = main(
        [
            str(input_dir),
            "--output-dir",
            str(tmp_path / "generated" / "xml"),
            "--reports-dir",
            str(tmp_path / "generated" / "reports"),
        ]
    )
    assert result == 0
    assert (tmp_path / "generated/xml/notice_prepared.xml").exists()
    report = (tmp_path / "generated/reports/notice_prepared_report.txt").read_text(encoding="utf-8")
    assert "Éléments graphic ajoutés : 1" in report
