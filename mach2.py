#!/usr/bin/env python3
"""Mach2 — clone local de Firecrawl. Extraction web économe en tokens.

Sous-commandes : scrape, crawl, map, batch, cache.
Voir SKILL.md / README.md pour le détail.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Console Windows : forcer l'UTF-8 pour les caractères ✓ → •
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import batch as batch_mod  # noqa: E402
from src import cache as cache_mod  # noqa: E402
from src import crawl as crawl_mod  # noqa: E402
from src import mapper as mapper_mod  # noqa: E402
from src import output  # noqa: E402
from src.scrape import scrape_one  # noqa: E402


def _print(msg: str = "") -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------- scrape
def cmd_scrape(a: argparse.Namespace) -> int:
    formats = [f.strip() for f in a.format.split(",") if f.strip()]
    r = scrape_one(
        a.url,
        formats=formats,
        render=a.render,
        only_main=not a.full,
        query=a.filter,
        max_chars=a.max_chars,
        timeout=a.timeout,
        wait_for=a.wait_for,
        use_cache=not a.no_cache,
        max_age=a.max_age,
    )
    if r.get("error"):
        _print(f"✗ {a.url}\n  erreur: {r['error']}")
        return 1

    meta = r.get("metadata", {})

    # Formats non-markdown → sortie directe si demandé seul
    if formats == ["links"]:
        lk = r.get("links", {})
        out_dir = Path(a.out).parent if a.out else output.default_out_dir("links")
        name = (Path(a.out).name if a.out else output.slug(a.url) + "-links.txt")
        path = output.write_lines(out_dir if not a.out else Path(a.out).parent,
                                  name, lk.get("all", []))
        _print(f"✓ {a.url}\n  liens: {len(lk.get('internal', []))} internes, "
               f"{len(lk.get('external', []))} externes\n  → {path}")
        return 0

    if formats == ["metadata"]:
        _print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    md = r.get("markdown", "")
    if a.out:
        path = Path(a.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = output._front_matter(meta) + "\n" + md
        path.write_text(content, encoding="utf-8")
    else:
        out_dir = output.default_out_dir("scrape")
        path = output.write_markdown(out_dir, a.url, md, meta)

    _print(output.summary_line(a.url, meta, md, path, from_cache=r.get("from_cache")))
    if a.show:
        _print("\n--- aperçu ---")
        _print(md[: a.show])
    return 0


# ---------------------------------------------------------------- batch
def cmd_batch(a: argparse.Namespace) -> int:
    urls = list(a.urls or [])
    if a.urls_file:
        urls += [ln.strip() for ln in Path(a.urls_file).read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
    if not urls:
        _print("Aucune URL fournie (positionnelles ou --urls-file).")
        return 2

    out_dir = Path(a.out) if a.out else output.default_out_dir("batch")
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = batch_mod.scrape_many(
        urls, out_dir=out_dir, concurrency=a.concurrency, render=a.render,
        only_main=not a.full, query=a.filter, max_chars=a.max_chars, timeout=a.timeout,
        use_cache=not a.no_cache,
    )
    ok = [e for e in entries if e.get("file")]
    _print(f"✓ batch : {len(ok)}/{len(entries)} pages récupérées → {out_dir}")
    _print(f"  manifest : {out_dir / 'manifest.json'}")
    for e in entries:
        if e.get("file"):
            _print(f"  • {e.get('title') or e['url']} — {e.get('words', 0)} mots — {Path(e['file']).name}")
        else:
            _print(f"  ✗ {e['url']} — {e.get('error')}")
    return 0 if ok else 1


# ---------------------------------------------------------------- map
def cmd_map(a: argparse.Namespace) -> int:
    res = mapper_mod.map_site(a.url, limit=a.limit, search=a.search)
    if not res["urls"]:
        _print(f"✗ Aucune URL découverte pour {a.url}")
        return 1
    out_dir = output.default_out_dir("map")
    name = (Path(a.out).name if a.out else output.slug(a.url) + "-urls.txt")
    target_dir = Path(a.out).parent if a.out else out_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    path = output.write_lines(target_dir, name, res["urls"])
    _print(f"✓ map {a.url}\n  {res['count']} URLs (sur {res['total_found']} trouvées)")
    _print(f"  sources : {', '.join(res['sources']) or '—'}")
    _print(f"  → {path}")
    for u in res["urls"][:15]:
        _print(f"  • {u}")
    if res["count"] > 15:
        _print(f"  … +{res['count'] - 15} autres (voir fichier)")
    return 0


# ---------------------------------------------------------------- crawl
def cmd_crawl(a: argparse.Namespace) -> int:
    out_dir = Path(a.out) if a.out else output.default_out_dir("crawl")
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = crawl_mod.crawl_site(
        a.url, out_dir=out_dir, depth=a.depth, limit=a.limit,
        same_domain=not a.all_domains, include=a.include, exclude=a.exclude,
        concurrency=a.concurrency, render=a.render, only_main=not a.full,
        query=a.filter, max_chars=a.max_chars, timeout=a.timeout, delay=a.delay,
    )
    ok = [e for e in entries if e.get("file")]
    _print(f"✓ crawl {a.url} : {len(ok)}/{len(entries)} pages → {out_dir}")
    _print(f"  manifest : {out_dir / 'manifest.json'}")
    for e in entries:
        if e.get("file"):
            _print(f"  • [d{e.get('depth')}] {e.get('title') or e['url']} — "
                   f"{e.get('words', 0)} mots — {Path(e['file']).name}")
        else:
            _print(f"  ✗ {e['url']} — {e.get('error')}")
    return 0 if ok else 1


# ---------------------------------------------------------------- cache
def cmd_cache(a: argparse.Namespace) -> int:
    if a.action == "clear":
        n = cache_mod.clear()
        _print(f"Cache vidé : {n} entrées supprimées.")
    else:
        d = cache_mod.CACHE_DIR
        n = len(list(d.glob("*.json"))) if d.exists() else 0
        _print(f"Cache : {n} entrées — {d}")
    return 0


# ---------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mach2", description="Mach2 — extraction web économe en tokens (clone Firecrawl).")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--render", action="store_true", help="Rendu JS via Playwright")
        sp.add_argument("--full", action="store_true", help="Garder toute la page (désactive only-main)")
        sp.add_argument("--filter", metavar="REQUÊTE", help="Ne garder que les passages pertinents")
        sp.add_argument("--max-chars", type=int, help="Plafonner la sortie markdown")
        sp.add_argument("--timeout", type=int, default=30, help="Timeout en secondes (défaut 30)")
        sp.add_argument("--no-cache", action="store_true", help="Ignorer le cache")

    # scrape
    s = sub.add_parser("scrape", help="Scraper une URL")
    s.add_argument("url")
    s.add_argument("--format", default="markdown",
                   help="markdown,html,rawhtml,links,metadata,json (séparés par virgule)")
    s.add_argument("--wait-for", help="Sélecteur CSS ou ms à attendre (avec --render)")
    s.add_argument("--out", help="Fichier de sortie")
    s.add_argument("--show", type=int, metavar="N", help="Afficher les N 1ers caractères")
    s.add_argument("--max-age", type=int, default=cache_mod.DEFAULT_TTL,
                   help="Fraîcheur cache en secondes (0 = pas de cache)")
    add_common(s)
    s.set_defaults(func=cmd_scrape)

    # batch
    b = sub.add_parser("batch", help="Scraper plusieurs URLs en parallèle")
    b.add_argument("urls", nargs="*")
    b.add_argument("--urls-file", help="Fichier d'URLs (une par ligne)")
    b.add_argument("--concurrency", type=int, default=5)
    b.add_argument("--out", help="Dossier de sortie")
    b.add_argument("--format", default="markdown", help=argparse.SUPPRESS)
    add_common(b)
    b.set_defaults(func=cmd_batch)

    # map
    m = sub.add_parser("map", help="Découvrir les URLs d'un site")
    m.add_argument("url")
    m.add_argument("--limit", type=int, default=5000)
    m.add_argument("--search", help="Filtrer les URLs contenant ce terme")
    m.add_argument("--out", help="Fichier de sortie")
    m.set_defaults(func=cmd_map)

    # crawl
    c = sub.add_parser("crawl", help="Crawler un site récursivement")
    c.add_argument("url")
    c.add_argument("--depth", type=int, default=2)
    c.add_argument("--limit", type=int, default=20)
    c.add_argument("--all-domains", action="store_true", help="Ne pas restreindre au domaine seed")
    c.add_argument("--include", help="Regex : n'inclure que les URLs qui matchent")
    c.add_argument("--exclude", help="Regex : exclure les URLs qui matchent")
    c.add_argument("--concurrency", type=int, default=5)
    c.add_argument("--delay", type=float, default=0.0, help="Délai (s) entre requêtes par worker")
    c.add_argument("--out", help="Dossier de sortie")
    add_common(c)
    c.set_defaults(func=cmd_crawl)

    # cache
    ca = sub.add_parser("cache", help="Gérer le cache")
    ca.add_argument("action", choices=["status", "clear"], nargs="?", default="status")
    ca.set_defaults(func=cmd_cache)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
