"""
Microsoft Fabric OneLake file storage service.

Stores raw uploaded bank statement files in the Lakehouse Files/ section
at path:  Files/bank_statements/{client_id}/{timestamp}_{filename}

Uses the ADLS Gen2 DFS API (onelake.dfs.fabric.microsoft.com).
Authentication: azure.identity.aio.InteractiveBrowserCredential (async-native,
does not block the event loop while waiting for browser sign-in).

Falls back to a no-op (returns None) when FABRIC_WORKSPACE_NAME or
FABRIC_LAKEHOUSE_NAME are not configured.
"""

import asyncio
import datetime
import io

import config

_ONELAKE_URL = "https://onelake.dfs.fabric.microsoft.com"
_FILES_PREFIX = "Files/bank_statements"


class LakehouseStorageService:
    def __init__(self):
        self._live = config.lakehouse_files_enabled()
        # Credential is created lazily on first upload (async context required)
        self._credential = None

        if self._live:
            print("[LakehouseStorageService] Ready — raw files will be saved to OneLake Files/")
        else:
            print(
                "[LakehouseStorageService] Skipped "
                "(set FABRIC_WORKSPACE_NAME + FABRIC_LAKEHOUSE_NAME to enable)"
            )

    def _get_credential(self):
        """Lazily create the async credential on first call.

        Uses DefaultAzureCredential (async) which picks up any existing
        authentication: az login, VS Code, environment variables, or managed
        identity — no browser popup required during request handling.
        """
        if self._credential is None:
            from azure.identity.aio import DefaultAzureCredential
            self._credential = DefaultAzureCredential()
        return self._credential

    async def upload_file(
        self,
        client_id: str,
        filename: str,
        file_bytes: bytes,
    ) -> str | None:
        """
        Upload raw bytes to OneLake and return the human-readable Lakehouse path,
        e.g. 'Files/bank_statements/cli_001/20260430_143022_statement.pdf'.
        Returns None when not configured or if the upload fails (non-fatal).

        On first call a browser window will open for Entra ID sign-in.
        Subsequent calls reuse the cached token with no popup.
        """
        if not self._live:
            return None

        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = filename.replace(" ", "_")

        # Path shown in Fabric UI under the Lakehouse Files/ tab
        relative_path = f"{_FILES_PREFIX}/{client_id}/{timestamp}_{safe_name}"

        # Full ADLS Gen2 path:  filesystem = workspace name
        #                       file path  = {lakehouse}.Lakehouse/{relative_path}
        fs_path = f"{config.FABRIC_LAKEHOUSE_NAME}.Lakehouse/{relative_path}"

        try:
            from azure.storage.filedatalake.aio import DataLakeServiceClient

            credential = self._get_credential()
            async with DataLakeServiceClient(
                account_url=_ONELAKE_URL,
                credential=credential,
            ) as service:
                file_client = (
                    service
                    .get_file_system_client(config.FABRIC_WORKSPACE_NAME)
                    .get_file_client(fs_path)
                )
                await file_client.upload_data(
                    io.BytesIO(file_bytes),
                    length=len(file_bytes),
                    overwrite=True,
                )

            print(f"[LakehouseStorageService] Saved -> {relative_path}")
            return relative_path

        except (Exception, asyncio.CancelledError) as exc:
            print(f"[LakehouseStorageService] Upload failed ({exc}); continuing without file storage")
            return None


lakehouse_storage_service = LakehouseStorageService()
