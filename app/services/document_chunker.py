"""Document text chunker for building RAG pipelines."""

import logging

logger = logging.getLogger(__name__)


class ChunkerState:
    """State manager for document text chunker to prevent complex argument passing."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: list[str] = []
        self.current_chunk: list[str] = []
        self.current_size = 0

    def flush_current_chunk(self, delimiter: str = "\n\n") -> None:
        """Store the current buffer as a chunk and reset current size."""
        if self.current_chunk:
            if delimiter == ". ":
                self.chunks.append(". ".join(self.current_chunk) + ".")
            else:
                self.chunks.append(delimiter.join(self.current_chunk))

        # Calculate overlap
        overlap_size = 0
        overlap_chunk: list[str] = []
        for item in reversed(self.current_chunk):
            item_len = len(item) + len(delimiter)
            if overlap_size + item_len < self.chunk_overlap:
                overlap_chunk.insert(0, item)
                overlap_size += item_len
            else:
                break
        self.current_chunk = overlap_chunk
        self.current_size = overlap_size

    def add_word(self, word: str) -> None:
        """Add word to state, flushing if size limit exceeded."""
        if self.current_size + len(word) + 1 > self.chunk_size:
            if self.current_chunk:
                self.chunks.append(" ".join(self.current_chunk))
            # Calculate word overlap
            overlap_size = 0
            overlap_chunk: list[str] = []
            for w in reversed(self.current_chunk):
                if overlap_size + len(w) + 1 < self.chunk_overlap:
                    overlap_chunk.insert(0, w)
                    overlap_size += len(w) + 1
                else:
                    break
            self.current_chunk = overlap_chunk
            self.current_size = overlap_size

        self.current_chunk.append(word)
        self.current_size += len(word) + 1

    def add_sentence(self, sentence: str) -> None:
        """Add sentence to state."""
        if len(sentence) > self.chunk_size:
            for word in sentence.split(" "):
                self.add_word(word)
        else:
            if self.current_size + len(sentence) + 2 > self.chunk_size:
                self.flush_current_chunk(". ")
            self.current_chunk.append(sentence)
            self.current_size += len(sentence) + 2

    def add_paragraph(self, paragraph: str) -> None:
        """Add paragraph to state."""
        if len(paragraph) > self.chunk_size:
            sentences = [s.strip() for s in paragraph.split(". ") if s.strip()]
            for sentence in sentences:
                self.add_sentence(sentence)
        else:
            if self.current_size + len(paragraph) + 2 > self.chunk_size:
                self.flush_current_chunk("\n\n")
            self.current_chunk.append(paragraph)
            self.current_size += len(paragraph) + 2


def chunk_text(
    text: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> list[str]:
    """Split large text content into overlapping, semantic chunks.

    Tries to split by paragraphs first, then sentences, and finally words.
    Prevents sentences/words from being cut in half.
    """
    if not text.strip():
        return []

    logger.info(
        "Chunking text (length: %d chars, size: %d, overlap: %d)",
        len(text),
        chunk_size,
        chunk_overlap,
    )

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    state = ChunkerState(chunk_size, chunk_overlap)

    for paragraph in paragraphs:
        state.add_paragraph(paragraph)

    # Final flush
    if state.current_chunk:
        state.chunks.append("\n\n".join(state.current_chunk))

    cleaned_chunks = [c.strip() for c in state.chunks if c.strip()]
    logger.info("Generated %d text chunks.", len(cleaned_chunks))
    return cleaned_chunks
