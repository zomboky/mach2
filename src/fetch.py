"""Couche de récupération HTTP — fetch statique (requests) + rendu JS optionnel (Playwright).

Renvoie un dict : {url, final_url, status, content_type, html, from_cache, render, error}
`html` contient le corps texte (HTML ou texte extrait de PDF si applicable).
"""

from __future__ import annotations

import requests

from . import cache

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Mach2/0.1"
)
DEFAULT_TIMEOUT = 30  # secondes


def _headers(extra: dict | None = None) -> dict:
    h = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr,en;q=0.8",
    }
    if extra:
        h.update(extra)
    return h


def _extract_pdf(content: bytes) -> str | None:
    """Extraction texte basique d'un PDF si pypdf est dispo, sinon None."""
    try:
        import io

        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return None
    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return None


def fetch_static(url: str, *, timeout: int = DEFAULT_TIMEOUT, headers: dict | None = None) -> dict:
    """Récupération HTTP statique via requests."""
    result = {
        "url": url,
        "final_url": url,
        "status": None,
        "content_type": None,
        "html": "",
        "from_cache": False,
        "render": False,
        "error": None,
    }
    try:
        resp = requests.get(
            url, headers=_headers(headers), timeout=timeout, allow_redirects=True
        )
        result["status"] = resp.status_code
        result["final_url"] = resp.url
        ctype = resp.headers.get("Content-Type", "").lower()
        result["content_type"] = ctype

        if "application/pdf" in ctype or url.lower().endswith(".pdf"):
            text = _extract_pdf(resp.content)
            if text is None:
                result["error"] = "PDF détecté mais pypdf non installé (pip install pypdf)"
            else:
                result["html"] = text
                result["content_type"] = "application/pdf"
            return result

        resp.encoding = resp.encoding or resp.apparent_encoding
        result["html"] = resp.text
    except requests.RequestException as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result


def fetch_render(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    wait_for: str | None = None,
    headers: dict | None = None,
) -> dict:
    """Récupération avec rendu JS via Playwright (Chromium)."""
    result = {
        "url": url,
        "final_url": url,
        "status": None,
        "content_type": "text/html",
        "html": "",
        "from_cache": False,
        "render": True,
        "error": None,
    }
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        result["error"] = (
            "Playwright non installé. Installe-le : "
            "pip install playwright && python -m playwright install chromium"
        )
        return result

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT, extra_http_headers=headers or {})
            resp = page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            if resp is not None:
                result["status"] = resp.status
                result["final_url"] = resp.url
            if wait_for:
                try:
                    if wait_for.isdigit():
                        page.wait_for_timeout(int(wait_for))
                    else:
                        page.wait_for_selector(wait_for, timeout=timeout * 1000)
                except Exception:
                    pass  # best-effort : on continue même si le sélecteur n'apparaît pas
            result["html"] = page.content()
            browser.close()
    except Exception as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            result["error"] = (
                "Navigateur Chromium manquant : python -m playwright install chromium"
            )
        else:
            result["error"] = f"{type(e).__name__}: {e}"
    return result


def fetch(
    url: str,
    *,
    render: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    wait_for: str | None = None,
    headers: dict | None = None,
    use_cache: bool = True,
    max_age: int = cache.DEFAULT_TTL,
) -> dict:
    """Point d'entrée unifié : cache → fetch (statique ou rendu) → mise en cache."""
    if use_cache:
        cached = cache.get(url, render=render, max_age=max_age)
        if cached is not None:
            meta = cached.get("meta", {})
            return {
                "url": url,
                "final_url": meta.get("final_url", url),
                "status": meta.get("status"),
                "content_type": meta.get("content_type"),
                "html": cached["html"],
                "from_cache": True,
                "render": render,
                "error": None,
            }

    result = fetch_render(url, timeout=timeout, wait_for=wait_for, headers=headers) if render \
        else fetch_static(url, timeout=timeout, headers=headers)

    if use_cache and result["html"] and not result["error"]:
        cache.put(
            url,
            result["html"],
            {
                "final_url": result["final_url"],
                "status": result["status"],
                "content_type": result["content_type"],
            },
            render=render,
        )
    return result
