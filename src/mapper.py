"""Découverte d'URLs d'un site — sitemap.xml (+ index récursif), robots.txt, liens page.

Équivalent de la fonction `map` de Firecrawl : renvoie rapidement la liste des
URLs d'un domaine sans scraper chaque page.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import extract, fetch


def _base(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _sitemaps_from_robots(base: str) -> list[str]:
    r = fetch.fetch_static(urljoin(base, "/robots.txt"), timeout=15)
    if r["error"] or not r["html"]:
        return []
    return re.findall(r"(?im)^\s*Sitemap:\s*(\S+)", r["html"])


def _parse_sitemap(url: str, seen: set[str], depth: int = 0) -> list[str]:
    """Parse un sitemap ou index de sitemaps (récursif, borné)."""
    if depth > 3 or url in seen:
        return []
    seen.add(url)
    r = fetch.fetch_static(url, timeout=20)
    if r["error"] or not r["html"]:
        return []
    soup = BeautifulSoup(r["html"], "xml")

    # Index de sitemaps → récursion
    sitemaps = [loc.get_text(strip=True) for loc in soup.select("sitemap > loc")]
    if sitemaps:
        urls: list[str] = []
        for sm in sitemaps:
            urls.extend(_parse_sitemap(sm, seen, depth + 1))
        return urls

    return [loc.get_text(strip=True) for loc in soup.select("url > loc")]


def map_site(url: str, *, limit: int = 5000, search: str | None = None) -> dict:
    """Découvre les URLs d'un site. Renvoie {urls, sources, count}."""
    base = _base(url)
    found: list[str] = []
    seen: set[str] = set()
    sources: list[str] = []

    # 1. Sitemaps depuis robots.txt + emplacements courants
    candidates = _sitemaps_from_robots(base)
    candidates += [urljoin(base, p) for p in ("/sitemap.xml", "/sitemap_index.xml")]
    for sm in dict.fromkeys(candidates):
        urls = _parse_sitemap(sm, seen)
        if urls:
            sources.append(sm)
            found.extend(urls)

    # 2. Liens de la page fournie (complément / fallback)
    r = fetch.fetch(url, use_cache=True, timeout=20)
    if not r["error"] and r["html"]:
        page_links = extract.links(r["html"], r["final_url"])["internal"]
        if page_links:
            sources.append(f"liens page ({url})")
            found.extend(page_links)

    # Dédup en gardant l'ordre
    ordered = list(dict.fromkeys(found))

    if search:
        s = search.lower()
        ordered = [u for u in ordered if s in u.lower()]

    return {
        "urls": ordered[:limit],
        "sources": sources,
        "count": min(len(ordered), limit),
        "total_found": len(ordered),
    }
