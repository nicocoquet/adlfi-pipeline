# Historique des versions

Toutes les modifications notables du projet sont consignées dans ce fichier.

## [0.1.0] — 2026-09-04

Première version publique du module d’enrichissement PACTOLS.

### Ajouté

- enrichissement des `skos:prefLabel` et `skos:altLabel` PACTOLS ;
- reconnaissance contrôlée des équivalences typographiques ;
- signalement des concepts dépréciés, absents et ambigus ;
- conservation systématique de la graphie du XML source ;
- génération du XML enrichi et des rapports TXT et CSV ;
- traitement reproductible par GitHub Actions avec une version figée de PACTOLS ;
- interface web avec authentification GitHub et dépôt par glisser-déposer ;
- téléchargement direct des trois fichiers produits ;
- tests automatisés du moteur, du traitement par lot et du service web.

[0.1.0]: https://github.com/nicocoquet/adlfi-pipeline/releases/tag/v0.1.0
