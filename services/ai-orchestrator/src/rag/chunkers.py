"""
Domain-aware chunkers for ClinicalMind RAG pipeline.

Three strategies, one per source type:
  - ArchetypeChunker: OpenEHR observation archetypes (one chunk per archetype instance)
  - ClinicalSentenceChunker: Nursing notes (sentence-level, 2-sentence overlap)
  - HierarchicalChunker: Protocol PDFs (parent section + child paragraph)

See ADR-003 for rationale.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def chunk_document(
    content: str,
    document_type: str,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Route to the appropriate chunker based on document_type.
    Returns a list of chunk dicts with content + metadata.
    """
    if document_type == "observation":
        return ArchetypeChunker().chunk(content, metadata)
    elif document_type == "nursing_note":
        return ClinicalSentenceChunker().chunk(content, metadata)
    elif document_type == "protocol_pdf":
        return HierarchicalChunker().chunk(content, metadata)
    else:
        logger.warning(f"Unknown document_type '{document_type}' — using sentence chunker")
        return ClinicalSentenceChunker().chunk(content, metadata)


class ArchetypeChunker:
    """
    Chunks OpenEHR observation archetypes.
    One archetype instance = one chunk.
    Preserves all structured fields as metadata.
    """

    def chunk(self, content: str, metadata: dict) -> list[dict]:
        chunks = []

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Archetype content is not valid JSON, falling back to text chunk")
            return [{"content": content, "source_type": "observation", **metadata}]

        # Handle array of archetypes (batch ingestion)
        instances = data if isinstance(data, list) else [data]

        for instance in instances:
            archetype_id = instance.get("archetype_id", instance.get("_type", "unknown"))
            timestamp = instance.get("time", instance.get("timestamp", metadata.get("timestamp")))

            # Serialise archetype to a human-readable text for embedding
            text_repr = _archetype_to_text(instance)

            chunks.append({
                "content": text_repr,
                "source_type": "observation",
                "archetype_id": archetype_id,
                "timestamp": str(timestamp) if timestamp else None,
                "metadata": {**metadata, "archetype_id": archetype_id},
            })

        return chunks


class ClinicalSentenceChunker:
    """
    Chunks free-text nursing notes at sentence boundaries.
    Uses 2-sentence overlap to preserve context across chunk boundaries.
    """

    def __init__(self, overlap: int = 2):
        self.overlap = overlap

    def chunk(self, content: str, metadata: dict) -> list[dict]:
        # Split on sentence boundaries
        sentences = _split_sentences(content)

        if not sentences:
            return []

        chunks = []
        i = 0
        while i < len(sentences):
            # Take a window of sentences
            window = sentences[i:i + 6]
            text = " ".join(window)

            if len(text.strip()) > 20:  # ignore very short chunks
                chunks.append({
                    "content": text.strip(),
                    "source_type": "nursing_note",
                    "archetype_id": None,
                    "timestamp": metadata.get("timestamp"),
                    "metadata": {**metadata, "sentence_start": i},
                })

            # Advance by (window - overlap) to create overlap
            i += max(1, 6 - self.overlap)

        return chunks


class HierarchicalChunker:
    """
    Hierarchical chunker for clinical protocol PDFs.

    Parent chunks: section headers + all content (not embedded, used for context assembly)
    Child chunks: individual paragraphs (embedded and indexed)

    Retrieval returns the child; context assembly prepends the parent header.
    """

    def chunk(self, content: str, metadata: dict) -> list[dict]:
        sections = _split_sections(content)
        chunks = []

        for section_title, section_body in sections:
            # Split section body into paragraphs
            paragraphs = [p.strip() for p in section_body.split("\n\n") if p.strip()]

            for j, para in enumerate(paragraphs):
                if len(para) < 30:
                    continue

                # Prepend section title as context
                chunk_content = f"[{section_title}]\n{para}"

                chunks.append({
                    "content": chunk_content,
                    "source_type": "protocol",
                    "archetype_id": None,
                    "timestamp": None,
                    "metadata": {
                        **metadata,
                        "section_title": section_title,
                        "paragraph_index": j,
                    },
                })

        return chunks


# ── Helpers ──────────────────────────────────────────────────────

def _archetype_to_text(archetype: dict) -> str:
    """Convert an archetype dict to a readable text representation for embedding."""
    lines = []
    archetype_id = archetype.get("archetype_id", "")
    if archetype_id:
        lines.append(f"Archetype: {archetype_id}")

    def _flatten(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.startswith("_"):
                    continue
                _flatten(v, f"{prefix}{k}: " if not prefix else f"{prefix}{k}: ")
        elif isinstance(obj, list):
            for item in obj:
                _flatten(item, prefix)
        else:
            if str(obj).strip():
                lines.append(f"{prefix}{obj}")

    _flatten(archetype)
    return "\n".join(lines[:50])  # cap at 50 lines


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using regex (spaCy preferred in production)."""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split a document into (section_title, body) tuples by heading detection."""
    section_pattern = re.compile(r"^(#{1,3}\s+.+|[A-Z][A-Z\s]{5,}:?)$", re.MULTILINE)
    matches = list(section_pattern.finditer(text))

    if not matches:
        return [("Document", text)]

    sections = []
    for i, match in enumerate(matches):
        title = match.group(0).strip("#").strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title, body))

    return sections
