# Pipeline AdlFI

Outils ouverts et reproductibles pour préparer, contrôler et enrichir les
fichiers XML-TEI de la revue *AdlFI. Archéologie de la France – Informations*.

## État du projet

La version `0.2.0` réunit deux traitements indépendants et complémentaires :

| Étape | Module | Entrée | Sorties |
| --- | --- | --- | --- |
| 1 | Préparation du XML | XML-TEI Métopes | XML préparé et rapport TXT |
| 2 | Indexation PACTOLS | XML-TEI Métopes, préparé ou non | XML enrichi et rapports TXT/CSV |

Les modules peuvent être utilisés séparément ou successivement depuis la
[page web du projet](https://nicocoquet.github.io/adlfi-pipeline/), avec une
seule connexion GitHub.

La rétroconversion des BSR au format PDF vers des DOCX structurés appartient à
la feuille de route du projet, mais n’est pas comprise dans cette release.

## Principes communs

- le fichier source n’est jamais modifié ;
- les opérations sont explicites, déterministes et reproductibles ;
- les cas incertains ne sont pas complétés arbitrairement ;
- chaque traitement produit un rapport de contrôle ;
- les deux modules sont idempotents : une seconde exécution ne crée aucun
  doublon ;
- aucun service d’intelligence artificielle n’est nécessaire à l’exécution du
  pipeline.

## Étape 1 — Préparation du XML

Le module `xml_preparer` réalise actuellement deux opérations sur les XML-TEI
produits avec Métopes.

### Ajout des éléments `graphic`

Pour chaque élément TEI `figure` qui ne contient pas encore de `graphic`, le
module insère comme premier enfant :

```xml
<graphic url="???"/>
```

Le marqueur `???` réserve l’emplacement de l’URL de l’illustration, qui sera
renseignée ultérieurement dans le processus éditorial. Un élément `graphic`
déjà présent n’est jamais modifié. Une figure contenant plusieurs `graphic`
est conservée en l’état et signalée dans le rapport.

### Suppression des éléments `anchor`

Tous les éléments TEI `anchor` sont supprimés. Leur texte consécutif (la
« queue » XML) est réinjecté à l’emplacement exact de l’ancre afin de préserver
intégralement le contenu éditorial.

Lorsqu’un identifiant d’ancre supprimé est encore visé par une référence dans
le document, le module ne modifie pas cette référence arbitrairement : il la
signale dans le rapport pour contrôle humain.

### Rapport de préparation

Le rapport TXT indique notamment :

- le nombre de figures rencontrées ;
- le nombre de `graphic` ajoutés ;
- le nombre de `graphic` déjà présents ;
- les figures contenant plusieurs `graphic` ;
- le nombre d’éléments `anchor` supprimés ;
- les références éventuelles vers des ancres supprimées ;
- le nombre total d’avertissements.

### Traitement local d’un fichier

```bash
tei-prepare input.xml \
  --output output/input_prepared.xml \
  --report-text reports/input_prepared_report.txt
```

### Traitement local par lot

```bash
tei-prepare-batch input/preparation \
  --output-dir generated/preparation/xml \
  --reports-dir generated/preparation/reports
```

## Étape 2 — Indexation PACTOLS

Le module `pactols_enricher` enrichit trois zones des XML-TEI issus de Métopes :

- `archeo_keywords_subjects` avec `pactols:Sujets` ;
- `archeo_keywords_subjects:chronology` avec `pactols:Chronologie` ;
- la partie située après `Nature de l’opération : ` dans
  `archeo_fieldwork_method`, avec `pactols:Sujets`.

Une correspondance unique avec un `skos:prefLabel` ou un `skos:altLabel`
français actif est enrichie, exactement ou après normalisation typographique.
La graphie du XML source est toujours conservée dans `term[@type="orig"]`.

Les enrichissements obtenus par `altLabel` sont signalés comme avertissements
avec le `prefLabel` actuel. Les concepts dépréciés, les absences et les
ambiguïtés restent intacts et sont consignés dans les rapports TXT et CSV.

### Traitement local d’un fichier

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

### Traitement local par lot

```bash
pactols-enrich-batch input/pactols \
  --subjects /chemin/vers/Pactols_Sujets_P1-SUJETS.rdf \
  --chronology /chemin/vers/Pactols_Sujets_P1-CHRONOLOGIE.rdf \
  --deprecated "/chemin/vers/Pactols_Sujets_P2-Concepts dépréciés.rdf" \
  --output-dir generated/pactols/xml \
  --reports-dir generated/pactols/reports \
  --pactols-version "PACTOLS 2026-07-22"
```

## Utilisation avec GitHub Actions

Les deux familles de fichiers sont séparées afin d’éviter tout traitement
croisé :

```text
input/
├── preparation/
└── pactols/

generated/
├── preparation/
│   ├── xml/
│   └── reports/
└── pactols/
    ├── xml/
    └── reports/
```

### Préparation

1. déposer un ou plusieurs XML dans `input/preparation/` ;
2. valider les changements sur la branche `main` ;
3. le workflow **Préparation XML** génère les fichiers
   `*_prepared.xml` dans `generated/preparation/xml/` ;
4. les rapports `*_prepared_report.txt` sont écrits dans
   `generated/preparation/reports/`.

### Indexation PACTOLS

1. déposer un ou plusieurs XML dans `input/pactols/` ;
2. valider les changements sur la branche `main` ;
3. le workflow **Enrichissement PACTOLS** récupère la version figée du
   référentiel et publie les XML enrichis dans `generated/pactols/xml/` ;
4. les rapports TXT et CSV sont écrits dans `generated/pactols/reports/`.

Les workflows peuvent aussi être lancés manuellement depuis l’onglet
**Actions**. Lorsqu’un résultat a réellement changé sur `main`, une issue
assignée au propriétaire du dépôt récapitule le traitement et fournit les liens
vers les fichiers produits. Une exécution sans changement ne crée aucune issue.

La suppression du dernier XML d’un dossier d’entrée se termine comme une
opération vide réussie et ne provoque pas de fausse alerte d’échec.

## Interface web

L’interface est disponible à l’adresse suivante :

https://nicocoquet.github.io/adlfi-pipeline/

Son utilisation est limitée aux comptes GitHub autorisés. Une connexion unique
donne accès aux deux modules pendant toute la session du navigateur.

Pour lancer un traitement :

1. se connecter avec GitHub ;
2. sélectionner ou déposer un fichier XML-TEI Métopes dans le module choisi ;
3. confirmer que le fichier source et les résultats seront temporairement
   visibles dans le dépôt ;
4. lancer le traitement ;
5. télécharger les résultats.

Après une préparation, le XML obtenu peut être transmis directement au module
d’indexation PACTOLS sans téléchargement ni nouveau dépôt. Le téléchargement du
fichier intermédiaire et de son rapport reste toujours possible.

Le JavaScript public ne contient aucun secret. Le service présent dans
[`service/`](service/) assure l’authentification GitHub, le dépôt du fichier dans
le répertoire d’entrée approprié et le suivi des Actions. Il est hébergé sur une
instance gratuite Render ; après une période d’inactivité, son premier réveil
peut prendre une cinquantaine de secondes.

## Installation et développement

Python 3.11 ou plus récent est nécessaire.

```bash
python -m pip install -e .
```

Pour installer les dépendances de développement et exécuter les tests :

```bash
python -m pip install -e '.[dev]'
pytest
```

La spécification fonctionnelle est disponible dans
[`docs/specification.md`](docs/specification.md).

## Auteurs et licence

- Nicolas Coquet — MSH Mondes, UAR 3225 ;
- Gaëlle David — MSH Mondes, UAR 3225.

Le logiciel est distribué sous licence MIT. Les informations de citation sont
fournies dans [`CITATION.cff`](CITATION.cff) et l’historique des versions dans
[`CHANGELOG.md`](CHANGELOG.md).
