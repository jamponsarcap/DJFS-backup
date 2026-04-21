# RM Insights — Portfolio Intelligence Dashboard

> **Team DJ FS** · Agentic Industry Hackathon 2026 · Capgemini  
> Nadiya Stakhyra · Jamyang Ponsar · Jack Ma · Fife Osikoya · Sonakshi

---

## Overview

RM Insights is an AI-powered portfolio intelligence tool built for Relationship Managers (RMs) in private banking. It eliminates the manual, time-intensive work of consolidating fragmented client data before a review — replacing it with a single, automated pre-review package generated in seconds.

The system aggregates holdings across personal, joint, and corporate accounts; extracts cash-flow patterns from uploaded bank statements; enriches the view with live market prices; and produces a concise, factual RM briefing — ready to use directly in a client conversation.

---

## The Problem

In the pre-review stage of private banking, analysts spend significant time manually consolidating fragmented, multi-entity data into a coherent portfolio narrative. This creates:

- Delays before RMs can engage clients
- Scalability challenges as client books grow
- Inconsistency and risk of human error in reporting

---

## The Solution

An AI-powered **Portfolio Intelligence Agent** that orchestrates four data sources automatically:

1. **Microsoft Fabric SQL** — structured account, holdings, and transaction data
2. **Azure AI Search + RAG** — relevant context extracted from uploaded bank statements
3. **External Market Data API** — live prices for gains/losses and performance attribution
4. **Azure OpenAI** — generates a concise, compliant RM narrative

The output is a single **Portfolio Insights Dashboard** the RM can read in under a minute.

---

## Dashboard Features

| Section | Description |
|---------|-------------|
| KPI Cards | Total value, total return, YTD return, risk alert count |
| Allocation Breakdown | Pie chart across equity, fixed income, cash, alternatives |
| Account Balances | Personal, joint, and corporate accounts side by side |
| Performance vs Benchmark | Line chart showing portfolio vs benchmark over time |
| Holdings Table | All positions with weight, market value, and gain/loss |
| Monthly Cash Flow | Bar chart of inflows vs outflows across the year |
| Risk Alerts | Colour-coded flags (high / medium / low) with descriptions |
| AI RM Briefing | One-click narrative generation via the Portfolio Intelligence Agent |
| Document Upload | Drag-and-drop bank statement parsing via Document Intelligence |
| Service Status Bar | Live indicator showing which Azure services are connected vs mock |

---

## Architecture

```
Investor / User
      │
      ▼
Portfolio Review App  (React + TypeScript + Vite)
      │  REST  /api/*
      ▼
FastAPI Backend
      │
      ├── Portfolio Intelligence Agent
      │       ├── 1. Microsoft Fabric SQL      (accounts, holdings, cashflows)
      │       ├── 2. Azure AI Search + RAG     (bank statement context)
      │       ├── 3. External Market Data API  (live prices)
      │       └── 4. Azure OpenAI              (RM narrative generation)
      │
      └── Azure Document Intelligence          (statement upload + extraction)
```

**Data governance:** All client data is stored in Fabric OneLake with structured schemas and RBAC. Access is controlled via Entra ID. RAG content is scoped to documents the user is authorised to view. Azure AI Content Safety enforces PII filtering and non-advice policies.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, Uvicorn |
| AI Orchestration | Azure AI Foundry Agent pattern |
| Language Model | Azure OpenAI (GPT-4o-mini, Standard tier) |
| Vector Search | Azure AI Search (hybrid + RAG pipeline) |
| Document Parsing | Azure Document Intelligence |
| Data Storage | Microsoft Fabric OneLake / Lakehouse (F2 capacity) |
| Identity | Microsoft Entra ID (RBAC, DefaultAzureCredential) |
| Market Data | External Market Data API (Alpha Vantage or equivalent) |

---

## Quick Start (no Azure account needed)

All Azure services fall back to realistic mock data by default. The full dashboard works locally without any credentials.

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
py -m venv .venv
source .venv/Scripts/activate   # Git Bash / macOS / Linux
# .venv\Scripts\Activate.ps1    # PowerShell

pip install -r requirements.txt
uvicorn main:app --reload
```

API running at **http://localhost:8000** · Interactive docs at **http://localhost:8000/docs**

### 2. Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Dashboard running at **http://localhost:5173**

---

## Connecting Azure Services

Copy `backend/.env.example` to `backend/.env` and populate your credentials. Each service activates automatically when its variables are present — no code changes needed. The status bar at the top of the dashboard shows **Live** (green) or **Mock** (amber) for each service.

| Service | Environment Variables |
|---------|----------------------|
| Microsoft Fabric SQL | `FABRIC_SERVER`, `FABRIC_DATABASE` |
| Azure OpenAI | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` |
| Azure AI Search | `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY` |
| Azure Document Intelligence | `AZURE_DOC_INTEL_ENDPOINT`, `AZURE_DOC_INTEL_KEY` |
| External Market Data | `MARKET_DATA_API_KEY` |

> **Cost note:** Use Azure OpenAI Standard (on-demand) pricing and Fabric F2 capacity to stay well within the $350 sandbox credit limit.

---

## Project Structure

```
RM_Insights/
├── backend/
│   ├── main.py                        # FastAPI app and API routes
│   ├── config.py                      # Environment variables and service flags
│   ├── requirements.txt
│   ├── agents/
│   │   └── portfolio_agent.py         # Orchestrator — runs all 4 data steps
│   ├── services/
│   │   ├── fabric_service.py          # Microsoft Fabric / SQL connector
│   │   ├── openai_service.py          # Azure OpenAI narrative generation
│   │   ├── search_service.py          # Azure AI Search + RAG pipeline
│   │   ├── document_intel_service.py  # Azure Document Intelligence
│   │   └── market_data_service.py     # External market prices
│   ├── models/
│   │   └── schemas.py                 # Pydantic request/response models
│   └── data/
│       └── mock_data.py               # Sample data for 3 demo clients
└── frontend/
    ├── src/
    │   ├── App.tsx                    # Root layout and data fetching
    │   ├── components/                # All dashboard UI components
    │   ├── api/client.ts              # Typed API call functions
    │   └── types/index.ts             # Shared TypeScript interfaces
    ├── package.json
    └── vite.config.ts                 # Dev server with API proxy
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/clients` | List all available clients |
| `GET` | `/api/portfolio/{client_id}` | Full portfolio data for a client |
| `GET` | `/api/insights/{client_id}` | Run the agent and return the RM briefing |
| `POST` | `/api/upload-statement/{client_id}` | Upload and parse a bank statement |
| `GET` | `/api/status` | Check which Azure services are live vs mock |
| `GET` | `/health` | Health check |

---

## Business Impact

- **RM Productivity** — pre-review preparation time reduced from hours to seconds
- **Consistency** — every client review follows the same structured, data-driven format
- **Analyst Redeployment** — frees analysts from manual consolidation for higher-value work
- **Scalability** — modular agent design; new data sources plug in without redesign
