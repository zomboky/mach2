"""Écriture des résultats en fichiers + résumés console compacts + manifest.json.

Principe « fichiers d'abord » : le contenu complet va dans des fichiers, la
console ne renvoie qu'un résumé compact (titre, taille, chemin) pour que le
contexte du LLM n'ingère jamais des pages entières.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def default_out_dir(prefix: str = "scrape") -> Path:
    """Dossier de sortie par défaut sous le scratchpad de session, sinon ./mach2_out."""
    base = os.environ.get("CLAUDE_SCRATCHPAD") or os.environ.get("TEMP") or "."
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    d = Path(base) / "mach2" / f"{prefix}-{stamp}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def slug(url: str, max_len: int = 60) -> str:
    """Nom de fichier lisible dérivé de l'URL."""
    p = urlparse(url)
    raw = (p.netloc + p.path).strip("/") or p.netloc or "page"
    s = re.sub(r"[^\w\-.]+", "_", raw).strip("_")
    if len(s) > max_len:
        s = s[:max_len].rstrip("_")
    return s or "page"


def _front_matter(meta: dict) -> str:
    lines = ["---"]
    for k in ("title", "sourceURL", "finalURL", "description", "language",
              "author", "date", "statusCode"):
        v = meta.get(k)
        if v:
            v = str(v).replace("\n", " ").strip()
            lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines)


def write_markdown(out_dir: Path, url: str, markdown: str, meta: dict,
                   *, name: str | None = None) -> Path:
    fname = (name or slug(url)) + ".md"
    path = out_dir / fname
    content = _front_matter(meta) + "\n" + (markdown or "")
    path.write_text(content, encoding="utf-8")
    return path


def word_count(text: str) -> int:
    return len(text.split())


def summary_line(url: str, meta: dict, markdown: str, path: Path,
                 *, from_cache: bool = False) -> str:
    title = meta.get("title", "(sans titre)")
    wc = word_count(markdown)
    chars = len(markdown)
    tag = " [cache]" if from_cache else ""
    return (f"✓ {url}{tag}\n"
            f"  titre : {title}\n"
            f"  taille: {wc} mots / {chars} car.\n"
            f"  → {path}")


def write_manifest(out_dir: Path, entries: list[dict]) -> Path:
    path = out_dir / "manifest.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(entries),
        "entries": entries,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_lines(out_dir: Path, name: str, lines: list[str]) -> Path:
    path = out_dir / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
