from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: list[str] = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[i : i + self.max_sentences_per_chunk]
            chunks.append(" ".join(group).strip())
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text]

        # Base case: no separator left to try, hard-cut by chunk_size.
        if not remaining_separators or remaining_separators[0] == "":
            return [
                current_text[i : i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        separator, rest = remaining_separators[0], remaining_separators[1:]
        parts = [part for part in current_text.split(separator) if part]

        # Recurse down: any part still too long gets split with the next separator.
        pieces: list[str] = []
        for part in parts:
            if len(part) > self.chunk_size:
                pieces.extend(self._split(part, rest))
            else:
                pieces.append(part)

        # Merge up: glue adjacent small pieces back together up to chunk_size,
        # otherwise a text made of many short lines explodes into tiny chunks.
        merged: list[str] = []
        current = ""
        for piece in pieces:
            candidate = f"{current}{separator}{piece}" if current else piece
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    merged.append(current)
                current = piece
        if current:
            merged.append(current)
        return merged


class HeadingChunker:
    """
    Split text at heading lines, one section per chunk.

    Detects Markdown headings ('#'..'######') and the letter/number section
    markers used in the Shopee policy corpus (e.g. "A. PHAM VI...",
    "1.2. Thoi gian toi da..."). A section longer than chunk_size is handed
    to RecursiveChunker, and its heading is re-attached to every resulting
    piece so a reader (or a retrieved chunk) never loses the "what section
    is this" context.
    """

    HEADING_PATTERN = re.compile(
        r"^(?:#{1,6}\s+\S.*"
        r"|[A-ZĐ]\.\s+\S.*"
        r"|\d+(?:\.\d+)*\.\s+[^\s].{0,80})$"
    )

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sections: list[tuple[str, list[str]]] = []
        current_heading = ""
        current_lines: list[str] = []
        for line in text.split("\n"):
            if self.HEADING_PATTERN.match(line.strip()):
                if current_lines:
                    sections.append((current_heading, current_lines))
                current_heading = line.strip()
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_lines:
            sections.append((current_heading, current_lines))

        chunks: list[str] = []
        for heading, section_lines in sections:
            section_text = "\n".join(section_lines).strip()
            if not section_text:
                continue
            if len(section_text) <= self.chunk_size:
                chunks.append(section_text)
            else:
                for piece in self._fallback.chunk(section_text):
                    if heading and not piece.startswith(heading):
                        piece = f"{heading}\n{piece}"
                    chunks.append(piece)
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(_dot(vec_a, vec_a))
    norm_b = math.sqrt(_dot(vec_b, vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=min(50, chunk_size // 4)).chunk(text),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3).chunk(text),
            "recursive": RecursiveChunker(chunk_size=chunk_size).chunk(text),
        }

        result: dict = {}
        for name, chunks in strategies.items():
            count = len(chunks)
            avg_length = (sum(len(c) for c in chunks) / count) if count else 0.0
            result[name] = {"count": count, "avg_length": avg_length, "chunks": chunks}
        return result
