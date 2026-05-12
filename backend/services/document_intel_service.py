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

            cols = _find_columns(headers)
            if cols["date"] is None or not _has_amount_cols(cols):
                continue

            rows: dict[int, dict[int, str]] = {}
            for cell in table.cells:
                if cell.row_index == 0:
                    continue
                rows.setdefault(cell.row_index, {})[cell.column_index] = cell.content.strip()

            for row_idx in sorted(rows.keys()):
                row = rows[row_idx]
                raw_amount = _resolve_amount(row, cols)
                if raw_amount is None:
                    continue
                tx = _parse_row(
                    raw_date=row.get(cols["date"], ""),
                    raw_amount=raw_amount,
                    description=row.get(cols["desc"], "") if cols["desc"] is not None else "",
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
            pages = list(pdf.pages)

            for page in pages:
                # Strategy 1: line-based table detection (native/scanned PDFs)
                tables = page.extract_tables() or []
                # Strategy 2: text-alignment detection (some Chrome PDFs)
                if not tables:
                    tables = page.extract_tables(table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                    }) or []

                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = {
                        i: str(cell).lower().strip()
                        for i, cell in enumerate(table[0])
                        if cell is not None
                    }
                    cols = _find_columns(header)
                    if cols["date"] is None or not _has_amount_cols(cols):
                        continue
                    for row in table[1:]:
                        if not row:
                            continue
                        row_map = {i: str(v or "").strip() for i, v in enumerate(row)}
                        raw_amount = _resolve_amount(row_map, cols)
                        if raw_amount is None:
                            continue
                        tx = _parse_row(
                            raw_date=row_map.get(cols["date"], ""),
                            raw_amount=raw_amount,
                            description=row_map.get(cols["desc"], "") if cols["desc"] is not None else "",
                            current_year=current_year,
                        )
                        if tx:
                            transactions.append(tx)

            # Strategy 3: balance-delta text fallback — for Chrome-printed PDFs where
            # table detection finds nothing. Reads raw text line by line, finds rows
            # with a date and a running balance, infers each transaction from the delta.
            if not transactions:
                print("[DocumentIntelligence] Table extraction found nothing — trying balance-delta text fallback")
                transactions = _extract_by_balance_delta(pages, current_year)
                print(f"[DocumentIntelligence] Balance-delta fallback: {len(transactions)} transactions found")

        return transactions


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _extract_by_balance_delta(pages: list, current_year: int) -> list[dict]:
    """
    Fallback for Chrome-printed PDFs where pdfplumber table detection fails.

    Reads each page as plain text, finds lines that contain a date and at least
    one monetary amount, then treats the last amount on each line as the running
    balance. The transaction amount is inferred from the delta between consecutive
    balances:
      - balance went up  → credit  (negative amount in our convention)
      - balance went down → debit  (positive amount in our convention)
    """
    import re
    amount_re = re.compile(r'[\$£€]?([\d,]+\.\d{2})')
    date_re   = re.compile(r'(\d{4}-\d{2}-\d{2}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})')

    dated_rows = []
    for page in pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            m = date_re.search(line)
            if not m:
                continue
            amounts = [float(a.replace(",", "")) for a in amount_re.findall(line)]
            if not amounts:
                continue
            dated_rows.append({"date": m.group(1), "balance": amounts[-1]})

    transactions = []
    prev_balance: float | None = None
    for row in dated_rows:
        balance = row["balance"]
        if prev_balance is None:
            prev_balance = balance
            continue
        delta = round(balance - prev_balance, 2)
        if abs(delta) < 0.01:
            prev_balance = balance
            continue
        # positive delta = balance increased = credit (inflow → negative in our convention)
        # negative delta = balance decreased = debit  (outflow → positive in our convention)
        tx = _parse_row(
            raw_date=row["date"],
            raw_amount=str(-delta),
            description="",
            current_year=current_year,
        )
        if tx:
            transactions.append(tx)
        prev_balance = balance

    return transactions

def _find_columns(header: dict[int, str]) -> dict:
    """
    Detect column indices from a normalised header map.

    Handles both single-column formats ('Amount') and two-column formats
    ('Withdrawals' / 'Deposits') used by most retail bank statements.
    """
    cols: dict[str, int | None] = {
        "date": None, "desc": None,
        "amount": None, "withdrawals": None, "deposits": None,
    }
    for i, h in header.items():
        if "trans date" in h or h == "date":
            cols["date"] = i
        elif "description" in h or "details" in h or "particulars" in h or "narrative" in h:
            cols["desc"] = i
        elif h == "amount":
            cols["amount"] = i
        elif "withdrawal" in h or ("debit" in h and "credit" not in h):
            cols["withdrawals"] = i
        elif "deposit" in h or ("credit" in h and "debit" not in h):
            cols["deposits"] = i
    return cols


def _has_amount_cols(cols: dict) -> bool:
    """True if at least one amount-type column was detected."""
    return any(cols[k] is not None for k in ("amount", "withdrawals", "deposits"))


def _resolve_amount(row: dict[int, str], cols: dict) -> str | None:
    """
    Return a raw amount string from a row, regardless of whether the statement
    uses a single 'Amount' column or separate 'Withdrawals'/'Deposits' columns.

    Convention (matches existing _parse_row logic):
      positive value  → debit / outflow
      negative value  → credit / inflow
    """
    if cols["amount"] is not None:
        val = row.get(cols["amount"], "").strip()
        return val if val else None

    # Two-column format: withdrawals are outflows (+), deposits are inflows (-)
    raw_w = row.get(cols["withdrawals"], "").strip() if cols["withdrawals"] is not None else ""
    raw_d = row.get(cols["deposits"], "").strip() if cols["deposits"] is not None else ""

    def _is_blank(s: str) -> bool:
        """True if the cell is empty or a placeholder dash (–, —, -)."""
        return not s.replace("$", "").replace(",", "").replace(" ", "") \
                    .replace("–", "").replace("—", "").replace("-", "")

    if not _is_blank(raw_w):
        return raw_w          # positive → outflow / debit
    if not _is_blank(raw_d):
        return f"-{raw_d}"    # negative → inflow / credit
    return None               # both empty (e.g. header repeat or subtotal row)


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
