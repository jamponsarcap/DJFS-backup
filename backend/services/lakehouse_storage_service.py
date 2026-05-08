"""
Microsoft Fabric OneLake file storage service.

Stores raw uploaded bank statement files in the Lakehouse Files/ section
at path:  Files/bank_statements/{client_id}/{timestamp}_{filename}

Uses the ADLS Gen2 DFS API (onelake.dfs.fabric.microsoft.com).
Authentication: sync DefaultAzureCredential with interactive browser fallback,
executed in a worker thread for compatibility with the installed Azure Identity
version.

Falls back to a no-op (returns None) when FABRIC_WORKSPACE_NAME or
FABRIC_LAKEHOUSE_NAME are not configured.
"""

import asyncio
import datetime

import config

_ONELAKE_URL = "https://onelake.dfs.fabric.microsoft.com"
_FILES_PREFIX = "Files/bank_statements"


class LakehouseStorageService:
    def __init__(self):
        self._live = config.lakehouse_files_enabled()
        # Credential is created lazily on first upload (async context required)
        self._credential = None

        if self._live:
            print(
                "[LakehouseStorageService] Ready — raw files will be saved to OneLake Files/ "
                f"({config.FABRIC_WORKSPACE_NAME}/{config.FABRIC_LAKEHOUSE_NAME})"
            )
        else:
            print(
                "[LakehouseStorageService] Skipped "
                "(set FABRIC_WORKSPACE_NAME + FABRIC_LAKEHOUSE_NAME to enable)"
            )

    def _get_credential(self):
        """Lazily create the credential on first call.

        Try any cached local Azure credentials first. If none are available,
        allow DefaultAzureCredential's built-in interactive browser fallback to
        open a sign-in flow for the user's Fabric account.
        """
        if self._credential is None:
            from azure.identity import DefaultAzureCredential

            self._credential = DefaultAzureCredential(
                exclude_interactive_browser_credential=False,
                shared_cache_username=config.CLOUDLABS_ID or None,
            )
        return self._credential

    def _upload_file_sync(
        self,
        directory_fs_path: str,
        fs_path: str,
        file_bytes: bytes,
    ) -> None:
        from azure.core.exceptions import ResourceExistsError
        from azure.storage.filedatalake import DataLakeServiceClient

        credential = self._get_credential()
        service = DataLakeServiceClient(
            account_url=_ONELAKE_URL,
            credential=credential,
        )

        try:
            file_system_client = service.get_file_system_client(config.FABRIC_WORKSPACE_NAME)
            directory_client = file_system_client.get_directory_client(directory_fs_path)
            try:
                directory_client.create_directory()
            except ResourceExistsError:
                pass

            file_client = file_system_client.get_file_client(fs_path)
            file_client.upload_data(
                file_bytes,
                length=len(file_bytes),
                overwrite=True,
            )
        finally:
            service.close()

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

        On first call a browser window may open for Entra ID sign-in.
        Subsequent calls reuse the cached token with no popup.
        """
        if not self._live:
            return None

        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = filename.replace(" ", "_")

        # Path shown in Fabric UI under the Lakehouse Files/ tab
        relative_path = f"{_FILES_PREFIX}/{client_id}/{timestamp}_{safe_name}"
        directory_fs_path = f"{config.FABRIC_LAKEHOUSE_NAME}.Lakehouse/{_FILES_PREFIX}/{client_id}"

        # Full ADLS Gen2 path:  filesystem = workspace name
        #                       file path  = {lakehouse}.Lakehouse/{relative_path}
        fs_path = f"{config.FABRIC_LAKEHOUSE_NAME}.Lakehouse/{relative_path}"

        try:
            await asyncio.to_thread(
                self._upload_file_sync,
                directory_fs_path,
                fs_path,
                file_bytes,
            )

            print(f"[LakehouseStorageService] Saved -> {relative_path}")
            return relative_path

        except (Exception, asyncio.CancelledError) as exc:
            print(
                "[LakehouseStorageService] Upload failed "
                f"({type(exc).__name__}: {exc}); continuing without file storage"
            )
            return None

    def _list_files_sync(self, client_id: str) -> list[dict]:
        from azure.storage.filedatalake import DataLakeServiceClient

        credential = self._get_credential()
        service = DataLakeServiceClient(account_url=_ONELAKE_URL, credential=credential)
        try:
            fs_client = service.get_file_system_client(config.FABRIC_WORKSPACE_NAME)
            dir_path = f"{config.FABRIC_LAKEHOUSE_NAME}.Lakehouse/{_FILES_PREFIX}/{client_id}"
            lakehouse_prefix = f"{config.FABRIC_LAKEHOUSE_NAME}.Lakehouse/"
            results = []
            for p in fs_client.get_paths(path=dir_path):
                if p.is_directory:
                    continue
                relative_path = p.name[len(lakehouse_prefix):]
                filename = p.name.split("/")[-1]
                results.append({
                    "path": relative_path,
                    "name": filename,
                    "size": p.content_length or 0,
                    "last_modified": p.last_modified.isoformat() if p.last_modified else None,
                })
            return results
        finally:
            service.close()

    async def list_files(self, client_id: str) -> list[dict]:
        """List all uploaded files for a client from OneLake."""
        if not self._live:
            return []
        try:
            return await asyncio.to_thread(self._list_files_sync, client_id)
        except Exception as exc:
            print(f"[LakehouseStorageService] List failed: {exc}")
            return []

    def _delete_file_sync(self, fs_path: str) -> None:
        from azure.storage.filedatalake import DataLakeServiceClient

        credential = self._get_credential()
        service = DataLakeServiceClient(
            account_url=_ONELAKE_URL,
            credential=credential,
        )
        try:
            file_client = service.get_file_system_client(config.FABRIC_WORKSPACE_NAME).get_file_client(fs_path)
            file_client.delete_file()
        finally:
            service.close()

    async def delete_file(self, lakehouse_path: str) -> bool:
        """
        Delete a previously uploaded file from OneLake by its relative path.
        Returns True on success, False on failure (non-fatal).
        """
        if not self._live or not lakehouse_path:
            return False

        fs_path = f"{config.FABRIC_LAKEHOUSE_NAME}.Lakehouse/{lakehouse_path}"
        try:
            await asyncio.to_thread(self._delete_file_sync, fs_path)
            print(f"[LakehouseStorageService] Deleted -> {lakehouse_path}")
            return True
        except Exception as exc:
            print(f"[LakehouseStorageService] Delete failed ({type(exc).__name__}: {exc})")
            return False


lakehouse_storage_service = LakehouseStorageService()
