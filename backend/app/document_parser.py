"""仅解析文本型 PRD；上传文件不会保存在服务器磁盘。

文件全程在内存（BytesIO）中处理，解析完成后即丢弃，不会落盘存储。这既保护了用户数据隐私，也避免了服务器被恶意文件填满。
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi import HTTPException
from pypdf import PdfReader    # 读取 PDF
from pypdf import PdfWriter    # 写入 PDF

ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"} #suffix后缀
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_CHARS = 30_000


def extract_document(file_name: str, content: bytes) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="仅支持 .txt、.md、.pdf 和 .docx 文件。")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件不能超过 8MB。")

    try:
        if suffix in {".txt", ".md"}:
            text = content.decode("utf-8-sig") #文本/Markdown：直接解码。
        elif suffix == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        else:
            text = "\n".join(paragraph.text for paragraph in Document(BytesIO(content)).paragraphs)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="无法解析该文件，请确认它未加密且包含可提取文本。") from exc
#pdf和word都是只能提取纯文本
    text = text.strip()
    if len(text) < 30:
        raise HTTPException(status_code=422, detail="文档可提取的文本不足 30 个字符。")
    if len(text) > MAX_DOCUMENT_CHARS:
        text = text[:MAX_DOCUMENT_CHARS]
    return text
