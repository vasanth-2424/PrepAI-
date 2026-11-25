from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import Settings
from app.utils.exceptions import AppException


@dataclass(frozen=True)
class ParsedPdfText:
    text: str
    page_count: int
    character_count: int

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
    "application/vnd.adobe.pdf",
}


class ResumeParser:
    """Extracts and validates text from uploaded PDF resumes."""

    MIN_TEXT_LENGTH = 30

    def __init__(self, settings: Settings):
        self._settings = settings

    def parse_upload(
        self, *, filename: str | None, content_type: str | None, data: bytes
    ) -> ParsedPdfText:
        self._validate_file_metadata(filename, content_type, data)
        return self._extract_text(data)

    def _validate_file_metadata(
        self, filename: str | None, content_type: str | None, data: bytes
    ) -> None:
        if not data:
            raise AppException("The uploaded file is empty.", status_code=400)

        if len(data) > self._settings.max_upload_size_bytes:
            raise AppException(
                f"File exceeds the maximum allowed size of {self._settings.max_upload_size_mb} MB.",
                status_code=413,
            )

        if content_type and content_type.split(";")[0].strip().lower() not in ALLOWED_CONTENT_TYPES:
            raise AppException("Only PDF files are accepted.", status_code=400)

        if filename and not filename.lower().endswith(".pdf"):
            raise AppException("Only PDF files are accepted.", status_code=400)

        if not data.startswith(b"%PDF"):
            raise AppException("The uploaded file is not a valid PDF.", status_code=400)

    def _extract_text(self, data: bytes) -> ParsedPdfText:
        try:
            reader = PdfReader(io.BytesIO(data))
        except PdfReadError as exc:
            logger.warning("PDF read error: %s", exc)
            raise AppException(
                "The PDF file appears to be corrupted or unreadable.",
                status_code=400,
            ) from exc
        except Exception as exc:
            logger.warning("Unexpected PDF extraction error: %s", exc)
            raise AppException(
                "Failed to extract text from the PDF. Please try a different file.",
                status_code=400,
            ) from exc

        if len(reader.pages) == 0:
            raise AppException("The PDF contains no pages.", status_code=400)

        page_texts: list[str] = []
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:
                logger.warning("Failed to extract text from a PDF page: %s", exc)
                page_text = ""
            page_texts.append(page_text.strip())

        combined_text = "\n\n".join(text for text in page_texts if text).strip()

        if not combined_text or len(combined_text) < self.MIN_TEXT_LENGTH:
            has_any_text = any(text for text in page_texts)
            if not has_any_text:
                raise AppException(
                    "This PDF appears to contain images only. OCR is not available yet. "
                    "Please upload a text-based PDF resume.",
                    status_code=422,
                )
            raise AppException(
                "Could not extract enough text from the PDF. "
                "Please upload a text-based PDF resume.",
                status_code=422,
            )

        return ParsedPdfText(
            text=combined_text,
            page_count=len(reader.pages),
            character_count=len(combined_text),
        )
