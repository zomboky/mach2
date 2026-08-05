"""Filtrage du markdown par pertinence à une requête — réduit encore les tokens.

Découpe le markdown en blocs (séparés par lignes vides), score chaque bloc par
recouvrement lexical avec les termes de la requête, garde les meilleurs en
conservant l'ordre du document et les titres de section pertinents.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[\wàâäéèêëîïôöùûüç]+", re.IGNORECASE | re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def filter_markdown(md: str, query: str, *, max_blocks: int = 40) -> str:
    """Garde les blocs les plus pertinents pour `query`, dans l'ordre du document."""
    if not md or not query:
        return md
    terms = set(_tokens(query))
    if not terms:
        return md

    blocks = [b for b in re.split(r"\n\s*\n", md) if b.strip()]
    scored = []
    for i, block in enumerate(blocks):
        toks = _tokens(block)
        if not toks:
            continue
        hits = sum(1 for t in toks if t in terms)
        # Bonus pour les titres markdown pertinents
        is_heading = block.lstrip().startswith("#")
        score = hits / (len(toks) ** 0.5)  # normalisation type TF
        if is_heading and hits:
            score += 1.0
        if score > 0:
            scored.append((score, i, block))

    if not scored:
        return md  # rien ne matche → on ne masque pas tout

    scored.sort(key=lambda x: x[0], reverse=True)
    keep_idx = sorted(i for _, i, _ in scored[:max_blocks])
    kept = [blocks[i] for i in keep_idx]
    return "\n\n".join(kept)


def truncate(md: str, max_chars: int | None) -> str:
    """Tronque proprement à max_chars (sur une frontière de bloc si possible)."""
    if not max_chars or len(md) <= max_chars:
        return md
    cut = md[:max_chars]
    nl = cut.rfind("\n\n")
    if nl > max_chars * 0.6:
        cut = cut[:nl]
    return cut.rstrip() + f"\n\n… [tronqué à {max_chars} caractères par Mach2]"
