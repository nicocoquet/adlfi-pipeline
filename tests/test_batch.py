from pathlib import Path

from pactols_enricher.batch import main

from test_enricher import RDF_TEMPLATE, concept, write_fixture


def test_batch_preserves_subdirectories_and_writes_reports(tmp_path: Path):
    base = "https://ark.frantiq.fr/ark:/26678/"
    subjects = write_fixture(
        tmp_path / "subjects.rdf",
        RDF_TEMPLATE.format(
            concepts=concept(base + "rural", [("fr", "établissement rural")])
        ),
    )
    chronology = write_fixture(
        tmp_path / "chronology.rdf",
        RDF_TEMPLATE.format(
            concepts=concept(base + "roman", [("fr", "Haut-Empire romain")])
        ),
    )
    source = tmp_path / "input" / "lot-a" / "notice.xml"
    source.parent.mkdir(parents=True)
    write_fixture(
        source,
        """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
<p rend="archeo_keywords_subjects">établissement rural, terme absent</p>
</body></text></TEI>""",
    )

    result = main(
        [
            str(tmp_path / "input"),
            "--subjects",
            str(subjects),
            "--chronology",
            str(chronology),
            "--output-dir",
            str(tmp_path / "generated" / "xml"),
            "--reports-dir",
            str(tmp_path / "generated" / "reports"),
            "--pactols-version",
            "test",
        ]
    )

    assert result == 0
    enriched = tmp_path / "generated" / "xml" / "lot-a" / "notice_enriched.xml"
    report = tmp_path / "generated" / "reports" / "lot-a" / "notice_report.txt"
    csv_report = tmp_path / "generated" / "reports" / "lot-a" / "notice_report.csv"
    assert enriched.exists()
    assert report.exists()
    assert csv_report.exists()
    assert "terme absent" in report.read_text(encoding="utf-8")
    assert "XML laissé inchangé" in report.read_text(encoding="utf-8")
