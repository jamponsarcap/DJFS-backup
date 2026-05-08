"""
Azure AI Search + RAG pipeline.
Searches indexed bank statements and financial documents for a given client.
Falls back to mock context when not configured.
"""

import asyncio
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

        if not chunks:
            print(f"[SearchService] No chunks to index for {filename}, skipping")
            return

        import re
        # AI Search keys allow only letters, digits, underscore, dash, equals sign
        safe_name = re.sub(r"[^a-zA-Z0-9_\-=]", "_", filename)

        documents = [
            {
                "id": f"{client_id}_{safe_name}_{i}",
                "client_id": client_id,
                "content": chunk["text"],
                "source": filename,
                "page": chunk.get("page"),
            }
            for i, chunk in enumerate(chunks)
        ]
        self._client.upload_documents(documents=documents)
        print(f"[SearchService] Indexed {len(documents)} chunks from {filename}")

    async def trigger_indexer(self) -> bool:
        """
        Trigger an on-demand indexer run so newly uploaded files in OneLake
        are picked up and searchable immediately.
        Returns True if the indexer was accepted (202), False otherwise.
        """
        if not self._live or not config._is_set(config.AZURE_SEARCH_INDEXER_NAME):
            print("[SearchService] Indexer trigger skipped (not configured)")
            return False

        def _run():
            from azure.search.documents.indexes import SearchIndexerClient
            from azure.core.credentials import AzureKeyCredential
            from azure.core.exceptions import HttpResponseError

            client = SearchIndexerClient(
                endpoint=config.AZURE_SEARCH_ENDPOINT,
                credential=AzureKeyCredential(config.AZURE_SEARCH_ADMIN_KEY),
            )
            try:
                client.run_indexer(config.AZURE_SEARCH_INDEXER_NAME)
                print(f"[SearchService] Indexer '{config.AZURE_SEARCH_INDEXER_NAME}' triggered (202 Accepted)")
                return True
            except HttpResponseError as e:
                if e.status_code == 409:
                    print(f"[SearchService] Indexer already running — skipping trigger")
                    return False
                raise

        try:
            return await asyncio.to_thread(_run)
        except Exception as e:
            print(f"[SearchService] Indexer trigger failed: {e}")
            return False


search_service = SearchService()
