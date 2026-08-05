"""Tests fumée hors-ligne pour Mach2 (aucun réseau requis).

Lancer : python tests/smoke_test.py
Ajouter un test réseau : MACH2_NET=1 python tests/smoke_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import extract, filter as flt, output  # noqa: E402

FIXTURE = """
<html lang="fr">
<head>
  <title>Article de test</title>
  <meta name="description" content="Une description de test.">
  <meta property="og:image" content="https://ex.com/img.png">
</head>
<body>
  <nav><a href="/home">Accueil</a><a href="/about">À propos</a></nav>
  <main>
    <h1>Titre principal</h1>
    <p>La sécurité des mots de passe est essentielle pour l'authentification.</p>
    <p>Ce paragraphe parle de cuisine et n'a aucun rapport avec le sujet.</p>
    <p>Le chiffrement protège les données lors de l'authentification.</p>
    <a href="https://externe.com/page">Lien externe</a>
    <a href="/interne/doc">Doc interne</a>
  </main>
  <footer>Pied de page © 2026</footer>
</body>
</html>
"""

BASE = "https://test.local/article"
_passed = 0
_failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ✓ {name}")
    else:
        _failed += 1
        print(f"  ✗ {name} {detail}")


def test_extract() -> None:
    print("extract:")
    md = extract.to_markdown(FIXTURE, BASE, only_main=True)
    check("markdown non vide", bool(md.strip()))
    check("contient le contenu principal", "authentification" in md.lower())
    check("retire la nav/footer", "Pied de page" not in md, f"→ {md!r}")

    meta = extract.metadata(FIXTURE, BASE)
    check("titre extrait", meta.get("title") == "Article de test", f"→ {meta.get('title')}")
    check("langue extraite", meta.get("language") == "fr")
    check("description extraite", "description" in meta)

    lk = extract.links(FIXTURE, BASE)
    check("liens internes détectés", any("/interne/doc" in u for u in lk["internal"]))
    check("liens externes détectés", any("externe.com" in u for u in lk["external"]))


def test_normalize() -> None:
    print("normalize_url:")
    a = extract.normalize_url("https://Ex.com/Path/")
    b = extract.normalize_url("https://ex.com/Path#frag")
    check("host minuscule + slash final retiré", a == "https://ex.com/Path", f"→ {a}")
    check("fragment retiré", b == "https://ex.com/Path", f"→ {b}")
    root = extract.normalize_url("https://ex.com")
    check("racine → /", root == "https://ex.com/", f"→ {root}")


def test_filter() -> None:
    print("filter:")
    md = extract.to_markdown(FIXTURE, BASE, only_main=True)
    filtered = flt.filter_markdown(md, "sécurité authentification chiffrement")
    check("filtre garde le pertinent", "authentification" in filtered.lower())
    check("filtre écarte le hors-sujet", "cuisine" not in filtered.lower(), f"→ {filtered!r}")

    trunc = flt.truncate("x" * 1000, 100)
    check("troncature respecte le plafond", len(trunc) < 200)
    check("marqueur de troncature", "tronqué" in trunc)


def test_output() -> None:
    print("output:")
    check("slug propre", output.slug("https://ex.com/a/b?x=1").startswith("ex.com_a_b"))
    with tempfile.TemporaryDirectory() as d:
        p = output.write_markdown(Path(d), BASE, "# Bonjour", {"title": "T", "sourceURL": BASE})
        content = p.read_text(encoding="utf-8")
        check("fichier écrit avec front-matter", "title: T" in content and "# Bonjour" in content)
        man = output.write_manifest(Path(d), [{"url": BASE, "file": str(p), "chars": 9}])
        check("manifest écrit", man.exists() and "entries" in man.read_text(encoding="utf-8"))


def test_network() -> None:
    if os.environ.get("MACH2_NET") != "1":
        print("network: (ignoré — MACH2_NET != 1)")
        return
    print("network:")
    from src.scrape import scrape_one
    r = scrape_one("https://example.com", formats=["markdown"], use_cache=False)
    check("scrape example.com", not r.get("error") and bool(r.get("markdown")))


def main() -> int:
    for t in (test_extract, test_normalize, test_filter, test_output, test_network):
        t()
    print(f"\n{_passed} réussis, {_failed} échoués")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
