# Spécification fonctionnelle — enrichissement PACTOLS

## Périmètre XML

Le programme ne traite que les paragraphes TEI suivants :

| `@rend` | Contenu traité | Index PACTOLS |
| --- | --- | --- |
| `archeo_keywords_subjects` | paragraphe entier | `pactols:Sujets` |
| `archeo_keywords_subjects:chronology` | paragraphe entier | `pactols:Chronologie` |
| `archeo_fieldwork_method` | texte après le préfixe `Nature de l’opération : ` | `pactols:Sujets` |

Les concepts multiples sont séparés par la chaîne exacte `, `. Ce séparateur
reste hors des éléments `index`.

## Règle de correspondance

Un concept est enrichi lorsqu’un et un seul `skos:prefLabel` français du
vocabulaire approprié est soit strictement identique au texte source, soit
équivalent après normalisation typographique.

- Les `skos:altLabel` ne déclenchent pas d’enrichissement.
- La normalisation couvre la casse, les espaces ordinaires ou insécables, les
  apostrophes droites ou courbes, `œ`/`oe` et l’espace entre un chiffre romain
  et son suffixe alphabétique (`IIIa`/`III a`).
- La normalisation ne modifie jamais le libellé source : il est conservé tel
  quel dans `term[@type="orig"]`.
- Une équivalence typographique n’est automatique que si elle conduit à un
  concept unique. Une collision entre plusieurs concepts est signalée comme
  ambiguë et n’est pas enrichie.
- Un terme non résolu reste inchangé dans le XML.

## Structure produite

Chaque concept résolu devient un `index` TEI externe contenant :

1. le libellé source dans `term[@type="orig"]` ;
2. la chaîne hiérarchique complète de PACTOLS, de la racine au concept ;
3. pour chaque niveau, son ARK relatif dans `@source`, son niveau dans `@n`,
   `@rendition="oe"` et tous ses `skos:prefLabel` dans l’ordre du RDF ;
4. sur le premier niveau seulement, `@indexName` et `@xml:base`.

## Sécurité et traçabilité

- Le fichier d’entrée n’est jamais modifié.
- Un paragraphe contenant déjà un `index` est laissé intact.
- Un paragraphe contenant un balisage enfant inattendu est laissé intact.
- Les sorties comprennent le XML enrichi et des rapports TXT et CSV.
- Les rapports indiquent la version déclarée de PACTOLS et le SHA-256 des
  fichiers d’entrée et de référentiel.
