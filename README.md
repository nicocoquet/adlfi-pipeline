# Pipeline AdlFI

Outils ouverts et reproductibles pour le traitement éditorial AdlFI : du PDF
BSR au XML-TEI enrichi et contrôlé.

## Enrichissement PACTOLS

Le premier module enrichit trois zones des XML-TEI issus de Métopes :

- `archeo_keywords_subjects` avec `pactols:Sujets` ;
- `archeo_keywords_subjects:chronology` avec `pactols:Chronologie` ;
- la partie située après `Nature de l’opération : ` dans
  `archeo_fieldwork_method`, avec `pactols:Sujets`.

Le traitement est strict et déterministe. Une correspondance exacte ou une
équivalence typographique unique avec un `skos:prefLabel` français est
enrichie. La graphie du XML source est toujours conservée dans
`term[@type="orig"]`. Les absences et ambiguïtés restent intactes et sont
consignées dans les rapports TXT et CSV, sans aucune correction du XML.

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

### Utilisation sur GitHub

1. Déposer un ou plusieurs XML non indexés dans [`input/`](input/), puis
   valider les changements sur la branche `main`.
2. Le workflow **Enrichissement PACTOLS** récupère la version figée du
   référentiel et traite récursivement tous les XML du dossier.
3. Il publie les XML enrichis dans `generated/xml/` et les rapports TXT et CSV
   dans `generated/reports/`.

Le workflow peut aussi être lancé manuellement depuis l’onglet **Actions**.
PACTOLS est identifié par un commit Git précis dans le workflow : chaque
traitement est ainsi reproductible. Le pipeline n’utilise aucun service d’IA.

### Traitement local par lot

```bash
pactols-enrich-batch input \
  --subjects /chemin/vers/Pactols_Sujets_P1-SUJETS.rdf \
  --chronology /chemin/vers/Pactols_Sujets_P1-CHRONOLOGIE.rdf \
  --output-dir generated/xml \
  --reports-dir generated/reports \
  --pactols-version "PACTOLS 2026-07-22"
```

### Développement

```bash
python -m pip install -e '.[dev]'
pytest
```

La spécification fonctionnelle est disponible dans
[`docs/specification.md`](docs/specification.md).
