from __future__ import annotations

import asyncio
import io
import ipaddress
import os
import re
import socket
import urllib.parse
import zipfile
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

import httpx

from services.parser import MAX_FILE_BYTES

ALLOWED_EXT = {".xlsx", ".xls", ".csv", ".json", ".txt", ".md", ".pdf", ".docx"}

# Яндекс.Диск public API (без авторизации)
_YADISK_RESOURCES = "https://cloud-api.yandex.net/v1/disk/public/resources"
_YADISK_DOWNLOAD = "https://cloud-api.yandex.net/v1/disk/public/resources/download"

HEADERS = {"User-Agent": "maxima-consulting-agent/1.0"}

_GDRIVE_API = "https://www.googleapis.com/drive/v3/files"
_GDRIVE_EXPORT_MIME = {
    "application/vnd.google-apps.spreadsheet": (
        ".xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    "application/vnd.google-apps.document": (
        ".docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
}


async def assert_public_url(url: str) -> None:
    """Запрещает запросы к внутренним адресам (защита от SSRF).

    Проверяется и первичный URL, и каждый редирект: адрес резолвится, и все
    полученные IP должны быть публичными. Остаточный риск — DNS rebinding между
    проверкой и подключением.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Допустимы только ссылки http/https")

    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"Не удалось определить адрес хоста {parsed.hostname}")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            raise ValueError("Ссылки на внутренние адреса не поддерживаются")


async def _check_request(request: httpx.Request) -> None:
    await assert_public_url(str(request.url))


def _client(**kwargs) -> httpx.AsyncClient:
    """HTTP-клиент, проверяющий каждый запрос (включая редиректы) на публичный адрес."""
    return httpx.AsyncClient(event_hooks={"request": [_check_request]}, **kwargs)


async def _fetch(url: str, timeout: float) -> Tuple[httpx.Response, bytes]:
    """GET с потоковым чтением: прерывает скачивание, если файл больше MAX_FILE_BYTES."""
    limit_mb = MAX_FILE_BYTES // (1024 * 1024)
    chunks: List[bytes] = []
    total = 0
    async with _client(follow_redirects=True, timeout=timeout) as client:
        async with client.stream("GET", url, headers=HEADERS) as resp:
            if resp.status_code != 200:
                return resp, b""
            declared = int(resp.headers.get("content-length") or 0)
            if declared > MAX_FILE_BYTES:
                raise ValueError(f"Файл больше {limit_mb} МБ")
            async for chunk in resp.aiter_bytes():
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    raise ValueError(f"Файл больше {limit_mb} МБ")
                chunks.append(chunk)
    return resp, b"".join(chunks)


def _google_drive_api_key() -> str:
    return os.getenv("GOOGLE_DRIVE_API_KEY", "").strip()


def detect_provider(url: str) -> str:
    """Возвращает 'yandex' | 'dropbox' | 'gdrive' | 'direct'."""
    lower = url.lower()
    if "disk.yandex" in lower or "yadi.sk" in lower:
        return "yandex"
    if "dropbox.com" in lower or "dropboxusercontent.com" in lower:
        return "dropbox"
    if "drive.google.com" in lower or "docs.google.com" in lower:
        return "gdrive"
    return "direct"


def _is_dropbox_folder(url: str) -> bool:
    """Определяет, является ли ссылка Dropbox папкой (sh/ или scl/fo/)."""
    return bool(re.search(r"dropbox\.com/(sh|scl/fo)/", url))


def _is_gdrive_folder(url: str) -> bool:
    lower = url.lower()
    return "/folders/" in lower or (
        "drive.google.com" in lower and "folderview" in lower
    )


def _extract_gdrive_folder_id(url: str) -> Optional[str]:
    m = re.search(r"/folders/([^/?#]+)", url)
    if m:
        return m.group(1)
    m2 = re.search(r"[?&]id=([^&]+)", url)
    if m2 and _is_gdrive_folder(url):
        return m2.group(1)
    return None


def _extract_gdrive_file_id(url: str) -> Optional[str]:
    m = re.search(r"/file/d/([^/?#]+)", url)
    if m:
        return m.group(1)
    m2 = re.search(r"[?&]id=([^&]+)", url)
    return m2.group(1) if m2 else None


def _gdrive_download_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def _gdrive_item_to_entry(item: Dict) -> Optional[Dict]:
    mime = item.get("mimeType", "")
    if mime == "application/vnd.google-apps.folder":
        return None

    name = item.get("name", "file")
    file_id = item["id"]
    size = int(item.get("size") or 0)

    if mime in _GDRIVE_EXPORT_MIME:
        ext, export_mime = _GDRIVE_EXPORT_MIME[mime]
        if not name.lower().endswith(ext):
            name = f"{name}{ext}"
        return {
            "name": name,
            "size": size,
            "url": f"{_GDRIVE_API}/{file_id}/export?mimeType={urllib.parse.quote(export_mime)}",
            "path": file_id,
            "gdrive_export": True,
        }

    if not _allowed_name(name):
        return None

    return {
        "name": name,
        "size": size,
        "url": _gdrive_download_url(file_id),
        "path": file_id,
    }


def to_download_url(url: str, provider: str) -> str:
    """Конвертирует share-ссылку в прямую download-ссылку для файла."""
    if provider == "yandex":
        return url

    if provider == "dropbox":
        parsed = urllib.parse.urlparse(url)
        qs = dict(urllib.parse.parse_qsl(parsed.query))
        qs["dl"] = "1"
        return parsed._replace(query=urllib.parse.urlencode(qs)).geturl()

    if provider == "gdrive":
        file_id = _extract_gdrive_file_id(url)
        if file_id:
            return _gdrive_download_url(file_id)

    return url


def _guess_filename_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    name = PurePosixPath(path).name or "file"
    return urllib.parse.unquote(name)


async def resolve_url(url: str) -> Dict:
    """
    Возвращает:
      {"type": "file", "download_url": str, "name": str, "provider": str}
    или
      {"type": "folder", "files": [{"name", "size", "url"}], "provider": str}
    """
    provider = detect_provider(url)

    # --- Яндекс.Диск ---
    if provider == "yandex":
        async with _client(follow_redirects=True, timeout=15) as client:
            resp = await client.get(
                _YADISK_RESOURCES,
                params={"public_key": url, "limit": 100},
                headers=HEADERS,
            )
        if resp.status_code != 200:
            raise ValueError(f"Яндекс.Диск API вернул {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        resource_type = data.get("type", "file")

        if resource_type == "dir":
            items = data.get("_embedded", {}).get("items", [])
            files = [
                {
                    "name": item["name"],
                    "size": item.get("size", 0),
                    "url": item.get("file", ""),  # прямая ссылка, если есть
                    "public_url": item.get("public_url", ""),
                    "path": item.get("path", ""),
                }
                for item in items
                if _allowed_name(item["name"])
            ]
            return {"type": "folder", "files": files, "provider": "yandex", "public_key": url}

        # Файл — получаем download URL
        dl_resp_data = await _yadisk_file_download_url(url)
        return {
            "type": "file",
            "download_url": dl_resp_data,
            "name": data.get("name", "file"),
            "provider": "yandex",
        }

    # --- Dropbox ---
    if provider == "dropbox":
        if _is_dropbox_folder(url):
            files = await _dropbox_list_folder(url)
            return {"type": "folder", "files": files, "provider": "dropbox", "folder_url": url}
        dl_url = to_download_url(url, "dropbox")
        name = _guess_filename_from_url(url)
        return {"type": "file", "download_url": dl_url, "name": name, "provider": "dropbox"}

    # --- Google Drive ---
    if provider == "gdrive":
        if _is_gdrive_folder(url):
            files = await _gdrive_list_folder(url)
            return {"type": "folder", "files": files, "provider": "gdrive", "folder_url": url}
        dl_url = to_download_url(url, "gdrive")
        file_id = _extract_gdrive_file_id(url)
        name = _guess_filename_from_url(url)
        if file_id and name in ("view", "edit", "file"):
            meta_name = await _gdrive_file_name(file_id)
            if meta_name:
                name = meta_name
        return {"type": "file", "download_url": dl_url, "name": name, "provider": "gdrive"}

    # --- Прямая ссылка ---
    name = _guess_filename_from_url(url)
    return {"type": "file", "download_url": url, "name": name, "provider": "direct"}


async def _yadisk_file_download_url(public_key: str) -> str:
    """Получить прямую download-ссылку через API Яндекс.Диска."""
    async with _client(follow_redirects=True, timeout=15) as client:
        resp = await client.get(
            _YADISK_DOWNLOAD,
            params={"public_key": public_key},
            headers=HEADERS,
        )
    if resp.status_code != 200:
        raise ValueError(f"Не удалось получить ссылку для скачивания: {resp.text[:200]}")
    return resp.json()["href"]


async def _gdrive_list_folder(folder_url: str) -> List[Dict]:
    api_key = _google_drive_api_key()
    if not api_key:
        raise ValueError(
            "Для папок Google Drive укажите GOOGLE_DRIVE_API_KEY в .env "
            "(Google Cloud Console → Drive API → API key). "
            "Папка должна быть доступна по ссылке."
        )

    folder_id = _extract_gdrive_folder_id(folder_url)
    if not folder_id:
        raise ValueError("Не удалось определить ID папки Google Drive")

    files: List[Dict] = []
    page_token: Optional[str] = None

    async with _client(timeout=30) as client:
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed=false",
                "fields": "nextPageToken,files(id,name,mimeType,size)",
                "pageSize": 100,
                "key": api_key,
                "includeItemsFromAllDrives": "true",
                "supportsAllDrives": "true",
            }
            if page_token:
                params["pageToken"] = page_token

            resp = await client.get(_GDRIVE_API, params=params, headers=HEADERS)
            if resp.status_code != 200:
                err_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                err_msg = err_body.get("error", {}).get("message", resp.text[:200])
                raise ValueError(f"Google Drive API: {err_msg}")

            data = resp.json()
            for item in data.get("files", []):
                entry = _gdrive_item_to_entry(item)
                if entry:
                    files.append(entry)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    return files


async def _gdrive_file_name(file_id: str) -> Optional[str]:
    api_key = _google_drive_api_key()
    if not api_key:
        return None
    async with _client(timeout=15) as client:
        resp = await client.get(
            f"{_GDRIVE_API}/{file_id}",
            params={"fields": "name", "key": api_key},
            headers=HEADERS,
        )
    if resp.status_code != 200:
        return None
    return resp.json().get("name")


async def _dropbox_list_folder(folder_url: str) -> List[Dict]:
    """
    Скачивает папку Dropbox как zip, распаковывает, возвращает список файлов.
    Файлы возвращаются с base64-содержимым или как временные blob-описания.
    """
    dl_url = to_download_url(folder_url, "dropbox")
    resp, body = await _fetch(dl_url, timeout=60)
    if resp.status_code != 200:
        raise ValueError(f"Dropbox вернул {resp.status_code}")

    files: list[dict] = []
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = PurePosixPath(info.filename).name
                if not _allowed_name(name):
                    continue
                files.append({
                    "name": name,
                    "size": info.file_size,
                    "url": "",  # содержимое передаём через /cloud/download
                    "_zip_path": info.filename,
                    "_folder_url": folder_url,
                })
    except zipfile.BadZipFile:
        raise ValueError("Не удалось распаковать архив Dropbox")

    return files


async def download_file(url: str, provider: str, extra: Optional[Dict] = None) -> Tuple[bytes, str]:
    """
    Скачивает файл и возвращает (bytes, filename).
    extra: для яндекс — {"public_key": ..., "path": ...}
           для dropbox zip — {"_folder_url": ..., "_zip_path": ...}
    """
    extra = extra or {}

    if provider == "yandex" and extra.get("path"):
        # Файл внутри папки Яндекс.Диска — получаем download_url через API
        async with _client(follow_redirects=True, timeout=15) as client:
            resp = await client.get(
                _YADISK_DOWNLOAD,
                params={
                    "public_key": extra["public_key"],
                    "path": extra["path"],
                },
                headers=HEADERS,
            )
        if resp.status_code != 200:
            raise ValueError(f"Яндекс.Диск: {resp.text[:200]}")
        dl_url = resp.json()["href"]
        return await _http_download(dl_url)

    if provider == "dropbox" and extra.get("_zip_path"):
        # Файл из zip-архива Dropbox
        folder_dl_url = to_download_url(extra["_folder_url"], "dropbox")
        resp, body = await _fetch(folder_dl_url, timeout=60)
        if resp.status_code != 200:
            raise ValueError(f"Dropbox вернул {resp.status_code}")
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            # размер до распаковки: защита от архива, раздувающегося при чтении
            if zf.getinfo(extra["_zip_path"]).file_size > MAX_FILE_BYTES:
                raise ValueError(f"Файл больше {MAX_FILE_BYTES // (1024 * 1024)} МБ")
            content = zf.read(extra["_zip_path"])
        name = PurePosixPath(extra["_zip_path"]).name
        return content, name

    if provider == "gdrive" and "googleapis.com" in url:
        api_key = _google_drive_api_key()
        if not api_key:
            raise ValueError("GOOGLE_DRIVE_API_KEY не задан в .env")
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}key={api_key}"

    return await _http_download(url)


async def _http_download(url: str) -> Tuple[bytes, str]:
    resp, body = await _fetch(url, timeout=60)
    if resp.status_code != 200:
        raise ValueError(f"HTTP {resp.status_code} при скачивании {url[:80]}")
    name = _guess_filename_from_response(resp, url)
    return body, name


def _guess_filename_from_response(resp: httpx.Response, url: str) -> str:
    cd = resp.headers.get("content-disposition", "")
    m = re.search(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';\s]+)', cd, re.IGNORECASE)
    if m:
        return urllib.parse.unquote(m.group(1).strip('"\''))
    return _guess_filename_from_url(url)


def _allowed_name(name: str) -> bool:
    ext = PurePosixPath(name).suffix.lower()
    return ext in ALLOWED_EXT
