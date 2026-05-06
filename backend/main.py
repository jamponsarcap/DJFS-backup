import asyncio
import datetime
import hashlib
import json
import os
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import config

from models.schemas import (
    Client, PortfolioData, InsightsResponse,
    DocumentUploadResponse, ServiceStatus,
)
from services.fabric_service import fabric_service
from services.document_intel_service import doc_intel_service
from services.search_service import search_service
from services.lakehouse_storage_service import lakehouse_storage_service
from agents.portfolio_agent import portfolio_agent
from services.market_data_service import market_data_service

_last_market_refresh: float = 0.0
_REFRESH_COOLDOWN = 60.0  # seconds


async def _do_market_refresh() -> dict:
    global _last_market_refresh
    market_data_service.clear_cache()
    _last_market_refresh = time.time()

    clients = await fabric_service.get_clients()
    total_updated = 0
    for client in clients:
        data = await fabric_service.get_portfolio_data(client["id"])
        if not data:
            continue
        holdings = data.get("holdings", [])
        if holdings:
            enriched = await market_data_service.enrich_holdings_with_market_data(holdings)
            total_updated += await fabric_service.update_holdings_market_data(client["id"], enriched)

    refreshed_at = datetime.datetime.utcnow().isoformat() + "Z"
    next_allowed = datetime.datetime.utcfromtimestamp(_last_market_refresh + _REFRESH_COOLDOWN).isoformat() + "Z"
    return {"refreshed_at": refreshed_at, "next_refresh_allowed": next_allowed, "holdings_updated": total_updated}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] Running initial market data refresh…")
    try:
        result = await _do_market_refresh()
        print(f"[startup] Market data refreshed: {result['holdings_updated']} holdings updated in DB")
    except Exception as e:
        print(f"[startup] Market data refresh failed (non-fatal): {e}")
    yield


