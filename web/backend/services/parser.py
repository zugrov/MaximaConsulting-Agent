from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

MAX_CHARS = 100_000  # лимит перед отправкой в LLM


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_CHARS:
        return text, False
    return text[:MAX_CHARS], True


def parse_file(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Принимает байты файла и имя. Возвращает:
      { "raw": str, "truncated": bool, "source_file": str }
    """
    suffix = Path(filename).suffix.lower()
    raw: str

    if suffix in {".xlsx", ".xls"}:
        raw = _parse_excel(file_bytes)
    elif suffix == ".csv":
        raw = _parse_csv(file_bytes)
    elif suffix == ".json":
        raw = _parse_json(file_bytes)
    elif suffix == ".pdf":
        raw = _parse_pdf(file_bytes)
    elif suffix in {".docx", ".doc"}:
        raw = _parse_docx(file_bytes)
    else:
        # .txt, .md и всё остальное
        raw = file_bytes.decode("utf-8", errors="ignore")

    raw, truncated = _truncate(raw)
    return {"raw": raw, "truncated": truncated, "source_file": filename}


def _parse_excel(data: bytes) -> str:
    import io
    xl = pd.ExcelFile(io.BytesIO(data))
    parts: list[str] = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(io.BytesIO(data), sheet_name=sheet).dropna(how="all").fillna("")
        parts.append(f"=== Лист: {sheet} ===\n{df.to_string(index=False)}")
    return "\n\n".join(parts)


def _parse_csv(data: bytes) -> str:
    import io
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            df = pd.read_csv(io.BytesIO(data), encoding=enc)
            return df.to_string(index=False)
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


def _parse_json(data: bytes) -> str:
    obj = json.loads(data.decode("utf-8"))
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _parse_pdf(data: bytes) -> str:
    try:
        import io
        import pdfplumber
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(f"--- Страница {i} ---\n{text}")
        return "\n\n".join(text_parts) if text_parts else "[PDF не содержит извлекаемого текста]"
    except ImportError:
        return "[pdfplumber не установлен — PDF не поддерживается]"


def _parse_docx(data: bytes) -> str:
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        return "[python-docx не установлен — DOCX не поддерживается]"
