"""Resume file validation and text extraction service using PyMuPDF and python-docx."""

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import docx
import pymupdf  # PyMuPDF

from app.schemas.resume import ResumeFormat, ResumeProcessingStatus


@dataclass
class ParseResult:
    """Result of parsing an uploaded resume document."""

    extracted_text: Optional[str]
    processing_status: ResumeProcessingStatus
    processing_message: str
    requires_ocr: bool = False


ALLOWED_EXTENSIONS = {
    ".pdf": ("PDF", "application/pdf"),
    ".docx": (
        "DOCX",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
}

ALLOWED_MIME_TYPES = {
    ".pdf": {
        "application/pdf",
        "application/x-pdf",
        "application/octet-stream",
    },
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
}


def validate_resume_file_type(
    filename: str, content: bytes, content_type: Optional[str] = None
) -> Tuple[ResumeFormat, str, str]:
    """Validate file extension, MIME type, and magic header bytes.

    Returns:
        Tuple of (file_format, canonical_mime_type, safe_extension)
    Raises:
        ValueError if format, MIME type, or file header is invalid.
    """
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Unsupported file format. Only PDF (.pdf) and Word (.docx) resumes are supported."
        )

    if content_type:
        normalized_mime = content_type.split(";")[0].strip().lower()
        if normalized_mime and normalized_mime not in ALLOWED_MIME_TYPES[ext]:
            raise ValueError(
                f"Invalid MIME type '{normalized_mime}' for {ext.upper()} resume file."
            )

    file_format, canonical_mime = ALLOWED_EXTENSIONS[ext]

    if not content:
        raise ValueError("Uploaded file is empty (0 bytes).")

    if file_format == "PDF":
        # Check PDF magic signature within first 1024 bytes
        if b"%PDF-" not in content[:1024]:
            raise ValueError(
                "Invalid or corrupted PDF file: missing PDF header signature."
            )
    elif file_format == "DOCX":
        # DOCX is an OpenXML ZIP archive containing word/document.xml
        if not content.startswith(b"PK"):
            raise ValueError(
                "Invalid or corrupted DOCX file: not a valid OpenXML archive."
            )
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise ValueError(
                        "Invalid DOCX file: missing word/document.xml structure."
                    )
        except zipfile.BadZipFile as exc:
            raise ValueError(
                "Corrupted DOCX file: archive could not be opened."
            ) from exc

    return file_format, canonical_mime, ext  # type: ignore[return-value]


def extract_resume_text(content: bytes, file_format: ResumeFormat) -> ParseResult:
    """Extract text from PDF (via PyMuPDF) or DOCX (via python-docx).

    Does not invent extracted information. Marks scanned PDFs as requiring OCR.
    """
    if file_format == "PDF":
        return _extract_pdf_text(content)
    if file_format == "DOCX":
        return _extract_docx_text(content)

    return ParseResult(
        extracted_text=None,
        processing_status="Failed",
        processing_message=f"Unsupported resume format: {file_format}",
        requires_ocr=False,
    )


def _extract_pdf_text(content: bytes) -> ParseResult:
    """Extract text from a PDF byte stream using PyMuPDF (pymupdf)."""
    try:
        with pymupdf.open(stream=content, filetype="pdf") as pdf_doc:
            if pdf_doc.is_encrypted:
                return ParseResult(
                    extracted_text=None,
                    processing_status="Failed",
                    processing_message="Encrypted/password-protected PDF cannot be parsed.",
                    requires_ocr=False,
                )

            page_count = pdf_doc.page_count
            if page_count == 0:
                return ParseResult(
                    extracted_text=None,
                    processing_status="Failed",
                    processing_message="Empty PDF document — contains 0 pages.",
                    requires_ocr=False,
                )

            page_texts = []
            total_images = 0

            for page in pdf_doc:
                text = page.get_text("text") or ""
                cleaned = text.strip()
                if cleaned:
                    page_texts.append(cleaned)
                total_images += len(page.get_images(full=True))

            combined_text = "\n\n".join(page_texts).strip()

            if not combined_text:
                if total_images > 0:
                    return ParseResult(
                        extracted_text=None,
                        processing_status="Failed",
                        processing_message=(
                            "Scanned PDF detected — requires OCR. "
                            "No machine-readable text layer was found in this document."
                        ),
                        requires_ocr=True,
                    )
                return ParseResult(
                    extracted_text=None,
                    processing_status="Failed",
                    processing_message="Empty PDF document — no readable text found.",
                    requires_ocr=False,
                )

            return ParseResult(
                extracted_text=combined_text,
                processing_status="Processed",
                processing_message=(
                    f"Successfully extracted {len(combined_text):,} characters "
                    f"across {page_count} {'page' if page_count == 1 else 'pages'}."
                ),
                requires_ocr=False,
            )
    except Exception as exc:
        return ParseResult(
            extracted_text=None,
            processing_status="Failed",
            processing_message=f"Corrupted or unreadable PDF document: {str(exc)}",
            requires_ocr=False,
        )


def _extract_docx_text(content: bytes) -> ParseResult:
    """Extract text from a DOCX byte stream using python-docx."""
    try:
        doc = docx.Document(io.BytesIO(content))
        blocks = []

        for para in doc.paragraphs:
            cleaned = para.text.strip()
            if cleaned:
                blocks.append(cleaned)

        # Also extract text from tables (common in two-column resume templates)
        seen_cells = set()
        for table in doc.tables:
            for row in table.rows:
                row_parts = []
                for cell in row.cells:
                    cell_id = id(cell._tc)
                    if cell_id in seen_cells:
                        continue
                    seen_cells.add(cell_id)
                    cell_text = cell.text.strip()
                    if cell_text:
                        row_parts.append(cell_text)
                if row_parts:
                    blocks.append(" | ".join(row_parts))

        combined_text = "\n".join(blocks).strip()

        if not combined_text:
            return ParseResult(
                extracted_text=None,
                processing_status="Failed",
                processing_message="Empty DOCX document — no readable text found.",
                requires_ocr=False,
            )

        return ParseResult(
            extracted_text=combined_text,
            processing_status="Processed",
            processing_message=(
                f"Successfully extracted {len(combined_text):,} characters "
                f"from DOCX document."
            ),
            requires_ocr=False,
        )
    except Exception as exc:
        return ParseResult(
            extracted_text=None,
            processing_status="Failed",
            processing_message=f"Corrupted or unreadable DOCX document: {str(exc)}",
            requires_ocr=False,
        )
