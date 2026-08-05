---
name: mach2
description: >-
  Recherche et extraction web économe en tokens — clone local de Firecrawl, sans clé API.
  À utiliser DÈS QU'IL FAUT lire/scraper une page web, récupérer le contenu d'URLs (y compris
  issues d'une recherche WebSearch), crawler un site, ou cartographier ses URLs. Renvoie du
  markdown propre écrit dans des FICHIERS (résumé compact en console) au lieu de déverser du
  HTML brut dans le contexte. Préférer Mach2 à WebFetch pour lire des pages lourdes ou plusieurs
  pages. Commandes : scrape, batch, map, crawl. Déclencheurs : "scrape", "extrais la page",
  "lis cet article", "récupère le contenu de", "crawl le site", "liste les URLs de".
---

# Mach2 — extraction web économe en tokens

Clone local de Firecrawl. Transforme des pages web en **markdown propre** (contenu principal
seulement, sans nav/pub/boilerplate) et **écrit les résultats dans des fichiers** ; la console
ne renvoie qu'un résumé compact (titre, taille, chemin). Ainsi le contexte n'ingère jamais des
pages entières → **économie massive de tokens**.

## Emplacement
`C:\Users\Zombo\.claude\skills\mach2\` — lancer avec `python mach2.py <commande>`.
(Le premier usage nécessite `pip install -r requirements.txt`.)

## Quand l'utiliser (important)
- Lire **une page lourde** (article, doc, page longue) → `scrape` puis lire le fichier .md.
- Lire **plusieurs pages** (résultats de recherche) → `batch`.
- **Recherche web** : utiliser d'abord l'outil **WebSearch** de Claude pour obtenir les URLs,
  puis `python mach2.py batch <url1> <url2> ...` pour récupérer le contenu propre.
- Explorer/lister les pages d'un site → `map` ; aspirer plusieurs pages d'un site → `crawl`.

Préférer Mach2 à WebFetch quand la page est volumineuse ou qu'il y a plusieurs URLs : Mach2
met en fichier (pas dans le contexte), filtre par pertinence et met en cache.

## Workflow de recherche (le plus fréquent)
1. `WebSearch` (outil Claude) → collecter les URLs pertinentes.
2. `python mach2.py batch <urls...> --filter "sujet de la recherche"`
3. Lire `manifest.json` (index compact) puis ouvrir **uniquement** les .md utiles.

## Commandes

### scrape — une URL
```
python mach2.py scrape <url> [--format markdown|html|rawhtml|links|metadata|json]
    [--render] [--wait-for <sel|ms>] [--full] [--filter "requête"] [--max-chars N]
    [--out FICHIER] [--show N] [--no-cache] [--max-age SECONDES]
```
- Défaut : markdown, contenu principal, mis en cache 24 h, écrit dans un fichier.
- `--filter "requête"` : ne garde que les passages pertinents. `--show N` : aperçu console.
- `--format metadata` imprime les métadonnées JSON ; `--format links` écrit la liste des liens.

### batch — plusieurs URLs en parallèle
```
python mach2.py batch <url1> <url2> ... | --urls-file FICHIER
    [--concurrency 5] [--filter "requête"] [--max-chars N] [--out DOSSIER] [--render]
```
Écrit un `.md` par page + `manifest.json`. C'est la brique du workflow WebSearch.

### map — découvrir les URLs d'un site
```
python mach2.py map <url> [--limit N] [--search "terme"] [--out FICHIER]
```
Source : sitemap.xml (+ index récursif), robots.txt, liens de la page. Ne scrape pas le contenu.

### crawl — aspirer un site récursivement
```
python mach2.py crawl <url> [--depth 2] [--limit 20] [--include REGEX] [--exclude REGEX]
    [--all-domains] [--concurrency 5] [--delay SEC] [--filter "requête"] [--out DOSSIER] [--render]
```
Écrit un `.md` par page + `manifest.json`. Reste sur le domaine seed par défaut.

### cache
```
python mach2.py cache status   # nb d'entrées
python mach2.py cache clear     # vider
```

## Rendu JavaScript
Statique par défaut (rapide). Pour les sites SPA/JS, ajouter `--render` (Playwright/Chromium).
Si absent : `pip install playwright && python -m playwright install chromium`.

## Sorties
- Dossier par défaut : `%TEMP%\mach2\<commande>-<horodatage>\` (ou `$CLAUDE_SCRATCHPAD` si défini).
- Chaque `.md` a un front-matter (title, sourceURL, description, language…).
- `crawl`/`batch` produisent `manifest.json` : `{url, title, file, chars, words, status}`.

## Bonnes pratiques tokens
- Toujours lire d'abord `manifest.json`, puis ouvrir seulement les fichiers pertinents.
- Utiliser `--filter "sujet"` et/ou `--max-chars` pour réduire la taille.
- S'appuyer sur le cache (ne pas mettre `--no-cache` sans raison).
