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

MARKET_DATA_API_KEY = os.getenv("MARKET_DATA_API_KEY", "")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# A service is "live" only when all its required env vars are set
def fabric_enabled() -> bool:
    return bool(FABRIC_SERVER and FABRIC_DATABASE)

def openai_enabled() -> bool:
    return bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY)

def search_enabled() -> bool:
    return bool(AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY)

def doc_intel_enabled() -> bool:
    return bool(AZURE_DOC_INTEL_ENDPOINT and AZURE_DOC_INTEL_KEY)

def market_data_enabled() -> bool:
    return bool(MARKET_DATA_API_KEY)
