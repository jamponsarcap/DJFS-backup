import datetime
import hashlib
import json
import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import config

from models.schemas import (
    Client, PortfolioData, InsightsResponse,
    DocumentUploadResponse, ServiceStatus,
)
from services.fabric_service import fabric_service
from services.document_intel_service import doc_intel_service
from services.search_service import search_service
from agents.portfolio_agent import portfolio_agent

app = FastAPI(
    title="RM Insights API",
    description="AI-powered portfolio intelligence for Relationship Managers",
    version="1.0.0",
)

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


def _record_upload(client_id: str, file_bytes: bytes, filename: str, snapshot: dict) -> None:
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
    _record_upload(client_id, contents, file.filename, snapshot)

    chunks = [
        {"text": f"{t['date']} {t['description']} {t['amount']}", "page": None}
        for t in extraction["transactions"]
    ]
    await search_service.index_document(client_id, file.filename, chunks)

    return DocumentUploadResponse(
        filename=file.filename,
        status="processed",
        extracted_transactions=len(extraction["transactions"]),
        summary=extraction["summary"],
        diff=result,
    )


@app.get("/api/upload-statement/{client_id}/last")
async def get_last_upload(client_id: str):
    """Return metadata about the last uploaded statement for this client, or null."""
    last = _get_last_upload(client_id)
    if not last:
        return None
    return {"filename": last["filename"], "uploaded_at": last["uploaded_at"]}


@app.post("/api/upload-statement/{client_id}/undo")
async def undo_last_upload(client_id: str):
    """Revert the DB changes from the most recent statement upload."""
    last = _get_last_upload(client_id)
    if not last:
        raise HTTPException(status_code=404, detail="No upload to undo for this client.")
    await fabric_service.undo_statement(client_id, last["snapshot"])
    _clear_last_upload(client_id)
    return {"status": "undone", "filename": last["filename"]}
