import asyncio
import datetime
import hashlib
import json
import os
import time
import traceback
from contextlib import asynccontextmanager

import pydantic
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
from services.foundry_agent_service import foundry_agent_service
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
    if config.market_data_enabled():
        print("[startup] Skipping auto market refresh — use the Refresh Market Data button to avoid exhausting API quota")
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
_LOCKS_FILE  = os.path.join(os.path.dirname(__file__), "data", "locked_files.json")


def _load_hashes() -> dict:
    if os.path.exists(_HASHES_FILE):
        with open(_HASHES_FILE) as f:
            return json.load(f)
    return {}


def _save_hashes(hashes: dict) -> None:
    with open(_HASHES_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def _load_locks() -> set:
    if os.path.exists(_LOCKS_FILE):
        with open(_LOCKS_FILE) as f:
            return set(json.load(f))
    return set()


def _save_locks(locks: set) -> None:
    with open(_LOCKS_FILE, "w") as f:
        json.dump(list(locks), f, indent=2)


def _check_duplicate(client_id: str, file_bytes: bytes) -> str | None:
    """Return the original filename if this file was already uploaded, else None."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    data = _load_hashes()
    client = data.get(client_id, {})
    return client.get("hashes", {}).get(file_hash)


def _migrate_client(client: dict) -> None:
    """In-place: promote old last_upload field into upload_history list."""
    if "last_upload" in client:
        old = client.pop("last_upload")
        if old and isinstance(old, dict):
            client.setdefault("upload_history", []).append(old)
    client.setdefault("upload_history", [])


def _record_upload(
    client_id: str,
    file_bytes: bytes,
    filename: str,
    snapshot: dict,
    lakehouse_path: str | None = None,
) -> None:
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    data = _load_hashes()
    if not isinstance(data.get(client_id), dict):
        data[client_id] = {"hashes": {}, "upload_history": []}
    client = data[client_id]
    _migrate_client(client)
    client["hashes"][file_hash] = filename
    client["upload_history"].insert(0, {
        "hash": file_hash,
        "filename": filename,
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
        "snapshot": snapshot,
        "lakehouse_path": lakehouse_path,
    })
    _save_hashes(data)


def _get_upload_history(client_id: str) -> list[dict]:
    data = _load_hashes()
    client = data.get(client_id, {})
    if "upload_history" not in client and client.get("last_upload"):
        return [client["last_upload"]]
    return client.get("upload_history", [])


def _get_last_upload(client_id: str) -> dict | None:
    history = _get_upload_history(client_id)
    return history[0] if history else None


def _pop_last_upload(client_id: str) -> dict | None:
    """Remove and return the most recent upload entry, also clearing its hash."""
    data = _load_hashes()
    client = data.get(client_id)
    if not client:
        return None
    _migrate_client(client)
    history = client.get("upload_history", [])
    if not history:
        return None
    last = history.pop(0)
    client.get("hashes", {}).pop(last.get("hash", ""), None)
    _save_hashes(data)
    return last


def _remove_upload_by_path(client_id: str, lakehouse_path: str) -> None:
    """Remove the upload_history entry matching lakehouse_path and clear its hash."""
    data = _load_hashes()
    client = data.get(client_id)
    if not client:
        return
    _migrate_client(client)
    history = client.get("upload_history", [])
    match = next((e for e in history if e.get("lakehouse_path") == lakehouse_path), None)
    if match:
        history.remove(match)
        client.get("hashes", {}).pop(match.get("hash", ""), None)
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
        foundry_summarization_agent=config.foundry_agent_enabled(),
        foundry_portfolio_agent=config.foundry_portfolio_agent_enabled(),
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
    Advisor-facing narrative summary for a client.
    Routes to SummarizationAgent (Foundry) when configured, otherwise falls back to Azure OpenAI.
    """
    try:
        result = await portfolio_agent.run(client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@app.get("/api/agent-portfolio/{client_id}")
async def get_agent_portfolio(client_id: str):
    """
    Full UI-ready portfolio insights payload produced by PortfolioInsightsAgent.
    The agent queries Fabric SQL and Azure AI Search itself and returns structured JSON
    with ui_metrics, charts, tables, statement_insights, and reconciliation_notes.
    Requires AZURE_AI_PORTFOLIO_AGENT_ID to be configured.
    """
    if not config.foundry_portfolio_agent_enabled():
        raise HTTPException(
            status_code=503,
            detail="PortfolioInsightsAgent not configured — set AZURE_AI_PORTFOLIO_AGENT_ID in .env",
        )

    portfolio = await fabric_service.get_portfolio_data(client_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    try:
        result = await foundry_agent_service.run_portfolio_insights(
            client_id, portfolio.get("client_name", client_id)
        )
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))

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

    indexer_triggered = await search_service.trigger_indexer()

    return DocumentUploadResponse(
        filename=file.filename,
        status="processed",
        extracted_transactions=len(extraction["transactions"]),
        summary=extraction["summary"],
        diff=result,
        lakehouse_path=lakehouse_path,
        indexer_triggered=indexer_triggered,
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


class _PathBody(pydantic.BaseModel):
    path: str


@app.get("/api/documents/{client_id}")
async def list_documents(client_id: str):
    """List all uploaded documents for a client from OneLake, with lock status."""
    files = await lakehouse_storage_service.list_files(client_id)
    locks = _load_locks()
    for f in files:
        f["locked"] = f["path"] in locks
    return files


@app.post("/api/documents/{client_id}/lock")
async def lock_document(client_id: str, body: _PathBody):
    locks = _load_locks()
    locks.add(body.path)
    _save_locks(locks)
    return {"locked": True, "path": body.path}


@app.post("/api/documents/{client_id}/unlock")
async def unlock_document(client_id: str, body: _PathBody):
    locks = _load_locks()
    locks.discard(body.path)
    _save_locks(locks)
    return {"locked": False, "path": body.path}


@app.post("/api/documents/{client_id}/delete")
async def delete_document(client_id: str, body: _PathBody):
    locks = _load_locks()
    if body.path in locks:
        raise HTTPException(status_code=403, detail="Document is locked. Unlock it before deleting.")
    deleted = await lakehouse_storage_service.delete_file(body.path)
    locks.discard(body.path)
    _save_locks(locks)
    _remove_upload_by_path(client_id, body.path)
    await search_service.trigger_indexer()
    return {"deleted": deleted, "path": body.path}


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
    """Return the full upload history for this client (newest first)."""
    return [
        {
            "filename": e["filename"],
            "uploaded_at": e["uploaded_at"],
            "lakehouse_path": e.get("lakehouse_path"),
        }
        for e in _get_upload_history(client_id)
    ]


@app.post("/api/upload-statement/{client_id}/undo")
async def undo_last_upload(client_id: str):
    """Revert the DB changes from the most recent statement upload and delete the file from OneLake."""
    last = _get_last_upload(client_id)
    if not last:
        raise HTTPException(status_code=404, detail="No upload to undo for this client.")
    await fabric_service.undo_statement(client_id, last["snapshot"])
    lakehouse_deleted = await lakehouse_storage_service.delete_file(last.get("lakehouse_path"))
    _pop_last_upload(client_id)
    return {"status": "undone", "filename": last["filename"], "lakehouse_deleted": lakehouse_deleted}
