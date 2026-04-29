"""
One-time script: creates (or re-creates) the Azure AI Search index.
Run from the backend/ directory: python -m data.create_search_index
"""
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
)

load_dotenv()

endpoint   = os.environ["AZURE_SEARCH_ENDPOINT"]
key        = os.environ["AZURE_SEARCH_API_KEY"]
index_name = os.environ.get("AZURE_SEARCH_INDEX", "portfolio-docs")

client = SearchIndexClient(endpoint, AzureKeyCredential(key))

fields = [
    SimpleField(name="id",        type=SearchFieldDataType.String, key=True),
    SimpleField(name="client_id", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SimpleField(name="source",    type=SearchFieldDataType.String, retrievable=True),
    SimpleField(name="page",      type=SearchFieldDataType.Int32,  retrievable=True),
]

index = SearchIndex(name=index_name, fields=fields)
client.create_or_update_index(index)
print(f"Index '{index_name}' created/updated successfully.")
