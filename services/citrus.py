"""CitrusAd reporting API integration with mock-data fallback.

CitrusAd uses an API key in the Authorization header and exposes a reporting
endpoint.  The exact path varies by customer contract – override CITRUS_API_URL
if your tenant has a custom base URL.
"""

import os
import httpx

_API_KEY = os.getenv("CITRUS_API_KEY", "")
_CUSTOMER_ID = os.getenv("CITRUS_CUSTOMER_ID", "")
_BASE = os.getenv("CITRUS_API_URL", "https://api.citrusad.com")
_MOCK = not (_API_KEY and _CUSTOMER_ID)

_HEADERS = {
    "Authorization": f"ApiKey {_API_KEY}",
    "Content-Type": "application/json",
}


def get_banner_report(start: str, end: str) -> dict:
    """Retrieve banner impressions + clicks from CitrusAd."""
    if _MOCK:
        return _mock_banners()

    # CitrusAd v1 reporting endpoint
    payload = {
        "customerId": _CUSTOMER_ID,
        "reportType": "banner",
        "startDate": _normalize_date(start),
        "endDate": _normalize_date(end),
        "groupBy": ["bannerId", "bannerName", "campaignName"],
        "metrics": ["impressions", "clicks"],
    }

    with httpx.Client(headers=_HEADERS, timeout=30) as client:
        r = client.post(f"{_BASE}/v1/analytics/report", json=payload)
        r.raise_for_status()
        data = r.json()

    rows = []
    for item in data.get("data", []):
        impressions = int(item.get("impressions", 0))
        clicks = int(item.get("clicks", 0))
        rows.append({
            "bannerId": item.get("bannerId", ""),
            "bannerName": item.get("bannerName", ""),
            "campaignName": item.get("campaignName", ""),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round(clicks / impressions * 100, 2) if impressions else 0.0,
        })

    rows.sort(key=lambda x: x["impressions"], reverse=True)
    return {"rows": rows}


def _normalize_date(d: str) -> str:
    """Convert GA4-style relative dates to ISO format for CitrusAd."""
    from datetime import datetime, timedelta
    if d == "today":
        return datetime.today().strftime("%Y-%m-%d")
    if d.endswith("daysAgo"):
        days = int(d.replace("daysAgo", ""))
        return (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    return d  # assume already ISO


def _mock_banners() -> dict:
    return {
        "_mock": True,
        "rows": [
            {"bannerId": "BAN-001", "bannerName": "Hero Home - Verano 2025", "campaignName": "Verano Premium", "impressions": 98400, "clicks": 2952, "ctr": 3.00},
            {"bannerId": "BAN-002", "bannerName": "Electrónica - Black Friday", "campaignName": "Black Friday Tech", "impressions": 74200, "clicks": 1484, "ctr": 2.00},
            {"bannerId": "BAN-003", "bannerName": "Belleza Top Banner", "campaignName": "Campaña Belleza Q2", "impressions": 61300, "clicks": 1839, "ctr": 3.00},
            {"bannerId": "BAN-004", "bannerName": "Sidebar Hogar", "campaignName": "Hogar & Deco", "impressions": 45800, "clicks": 687, "ctr": 1.50},
            {"bannerId": "BAN-005", "bannerName": "PDP Banner Bebidas", "campaignName": "Bebidas Saludables", "impressions": 38100, "clicks": 1143, "ctr": 3.00},
            {"bannerId": "BAN-006", "bannerName": "Carrito Upsell Snacks", "campaignName": "Snacks Impulse", "impressions": 29700, "clicks": 891, "ctr": 3.00},
            {"bannerId": "BAN-007", "bannerName": "Search Banner Café", "campaignName": "Café Premium", "impressions": 22400, "clicks": 896, "ctr": 4.00},
            {"bannerId": "BAN-008", "bannerName": "Category Banner Ropa", "campaignName": "Nueva Temporada", "impressions": 18900, "clicks": 378, "ctr": 2.00},
        ],
    }
