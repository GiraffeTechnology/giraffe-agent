"""
1688 Open Platform API client.

COMPLIANCE: Direct scraping of 1688.com is prohibited by its robots.txt
and Terms of Service (Section 9). This module uses the official 1688 Open
Platform API exclusively.

Pre-requisites (blocking — cannot run without these):
  1. Register a developer account at https://open.1688.com
  2. Apply for product search API permission (alibaba.china.product.search)
  3. Obtain AppKey, AppSecret, and AccessToken
  4. Set ALIBABA_1688_APP_KEY / APP_SECRET / ACCESS_TOKEN in .env.market-reference
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# 1688 Open Platform gateway
_GATEWAY = "https://gw.open.1688.com/openapi"
_API_VERSION = 2
DOMAIN = "open.1688.com"

_rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("SCRAPE_RATE_LIMIT_PER_MINUTE", "5"))
)


def _sign(params: dict, app_secret: str) -> str:
    """
    1688 Open Platform HMAC-MD5 signature.
    Algorithm: sort keys, concat key+value, wrap with secret, HMAC-MD5 uppercase.
    """
    sorted_pairs = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    payload = f"{app_secret}{sorted_pairs}{app_secret}"
    return hmac.new(
        app_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.md5,
    ).hexdigest().upper()


def _check_credentials() -> tuple[str, str, str]:
    app_key = os.getenv("ALIBABA_1688_APP_KEY", "")
    app_secret = os.getenv("ALIBABA_1688_APP_SECRET", "")
    access_token = os.getenv("ALIBABA_1688_ACCESS_TOKEN", "")
    if not all([app_key, app_secret, access_token]):
        raise EnvironmentError(
            "1688 API credentials not configured. "
            "Set ALIBABA_1688_APP_KEY, ALIBABA_1688_APP_SECRET, "
            "ALIBABA_1688_ACCESS_TOKEN in .env.market-reference. "
            "Apply at https://open.1688.com"
        )
    return app_key, app_secret, access_token


def search_products(
    keyword: str,
    page: int = 1,
    page_size: int = 20,
    snapshot_dir: Optional[str] = None,
) -> list[dict]:
    """
    Call alibaba.china.product.search via the official 1688 Open Platform API.
    Returns a list of raw product dicts with price, seller, and URL fields.

    Each response is saved as a JSON snapshot for audit traceability.
    """
    app_key, app_secret, access_token = _check_credentials()

    params = {
        "app_key": app_key,
        "access_token": access_token,
        "timestamp": str(int(time.time() * 1000)),
        "keyWord": keyword,
        "currentPage": str(page),
        "pageSize": str(min(page_size, 20)),
    }
    params["sign"] = _sign(params, app_secret)

    url = f"{_GATEWAY}/param2/{_API_VERSION}/com.alibaba.product/alibaba.china.product.search/{app_key}"
    source_url = f"{url}?keyWord={keyword}&currentPage={page}"

    _rate_limiter.wait(DOMAIN)

    scraped_at = datetime.now(timezone.utc)
    try:
        resp = requests.get(
            url,
            params=params,
            headers={"User-Agent": os.getenv("SCRAPE_USER_AGENT", "GiraffePricingResearch/1.0")},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("1688 API request failed: %s", exc)
        return []

    raw_data = resp.json()
    _save_snapshot(raw_data, source_url, scraped_at, snapshot_dir)

    products = raw_data.get("result", {}).get("productList", [])
    return [
        _normalise_product(p, source_url, scraped_at, snapshot_dir)
        for p in products
        if _has_price(p)
    ]


def _has_price(product: dict) -> bool:
    try:
        price_range = product.get("tradePrice", {}) or product.get("priceRange", {})
        return bool(price_range)
    except Exception:
        return False


def _normalise_product(
    product: dict,
    source_url: str,
    scraped_at: datetime,
    snapshot_dir: Optional[str],
) -> dict:
    price_range = product.get("tradePrice", {}) or product.get("priceRange", {})
    # Use the lower bound of the price range as a conservative unit price
    try:
        unit_price = float(
            price_range.get("minPrice") or price_range.get("price") or 0
        )
    except (TypeError, ValueError):
        unit_price = 0.0

    offer_url = product.get("detailUrl", source_url)
    if offer_url and not offer_url.startswith("http"):
        offer_url = f"https:{offer_url}"

    snapshot_path = _save_snapshot(product, offer_url, scraped_at, snapshot_dir)

    return {
        "source_platform": "alibaba_1688",
        "source_url": offer_url,
        "seller_id": str(product.get("sellerUserId") or product.get("memberId", "")),
        "sku_model_raw": product.get("subject") or product.get("title", ""),
        "unit_price": unit_price,
        "currency": "CNY",
        "moq": _parse_moq(product),
        "quote_timestamp": scraped_at,
        "scraped_at": scraped_at,
        "raw_html_snapshot_path": snapshot_path,
        "extraction_method": "api_direct",
        "extraction_confidence": 1.0,  # API response is structured — no NLP extraction
    }


def _parse_moq(product: dict) -> Optional[int]:
    try:
        return int(product.get("minOrderQuantity") or product.get("moq") or 0) or None
    except (TypeError, ValueError):
        return None


def _save_snapshot(
    data: dict,
    source_url: str,
    scraped_at: datetime,
    snapshot_dir: Optional[str],
) -> Optional[str]:
    if not snapshot_dir:
        snapshot_dir = os.getenv("HTML_SNAPSHOT_DIR", "/data/snapshots")
    Path(snapshot_dir).mkdir(parents=True, exist_ok=True)

    ts = scraped_at.strftime("%Y%m%dT%H%M%SZ")
    url_slug = source_url.replace("https://", "").replace("/", "_")[:80]
    filename = f"1688_{ts}_{url_slug}.json"
    path = Path(snapshot_dir) / filename

    payload = {
        "source_url": source_url,
        "scraped_at": scraped_at.isoformat(),
        "data": data,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
