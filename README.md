# Pipeline AdlFI

Outils ouverts et reproductibles pour le traitement éditorial AdlFI : du PDF
BSR au XML-TEI enrichi et contrôlé.

## Enrichissement PACTOLS

Le premier module enrichit trois zones des XML-TEI issus de Métopes :

- `archeo_keywords_subjects` avec `pactols:Sujets` ;
- `archeo_keywords_subjects:chronology` avec `pactols:Chronologie` ;
- la partie située après `Nature de l’opération : ` dans
  `archeo_fieldwork_method`, avec `pactols:Sujets`.

Le traitement est strict et déterministe. Une correspondance unique avec un
`skos:prefLabel` ou un `skos:altLabel` français actif est enrichie, exactement
ou après normalisation typographique. La graphie du XML source est toujours
conservée dans `term[@type="orig"]`. Les enrichissements obtenus par
`altLabel` sont signalés comme avertissements avec le `prefLabel` actuel. Les
concepts dépréciés, les absences et les ambiguïtés restent intacts et sont
consignés dans les rapports TXT et CSV.

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
  --deprecated "/chemin/vers/Pactols_Sujets_P2-Concepts dépréciés.rdf" \
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
4. Lorsqu’un résultat a réellement changé sur `main`, il crée une issue
   assignée au propriétaire du dépôt avec les statistiques et les liens vers
   les fichiers produits. Une exécution sans changement ne crée aucune issue.

Le workflow peut aussi être lancé manuellement depuis l’onglet **Actions**.
PACTOLS est identifié par un commit Git précis dans le workflow : chaque
traitement est ainsi reproductible. Le pipeline n’utilise aucun service d’IA.
La suppression du dernier XML de `input/` se termine comme une opération vide
réussie et ne provoque pas de fausse alerte d’échec.

### Traitement local par lot

```bash
pactols-enrich-batch input \
  --subjects /chemin/vers/Pactols_Sujets_P1-SUJETS.rdf \
  --chronology /chemin/vers/Pactols_Sujets_P1-CHRONOLOGIE.rdf \
  --deprecated "/chemin/vers/Pactols_Sujets_P2-Concepts dépréciés.rdf" \
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

### GitHub Pages

https://nicocoquet.github.io/adlfi-pipeline/

L’interface interactive est limitée à `nicocoquet` et `gaelle-david`. Le
JavaScript public ne contient aucun secret : le petit service dans
[`service/`](service/) assure la connexion GitHub, le dépôt dans `input/` et le
suivi des Actions. Tant que son URL n’est pas renseignée dans `web/config.js`,
la page présente l’interface sans autoriser l’envoi.
