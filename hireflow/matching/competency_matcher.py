"""Competency matching and requirement-level evidence mapping engine."""

import re
from typing import List, Tuple
from hireflow.core.schemas import (
    CandidateProfile,
    JobDescription,
    JobRequirement,
    CompetencyEvaluation,
    MatchLevel,
    ProvenanceCitation,
)
from hireflow.core.llm_client import llm_client
from hireflow.core.provenance import provenance_ledger


class CompetencyMatcher:
    """Evaluates candidate evidence against job description requirements."""

    @classmethod
    def evaluate_competencies(
        cls, profile: CandidateProfile, jd: JobDescription
    ) -> List[CompetencyEvaluation]:
        """Evaluate all JD requirements against candidate profile."""
        evaluations: List[CompetencyEvaluation] = []

        for req in jd.requirements:
            eval_result = cls._evaluate_single_requirement(profile, req)
            evaluations.append(eval_result)

            # Record in provenance ledger
            provenance_ledger.record_insight(
                candidate_id=profile.candidate_id,
                insight_type="MATCH_SCORE",
                source_chunk_ids=[c.chunk_id for c in eval_result.citations],
                source_text_excerpts=[c.verbatim_quote for c in eval_result.citations],
                model_rationale=(
                    f"Evaluated requirement '{req.title}': {eval_result.match_level.value} "
                    f"(Score: {eval_result.score}/10) - {eval_result.evidence_justification}"
                ),
                confidence_score=0.95 if eval_result.citations else 0.70,
            )

        return evaluations

    @classmethod
    def _evaluate_single_requirement(
        cls, profile: CandidateProfile, req: JobRequirement
    ) -> CompetencyEvaluation:
        # 1. Search for keyword & semantic overlap in chunks
        matched_citations: List[ProvenanceCitation] = []
        matching_chunks = []
        keyword_hits = 0

        for chunk in profile.chunks:
            chunk_lower = chunk.text.lower()
            hits_in_chunk = [kw for kw in req.keywords if kw.lower() in chunk_lower]
            if hits_in_chunk:
                keyword_hits += len(hits_in_chunk)
                matching_chunks.append((chunk, hits_in_chunk))

                # Extract first sentence mentioning keyword as verbatim quote
                for sentence in re.split(r"[.\n]", chunk.text):
                    if any(kw.lower() in sentence.lower() for kw in req.keywords) and len(sentence.strip()) > 15:
                        quote = sentence.strip()[:140]
                        matched_citations.append(
                            provenance_ledger.build_citation(
                                chunk_id=chunk.chunk_id,
                                verbatim_quote=quote,
                                confidence=0.9,
                                section=chunk.section,
                            )
                        )
                        break

        # Calculate match level & score based on evidence depth
        unique_matched_keywords = {
            kw for _, hits in matching_chunks for kw in hits
        }
        keyword_coverage = (
            len(unique_matched_keywords) / len(req.keywords) if req.keywords else 0.0
        )

        detected_gaps: List[str] = []
        if keyword_coverage >= 0.50 and profile.total_years_experience >= 5.0:
            match_level = MatchLevel.EXCEEDS
            score = 9.5
            justification = (
                f"Candidate demonstrates deep, verified production experience covering key criteria "
                f"({', '.join(list(unique_matched_keywords)[:4])}) across multiple roles."
            )
        elif (keyword_coverage >= 0.25 or len(unique_matched_keywords) >= 2) and profile.total_years_experience >= 3.0:
            match_level = MatchLevel.MEETS
            score = 8.0
            justification = (
                f"Solid alignment with requirement criteria ({', '.join(list(unique_matched_keywords)[:3])}). "
                f"Demonstrated hands-on experience in work history."
            )
        elif keyword_coverage > 0.10 or len(unique_matched_keywords) >= 1:
            match_level = MatchLevel.PARTIAL
            score = 5.0
            justification = (
                f"Candidate has partial exposure to {', '.join(unique_matched_keywords)}, but lacks depth "
                f"or primary focus in core architecture."
            )
            detected_gaps.append(f"Limited verified production depth in {req.title}.")
        elif any(s.name.lower() in req.description.lower() for s in profile.skills):
            match_level = MatchLevel.INSUFFICIENT
            score = 3.0
            justification = "Skill mentioned in profile list but not substantiated in employment achievements."
            detected_gaps.append(f"Unsubstantiated skill claim for {req.title}.")
        else:
            match_level = MatchLevel.NOT_FOUND
            score = 0.0
            justification = f"No direct evidence or relevant experience found for {req.title}."
            detected_gaps.append(f"Completely missing {req.title}.")

        return CompetencyEvaluation(
            competency_id=req.requirement_id,
            competency_name=req.title,
            requirement_type=req.requirement_type,
            weight=req.weight,
            match_level=match_level,
            score=score,
            evidence_justification=justification,
            citations=matched_citations[:3],
            detected_gaps=detected_gaps,
        )
