"""
Azure Document Intelligence service.
Extracts transactions from uploaded bank statement PDFs.

When Azure Document Intelligence is configured, uses the cloud prebuilt-layout model.
Otherwise falls back to local parsing with pdfplumber — so any PDF you upload
is read dynamically rather than returning static data.
"""

import asyncio
import datetime
import io
import config


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
            print("[DocumentIntelligenceService] Using Azure Document Intelligence")
        else:
            print("[DocumentIntelligenceService] Azure not configured — will parse PDFs locally with pdfplumber")

    async def extract_statement(self, file_bytes: bytes, filename: str) -> dict:
        if self._live:
            transactions = await self._extract_azure(file_bytes)
        else:
            transactions = self._extract_local(file_bytes)

        return {
            "transactions": transactions,
            "summary": f"Extracted {len(transactions)} transactions from {filename}.",
        }

    # ── Azure Document Intelligence path ──────────────────────────────────────

    async def _extract_azure(self, file_bytes: bytes) -> list[dict]:
        loop = asyncio.get_event_loop()

        def _analyze():
            poller = self._client.begin_analyze_document(
                "prebuilt-layout",
                analyze_request=io.BytesIO(file_bytes),
                content_type="application/octet-stream",
            )
            return poller.result()

        result = await loop.run_in_executor(None, _analyze)
        return self._parse_azure_tables(result)

    def _parse_azure_tables(self, result) -> list[dict]:
        """Parse tables from the Azure Document Intelligence result."""
        transactions = []
        current_year = datetime.date.today().year

        for table in result.tables:
            headers: dict[int, str] = {}
            for cell in table.cells:
                if cell.row_index == 0:
                    headers[cell.column_index] = cell.content.lower().strip()

            date_col, desc_col, amount_col = _find_columns(headers)
            if date_col is None or amount_col is None:
                continue

            rows: dict[int, dict[int, str]] = {}
            for cell in table.cells:
                if cell.row_index == 0:
                    continue
                rows.setdefault(cell.row_index, {})[cell.column_index] = cell.content.strip()

            for row_idx in sorted(rows.keys()):
                row = rows[row_idx]
                tx = _parse_row(
                    raw_date=row.get(date_col, ""),
                    raw_amount=row.get(amount_col, ""),
                    description=row.get(desc_col, "") if desc_col is not None else "",
                    current_year=current_year,
                )
                if tx:
                    transactions.append(tx)

        return transactions

    # ── Local pdfplumber path ─────────────────────────────────────────────────

    def _extract_local(self, file_bytes: bytes) -> list[dict]:
        """Parse the uploaded PDF directly without Azure — works for any statement."""
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError(
                "pdfplumber is required for local PDF parsing. "
                "Run: pip install pdfplumber"
            )

        transactions = []
        current_year = datetime.date.today().year

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                for table in (page.extract_tables() or []):
                    if not table or len(table) < 2:
                        continue

                    header = {
                        i: str(cell).lower().strip()
                        for i, cell in enumerate(table[0])
                        if cell is not None
                    }
                    date_col, desc_col, amount_col = _find_columns(header)
                    if date_col is None or amount_col is None:
                        continue

                    for row in table[1:]:
                        if not row:
                            continue
                        tx = _parse_row(
                            raw_date=str(row[date_col] or "").strip(),
                            raw_amount=str(row[amount_col] or "").strip(),
                            description=str(row[desc_col] or "").strip() if desc_col is not None else "",
                            current_year=current_year,
                        )
                        if tx:
                            transactions.append(tx)

        return transactions


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _find_columns(header: dict[int, str]) -> tuple[int | None, int | None, int | None]:
    """Return (date_col, desc_col, amount_col) indices from a header map."""
    date_col = next(
        (i for i, h in header.items() if "trans date" in h or h == "date"), None
    )
    desc_col = next(
        (i for i, h in header.items() if "description" in h), None
    )
    amount_col = next(
        (i for i, h in header.items() if h == "amount"), None
    )
    return date_col, desc_col, amount_col


def _parse_row(raw_date: str, raw_amount: str, description: str, current_year: int) -> dict | None:
    """Parse a single table row into a transaction dict. Returns None if unparseable."""
    if not raw_date or not raw_amount:
        return None

    amount_str = (
        raw_amount
        .replace("$", "")
        .replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .strip()
    )
    try:
        amount = float(amount_str)
    except ValueError:
        return None

    # Dates like "Feb 19" → "2026-02-19"
    try:
        parsed = datetime.datetime.strptime(f"{raw_date} {current_year}", "%b %d %Y")
        date_str = parsed.strftime("%Y-%m-%d")
    except ValueError:
        date_str = raw_date

    return {
        "date": date_str,
        "description": description,
        "amount": amount,
        "type": "credit" if amount < 0 else "debit",
    }


doc_intel_service = DocumentIntelligenceService()
