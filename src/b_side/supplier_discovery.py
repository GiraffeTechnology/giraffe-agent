"""
B-side supplier discovery — read-only extraction of publicly listed supplier
cards from Alibaba showroom/category pages.

Scope and constraints (compliance-by-design):
  - Only fetches showroom/category listing pages (robots.txt allowed paths),
    never product-detail pages behind anti-bot challenges, login, or search
    APIs requiring authentication.
  - No login, no CAPTCHA solving, no session/cookie reuse across requests.
  - Read-only: does not place orders, message suppliers, or submit forms.
  - Returns an empty list (never raises) on network failure, timeout, or an
    anti-bot challenge page, so callers can apply their own fallback policy.
"""
import re
from dataclasses import dataclass, field

import httpx

from src.m_side.m_event_logger import log_m_event

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
REQUEST_TIMEOUT_SECONDS = 15

# Markers that indicate Alibaba served an anti-bot challenge page instead of
# real listing content (e.g. the AWSC CAPTCHA / "punish" wall).
_ANTI_BOT_MARKERS = ("punish-component", "AWSC/CAPTCHA", "sufei-punish")


@dataclass
class DiscoveredSupplierCard:
    supplier_name: str
    product_title: str
    moq: str | None = None
    price_range_usd: str | None = None
    sold_count: str | None = None
    years_on_platform: int | None = None
    source_url: str = ""
    raw_fields: dict = field(default_factory=dict)


class SupplierDiscoveryError(Exception):
    """Raised only for programmer errors (e.g. bad URL), never for network/anti-bot failures."""


def _is_anti_bot_challenge(html: str) -> bool:
    return any(marker in html for marker in _ANTI_BOT_MARKERS)


def fetch_showroom_html(url: str) -> str | None:
    """
    Fetch a showroom/category listing page. Returns None (not an exception)
    on network failure, non-200 response, or an anti-bot challenge page —
    callers must treat None as "discovery unavailable, apply fallback".
    """
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
    except (httpx.TransportError, httpx.TimeoutException) as exc:
        log_m_event(
            event_type="SUPPLIER_DISCOVERY_FETCH_FAILED",
            payload={"url": url, "reason": str(exc)},
        )
        return None

    if resp.status_code != 200:
        log_m_event(
            event_type="SUPPLIER_DISCOVERY_FETCH_FAILED",
            payload={"url": url, "reason": f"http_{resp.status_code}"},
        )
        return None

    if _is_anti_bot_challenge(resp.text):
        log_m_event(
            event_type="SUPPLIER_DISCOVERY_BLOCKED",
            payload={"url": url, "reason": "anti_bot_challenge"},
        )
        return None

    return resp.text


def parse_showroom_cards(html: str, source_url: str, limit: int = 10) -> list[DiscoveredSupplierCard]:
    """
    Parse supplier/product cards out of a showroom listing page's static HTML.
    Best-effort regex extraction (no JS execution) — fields that aren't found
    are left as None rather than guessed.
    """
    cards: list[DiscoveredSupplierCard] = []

    supplier_names = re.findall(r'title="([^"]{3,80})" data-component="SupplierNameLink"', html)
    years = [int(y) for y in re.findall(r">(\d+)\s*yrs?</", html)]

    title_matches = list(
        re.finditer(r'data-component="ProductTitle"[^>]*>(.*?)</a>', html, re.S)
    )
    price_matches = list(re.finditer(r'data-component="ProductPrice"[^>]*>([^<]{1,40})</', html))
    moq_matches = list(re.finditer(r"MOQ:\s*([^<]{2,30})", html))
    sold_matches = list(re.finditer(r"([\d,]+)\s*sold", html))

    for i, title_match in enumerate(title_matches[:limit]):
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()

        card_start = title_match.start()
        card_end = title_matches[i + 1].start() if i + 1 < len(title_matches) else len(html)

        price_match = next((m for m in price_matches if card_start <= m.start() < card_end), None)
        price = price_match.group(1).strip().lstrip("$") if price_match else None

        moq_match = next((m for m in moq_matches if card_start <= m.start() < card_end), None)
        moq = moq_match.group(1).strip() if moq_match else None

        sold_match = next((m for m in sold_matches if card_start <= m.start() < card_end), None)
        sold = f"{sold_match.group(1)} sold" if sold_match else None

        supplier_name = supplier_names[i] if i < len(supplier_names) else None
        years_val = years[i] if i < len(years) else None

        if not (title and supplier_name):
            continue

        cards.append(
            DiscoveredSupplierCard(
                supplier_name=supplier_name,
                product_title=title,
                moq=moq,
                price_range_usd=price,
                sold_count=sold,
                years_on_platform=years_val,
                source_url=source_url,
            )
        )

    return cards


def discover_suppliers(showroom_url: str, limit: int = 10) -> list[DiscoveredSupplierCard]:
    """
    Fetch + parse a showroom page. Returns [] (not an exception) if the page
    is unreachable or blocked by an anti-bot challenge.
    """
    html = fetch_showroom_html(showroom_url)
    if html is None:
        return []
    return parse_showroom_cards(html, source_url=showroom_url, limit=limit)
