"""Semantic chunking engine tracking document character offsets and sections."""

import re
from typing import List, Tuple
from hireflow.core.schemas import DocumentChunk
from hireflow.core.provenance import create_chunk_hash


SECTION_PATTERNS = {
    "summary": re.compile(r"^(executive\s+summary|summary|profile|about\s+me|overview)", re.IGNORECASE),
    "experience": re.compile(r"^(work\s+experience|experience|employment\s+history|professional\s+experience|career)", re.IGNORECASE),
    "skills": re.compile(r"^(technical\s+skills|skills|core\s+competencies|technologies|proficiencies)", re.IGNORECASE),
    "education": re.compile(r"^(education|academic\s+background|degrees|qualifications)", re.IGNORECASE),
    "projects": re.compile(r"^(key\s+projects|projects|portfolio|technical\s+projects)", re.IGNORECASE),
    "certifications": re.compile(r"^(certifications|licenses|courses|awards)", re.IGNORECASE),
}


class SemanticChunker:
    """Splits resume and JD text into semantic chunks with offsets and section attribution."""

    @staticmethod
    def identify_section(line: str) -> str:
        """Classify a line as a section heading if applicable."""
        cleaned = re.sub(r"^[#\*\-\s]+", "", line).strip()
        cleaned = re.sub(r"[:\s]+$", "", cleaned).strip()
        for sec_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(cleaned):
                return sec_name
        return ""

    @classmethod
    def chunk_document(cls, text: str, doc_id: str) -> List[DocumentChunk]:
        """Divide raw document text into paragraph-level chunks with char offsets."""
        chunks: List[DocumentChunk] = []
        lines = text.splitlines(keepends=True)

        current_section = "summary"
        current_chunk_lines: List[str] = []
        chunk_start_char = 0
        current_offset = 0

        chunk_counter = 1

        for line in lines:
            line_len = len(line)
            stripped = line.strip()

            # Check if this line introduces a new section
            detected_sec = cls.identify_section(stripped) if stripped else ""
            if detected_sec:
                # Flush previous chunk if non-empty
                if current_chunk_lines:
                    chunk_text = "".join(current_chunk_lines).strip()
                    if chunk_text:
                        chunk_end_char = chunk_start_char + len("".join(current_chunk_lines))
                        chunk_id = f"chk_{doc_id}_{chunk_counter:03d}"
                        chunks.append(
                            DocumentChunk(
                                chunk_id=chunk_id,
                                doc_id=doc_id,
                                text=chunk_text,
                                section=current_section,
                                start_char=chunk_start_char,
                                end_char=chunk_end_char,
                                chunk_hash=create_chunk_hash(chunk_text),
                                metadata={"line_count": len(current_chunk_lines)},
                            )
                        )
                        chunk_counter += 1
                    current_chunk_lines = []

                current_section = detected_sec
                chunk_start_char = current_offset

            # Break chunks at empty lines / paragraph boundaries if current chunk has enough content
            if not stripped and len("".join(current_chunk_lines).strip()) > 150:
                chunk_text = "".join(current_chunk_lines).strip()
                if chunk_text:
                    chunk_end_char = chunk_start_char + len("".join(current_chunk_lines))
                    chunk_id = f"chk_{doc_id}_{chunk_counter:03d}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            doc_id=doc_id,
                            text=chunk_text,
                            section=current_section,
                            start_char=chunk_start_char,
                            end_char=chunk_end_char,
                            chunk_hash=create_chunk_hash(chunk_text),
                            metadata={"line_count": len(current_chunk_lines)},
                        )
                    )
                    chunk_counter += 1
                current_chunk_lines = []
                chunk_start_char = current_offset + line_len
            else:
                if not current_chunk_lines:
                    chunk_start_char = current_offset
                current_chunk_lines.append(line)

            current_offset += line_len

        # Flush final chunk
        if current_chunk_lines:
            chunk_text = "".join(current_chunk_lines).strip()
            if chunk_text:
                chunk_end_char = chunk_start_char + len("".join(current_chunk_lines))
                chunk_id = f"chk_{doc_id}_{chunk_counter:03d}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        text=chunk_text,
                        section=current_section,
                        start_char=chunk_start_char,
                        end_char=chunk_end_char,
                        chunk_hash=create_chunk_hash(chunk_text),
                        metadata={"line_count": len(current_chunk_lines)},
                    )
                )

        return chunks
