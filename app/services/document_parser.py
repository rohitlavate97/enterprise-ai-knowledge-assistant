"""Document text extraction parser for multiple formats."""

import logging
from pathlib import Path

import pypdf

logger = logging.getLogger(__name__)


async def extract_text(file_path: Path, mime_type: str) -> str:
    """Extract all text content from a file based on its MIME type."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found at: {file_path}")

    logger.info(
        "Extracting text from: %s (MIME: %s)", file_path.name, mime_type
    )

    # 1. Plain Text or Markdown
    if (
        mime_type in {"text/plain", "text/markdown"}
        or file_path.suffix in {".txt", ".md"}
    ):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 if utf-8 fails
            with file_path.open("r", encoding="latin-1") as f:
                return f.read()

    # 2. PDF Document
    elif mime_type == "application/pdf" or file_path.suffix == ".pdf":
        try:
            text_pages = []
            reader = pypdf.PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
                else:
                    logger.warning(
                        "No text found on page %d of %s", i + 1, file_path.name
                    )
            return "\n\n".join(text_pages)
        except Exception as err:
            raise ValueError(
                f"Failed to parse PDF document: {str(err)}"
            ) from err

    # 3. Unsupported MIME types
    else:
        raise ValueError(f"Unsupported file format or MIME type: {mime_type}")
