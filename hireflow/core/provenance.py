"""Audit trail tracker, provenance ledger, and citation verification engine."""

import hashlib
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from hireflow.core.schemas import DocumentChunk, ProvenanceCitation, ProvenanceRecord


def create_chunk_hash(text: str) -> str:
    """Generate SHA256 hash of text snippet."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


class ProvenanceLedger:
    """In-memory and exportable provenance store ensuring zero ungrounded claims."""

    def __init__(self):
        self._chunks: Dict[str, DocumentChunk] = {}
        self._records: List[ProvenanceRecord] = []

    def register_chunks(self, chunks: List[DocumentChunk]):
        """Register chunks for citation resolution."""
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Retrieve chunk by ID."""
        return self._chunks.get(chunk_id)

    def record_insight(
        self,
        candidate_id: str,
        insight_type: str,
        source_chunk_ids: List[str],
        source_text_excerpts: List[str],
        model_rationale: str,
        confidence_score: float = 1.0,
    ) -> ProvenanceRecord:
        """Create and store an immutable audit record."""
        record = ProvenanceRecord(
            record_id=f"prov_{uuid.uuid4().hex[:12]}",
            candidate_id=candidate_id,
            insight_type=insight_type,
            source_chunk_ids=source_chunk_ids,
            source_text_excerpts=source_text_excerpts,
            model_rationale=model_rationale,
            confidence_score=confidence_score,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._records.append(record)
        return record

    def build_citation(
        self,
        chunk_id: str,
        verbatim_quote: str,
        confidence: float = 1.0,
        section: Optional[str] = None,
    ) -> ProvenanceCitation:
        """Build verified citation against registered chunk."""
        chunk = self._chunks.get(chunk_id)
        sec = section or (chunk.section if chunk else "general")
        start_char = None
        end_char = None

        if chunk and verbatim_quote in chunk.text:
            rel_start = chunk.text.index(verbatim_quote)
            start_char = chunk.start_char + rel_start
            end_char = start_char + len(verbatim_quote)

        return ProvenanceCitation(
            chunk_id=chunk_id,
            verbatim_quote=verbatim_quote,
            section=sec,
            confidence=confidence,
            start_char=start_char,
            end_char=end_char,
        )

    def verify_citations(self, citations: List[ProvenanceCitation]) -> Dict[str, Any]:
        """Verify that citations exist in the registered chunk store."""
        verified = 0
        total = len(citations)
        missing_chunks = []
        unmatched_quotes = []

        for cit in citations:
            chunk = self._chunks.get(cit.chunk_id)
            if not chunk:
                missing_chunks.append(cit.chunk_id)
                continue
            if cit.verbatim_quote not in chunk.text:
                unmatched_quotes.append((cit.chunk_id, cit.verbatim_quote))
            else:
                verified += 1

        return {
            "total_citations": total,
            "verified_citations": verified,
            "verification_rate": (verified / total * 100.0) if total > 0 else 100.0,
            "missing_chunks": missing_chunks,
            "unmatched_quotes": unmatched_quotes,
        }

    def get_candidate_records(self, candidate_id: str) -> List[ProvenanceRecord]:
        """Retrieve all provenance records for a specific candidate."""
        return [r for r in self._records if r.candidate_id == candidate_id]

    def export_audit_markdown(self, candidate_id: str) -> str:
        """Render markdown view of audit trail."""
        records = self.get_candidate_records(candidate_id)
        if not records:
            return f"No audit records found for candidate `{candidate_id}`."

        lines = [
            f"# Audit Provenance Trail for Candidate: `{candidate_id}`",
            f"*Total Audit Events Recorded: {len(records)}*\n",
            "| Record ID | Type | Confidence | Source Chunks | Rationale |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for r in records:
            chunks_str = ", ".join(f"`{cid}`" for cid in r.source_chunk_ids) or "None"
            lines.append(
                f"| `{r.record_id}` | `{r.insight_type}` | {r.confidence_score:.2f} | {chunks_str} | {r.model_rationale} |"
            )

        lines.append("\n### Detailed Evidence Citations\n")
        for r in records:
            if r.source_text_excerpts:
                lines.append(f"**Event `{r.record_id}` ({r.insight_type}):**")
                for excerpt in r.source_text_excerpts:
                    lines.append(f"> \"{excerpt}\"")
                lines.append("")

        return "\n".join(lines)


# Global provenance ledger instance
provenance_ledger = ProvenanceLedger()
