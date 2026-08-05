"""Scrape d'une URL → formats demandés (markdown, html, rawhtml, links, metadata, json)."""

from __future__ import annotations

from . import extract, fetch, filter as flt


def scrape_one(
    url: str,
    *,
    formats: list[str] | None = None,
    render: bool = False,
    only_main: bool = True,
    query: str | None = None,
    max_chars: int | None = None,
    timeout: int = 30,
    wait_for: str | None = None,
    use_cache: bool = True,
    max_age: int | None = None,
) -> dict:
    """Récupère et transforme une URL. Renvoie un dict de résultat structuré."""
    formats = formats or ["markdown"]
    kw = {} if max_age is None else {"max_age": max_age}
    fetched = fetch.fetch(
        url, render=render, timeout=timeout, wait_for=wait_for,
        use_cache=use_cache, **kw,
    )

    result: dict = {
        "url": url,
        "final_url": fetched["final_url"],
        "status": fetched["status"],
        "from_cache": fetched["from_cache"],
        "error": fetched["error"],
        "metadata": {},
    }
    if fetched["error"] or not fetched["html"]:
        result["error"] = fetched["error"] or "réponse vide"
        return result

    html = fetched["html"]
    result["metadata"] = extract.metadata(html, url, fetched)

    md = None
    if any(f in formats for f in ("markdown", "json")):
        md = extract.to_markdown(html, url, only_main=only_main)
        if query:
            md = flt.filter_markdown(md, query)
        if max_chars:
            md = flt.truncate(md, max_chars)

    if "markdown" in formats:
        result["markdown"] = md
    if "html" in formats:
        result["html"] = html  # HTML (potentiellement rendu)
    if "rawhtml" in formats:
        result["rawHtml"] = html
    if "links" in formats:
        result["links"] = extract.links(html, fetched["final_url"])
    if "metadata" in formats:
        pass  # déjà dans result["metadata"]
    if "json" in formats:
        # Extraction structurée déléguée au LLM : on fournit le markdown propre.
        result["json"] = {"_note": "markdown fourni pour extraction par le LLM",
                          "markdown": md}

    return result
