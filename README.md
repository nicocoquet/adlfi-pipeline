# adlfi-pipeline

Outils ouverts et reproductibles pour le traitement éditorial AdlFI : du PDF
BSR au XML-TEI enrichi et contrôlé.

## Prototype d’enrichissement PACTOLS

Le premier module enrichit trois zones des XML-TEI issus de Métopes :

- `archeo_keywords_subjects` avec `pactols:Sujets` ;
- `archeo_keywords_subjects:chronology` avec `pactols:Chronologie` ;
- la partie située après `Nature de l’opération : ` dans
  `archeo_fieldwork_method`, avec `pactols:Sujets`.

Le traitement est strict et déterministe. Seule une correspondance exacte et
unique avec un `skos:prefLabel` français est enrichie. Les variantes
typographiques, absences et ambiguïtés sont laissées intactes et consignées
dans les rapports TXT et CSV.

### Installation

Python 3.11 ou plus récent est nécessaire.

```bash
python -m pip install -e .
```

### Utilisation

```bash
pactols-enrich \
  input.xml \
  --subjects /chemin/vers/Pactols_Sujets_P1-SUJETS.rdf \
  --chronology /chemin/vers/Pactols_Sujets_P1-CHRONOLOGIE.rdf \
  --output output/input_enriched.xml \
  --report-text reports/input_report.txt \
  --report-csv reports/input_report.csv \
  --pactols-version "PACTOLS 2026-07-22"
```

Le fichier source n’est jamais modifié. Une seconde exécution sur un fichier
déjà enrichi n’ajoute aucun doublon.

### Développement

```bash
python -m pip install -e '.[dev]'
pytest
```

La spécification fonctionnelle est disponible dans
[`docs/specification.md`](docs/specification.md).
