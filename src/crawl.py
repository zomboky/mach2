"""Crawl récursif BFS d'un site — scrape chaque page découverte.

Respecte profondeur, limite, même-domaine, motifs include/exclude. Concurrence
par niveau via ThreadPoolExecutor. Écrit un .md par page + manifest.json.
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from . import extract, output
from .scrape import scrape_one


def crawl_site(
    seed: str,
    *,
    out_dir: Path,
    depth: int = 2,
    limit: int = 20,
    same_domain: bool = True,
    include: str | None = None,
    exclude: str | None = None,
    concurrency: int = 5,
    render: bool = False,
    only_main: bool = True,
    query: str | None = None,
    max_chars: int | None = None,
    timeout: int = 30,
    delay: float = 0.0,
) -> list[dict]:
    seed = extract.normalize_url(seed)
    seed_host = urlparse(seed).netloc
    inc = re.compile(include) if include else None
    exc = re.compile(exclude) if exclude else None

    visited: set[str] = set()
    entries: list[dict] = []
    frontier = [seed]

    def allowed(u: str) -> bool:
        p = urlparse(u)
        if p.scheme not in ("http", "https"):
            return False
        if same_domain and p.netloc != seed_host:
            return False
        if inc and not inc.search(u):
            return False
        if exc and exc.search(u):
            return False
        return True

    for level in range(depth + 1):
        if not frontier or len(visited) >= limit:
            break
        # Prochaine vague à traiter à ce niveau
        batch = []
        for u in frontier:
            if u not in visited and allowed(u) and len(visited) + len(batch) < limit:
                batch.append(u)
        if not batch:
            break
        for u in batch:
            visited.add(u)

        next_frontier: list[str] = []

        def work(u: str) -> dict:
            if delay:
                time.sleep(delay)
            r = scrape_one(
                u, formats=["markdown", "links"], render=render,
                only_main=only_main, query=query, max_chars=max_chars, timeout=timeout,
            )
            return r

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            futures = {pool.submit(work, u): u for u in batch}
            for fut in as_completed(futures):
                u = futures[fut]
                try:
                    r = fut.result()
                except Exception as e:
                    entries.append({"url": u, "error": f"{type(e).__name__}: {e}",
                                    "file": None, "depth": level})
                    continue
                if r.get("error") or not r.get("markdown"):
                    entries.append({"url": u, "status": r.get("status"),
                                    "error": r.get("error") or "vide",
                                    "file": None, "depth": level})
                    continue
                meta = r.get("metadata", {})
                path = output.write_markdown(out_dir, u, r["markdown"], meta)
                entries.append({
                    "url": u,
                    "title": meta.get("title"),
                    "status": r.get("status"),
                    "chars": len(r["markdown"]),
                    "words": output.word_count(r["markdown"]),
                    "depth": level,
                    "file": str(path),
                })
                # Collecte des liens pour le niveau suivant
                if level < depth:
                    for link in r.get("links", {}).get("internal", []):
                        link = extract.normalize_url(link)
                        if link not in visited and allowed(link):
                            next_frontier.append(link)

        frontier = list(dict.fromkeys(next_frontier))

    output.write_manifest(out_dir, entries)
    return entries
