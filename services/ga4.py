"""GA4 Data API v1beta integration with mock-data fallback."""

import os
import random
from datetime import datetime, timedelta
from typing import Optional

_MOCK = not (os.getenv("GA4_PROPERTY_ID") and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))


def _client():
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    return BetaAnalyticsDataClient()


def _prop():
    return f"properties/{os.getenv('GA4_PROPERTY_ID')}"


# ── helpers ───────────────────────────────────────────────────────────────────

def _rows_to_list(response, dim_names, metric_names):
    out = []
    for row in response.rows:
        record = {}
        for i, d in enumerate(dim_names):
            record[d] = row.dimension_values[i].value
        for i, m in enumerate(metric_names):
            val = row.metric_values[i].value
            record[m] = float(val) if "." in val else int(val)
        out.append(record)
    return out


def _date_range(start: str, end: str):
    from google.analytics.data_v1beta.types import DateRange
    return DateRange(start_date=start, end_date=end)


def _dim(name: str):
    from google.analytics.data_v1beta.types import Dimension
    return Dimension(name=name)


def _metric(name: str):
    from google.analytics.data_v1beta.types import Metric
    return Metric(name=name)


def _in_list_filter(field: str, values: list):
    from google.analytics.data_v1beta.types import (
        FilterExpression, Filter
    )
    return FilterExpression(
        filter=Filter(
            field_name=field,
            in_list_filter=Filter.InListFilter(values=values),
        )
    )


# ── public API ────────────────────────────────────────────────────────────────

def get_overview(start: str, end: str) -> dict:
    """Active users + sessions grouped by date."""
    if _MOCK:
        return _mock_overview(start, end)

    from google.analytics.data_v1beta.types import RunReportRequest, OrderBy
    client = _client()
    resp = client.run_report(
        RunReportRequest(
            property=_prop(),
            date_ranges=[_date_range(start, end)],
            dimensions=[_dim("date")],
            metrics=[_metric("activeUsers"), _metric("sessions")],
            order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
        )
    )
    rows = _rows_to_list(resp, ["date"], ["activeUsers", "sessions"])
    total_users = sum(r["activeUsers"] for r in rows)
    total_sessions = sum(r["sessions"] for r in rows)
    return {"rows": rows, "totals": {"activeUsers": total_users, "sessions": total_sessions}}


def get_source_medium(start: str, end: str) -> dict:
    """Session counts by source / medium."""
    if _MOCK:
        return _mock_source_medium()

    from google.analytics.data_v1beta.types import RunReportRequest, OrderBy
    client = _client()
    resp = client.run_report(
        RunReportRequest(
            property=_prop(),
            date_ranges=[_date_range(start, end)],
            dimensions=[_dim("sessionSource"), _dim("sessionMedium")],
            metrics=[_metric("sessions")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            limit=15,
        )
    )
    return {"rows": _rows_to_list(resp, ["sessionSource", "sessionMedium"], ["sessions"])}


def get_category_views(start: str, end: str) -> dict:
    """view_item_list counts by item list name (= category)."""
    if _MOCK:
        return _mock_category_views()

    from google.analytics.data_v1beta.types import RunReportRequest, OrderBy
    client = _client()
    resp = client.run_report(
        RunReportRequest(
            property=_prop(),
            date_ranges=[_date_range(start, end)],
            dimensions=[_dim("itemListName")],
            metrics=[_metric("itemListViews")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="itemListViews"), desc=True)],
            limit=20,
        )
    )
    return {"rows": _rows_to_list(resp, ["itemListName"], ["itemListViews"])}


