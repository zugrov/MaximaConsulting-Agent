from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.auth import get_current_user
from services.cloud import detect_provider, download_file, resolve_url

router = APIRouter()


class ResolveRequest(BaseModel):
    url: str


class FileItem(BaseModel):
    name: str
    size: int = 0
    url: str = ""
    path: str = ""
    zip_path: str = ""
    folder_url: str = ""


class ResolveResponse(BaseModel):
    type: str
    provider: str
    name: str = ""
    download_url: str = ""
    files: List[FileItem] = []
    message: str = ""
    public_key: str = ""
    folder_url: str = ""


class DownloadFileRef(BaseModel):
    name: str
    url: str = ""
    provider: str
    path: str = ""
    zip_path: str = ""
    folder_url: str = ""
    public_key: str = ""


class DownloadRequest(BaseModel):
    files: List[DownloadFileRef]


class DownloadedFile(BaseModel):
    name: str
    content_b64: str
    size: int


class DownloadResponse(BaseModel):
    files: List[DownloadedFile]


@router.post("/resolve", response_model=ResolveResponse)
async def resolve(
    body: ResolveRequest,
    _: Annotated[dict, Depends(get_current_user)],
) -> ResolveResponse:
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=422, detail="URL не может быть пустым")
    try:
        result = await resolve_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result["type"] == "folder":
        items = [
            FileItem(
                name=f["name"],
                size=f.get("size", 0),
                url=f.get("url", ""),
                path=f.get("path", ""),
                zip_path=f.get("_zip_path", ""),
                folder_url=f.get("_folder_url", ""),
            )
            for f in result.get("files", [])
        ]
        return ResolveResponse(
            type="folder",
            provider=result["provider"],
            files=items,
            public_key=result.get("public_key", ""),
            folder_url=result.get("folder_url", ""),
        )

    if result["type"] == "folder_unsupported":
        return ResolveResponse(
            type="folder_unsupported",
            provider=result["provider"],
            message=result.get("message", ""),
        )

    return ResolveResponse(
        type="file",
        provider=result["provider"],
        name=result.get("name", ""),
        download_url=result.get("download_url", ""),
    )


@router.post("/download", response_model=DownloadResponse)
async def download(
    body: DownloadRequest,
    _: Annotated[dict, Depends(get_current_user)],
) -> DownloadResponse:
    import base64

    if not body.files:
        raise HTTPException(status_code=422, detail="Список файлов пуст")

    results: list[DownloadedFile] = []
    for ref in body.files:
        extra: dict = {}
        if ref.path:
            extra["path"] = ref.path
            extra["public_key"] = ref.public_key
        if ref.zip_path:
            extra["_zip_path"] = ref.zip_path
            extra["_folder_url"] = ref.folder_url

        try:
            content, name = await download_file(ref.url, ref.provider, extra)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"{ref.name}: {e}")

        results.append(
            DownloadedFile(
                name=name or ref.name,
                content_b64=base64.b64encode(content).decode(),
                size=len(content),
            )
        )

    return DownloadResponse(files=results)