app = FastAPI(
    title="RM Insights API",
    description="AI-powered portfolio intelligence for Relationship Managers",
    version="1.0.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"[ERROR] Unhandled exception on {request.method} {request.url}\n{tb}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_HASHES_FILE = os.path.join(os.path.dirname(__file__), "data", "uploaded_hashes.json")


def _load_hashes() -> dict:
    if os.path.exists(_HASHES_FILE):
        with open(_HASHES_FILE) as f:
            return json.load(f)
    return {}


def _save_hashes(hashes: dict) -> None:
    with open(_HASHES_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def _check_duplicate(client_id: str, file_bytes: bytes) -> str | None:
    """Return the original filename if this file was already uploaded, else None."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    data = _load_hashes()
    client = data.get(client_id, {})
    return client.get("hashes", {}).get(file_hash)


def _record_upload(
    client_id: str,
    file_bytes: bytes,
    filename: str,
    snapshot: dict,
    lakehouse_path: str | None = None,
) -> None:
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    data = _load_hashes()
    client = data.setdefault(client_id, {"hashes": {}, "last_upload": None})
    # Migrate old flat-hash format if needed
    if client and not isinstance(client, dict):
        client = {"hashes": {}, "last_upload": None}
        data[client_id] = client
    client.setdefault("hashes", {})[file_hash] = filename
    client["last_upload"] = {
        "hash": file_hash,
        "filename": filename,
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
        "snapshot": snapshot,
        "lakehouse_path": lakehouse_path,
    }
    _save_hashes(data)


def _get_last_upload(client_id: str) -> dict | None:
    data = _load_hashes()
    return data.get(client_id, {}).get("last_upload")


def _clear_last_upload(client_id: str) -> None:
    """Remove snapshot + hash so the same doc can be re-uploaded after undo."""
    data = _load_hashes()
    client = data.get(client_id)
    if not client:
        return
    last = client.get("last_upload")
    if last:
        client.get("hashes", {}).pop(last["hash"], None)
        client["last_upload"] = None
    _save_hashes(data)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status", response_model=ServiceStatus)
async def service_status():
    """Returns which Azure services are configured (live) vs mock."""
    return ServiceStatus(
        fabric=config.fabric_enabled(),
        openai=config.openai_enabled(),
        ai_search=config.search_enabled(),
        doc_intelligence=config.doc_intel_enabled(),
        market_data=config.market_data_enabled(),
    )


@app.get("/api/clients", response_model=list[Client])
async def list_clients():
    clients = await fabric_service.get_clients()
    return clients


@app.get("/api/portfolio/{client_id}", response_model=PortfolioData)
async def get_portfolio(client_id: str):
    data = await fabric_service.get_portfolio_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    holdings = data.get("holdings", [])
    if holdings:
        data["holdings"] = await market_data_service.enrich_holdings_with_market_data(holdings)

    return data


@app.get("/api/insights/{client_id}", response_model=InsightsResponse)
async def get_insights(client_id: str):
    """
    Run the Portfolio Intelligence Agent for a given client.
    Orchestrates Fabric + RAG + market data + OpenAI narrative generation.
    """
    try:
        result = await portfolio_agent.run(client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@app.post("/api/upload-statement/{client_id}", response_model=DocumentUploadResponse)
async def upload_statement(client_id: str, file: UploadFile = File(...)):
    """
    Upload a bank statement PDF.
    Extracts transactions via Azure Document Intelligence,
    writes them to the Fabric SQL database, and returns a diff
    showing exactly what changed in the portfolio.
    Rejects duplicate files (same content) for the same client.
    """
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Only PDF and image files are supported")

    contents = await file.read()

    original = _check_duplicate(client_id, contents)
    if original:
        raise HTTPException(
            status_code=409,
            detail=f'This document has already been uploaded (original: "{original}"). '
                   "Upload a different statement to update the portfolio.",
        )

    extraction = await doc_intel_service.extract_statement(contents, file.filename)
    result = await fabric_service.apply_statement(client_id, extraction)

    snapshot = result.pop("_snapshot", {"accounts": [], "cash_flows": {}})

    # Store the raw file in the Lakehouse Files/ section (non-fatal, 45 s timeout)
    try:
        lakehouse_path = await asyncio.wait_for(
            lakehouse_storage_service.upload_file(client_id, file.filename, contents),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        print("[upload] Lakehouse upload timed out (browser auth not completed) — continuing")
        lakehouse_path = None
    except Exception as e:
        print(f"[upload] Lakehouse upload error (non-fatal): {e}")
        lakehouse_path = None

    _record_upload(client_id, contents, file.filename, snapshot, lakehouse_path)

    chunks = [
        {"text": f"{t['date']} {t['description']} {t['amount']}", "page": None}
        for t in extraction["transactions"]
    ]
    try:
        await search_service.index_document(client_id, file.filename, chunks)
    except Exception as e:
        print(f"[upload] Search indexing failed (non-fatal): {e}")

    return DocumentUploadResponse(
        filename=file.filename,
        status="processed",
        extracted_transactions=len(extraction["transactions"]),
        summary=extraction["summary"],
        diff=result,
        lakehouse_path=lakehouse_path,
    )


@app.get("/api/holdings-history/{client_id}")
async def get_holdings_history(client_id: str):
    """Weekly price history for all non-cash holdings, normalised to % change from first point."""
    data = await fabric_service.get_portfolio_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    holdings = [h for h in data.get("holdings", []) if h.get("asset_class") != "cash"]

    raw: dict[str, dict] = {}
    for h in holdings:
        symbol = h["symbol"]
        hist = await market_data_service.get_price_history(symbol)
        if hist:
            raw[symbol] = {"name": h["name"], "asset_class": h["asset_class"], "history": hist}

    if not raw:
        return {"dates": [], "series": []}

    min_len = min(len(v["history"]) for v in raw.values())
    all_dates: list[str] = []
    series = []
    for symbol, info in raw.items():
        hist = info["history"][-min_len:]
        if not all_dates:
            all_dates = [e["date"] for e in hist]
        first = hist[0]["price"]
        if first == 0:
            continue
        series.append({
            "symbol": symbol,
            "name": info["name"],
            "asset_class": info["asset_class"],
            "values": [round((e["price"] / first - 1) * 100, 2) for e in hist],
        })

    return {"dates": all_dates, "series": series}


@app.post("/api/market-data/refresh")
async def refresh_market_data():
    """Clear the price cache, fetch fresh market data for all clients, and persist to DB."""
    global _last_market_refresh
    elapsed = time.time() - _last_market_refresh
    if _last_market_refresh > 0 and elapsed < _REFRESH_COOLDOWN:
        wait = int(_REFRESH_COOLDOWN - elapsed) + 1
        raise HTTPException(status_code=429, detail=f"Please wait {wait}s before refreshing again.")
    return await _do_market_refresh()


@app.get("/api/market-data/refresh-status")
async def refresh_status():
    """Returns when the last refresh happened and when the next one is allowed."""
    if _last_market_refresh == 0:
        return {"last_refreshed": None, "next_refresh_allowed": None, "cooldown_remaining": 0}
    elapsed = time.time() - _last_market_refresh
    cooldown_remaining = max(0, int(_REFRESH_COOLDOWN - elapsed))
    last = datetime.datetime.utcfromtimestamp(_last_market_refresh).isoformat() + "Z"
    next_allowed = datetime.datetime.utcfromtimestamp(_last_market_refresh + _REFRESH_COOLDOWN).isoformat() + "Z"
    return {"last_refreshed": last, "next_refresh_allowed": next_allowed, "cooldown_remaining": cooldown_remaining}


@app.get("/api/upload-statement/{client_id}/last")
async def get_last_upload(client_id: str):
    """Return metadata about the last uploaded statement for this client, or null."""
    last = _get_last_upload(client_id)
    if not last:
        return None
    return {
        "filename": last["filename"],
        "uploaded_at": last["uploaded_at"],
        "lakehouse_path": last.get("lakehouse_path"),
    }


@app.post("/api/upload-statement/{client_id}/undo")
async def undo_last_upload(client_id: str):
    """Revert the DB changes from the most recent statement upload."""
    last = _get_last_upload(client_id)
    if not last:
        raise HTTPException(status_code=404, detail="No upload to undo for this client.")
    await fabric_service.undo_statement(client_id, last["snapshot"])
    _clear_last_upload(client_id)
    return {"status": "undone", "filename": last["filename"]}