def get_sku_metrics(eans: list[str], start: str, end: str) -> dict:
    """Item funnel metrics filtered by a list of EANs (itemId)."""
    if not eans:
        return {"rows": []}

    if _MOCK:
        return _mock_sku_metrics(eans)

    from google.analytics.data_v1beta.types import RunReportRequest, OrderBy
    client = _client()
    resp = client.run_report(
        RunReportRequest(
            property=_prop(),
            date_ranges=[_date_range(start, end)],
            dimensions=[_dim("itemId"), _dim("itemName")],
            metrics=[
                _metric("itemListViews"),
                _metric("itemViews"),
                _metric("itemsAddedToCart"),
                _metric("itemsPurchased"),
                _metric("itemRevenue"),
            ],
            dimension_filter=_in_list_filter("itemId", eans),
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="itemRevenue"), desc=True)],
        )
    )
    return {"rows": _rows_to_list(
        resp,
        ["itemId", "itemName"],
        ["itemListViews", "itemViews", "itemsAddedToCart", "itemsPurchased", "itemRevenue"],
    )}


# ── mock data ────────────────────────────────────────────────────────────────

def _mock_overview(start: str, end: str) -> dict:
    random.seed(42)
    # Generate 30 days of data regardless of range
    base = datetime.today() - timedelta(days=29)
    rows = []
    for i in range(30):
        day = base + timedelta(days=i)
        rows.append({
            "date": day.strftime("%Y%m%d"),
            "activeUsers": random.randint(800, 2400),
            "sessions": random.randint(1000, 3000),
        })
    total_users = sum(r["activeUsers"] for r in rows)
    total_sessions = sum(r["sessions"] for r in rows)
    return {"rows": rows, "totals": {"activeUsers": total_users, "sessions": total_sessions}, "_mock": True}


def _mock_source_medium() -> dict:
    return {
        "_mock": True,
        "rows": [
            {"sessionSource": "google", "sessionMedium": "organic", "sessions": 12340},
            {"sessionSource": "google", "sessionMedium": "cpc", "sessions": 8210},
            {"sessionSource": "(direct)", "sessionMedium": "(none)", "sessions": 5430},
            {"sessionSource": "instagram", "sessionMedium": "social", "sessions": 3120},
            {"sessionSource": "email", "sessionMedium": "email", "sessions": 2180},
            {"sessionSource": "facebook", "sessionMedium": "cpc", "sessions": 1870},
            {"sessionSource": "bing", "sessionMedium": "organic", "sessions": 920},
            {"sessionSource": "referral", "sessionMedium": "referral", "sessions": 710},
        ],
    }


def _mock_category_views() -> dict:
    return {
        "_mock": True,
        "rows": [
            {"itemListName": "Electrónica", "itemListViews": 18430},
            {"itemListName": "Ropa y Accesorios", "itemListViews": 14200},
            {"itemListName": "Hogar y Jardín", "itemListViews": 9870},
            {"itemListName": "Deportes", "itemListViews": 7340},
            {"itemListName": "Juguetes", "itemListViews": 5910},
            {"itemListName": "Belleza y Cuidado", "itemListViews": 4820},
            {"itemListName": "Alimentos y Bebidas", "itemListViews": 3650},
            {"itemListName": "Automotriz", "itemListViews": 2100},
            {"itemListName": "Mascotas", "itemListViews": 1740},
            {"itemListName": "Libros", "itemListViews": 980},
        ],
    }


def _mock_sku_metrics(eans: list[str]) -> dict:
    random.seed(99)
    rows = []
    for ean in eans:
        views_list = random.randint(300, 5000)
        views_item = int(views_list * random.uniform(0.3, 0.7))
        atc = int(views_item * random.uniform(0.1, 0.35))
        purchased = int(atc * random.uniform(0.3, 0.7))
        revenue = round(purchased * random.uniform(15.0, 250.0), 2)
        rows.append({
            "itemId": ean,
            "itemName": f"Producto EAN {ean}",
            "itemListViews": views_list,
            "itemViews": views_item,
            "itemsAddedToCart": atc,
            "itemsPurchased": purchased,
            "itemRevenue": revenue,
        })
    return {"rows": rows, "_mock": True}
