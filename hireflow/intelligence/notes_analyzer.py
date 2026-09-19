"""Interviewer notes and transcript parser for evidence extraction."""

import re
from typing import List, Dict, Any
from hireflow.core.schemas import InterviewNoteClaim


class NotesAnalyzer:
    """Extracts structured evidence, interviewer assessments, and candidate quotes from notes."""

    @classmethod
    def parse_notes(cls, raw_notes: str) -> List[InterviewNoteClaim]:
        """Parse raw interview notes into individual evaluated claims."""
        claims: List[InterviewNoteClaim] = []
        lines = [l.strip() for l in raw_notes.splitlines() if l.strip()]

        current_topic = "General Technical Evaluation"
        current_summary = []
        current_rating = "ACCEPTABLE"
        direct_quote = None

        for line in lines:
            # Check for topic / competency headers (e.g. ## Topic or Topic: ...)
            if line.startswith(("#", "Competency:", "Topic:", "Section:")):
                if current_summary:
                    claims.append(
                        InterviewNoteClaim(
                            topic=current_topic,
                            candidate_response_summary=" ".join(current_summary),
                            interviewer_rating=current_rating,
                            direct_quote=direct_quote,
                            is_verified=current_rating in ["STRONG", "ACCEPTABLE"],
                        )
                    )
                    current_summary = []
                    direct_quote = None

                current_topic = re.sub(r"^[#\s]+|^(Competency|Topic|Section):\s*", "", line).strip()
                current_rating = "ACCEPTABLE"
                continue

            # Skip metadata or final summary sections from competency claim extraction
            if any(k in current_topic.lower() for k in ["final comments", "summary comments", "general notes", "interviewer comments"]):
                current_rating = "NOT_EVALUATED"

            # Look for explicit rating keywords
            lower_line = line.lower()
            if any(k in lower_line for k in ["not evaluated", "didn't cover", "did not evaluate", "skipped", "out of time", "need to validate"]):
                current_rating = "NOT_EVALUATED"
            elif any(k in lower_line for k in ["strong hire", "excellent", "deep answer", "rating: strong", "great depth", "strong depth"]):
                if current_rating != "NOT_EVALUATED":
                    current_rating = "STRONG"
            elif any(k in lower_line for k in ["weak", "struggled", "failed", "rating: weak", "superficial", "red flag"]):
                if current_rating != "NOT_EVALUATED":
                    current_rating = "WEAK"

            # Check for quoted candidate text
            quote_match = re.search(r'"([^"]+)"', line)
            if quote_match and not direct_quote:
                direct_quote = quote_match.group(1)

            current_summary.append(line)

        # Flush final claim
        if current_summary:
            claims.append(
                InterviewNoteClaim(
                    topic=current_topic,
                    candidate_response_summary=" ".join(current_summary),
                    interviewer_rating=current_rating,
                    direct_quote=direct_quote,
                    is_verified=current_rating in ["STRONG", "ACCEPTABLE"],
                )
            )

        return claims
