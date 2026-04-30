from dotenv import load_dotenv
import os

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY", "")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "portfolio-docs")

AZURE_DOC_INTEL_ENDPOINT = os.getenv("AZURE_DOC_INTEL_ENDPOINT", "")
AZURE_DOC_INTEL_KEY = os.getenv("AZURE_DOC_INTEL_KEY", "")

FABRIC_SERVER = os.getenv("FABRIC_SERVER", "")
FABRIC_DATABASE = os.getenv("FABRIC_DATABASE", "")
FABRIC_WORKSPACE_NAME = os.getenv("FABRIC_WORKSPACE_NAME", "")
FABRIC_LAKEHOUSE_NAME = os.getenv("FABRIC_LAKEHOUSE_NAME", "")

MARKET_DATA_API_KEY = os.getenv("MARKET_DATA_API_KEY", "")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

def _is_set(value: str) -> bool:
    """True only when the value is non-empty and not a placeholder like <your-key>."""
    return bool(value) and "<" not in value

# A service is "live" only when all its required env vars are set and not placeholders
def fabric_enabled() -> bool:
    return _is_set(FABRIC_SERVER) and _is_set(FABRIC_DATABASE)

def lakehouse_files_enabled() -> bool:
    return _is_set(FABRIC_WORKSPACE_NAME) and _is_set(FABRIC_LAKEHOUSE_NAME)

def openai_enabled() -> bool:
    return _is_set(AZURE_OPENAI_ENDPOINT) and _is_set(AZURE_OPENAI_API_KEY)

def search_enabled() -> bool:
    return _is_set(AZURE_SEARCH_ENDPOINT) and _is_set(AZURE_SEARCH_API_KEY)

def doc_intel_enabled() -> bool:
    return _is_set(AZURE_DOC_INTEL_ENDPOINT) and _is_set(AZURE_DOC_INTEL_KEY)

def market_data_enabled() -> bool:
    return _is_set(MARKET_DATA_API_KEY)
