# Service d’authentification de l’interface

Ce petit service conserve les secrets et les jetons GitHub hors de la page
publique. Il n’enrichit pas les XML et ne les stocke pas : il transmet le
fichier à `input/`, suit le workflow existant et renvoie les liens vers les
résultats.

## Configuration

Créer une GitHub App avec une URL de rappel correspondant à
`https://<hôte-du-service>/auth/callback`, l’installer uniquement sur
`nicocoquet/adlfi-pipeline`, puis définir :

```text
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
SESSION_SECRET=une-valeur-aleatoire-longue
GITHUB_REPOSITORY=nicocoquet/adlfi-pipeline
PAGES_URL=https://nicocoquet.github.io/adlfi-pipeline/
ALLOWED_USERS=nicocoquet,gaelle-david
```

Permissions minimales de l’application : **Contents: read and write** et
**Actions: read**. Les comptes autorisés doivent eux-mêmes disposer du droit
d’écriture sur le dépôt.

## Exécution locale

```bash
python -m pip install -e '.[web]'
uvicorn service.main:app --reload
```

Renseigner ensuite l’URL publique du service dans `web/config.js`.
