# Mach2

Local clone of **Firecrawl**, packaged as a **Claude Code skill**. Web search and extraction,
**no API key required**, built to save as much context tokens as possible.

The idea: instead of dumping raw HTML into the LLM's context, Mach2 extracts the **main content
as clean markdown**, **writes it to files**, and only returns a **compact summary** to the
console (title, size, path). The LLM then reads only the files it actually needs.

## What Mach2 does

- **Fetch** — static HTTP ([requests](https://requests.readthedocs.io/)) by default; optional
  JavaScript rendering (Playwright/Chromium) for SPA/React sites.
- **Extract** — HTML -> clean markdown via [trafilatura](https://trafilatura.readthedocs.io/)
  (nav, footer, ads and boilerplate stripped out), plus metadata (title, author, language...)
  and links (internal/external).
- **Filter** — keeps only the blocks relevant to a query (lexical-overlap scoring) and caps the
  output size in characters.
- **Cache** — disk cache with a TTL (24h by default, equivalent to Firecrawl's `maxAge`) to
  avoid re-downloading the same URL.
- **Output-first** — everything goes to disk (`.md` + front matter, `manifest.json` for
  multi-page runs); the console only ever gets a summary.

## Requirements

- Python 3.10+
- Optional — JS rendering (SPA sites): [Playwright](https://playwright.dev/) + Chromium

## Installation

Mach2 is a Claude Code skill: it lives under `~/.claude/skills/` and is invoked via
`python mach2.py <command>`, not as a globally installed executable.

```bash
git clone https://github.com/zomboky/mach2.git ~/.claude/skills/mach2
cd ~/.claude/skills/mach2
pip install -r requirements.txt
```

On Windows, the equivalent path is `C:\Users\<you>\.claude\skills\mach2\`.

JavaScript rendering (SPA/React sites) — optional, installed separately:

```bash
pip install playwright
python -m playwright install chromium
```

## Commands

| Command | Role | Firecrawl equivalent |
|---------|------|-----------------------|
| `scrape <url>` | 1 page -> clean markdown / links / metadata | `/scrape` |
| `batch <urls>` | multiple URLs in parallel -> files + manifest | `/batch/scrape` |
| `map <url>` | discover a site's URLs (sitemap + links) | `/map` |
| `crawl <url>` | recursively crawl a site | `/crawl` |
| `cache` | manage the local disk cache | `maxAge` |

### Examples

```bash
# One page, console preview
python mach2.py scrape https://example.com --show 300

# Filter content by relevance + cap the output size
python mach2.py scrape https://a-long-article.com --filter "security authentication" --max-chars 4000

# JS site (SPA)
python mach2.py scrape https://app-react.com --render --wait-for ".content"

# Multiple URLs (search workflow: WebSearch -> batch)
python mach2.py batch https://a.com https://b.com https://c.com --filter "price pricing"

# Map a site
python mach2.py map https://fastapi.tiangolo.com --search tutorial

# Crawl 2 levels deep, 15 pages max
python mach2.py crawl https://docs.example.com --depth 2 --limit 15

# Cache status / clear
python mach2.py cache status
python mach2.py cache clear
```

### Search workflow (the most common one)

1. `WebSearch` (Claude's tool) to collect the relevant URLs.
2. `python mach2.py batch <urls...> --filter "research topic"`
3. Read `manifest.json` (compact index), then open **only** the useful `.md` files.

## Why it's token-efficient

1. **Files first** — the full content goes to disk, not into the context.
2. **Main content only** — trafilatura strips nav / footer / ads / boilerplate.
3. **`--filter`** — keeps only the passages relevant to a query.
4. **`--max-chars`** — hard cap, cleanly truncated on a block boundary.
5. **Disk cache with TTL** — no unnecessary re-downloads.
6. **`manifest.json`** — compact index; only the useful files get opened.

## Output

- Default directory: `%TEMP%\mach2\<command>-<timestamp>\` (or `$CLAUDE_SCRATCHPAD` if set in
  the environment).
- Each `.md` has a front matter block (`title`, `sourceURL`, `finalURL`, `description`,
  `language`, `author`, `date`, `statusCode`).
- `batch`/`crawl` additionally produce a `manifest.json`:
  `{generated_at, count, entries: [{url, title, file, chars, words, status}]}`.

## Architecture

```
mach2.py          CLI (argparse): scrape, batch, map, crawl, cache
src/
  fetch.py        static HTTP (requests) + optional JS rendering (Playwright)
  extract.py      HTML -> markdown + metadata + links (trafilatura / bs4)
  scrape.py       scrape 1 URL -> formats (markdown, html, rawhtml, links, metadata, json)
  batch.py        parallel scrape (ThreadPool) + manifest
  mapper.py       URL discovery (recursive sitemap.xml, robots.txt, page links)
  crawl.py        BFS crawl, same-domain by default, --include/--exclude regex
  cache.py        disk cache with TTL (key = hash of URL + render mode)
  filter.py       relevance filtering (per-block TF score) + truncation
  output.py       file writing + front matter + console summaries + manifest.json
tests/
  smoke_test.py   end-to-end smoke tests
```

## Customizing

- Cache TTL: `DEFAULT_TTL` in [`src/cache.py`](src/cache.py) (24h by default).
- Relevance-filtering algorithm: [`src/filter.py`](src/filter.py) (per-block TF score, bonus
  for relevant markdown headings, tunable `max_blocks`).
- Front-matter fields and output file naming: [`src/output.py`](src/output.py).
- Default output directory: `CLAUDE_SCRATCHPAD` environment variable, falls back to `%TEMP%`.
- Default `batch`/`crawl` concurrency: `--concurrency` flag (default 5).

## Limitations (compared to Firecrawl)

- No built-in search engine -> use Claude's **WebSearch** tool upstream.
- Structured JSON extraction: clean markdown is provided, and the extraction "intelligence" is
  left to the LLM reading the file (no billed API call on Mach2's side).
- Screenshots / audio / video / webhooks are not implemented.
- PDF: basic text extraction if `pypdf` is installed (not required by default).
