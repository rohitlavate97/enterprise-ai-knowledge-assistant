"""Unit and integration tests for document parsing and text chunking pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.document_chunker import chunk_text
from app.services.document_parser import extract_text


def test_text_chunker_basic() -> None:
    """Test text chunker with standard short text."""
    text = "This is a short sentence. It should result in a single chunk."
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_text_chunker_boundary_preservation() -> None:
    """Test chunker preserves sentence/paragraph boundaries without word splitting."""
    # Sentence split boundary preservation
    text = (
        "First sentence of the document. "
        "Second sentence that is longer. Third sentence."
    )
    chunks = chunk_text(text, chunk_size=40, chunk_overlap=10)
    assert len(chunks) > 1
    # Check that sentences are not cut in half
    for chunk in chunks:
        assert chunk.endswith(".")


def test_text_chunker_overlap() -> None:
    """Test chunker correctly implements sliding window overlaps."""
    text = (
        "Paragraph one of text.\n\nParagraph two of text.\n\nParagraph three of text."
    )
    chunks = chunk_text(text, chunk_size=35, chunk_overlap=15)
    assert len(chunks) > 1
    # Ensure second chunk overlaps with the paragraph structures
    assert any("Paragraph two" in c for c in chunks)


@pytest.mark.asyncio
async def test_extract_text_txt(tmp_path: Path) -> None:
    """Test extracting text from plain text files."""
    file_path = tmp_path / "test.txt"
    content = "Hello, world! This is plain text."
    file_path.write_text(content, encoding="utf-8")

    extracted = await extract_text(file_path, "text/plain")
    assert extracted == content


@pytest.mark.asyncio
async def test_extract_text_pdf(tmp_path: Path) -> None:
    """Test extracting text from PDF files using mocked pypdf reader."""
    file_path = tmp_path / "test.pdf"
    file_path.write_text("fake pdf binary", encoding="utf-8")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Extracted text from PDF page."

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        extracted = await extract_text(file_path, "application/pdf")
        assert extracted == "Extracted text from PDF page."
        mock_page.extract_text.assert_called_once()


@pytest.mark.asyncio
async def test_extract_text_unsupported(tmp_path: Path) -> None:
    """Test extracting text from unsupported formats raises ValueError."""
    file_path = tmp_path / "test.png"
    file_path.write_text("fake png binary", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file format"):
        await extract_text(file_path, "image/png")
