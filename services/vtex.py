"""VTEX Catalog API integration with mock-data fallback."""

import os
import httpx
from typing import Optional

_ACCOUNT = os.getenv("VTEX_ACCOUNT", "")
_KEY = os.getenv("VTEX_APP_KEY", "")
_TOKEN = os.getenv("VTEX_APP_TOKEN", "")
_ENV = os.getenv("VTEX_ENVIRONMENT", "vtexcommercestable")
_MOCK = not (_ACCOUNT and _KEY and _TOKEN)

_BASE = f"https://{_ACCOUNT}.{_ENV}.com.br" if _ACCOUNT else ""
_HEADERS = {"X-VTEX-API-AppKey": _KEY, "X-VTEX-API-AppToken": _TOKEN}


def search_skus(q: Optional[str] = None) -> dict:
    """Search SKUs by EAN or name. Falls back to listing first page."""
    if _MOCK:
        return _mock_skus(q)

    with httpx.Client(headers=_HEADERS, timeout=15) as client:
        # If query looks like an EAN (numeric), try EAN lookup first
        if q and q.strip().isdigit():
            r = client.get(f"{_BASE}/api/catalog_system/pvt/sku/stockkeepingunitbyean/{q.strip()}")
            if r.status_code == 200:
                sku = r.json()
                return {"skus": [_normalize_sku(sku)]}

        # Otherwise search by name or return first page
        url = f"{_BASE}/api/catalog_system/pvt/sku/stockkeepingunitids"
        params = {"page": 1, "pagesize": 50}
        r = client.get(url, params=params)
        r.raise_for_status()
        sku_ids = r.json()

        # Fetch details for first batch
        skus = []
        for sku_id in sku_ids[:20]:
            detail = client.get(
                f"{_BASE}/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
            )
            if detail.status_code == 200:
                data = detail.json()
                sku = _normalize_sku(data)
                if not q or q.lower() in sku["name"].lower() or q in sku["ean"]:
                    skus.append(sku)

        return {"skus": skus}


def get_sku_by_ean(ean: str) -> Optional[dict]:
    """Resolve a single EAN to SKU metadata."""
    if _MOCK:
        return {"ean": ean, "id": f"SKU-{ean[-4:]}", "name": f"Producto EAN {ean}"}

    with httpx.Client(headers=_HEADERS, timeout=10) as client:
        r = client.get(f"{_BASE}/api/catalog_system/pvt/sku/stockkeepingunitbyean/{ean}")
        if r.status_code == 200:
            return _normalize_sku(r.json())
    return None


def _normalize_sku(raw: dict) -> dict:
    return {
        "id": str(raw.get("Id", "")),
        "ean": raw.get("Ean") or raw.get("EAN") or "",
        "name": raw.get("NameComplete") or raw.get("Name", ""),
        "productId": str(raw.get("ProductId", "")),
    }


def _mock_skus(q: Optional[str]) -> dict:
    all_skus = [
        {"id": "10001", "ean": "7891000315507", "name": "Leche Entera 1L", "productId": "1001"},
        {"id": "10002", "ean": "7891000315514", "name": "Leche Descremada 1L", "productId": "1002"},
        {"id": "10003", "ean": "7891910000197", "name": "Café Molido 500g", "productId": "1003"},
        {"id": "10004", "ean": "7896004700191", "name": "Aceite de Oliva 500ml", "productId": "1004"},
        {"id": "10005", "ean": "7891152402019", "name": "Arroz Integral 1kg", "productId": "1005"},
        {"id": "10006", "ean": "7896336010058", "name": "Jabón Liquido 500ml", "productId": "1006"},
        {"id": "10007", "ean": "7891167022396", "name": "Shampoo Control Caída 400ml", "productId": "1007"},
        {"id": "10008", "ean": "7502249561218", "name": "Desodorante Spray 150ml", "productId": "1008"},
        {"id": "10009", "ean": "7891010116606", "name": "Crema Hidratante 200ml", "productId": "1009"},
        {"id": "10010", "ean": "7898924560083", "name": "Protector Solar FPS50 120ml", "productId": "1010"},
        {"id": "10011", "ean": "7891234567890", "name": "Detergente Líquido 1L", "productId": "1011"},
        {"id": "10012", "ean": "7890901234567", "name": "Yogur Natural 180g", "productId": "1012"},
    ]
    if q:
        q_lower = q.lower()
        all_skus = [s for s in all_skus if q_lower in s["name"].lower() or q in s["ean"]]
    return {"skus": all_skus, "_mock": True}
