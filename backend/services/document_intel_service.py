"""
Azure Document Intelligence service.
Extracts cash-flow rows and metadata from uploaded bank statements / PDFs.
Falls back to mock extraction when not configured.
"""

import config


MOCK_EXTRACTION = {
    "transactions": [
        {"date": "2025-03-01", "description": "Salary credit", "amount": 15000.00, "type": "credit"},
        {"date": "2025-03-03", "description": "Mortgage payment", "amount": -3200.00, "type": "debit"},
        {"date": "2025-03-10", "description": "Dividend – MSFT", "amount": 840.00, "type": "credit"},
        {"date": "2025-03-15", "description": "Utilities", "amount": -320.00, "type": "debit"},
        {"date": "2025-03-22", "description": "Investment top-up", "amount": 10000.00, "type": "credit"},
    ],
    "summary": "Extracted 5 transactions from uploaded statement (mock mode).",
}


class DocumentIntelligenceService:
    def __init__(self):
        self._live = config.doc_intel_enabled()
        if self._live:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            self._client = DocumentIntelligenceClient(
                endpoint=config.AZURE_DOC_INTEL_ENDPOINT,
                credential=AzureKeyCredential(config.AZURE_DOC_INTEL_KEY),
            )
        else:
            print("[DocumentIntelligenceService] Running in mock mode (AZURE_DOC_INTEL_ENDPOINT not set)")

    async def extract_statement(self, file_bytes: bytes, filename: str) -> dict:
        if not self._live:
            return MOCK_EXTRACTION

        # PLACEHOLDER ─ use prebuilt-document or prebuilt-layout model
        # import io
        # poller = self._client.begin_analyze_document(
        #     "prebuilt-layout",
        #     analyze_request=io.BytesIO(file_bytes),
        #     content_type="application/octet-stream",
        # )
        # result = poller.result()
        # transactions = _parse_tables(result)
        # return {"transactions": transactions, "summary": f"Extracted {len(transactions)} rows from {filename}"}
        raise NotImplementedError

    def _parse_tables(self, result) -> list[dict]:
        """Convert Document Intelligence table output to transaction rows."""
        # PLACEHOLDER ─ iterate result.tables, map columns to date/description/amount
        raise NotImplementedError


doc_intel_service = DocumentIntelligenceService()
