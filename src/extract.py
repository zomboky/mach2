"""Extraction : HTML → markdown propre + métadonnées + liens.

Cœur du gain de tokens : trafilatura isole le contenu principal (retire
nav/pied/pub/boilerplate) et sort du markdown. Repli sur bs4 + markdownify.
"""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

import trafilatura
from bs4 import BeautifulSoup


def normalize_url(url: str) -> str:
    """Normalise une URL pour la déduplication (host en minuscule, sans fragment,
    slash final retiré sauf racine)."""
    url = urldefrag(url)[0]
    p = urlparse(url)
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((p.scheme, p.netloc.lower(), path, p.params, p.query, ""))


def to_markdown(html: str, url: str, *, only_main: bool = True) -> str:
    """Convertit le HTML en markdown propre."""
    if not html:
        return ""

    md = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=True,
        include_tables=True,
        include_images=False,
        favor_recall=not only_main,  # only_main → favorise la précision
        with_metadata=False,
        url=url,
    )
    if md and md.strip():
        return md.strip()

    # Repli : nettoyage bs4 + markdownify
    return _fallback_markdown(html, only_main=only_main)


def _fallback_markdown(html: str, *, only_main: bool = True) -> str:
    try:
        from markdownify import markdownify as mdify
    except ImportError:
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text("\n", strip=True)

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    if only_main:
        for tag in soup(["nav", "header", "footer", "aside", "form"]):
            tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    return mdify(str(main), heading_style="ATX", strip=["img"]).strip()


def metadata(html: str, url: str, fetch_meta: dict | None = None) -> dict:
    """Extrait les métadonnées (title, description, og:*, lang, etc.)."""
    meta: dict = {"sourceURL": url}
    if fetch_meta:
        meta["statusCode"] = fetch_meta.get("status")
        meta["contentType"] = fetch_meta.get("content_type")
        if fetch_meta.get("final_url") and fetch_meta["final_url"] != url:
            meta["finalURL"] = fetch_meta["final_url"]

    try:
        tmeta = trafilatura.extract_metadata(html, default_url=url)
        if tmeta:
            d = tmeta.as_dict() if hasattr(tmeta, "as_dict") else {}
            for k in ("title", "author", "date", "sitename", "description"):
                if d.get(k):
                    meta[k] = d[k]
    except Exception:
        pass

    # Complément via bs4 (og:, lang, meta description)
    try:
        soup = BeautifulSoup(html, "lxml")
        # La balise <title> prime (fidélité Firecrawl) sur le titre deviné par trafilatura.
        if soup.title and soup.title.string and soup.title.string.strip():
            meta["title"] = soup.title.string.strip()
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            meta["language"] = html_tag["lang"]
        for m in soup.find_all("meta"):
            prop = (m.get("property") or m.get("name") or "").lower()
            content = m.get("content")
            if not content:
                continue
            if prop == "description" and "description" not in meta:
                meta["description"] = content.strip()
            elif prop == "og:title":
                meta["ogTitle"] = content.strip()
            elif prop == "og:description":
                meta["ogDescription"] = content.strip()
            elif prop == "og:image":
                meta["ogImage"] = content.strip()
    except Exception:
        pass
    return meta


def links(html: str, base_url: str) -> dict:
    """Extrait tous les liens <a href>, résolus en absolu, classés interne/externe."""
    soup = BeautifulSoup(html, "lxml")
    base_host = urlparse(base_url).netloc
    internal: list[str] = []
    external: list[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urldefrag(urljoin(base_url, href))[0]
        scheme = urlparse(absolute).scheme
        if scheme not in ("http", "https"):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        if urlparse(absolute).netloc == base_host:
            internal.append(absolute)
        else:
            external.append(absolute)

    return {"internal": internal, "external": external, "all": internal + external}
