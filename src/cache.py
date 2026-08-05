"""Cache disque simple avec TTL — évite de re-télécharger la même URL.

Équivalent du paramètre `maxAge` de Firecrawl. La clé est un hash de l'URL
(+ mode render), la valeur est le HTML brut récupéré, stockée sous forme de
fichiers dans un dossier de cache.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

# Dossier de cache par défaut : à côté du skill, dossier .cache/
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
DEFAULT_TTL = 24 * 3600  # 24 h


def _key(url: str, render: bool = False) -> str:
    raw = f"{'R' if render else 'S'}:{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def get(url: str, *, render: bool = False, max_age: int = DEFAULT_TTL) -> dict | None:
    """Renvoie l'entrée de cache si présente et pas expirée, sinon None."""
    if max_age <= 0:
        return None
    path = CACHE_DIR / f"{_key(url, render)}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    age = time.time() - data.get("fetched_at", 0)
    if age > max_age:
        return None
    data["_cache_age"] = int(age)
    return data


def put(url: str, html: str, meta: dict, *, render: bool = False) -> None:
    """Stocke le HTML + métadonnées de fetch pour une URL."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_key(url, render)}.json"
    payload = {
        "url": url,
        "render": render,
        "fetched_at": time.time(),
        "html": html,
        "meta": meta,
    }
    try:
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # le cache est best-effort


def clear() -> int:
    """Vide le cache. Renvoie le nombre de fichiers supprimés."""
    if not CACHE_DIR.exists():
        return 0
    n = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    return n
