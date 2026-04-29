"""
Azure AI Search + RAG pipeline.
Searches indexed bank statements and financial documents for a given client.
Falls back to mock context when not configured.
"""

import config


MOCK_SEARCH_RESULTS = [
    {
        "id": "doc_001",
        "content": "March 2025 bank statement: Total credits £42,150. Total debits £19,800. Closing balance £312,400.",
        "source": "barclays_statement_mar25.pdf",
        "score": 0.94,
    },
    {
        "id": "doc_002",
        "content": "Investment note: Gold ETF purchase – 500 units at £158.20 on 2025-01-14.",
        "source": "trade_confirmation_jan25.pdf",
        "score": 0.87,
    },
]


class SearchService:
    def __init__(self):
        self._live = config.search_enabled()
        if self._live:
            from azure.search.documents import SearchClient
            from azure.core.credentials import AzureKeyCredential
            self._client = SearchClient(
                endpoint=config.AZURE_SEARCH_ENDPOINT,
                index_name=config.AZURE_SEARCH_INDEX,
                credential=AzureKeyCredential(config.AZURE_SEARCH_API_KEY),
            )
        else:
            print("[SearchService] Running in mock mode (AZURE_SEARCH_ENDPOINT not set)")

    async def search_documents(self, query: str, client_id: str, top: int = 5) -> list[dict]:
        if not self._live:
            return MOCK_SEARCH_RESULTS

        results = self._client.search(
            search_text=query,
            filter=f"client_id eq '{client_id}'",
            top=top,
            select=["id", "content", "source"],
        )
        return [
            {
                "id": r["id"],
                "content": r["content"],
                "source": r["source"],
                "score": r["@search.score"],
            }
            for r in results
        ]

    async def index_document(self, client_id: str, filename: str, chunks: list[dict]):
        """Upload extracted document chunks into the search index."""
        if not self._live:
            print(f"[SearchService] Mock: would index {len(chunks)} chunks from {filename}")
            return

        documents = [
            {
                "id": f"{client_id}_{filename}_{i}",
                "client_id": client_id,
                "content": chunk["text"],
                "source": filename,
                "page": chunk.get("page"),
            }
            for i, chunk in enumerate(chunks)
        ]
        self._client.upload_documents(documents=documents)
        print(f"[SearchService] Indexed {len(documents)} chunks from {filename}")


search_service = SearchService()
