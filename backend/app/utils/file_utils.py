"""Safe handling of uploaded certificate files (JSON only, size-limited, never saved to disk)."""
import json

from fastapi import UploadFile

from app.utils.exceptions import AppError

MAX_UPLOAD_BYTES = 64 * 1024
ALLOWED_CONTENT_TYPES = {"application/json", "text/plain", "application/octet-stream", ""}


def read_json_upload(upload: UploadFile) -> dict:
    name = (upload.filename or "").lower()
    if not name.endswith(".json"):
        raise AppError(400, "INVALID_FILE_TYPE", "Only .json certificate files are accepted.")
    if (upload.content_type or "") not in ALLOWED_CONTENT_TYPES:
        raise AppError(400, "INVALID_FILE_TYPE", "Unexpected file content type.")

    raw = upload.file.read(MAX_UPLOAD_BYTES + 1)  # never read more than the limit
    if len(raw) > MAX_UPLOAD_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", f"File exceeds {MAX_UPLOAD_BYTES // 1024} KB.")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AppError(400, "INVALID_JSON", "The file is not valid UTF-8 JSON.") from exc
    if not isinstance(data, dict):
        raise AppError(400, "INVALID_JSON", "The JSON file must contain a certificate object.")
    return data