"""
main.py
-------
FastAPI app — runs the web server on localhost:8000

Start with:
    uvicorn main:app --reload

Then open:
    http://localhost:8000

API endpoints:
    GET /                         → serves the dashboard HTML
    GET /api/portfolio/{client}   → returns full portfolio JSON for one client
    GET /api/clients              → returns list of client names
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from data    import load_client, CLIENTS
from prices  import fetch_prices
from metrics import calculate

app = FastAPI(title="Portfolio Dashboard")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/clients")
async def get_clients():
    """Return the list of client names."""
    return {"clients": CLIENTS}


@app.get("/api/portfolio/{client}")
async def get_portfolio(client: str):
    """
    Return the full portfolio for one client as JSON.
    The dashboard calls this every time you switch tabs.
    """
    if client not in CLIENTS:
        raise HTTPException(
            status_code=404,
            detail=f"Client '{client}' not found. Available: {CLIENTS}"
        )

    # Step 1 — read positions from Excel
    df = load_client(client)

    # Step 2 — fetch live prices from Yahoo Finance
    price_map = fetch_prices(df["ticker"].tolist())

    # Step 3 — calculate all metrics
    result         = calculate(df, price_map)
    result["client"] = client

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
