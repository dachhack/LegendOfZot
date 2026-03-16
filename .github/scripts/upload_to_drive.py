#!/usr/bin/env python3
"""Upload a file to Google Drive using OAuth2 refresh token."""

import json
import os
import sys
from datetime import datetime, timezone

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials


def get_drive_service():
    """Authenticate using OAuth2 refresh token (uploads as the user)."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "").strip()

    if not all([client_id, client_secret, refresh_token]):
        print("ERROR: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN must all be set",
              file=sys.stderr)
        sys.exit(1)

    print("Authenticating with OAuth2 refresh token...")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )

    service = build("drive", "v3", credentials=creds)
    return service


def upload_file(file_path):
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        print("ERROR: GOOGLE_DRIVE_FOLDER_ID not set", file=sys.stderr)
        sys.exit(1)

    print(f"Folder ID: {folder_id}")
    print(f"File: {file_path} ({os.path.getsize(file_path) / (1024*1024):.1f} MB)")

    service = get_drive_service()

    # Test API connectivity
    print("Testing API connectivity...")
    try:
        about = service.about().get(fields="user").execute()
        print(f"API OK - authenticated as: {about['user'].get('emailAddress', '?')}")
    except Exception as e:
        print(f"ERROR: API connectivity test failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Verify folder exists
    print("Verifying folder access...")
    try:
        folder = service.files().get(fileId=folder_id, fields="id, name").execute()
        print(f"Folder: {folder['name']} (id={folder['id']})")
    except Exception as e:
        print(f"ERROR: Cannot access folder {folder_id}: {e}", file=sys.stderr)
        sys.exit(1)

    # Upload the file
    filename = os.path.basename(file_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name_parts = filename.rsplit(".", 1)
    if len(name_parts) == 2:
        timestamped = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
    else:
        timestamped = f"{filename}_{timestamp}"

    media = MediaFileUpload(file_path, mimetype="application/vnd.android.package-archive")

    print(f"Uploading: {timestamped}")
    try:
        uploaded = service.files().create(
            body={"name": timestamped, "parents": [folder_id]},
            media_body=media,
            fields="id, name, webViewLink",
        ).execute()
        print(f"SUCCESS! Uploaded: {uploaded['name']}")
        print(f"File ID: {uploaded['id']}")
        print(f"Link: {uploaded.get('webViewLink', 'N/A')}")
    except Exception as e:
        print(f"ERROR: Upload failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Update latest copy
    if len(name_parts) == 2:
        latest_name = f"{name_parts[0]}_latest.{name_parts[1]}"
    else:
        latest_name = f"{filename}_latest"
    try:
        results = service.files().list(
            q=f"name = '{latest_name}' and '{folder_id}' in parents and trashed = false",
            fields="files(id, name)",
        ).execute()
        existing = results.get("files", [])
        if existing:
            media3 = MediaFileUpload(file_path, mimetype="application/vnd.android.package-archive")
            service.files().update(
                fileId=existing[0]["id"],
                media_body=media3,
                fields="id, name",
            ).execute()
            print(f"Updated latest: {latest_name}")
        else:
            media3 = MediaFileUpload(file_path, mimetype="application/vnd.android.package-archive")
            service.files().create(
                body={"name": latest_name, "parents": [folder_id]},
                media_body=media3,
                fields="id, name",
            ).execute()
            print(f"Created latest: {latest_name}")
    except Exception as e:
        print(f"WARNING: Could not update latest copy: {e}")

    print("Done!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file_path>")
        sys.exit(1)
    upload_file(sys.argv[1])
