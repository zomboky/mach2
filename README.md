# Mach2 🚀

Clone local de **Firecrawl**, packagé en **skill Claude Code**. Objectif : faire des recherches
et de l'extraction web en **économisant un maximum de tokens** et sans clé API.

Le principe : au lieu de déverser du HTML brut dans le contexte du LLM, Mach2 extrait le
**contenu principal en markdown propre** (via [trafilatura](https://trafilatura.readthedocs.io/)),
l'écrit dans des **fichiers**, et ne renvoie qu'un **résumé compact** (titre, taille, chemin).

## Installation

```bash
cd C:\Users\Zombo\.claude\skills\mach2
pip install -r requirements.txt
# Optionnel — rendu JavaScript :
pip install playwright
python -m playwright install chromium
```

## Commandes

| Commande | Rôle | Équivalent Firecrawl |
|----------|------|----------------------|
| `scrape <url>` | 1 page → markdown propre / liens / métadonnées | `/scrape` |
| `batch <urls>` | plusieurs URLs en parallèle → fichiers + manifest | `/batch/scrape` |
| `map <url>`   | découvrir les URLs d'un site (sitemap + liens) | `/map` |
| `crawl <url>` | aspirer un site récursivement | `/crawl` |
| `cache`       | gérer le cache disque local | `maxAge` |

### Exemples

```bash
# Une page, aperçu console
python mach2.py scrape https://example.com --show 300

# Filtrer le contenu par pertinence + plafonner la taille
python mach2.py scrape https://un-long-article.com --filter "sécurité authentification" --max-chars 4000

# Site JS (SPA)
python mach2.py scrape https://app-react.com --render --wait-for ".content"

# Plusieurs URLs (workflow recherche : WebSearch → batch)
python mach2.py batch https://a.com https://b.com https://c.com --filter "prix pricing"

# Cartographier un site
python mach2.py map https://fastapi.tiangolo.com --search tutorial

# Crawl 2 niveaux, 15 pages max
python mach2.py crawl https://docs.exemple.com --depth 2 --limit 15
```

## Pourquoi c'est économe en tokens

1. **Fichiers d'abord** — le contenu complet va sur disque, pas dans le contexte.
2. **Contenu principal only** — trafilatura retire nav / pied / pub / boilerplate.
3. **`--filter`** — ne garde que les passages pertinents à une requête.
4. **`--max-chars`** — plafond dur.
5. **Cache disque TTL** — pas de re-téléchargement.
6. **`manifest.json`** — index compact ; on n'ouvre que les fichiers utiles.

## Architecture

```
mach2.py          CLI (argparse)
src/
  fetch.py        HTTP statique (requests) + rendu JS optionnel (Playwright)
  extract.py      HTML → markdown + métadonnées + liens (trafilatura / bs4)
  scrape.py       scrape 1 URL → formats
  batch.py        scrape parallèle
  mapper.py       découverte d'URLs (sitemap/robots/liens)
  crawl.py        crawl BFS
  cache.py        cache disque TTL
  filter.py       filtrage par pertinence + troncature
  output.py       écriture fichiers + résumés + manifest
```

## Limites (par rapport à Firecrawl)
- Pas de moteur de recherche intégré → on utilise l'outil **WebSearch** de Claude.
- Extraction JSON structurée : le markdown propre est fourni, l'« intelligence » d'extraction
  est faite par le LLM qui lit le fichier (pas d'appel API payant).
- Screenshots / audio / vidéo / webhooks non implémentés.
- PDF : extraction texte basique si `pypdf` est installé.
