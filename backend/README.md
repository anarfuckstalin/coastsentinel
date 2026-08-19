# CoastSentinel — moteur scientifique et API

Paquet Python du système d'alerte côtière multi-échelle : paramétrisations
publiées, climatologie locale, moteur d'alerte, API FastAPI.

Documentation complète du projet : `../README.md`.
Règles à respecter avant toute modification : `../AGENTS.md`.

```bash
pip install -e ".[science]"
uvicorn coastsentinel.api:app --reload      # http://localhost:8000/api/docs
pytest -q
```

Licence Apache-2.0. Aide à la décision et recherche — ne se substitue pas aux
alertes officielles des services nationaux compétents.
