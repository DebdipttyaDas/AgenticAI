"""Post-interview coverage auditor and final recommendation generator."""

from typing import List, Tuple
from hireflow.core.schemas import (
    JobDescription,
    InterviewNoteClaim,
    CompetencyCoverageResult,
    InterviewEvaluationReport,
    FinalRecommendation,
    ProvenanceCitation,
)
from hireflow.core.provenance import provenance_ledger
from hireflow.core.config import settings


class CoverageAuditor:
    """Audits interviewer notes against JD requirements, calculating coverage and blind spots."""

    @classmethod
    def audit_interview_performance(
        cls,
        candidate_id: str,
        candidate_name: str,
        jd: JobDescription,
        claims: List[InterviewNoteClaim],
    ) -> InterviewEvaluationReport:
        """Run post-interview coverage evaluation and generate final scorecard."""
        results: List[CompetencyCoverageResult] = []
        covered_count = 0
        total_score = 0.0
        max_possible = 0.0

        evaluated_strengths: List[str] = []
        verified_risks: List[str] = []
        unanswered_areas: List[str] = []
        audit_citations: List[ProvenanceCitation] = []

        for req in jd.requirements:
            # 1. Match claim based on explicit topic or primary domain keywords
            topic_claims = [
                c for c in claims
                if any(term in c.topic.lower() for term in [req.title.lower()] + [kw.lower() for kw in req.keywords if len(kw) > 3 and kw.lower() not in ["systems", "software", "building", "production"]])
            ]

            if topic_claims:
                matched_claims = topic_claims
            else:
                core_kws = [kw.lower() for kw in req.keywords if len(kw) > 3 and kw.lower() not in ["systems", "software", "building", "hands", "proven", "leading", "senior", "experience", "production", "schemas"]]
                matched_claims = [
                    c for c in claims
                    if any(kw in c.candidate_response_summary.lower() for kw in core_kws)
                ]

            # Filter for claims that were actually evaluated with concrete assessments
            evaluated_claims = [
                c for c in matched_claims if c.interviewer_rating in ["STRONG", "ACCEPTABLE", "WEAK"]
            ]

            if evaluated_claims:
                covered_count += 1
                best_rating = "ACCEPTABLE"
                if any(c.interviewer_rating == "STRONG" for c in evaluated_claims):
                    best_rating = "STRONG"
                    score = 9.0
                    evaluated_strengths.append(f"Demonstrated strong mastery in {req.title}.")
                elif any(c.interviewer_rating == "WEAK" for c in evaluated_claims):
                    best_rating = "WEAK"
                    score = 4.0
                    verified_risks.append(f"Struggled with technical depth in {req.title}.")
                else:
                    score = 7.5

                evidence_text = " | ".join([c.candidate_response_summary[:120] for c in evaluated_claims])
                results.append(
                    CompetencyCoverageResult(
                        competency_id=req.requirement_id,
                        competency_name=req.title,
                        requirement_type=req.requirement_type,
                        was_covered=True,
                        rating=best_rating,
                        score=score,
                        evidence_summary=evidence_text,
                        blind_spot_identified=False,
                    )
                )
                total_score += score * req.weight
                max_possible += 10.0 * req.weight

                # Add citation
                first_quote = next((c.direct_quote for c in evaluated_claims if c.direct_quote), None)
                if first_quote:
                    audit_citations.append(
                        ProvenanceCitation(
                            chunk_id=f"interview_{req.requirement_id}",
                            verbatim_quote=first_quote,
                            section="interview_notes",
                            confidence=0.95,
                        )
                    )
            else:
                # Competency was NOT covered
                results.append(
                    CompetencyCoverageResult(
                        competency_id=req.requirement_id,
                        competency_name=req.title,
                        requirement_type=req.requirement_type,
                        was_covered=False,
                        rating="NOT_COVERED",
                        score=0.0,
                        evidence_summary="Not evaluated or skipped during interview.",
                        blind_spot_identified=True,
                        recommended_next_round_probe=(
                            f"Focus probe in Round 2: Evaluate hands-on experience and architecture decisions in {req.title}."
                        ),
                    )
                )
                unanswered_areas.append(
                    f"Requirement '{req.title}' ({req.requirement_type.value}) was completely unevaluated."
                )

        total_reqs = len(jd.requirements)
        coverage_ratio = round((covered_count / total_reqs * 100.0) if total_reqs > 0 else 0.0, 1)
        final_normalized_score = round((total_score / max_possible * 100.0) if max_possible > 0 else 0.0, 1)

        # Recommendation logic
        if final_normalized_score >= 85.0 and coverage_ratio >= settings.min_interview_coverage_ratio and len(verified_risks) == 0:
            recommendation = FinalRecommendation.STRONG_HIRE
            verdict = "Outstanding performance across all evaluated core competencies with zero red flags."
        elif final_normalized_score >= 70.0 and len(verified_risks) <= 1:
            recommendation = FinalRecommendation.HIRE
            verdict = "Solid technical performance meeting core hiring bar."
        elif final_normalized_score >= 50.0 or coverage_ratio < 60.0:
            recommendation = FinalRecommendation.INCLINED
            verdict = f"Potential fit, but significant coverage blind spots ({100 - coverage_ratio:.0f}% unassessed) require follow-up."
        else:
            recommendation = FinalRecommendation.DO_NOT_HIRE
            verdict = "Candidate failed to demonstrate required technical competencies."

        report = InterviewEvaluationReport(
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            role_title=jd.title,
            coverage_ratio=coverage_ratio,
            final_score=final_normalized_score,
            recommendation=recommendation,
            executive_verdict=verdict,
            competency_results=results,
            evaluated_strengths=evaluated_strengths,
            verified_risks=verified_risks,
            unanswered_areas_for_next_round=unanswered_areas,
            audit_trail=audit_citations,
        )

        provenance_ledger.record_insight(
            candidate_id=candidate_id,
            insight_type="RECOMMENDATION",
            source_chunk_ids=[c.chunk_id for c in audit_citations],
            source_text_excerpts=[c.verbatim_quote for c in audit_citations],
            model_rationale=f"Final interview verdict: {recommendation.value} (Coverage: {coverage_ratio}%, Score: {final_normalized_score}%)",
            confidence_score=0.90,
        )

        return report
