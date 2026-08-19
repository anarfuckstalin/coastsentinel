# --- image du backend : API FastAPI + moteur scientifique -------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# README.md est indispensable au build, pas décoratif : pyproject.toml le
# déclare en `readme`, et hatchling refuse de générer les métadonnées s'il
# manque. L'omettre fait échouer la construction de l'image, jamais le
# développement local — d'où un échec qui ne se voit qu'en CI.
COPY pyproject.toml README.md ./
COPY coastsentinel ./coastsentinel

RUN pip install --no-cache-dir ".[science]" \
 && adduser --disabled-password --gecos "" --uid 10001 coast \
 && chown -R coast /app
USER coast

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/sante').status==200 else 1)"

CMD ["uvicorn", "coastsentinel.api:app", "--host", "0.0.0.0", "--port", "8000"]
