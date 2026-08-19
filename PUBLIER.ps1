<#
    Publication du projet sur GitHub.

    Le script prépare tout ce qui peut l'être sans identité : il écrit le
    workflow de publication d'images, initialise le dépôt, contrôle ce qui
    part, puis pousse. L'authentification reste entièrement entre tes mains
    et celles de Git Credential Manager — ce script ne demande, ne lit et
    n'enregistre aucun mot de passe ni aucun jeton.

    Usage :  clic droit sur PUBLIER.bat -> Exécuter
       ou :  powershell -ExecutionPolicy Bypass -File PUBLIER.ps1
#>

# NE PAS mettre $ErrorActionPreference sur 'Stop' ici. Dans PowerShell 5.1,
# tout ce qu'une commande native ecrit sur stderr devient alors une erreur
# terminante — or `git push` y ecrit sa progression a chaque execution. Le
# script casserait precisement a l'etape qui compte. On controle donc les
# codes de retour explicitement, ce qui est de toute facon plus sur.
$ErrorActionPreference = 'Continue'
$racine = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $racine

function Titre($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function OK($t)    { Write-Host "  OK   $t" -ForegroundColor Green }
function Info($t)  { Write-Host "  ...  $t" -ForegroundColor Gray }
function Stop2($t) { Write-Host "`nARRET : $t" -ForegroundColor Red; exit 1 }

Titre "1. Verifications"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Stop2 "git n'est pas installe. Telecharge-le sur https://git-scm.com puis relance."
}
OK ("git " + ((git --version) -replace 'git version ',''))

if (-not (Test-Path "$racine\backend\coastsentinel\api.py")) {
    Stop2 "Ce script doit se trouver a la racine du projet CoastSentinel."
}
OK "racine du projet reconnue"

Titre "2. Workflow de publication des images"

# Ce fichier ne peut pas etre depose par un outil distant : GitHub protege le
# dossier .github/workflows. Le script l'ecrit donc lui-meme, en UTF-8 sans
# BOM — un BOM ferait echouer l'analyse YAML par GitHub Actions.
$dossierWf = Join-Path $racine ".github\workflows"
New-Item -ItemType Directory -Force -Path $dossierWf | Out-Null

$yaml = @'
name: Images Docker

# Publie deux images sur GitHub Container Registry a chaque commit sur main
# et a chaque tag de version. Aucun secret a configurer : GITHUB_TOKEN suffit
# des lors que le job declare `packages: write`.

on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:

env:
  REGISTRY: ghcr.io

jobs:
  images:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    strategy:
      fail-fast: false
      matrix:
        include:
          - nom: backend
            contexte: ./backend
          - nom: frontend
            contexte: ./frontend

    steps:
      - uses: actions/checkout@v4

      # Le nom du depot peut contenir des majuscules ; une reference d'image
      # doit etre entierement en minuscules, sans quoi le push echoue.
      - name: Nom d'image en minuscules
        id: nom
        run: echo "image=${REGISTRY}/${GITHUB_REPOSITORY,,}-${{ matrix.nom }}" >> "$GITHUB_OUTPUT"

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Etiquettes et metadonnees
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.nom.outputs.image }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,format=short
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Construction et publication
        uses: docker/build-push-action@v6
        with:
          context: ${{ matrix.contexte }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
'@

$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $dossierWf "docker.yml"), $yaml, $utf8)
OK ".github\workflows\docker.yml ecrit"

Titre "3. Depot local"

if (-not (Test-Path "$racine\.git")) {
    # -b n'existe qu'a partir de git 2.28 ; sur une version anterieure on
    # renomme la branche apres coup plutot que d'echouer.
    git init -b main 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        git init | Out-Null
        if ($LASTEXITCODE -ne 0) { Stop2 "git init a echoue." }
        git branch -M main 2>$null | Out-Null
    }
    OK "depot initialise (branche main)"
} else {
    Info "depot deja initialise"
}

if (-not (git config user.name)) {
    git config user.name "Amine Bouhadi"
    git config user.email "amine.bouhadi@etu.uae.ac.ma"
    OK "identite d'auteur enregistree pour ce depot"
}

git add -A
if ($LASTEXITCODE -ne 0) { Stop2 "git add a echoue." }
$suivis = @(git diff --cached --name-only)

if (-not $suivis) {
    Info "aucun changement a valider"
} else {
    # Garde-fou : ces dossiers pesent des centaines de Mo et n'ont rien a
    # faire dans un depot. S'ils passent, c'est que .gitignore est absent.
    $indesirables = $suivis | Where-Object {
        $_ -match '^(frontend/)?node_modules/' -or
        $_ -match '(^|/)\.venv/' -or
        $_ -match '^frontend/dist/'
    }
    if ($indesirables) {
        Write-Host "`n  Fichiers qui ne devraient pas etre suivis :" -ForegroundColor Red
        $indesirables | Select-Object -First 10 | ForEach-Object { Write-Host "    $_" }
        Stop2 "verifie que .gitignore est bien present a la racine, puis relance."
    }
    OK ("$($suivis.Count) fichiers prets, aucun artefact indesirable")

    git commit -q -m "CoastSentinel 1.0.0 - systeme d'alerte cotiere multi-echelle"
    if ($LASTEXITCODE -ne 0) { Stop2 "git commit a echoue." }
    OK "commit cree"
}

Titre "4. Depot distant"

$origine = git remote get-url origin 2>$null
if (-not $origine) {
    Write-Host ""
    Write-Host "  Cree d'abord un depot VIDE sur GitHub - sans README, sans"
    Write-Host "  licence, sans .gitignore : sinon les deux historiques divergent"
    Write-Host "  et le push est refuse."
    Write-Host ""
    $url = Read-Host "  Colle l'URL du depot (https://github.com/<compte>/coastsentinel.git)"
    if (-not $url) { Stop2 "aucune URL fournie." }
    git remote add origin $url.Trim()
    if ($LASTEXITCODE -ne 0) { Stop2 "impossible d'enregistrer origin." }
    OK "origin enregistre"
} else {
    Info "origin deja configure : $origine"
}

Titre "5. Envoi"

Write-Host "  Une fenetre d'authentification GitHub peut s'ouvrir."
Write-Host "  Elle vient de Git, pas de ce script : personne d'autre que toi"
Write-Host "  ne voit tes identifiants."
Write-Host ""

git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Stop2 "le push a echoue. Message ci-dessus. Cause frequente : le depot distant n'est pas vide."
}

Titre "Termine"
Write-Host ""
Write-Host "  Le push declenche deux workflows :" -ForegroundColor Green
Write-Host "    ci.yml     - ruff, 63 tests, build TypeScript"
Write-Host "    docker.yml - images backend et frontend sur ghcr.io"
Write-Host ""
Write-Host "  Suis-les dans l'onglet Actions du depot."
Write-Host "  Les images sortent PRIVEES : Packages -> Package settings ->"
Write-Host "  Change visibility pour les rendre publiques."
Write-Host ""
Read-Host "  Entree pour fermer"
