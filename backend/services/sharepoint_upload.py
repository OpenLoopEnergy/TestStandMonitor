"""
Upload exported Excel files to SharePoint via Microsoft Graph API.
All config is optional — if any env var is missing, uploads are silently skipped.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

_TENANT_ID     = os.getenv("AZURE_TENANT_ID")
_CLIENT_ID     = os.getenv("AZURE_CLIENT_ID")
_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
_SP_HOSTNAME   = os.getenv("SHAREPOINT_HOSTNAME", "openloop.sharepoint.com")
_SP_DRIVE_NAME = os.getenv("SHAREPOINT_DRIVE_NAME", "Tech Services")
_SP_FOLDER     = os.getenv("SHAREPOINT_FOLDER", "Test Stand Results")


def _configured() -> bool:
    return all([_TENANT_ID, _CLIENT_ID, _CLIENT_SECRET])


def _get_token() -> str:
    url = f"https://login.microsoftonline.com/{_TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "grant_type":    "client_credentials",
        "client_id":     _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "scope":         "https://graph.microsoft.com/.default",
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_drive_id(token: str) -> str:
    """Resolve the document library drive ID by name from the root site."""
    headers = {"Authorization": f"Bearer {token}"}

    # Get root site ID
    site_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{_SP_HOSTNAME}",
        headers=headers, timeout=15,
    )
    site_resp.raise_for_status()
    site_id = site_resp.json()["id"]

    # Find drive by display name
    drives_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives",
        headers=headers, timeout=15,
    )
    drives_resp.raise_for_status()
    drives = drives_resp.json().get("value", [])

    for drive in drives:
        if drive.get("name", "").lower() == _SP_DRIVE_NAME.lower():
            return site_id, drive["id"]

    names = [d.get("name") for d in drives]
    raise ValueError(f"Drive '{_SP_DRIVE_NAME}' not found. Available: {names}")


def upload_to_sharepoint(file_path: str, filename: str) -> None:
    """Upload a local file to SharePoint. No-ops silently if not configured."""
    if not _configured():
        logger.debug("SharePoint upload skipped — Azure env vars not set.")
        return

    try:
        token = _get_token()
        site_id, drive_id = _get_drive_id(token)

        upload_url = (
            f"https://graph.microsoft.com/v1.0"
            f"/sites/{site_id}/drives/{drive_id}"
            f"/root:/{_SP_FOLDER}/{filename}:/content"
        )

        with open(file_path, "rb") as fh:
            file_bytes = fh.read()

        resp = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            data=file_bytes,
            timeout=60,
        )
        resp.raise_for_status()
        logger.info("Uploaded %s to SharePoint/%s/%s", filename, _SP_DRIVE_NAME, _SP_FOLDER)

    except Exception as e:
        # Never block the export — just log the failure
        logger.error("SharePoint upload failed for %s: %s", filename, e)
