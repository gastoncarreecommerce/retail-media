import ipaddress
import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

import services.ga4 as ga4_svc
import services.vtex as vtex_svc
import services.citrus as citrus_svc

app = FastAPI(title="Retail Media Dashboard", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── IP helpers ────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    """Return the real client IP, preferring X-Forwarded-For (set by Vercel)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host or ""


def _ip_allowed(ip_str: str, allowed_raw: str) -> bool:
    """Check whether ip_str matches any entry in the comma-separated allowlist.
    Each entry can be a single IP or a CIDR range (e.g. 200.1.2.0/24).
    """
    try:
        client = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    for entry in allowed_raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if client in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                if client == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue
    return False


# ── IP whitelist middleware ───────────────────────────────────────────────────

@app.middleware("http")
async def ip_whitelist(request: Request, call_next):
    # /api/my-ip is always open so admins can discover their public IP
    if request.url.path == "/api/my-ip":
        return await call_next(request)

    allowed_raw = os.getenv("ALLOWED_IPS", "").strip()

    # If no allowlist is configured, let everything through
    if not allowed_raw:
        return await call_next(request)

    client_ip = _client_ip(request)
    if _ip_allowed(client_ip, allowed_raw):
        return await call_next(request)

    return HTMLResponse(
        content="""<!doctype html><html><head><meta charset="UTF-8">
        <title>Acceso restringido</title>
        <style>
          body{font-family:system-ui,sans-serif;display:flex;align-items:center;
               justify-content:center;min-height:100vh;margin:0;background:#060d1f;color:#e2e8f5;}
          .box{text-align:center;padding:48px 40px;border:1px solid rgba(255,255,255,.08);
               border-radius:18px;background:#0d1831;max-width:420px;}
          h1{font-size:22px;font-weight:800;margin-bottom:12px;color:#f87171;}
          p{font-size:14px;color:#8fa0bf;line-height:1.6;}
          code{font-family:monospace;font-size:13px;background:#162039;
               padding:2px 7px;border-radius:5px;color:#60a5fa;}
        </style></head><body>
        <div class="box">
          <h1>🔒 Acceso restringido</h1>
          <p>Este dashboard solo es accesible desde la red corporativa de Carrefour
             o mediante VPN.</p>
          <p>Conectate al VPN e intentá nuevamente.</p>
        </div></body></html>""",
        status_code=403,
    )


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    password = body.get("password", "")
    expected = os.getenv("DASHBOARD_PASSWORD", "")

    if not expected:
        # No password configured → open access (useful during local dev)
        return {"ok": True}

    if password == expected:
        return {"ok": True}

    raise HTTPException(status_code=401, detail="Contraseña incorrecta.")


@app.get("/api/my-ip")
async def my_ip(request: Request):
    """Helper: returns the IP Vercel sees for your connection.
    Use this to find the public IP you need to add to ALLOWED_IPS.
    """
    return {"ip": _client_ip(request)}


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
