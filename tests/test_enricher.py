from pathlib import Path

from lxml import etree

from pactols_enricher.enricher import Enricher, NS
from pactols_enricher.vocabulary import Vocabulary

RDF_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:skos="http://www.w3.org/2004/02/skos/core#">
{concepts}
</rdf:RDF>
"""


def concept(uri, labels, broader=""):
    label_xml = "".join(
        f'<skos:prefLabel xml:lang="{lang}">{text}</skos:prefLabel>'
        for lang, text in labels
    )
    broader_xml = (
        f'<skos:broader rdf:resource="{broader}"/>' if broader else ""
    )
    return f"""<rdf:Description rdf:about="{uri}">
  <rdf:type rdf:resource="http://www.w3.org/2004/02/skos/core#Concept"/>
  {label_xml}{broader_xml}
</rdf:Description>"""


def write_fixture(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def vocabularies(tmp_path):
    base = "https://ark.frantiq.fr/ark:/26678/"
    subjects = RDF_TEMPLATE.format(
        concepts="".join(
            [
                concept(base + "subject-root", [("fr", "entités matérielles"), ("en", "material entity")]),
                concept(base + "rural", [("es", "asentamiento rural"), ("fr", "établissement rural")], base + "subject-root"),
                concept(base + "variant", [("fr", "bois d'oeuvre")], base + "subject-root"),
                concept(base + "fieldwork-root", [("fr", "entités immatérielles")]),
                concept(base + "diagnostic", [("fr", "opération de diagnostic"), ("en", "test trench")], base + "fieldwork-root"),
            ]
        )
    )
    chronology = RDF_TEMPLATE.format(
        concepts="".join(
            [
                concept(base + "chronology-root", [("fr", "entités temporelles")]),
                concept(base + "roman", [("fr", "Haut-Empire romain"), ("en", "Early Roman Empire")], base + "chronology-root"),
                concept(base + "bronze", [("fr", "Bronze final III a")], base + "chronology-root"),
            ]
        )
    )
    return (
        Vocabulary(write_fixture(tmp_path / "subjects.rdf", subjects)),
        Vocabulary(write_fixture(tmp_path / "chronology.rdf", chronology)),
    )


def input_xml(tmp_path):
    return write_fixture(
        tmp_path / "input.xml",
        """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
<div subtype="notice"><head>Anais – Churet</head>
<p xml:id="p3" rend="archeo_keywords_subjects">établissement rural, bois d’œuvre</p>
<p xml:id="p4" rend="archeo_keywords_subjects:chronology">Haut-Empire romain, Bronze final IIIa</p>
<p xml:id="p8" rend="archeo_fieldwork_method">Nature de l’opération : opération de diagnostic</p>
</div></body></text></TEI>""",
    )


def test_enriches_three_zones_and_preserves_separator_and_prefix(tmp_path):
    subjects, chronology = vocabularies(tmp_path)
    tree, entries = Enricher(subjects, chronology).enrich_file(input_xml(tmp_path))

    p3 = tree.xpath('//*[@xml:id="p3"]', namespaces={"xml": "http://www.w3.org/XML/1998/namespace"})[0]
    p4 = tree.xpath('//*[@xml:id="p4"]', namespaces={"xml": "http://www.w3.org/XML/1998/namespace"})[0]
    p8 = tree.xpath('//*[@xml:id="p8"]', namespaces={"xml": "http://www.w3.org/XML/1998/namespace"})[0]

    assert p3.xpath('./tei:index/tei:term[@type="orig"]/text()', namespaces=NS) == ["établissement rural", "bois d’œuvre"]
    assert p3[0].tail == ", "
    assert p3.xpath('.//tei:index/@source', namespaces=NS) == ["26678/subject-root", "26678/rural", "26678/subject-root", "26678/variant"]
    assert p3.xpath('./tei:index/tei:index/@indexName', namespaces=NS) == ["pactols:Sujets"] * 2
    assert p4.xpath('./tei:index/tei:index/@indexName', namespaces=NS) == ["pactols:Chronologie"] * 2
    assert p4.xpath('./tei:index/tei:term[@type="orig"]/text()', namespaces=NS) == ["Haut-Empire romain", "Bronze final IIIa"]
    assert p8.text == "Nature de l’opération : "
    assert p8.xpath('./tei:index/tei:term[@type="orig"]/text()', namespaces=NS) == ["opération de diagnostic"]

    statuses = {(entry.label, entry.status, entry.candidate) for entry in entries}
    assert ("établissement rural", "indexed_exact", "") in statuses
    assert ("bois d’œuvre", "indexed_typographic", "bois d'oeuvre") in statuses
    assert ("Bronze final IIIa", "indexed_typographic", "Bronze final III a") in statuses
    assert ("Haut-Empire romain", "indexed_exact", "") in statuses
    assert ("opération de diagnostic", "indexed_exact", "") in statuses


def test_second_run_does_not_duplicate_indexes(tmp_path):
    subjects, chronology = vocabularies(tmp_path)
    enricher = Enricher(subjects, chronology)
    tree, _ = enricher.enrich_file(input_xml(tmp_path))
    enriched = tmp_path / "enriched.xml"
    tree.write(str(enriched), encoding="UTF-8", xml_declaration=True)

    second_tree, entries = enricher.enrich_file(enriched)

    assert len(second_tree.xpath("//tei:index[@indexName='Index']", namespaces=NS)) == 5
    assert [entry.status for entry in entries] == ["already_indexed"] * 3


def test_unexpected_child_markup_is_left_unchanged(tmp_path):
    subjects, chronology = vocabularies(tmp_path)
    source = write_fixture(
        tmp_path / "marked.xml",
        """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
<p xml:id="p3" rend="archeo_keywords_subjects"><hi>établissement rural</hi></p>
</body></text></TEI>""",
    )

    tree, entries = Enricher(subjects, chronology).enrich_file(source)

    assert tree.xpath('count(//tei:p[@xml:id="p3"]/tei:hi)', namespaces={**NS, "xml": "http://www.w3.org/XML/1998/namespace"}) == 1
    assert entries[0].status == "invalid_structure"
