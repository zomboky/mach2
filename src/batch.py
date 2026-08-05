"""Scrape de plusieurs URLs en parallèle → fichiers + manifest.

Brique du workflow de recherche : WebSearch (Claude) fournit les URLs, Mach2 les
transforme en markdown propre écrit dans des fichiers.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import output
from .scrape import scrape_one


def scrape_many(
    urls: list[str],
    *,
    out_dir: Path,
    concurrency: int = 5,
    render: bool = False,
    only_main: bool = True,
    query: str | None = None,
    max_chars: int | None = None,
    timeout: int = 30,
    use_cache: bool = True,
) -> list[dict]:
    """Scrape une liste d'URLs en parallèle, écrit un .md par page + manifest.json."""
    urls = list(dict.fromkeys(u for u in urls if u.strip()))  # dédup, garde l'ordre
    entries: list[dict] = []

    def work(u: str) -> dict:
        return scrape_one(
            u, formats=["markdown"], render=render, only_main=only_main,
            query=query, max_chars=max_chars, timeout=timeout, use_cache=use_cache,
        )

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = {pool.submit(work, u): u for u in urls}
        for fut in as_completed(futures):
            u = futures[fut]
            try:
                results[u] = fut.result()
            except Exception as e:
                results[u] = {"url": u, "error": f"{type(e).__name__}: {e}"}

    # Écriture dans l'ordre d'entrée
    for u in urls:
        r = results.get(u, {"url": u, "error": "aucun résultat"})
        if r.get("error") or not r.get("markdown"):
            entries.append({"url": u, "status": r.get("status"),
                            "error": r.get("error") or "vide", "file": None})
            continue
        meta = r.get("metadata", {})
        path = output.write_markdown(out_dir, u, r["markdown"], meta)
        entries.append({
            "url": u,
            "title": meta.get("title"),
            "status": r.get("status"),
            "chars": len(r["markdown"]),
            "words": output.word_count(r["markdown"]),
            "from_cache": r.get("from_cache", False),
            "file": str(path),
        })

    output.write_manifest(out_dir, entries)
    return entries
