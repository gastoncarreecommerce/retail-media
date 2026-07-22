from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
import os
from dotenv import load_dotenv

load_dotenv()

import services.ga4 as ga4_svc
import services.vtex as vtex_svc
import services.citrus as citrus_svc

app = FastAPI(title="Retail Media Dashboard", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── GA4 ───────────────────────────────────────────────────────────────────────

@app.get("/api/ga4/overview")
def overview(
    start: Annotated[str, Query()] = "30daysAgo",
    end: Annotated[str, Query()] = "today",
):
    try:
        return ga4_svc.get_overview(start, end)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.get("/api/ga4/source-medium")
def source_medium(
    start: Annotated[str, Query()] = "30daysAgo",
    end: Annotated[str, Query()] = "today",
):
    try:
        return ga4_svc.get_source_medium(start, end)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.get("/api/ga4/category-views")
def category_views(
    start: Annotated[str, Query()] = "30daysAgo",
    end: Annotated[str, Query()] = "today",
):
    try:
        return ga4_svc.get_category_views(start, end)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.get("/api/ga4/sku-metrics")
def sku_metrics(
    eans: Annotated[list[str], Query()] = [],
    start: Annotated[str, Query()] = "30daysAgo",
    end: Annotated[str, Query()] = "today",
):
    try:
        return ga4_svc.get_sku_metrics(eans, start, end)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.get("/api/ga4/sku-source-medium")
def sku_source_medium(
    eans: Annotated[list[str], Query()] = [],
    start: Annotated[str, Query()] = "30daysAgo",
    end: Annotated[str, Query()] = "today",
):
    try:
        return ga4_svc.get_sku_source_medium(eans, start, end)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


@app.get("/api/ga4/demographics")
def demographics(
    start: Annotated[str, Query()] = "30daysAgo",
    end: Annotated[str, Query()] = "today",
):
    try:
        return ga4_svc.get_demographics(start, end)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


# ── VTEX ──────────────────────────────────────────────────────────────────────

@app.get("/api/vtex/skus")
def vtex_skus(q: str | None = None):
    try:
        return vtex_svc.search_skus(q)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


# ── Citrus ────────────────────────────────────────────────────────────────────

@app.get("/api/citrus/banners")
def citrus_banners(
    start: Annotated[str, Query()] = "30daysAgo",
    end: Annotated[str, Query()] = "today",
):
    try:
        return citrus_svc.get_banner_report(start, end)
    except Exception as e:
        raise HTTPException(502, detail=str(e))


# ── Static frontend (must be last) ───────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
