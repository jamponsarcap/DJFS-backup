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
    then indexes the content into Azure AI Search for RAG.
    """
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Only PDF and image files are supported")

    contents = await file.read()
    extraction = await doc_intel_service.extract_statement(contents, file.filename)

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
    )
