"""Role-specific and candidate-tailored interview question generator."""

from typing import List
from hireflow.core.schemas import (
    CandidateProfile,
    JobDescription,
    CompetencyEvaluation,
    TailoredQuestion,
    MatchLevel,
)
from hireflow.core.llm_client import llm_client
from hireflow.core.provenance import provenance_ledger
from hireflow.intelligence.probe_tree import ProbeTreeBuilder


class InterviewQuestionGenerator:
    """Produces depth-first tailored interview questions with probe trees and signal rubrics."""

    @classmethod
    def generate_interview_plan(
        cls,
        profile: CandidateProfile,
        jd: JobDescription,
        evaluations: List[CompetencyEvaluation],
    ) -> List[TailoredQuestion]:
        """Generate tailored questions covering core competencies and detected gaps."""
        questions: List[TailoredQuestion] = []
        q_counter = 1

        # 1. Generate questions for top JD competencies
        for ev in evaluations:
            # Find relevant resume anchor
            anchor = "General Experience"
            if ev.citations:
                anchor = ev.citations[0].verbatim_quote[:100]
            elif profile.experience:
                anchor = f"Role at {profile.experience[0].company} ({profile.experience[0].role})"

            follow_ups = ProbeTreeBuilder.build_probe_tree_for_competency(
                ev.competency_name, ev.match_level, anchor
            )

            if ev.match_level == MatchLevel.EXCEEDS:
                q_text = (
                    f"In your work at {anchor}, you demonstrated extensive expertise in {ev.competency_name}. "
                    f"Can you walk us through the most challenging production failure or scalability barrier you solved in this domain?"
                )
                green_flags = [
                    "Discusses nuanced architectural tradeoffs (e.g., CAP theorem, replication lag).",
                    "Provides exact metrics on load, RPS, latency, and fault-tolerance.",
                    "Demonstrates clear ownership of system reliability and post-mortems.",
                ]
                red_flags = [
                    "Gives only high-level conceptual answers without production war stories.",
                    "Cannot explain what happens when nodes fail or partition.",
                    "Blames third-party tools without understanding underlying mechanics.",
                ]
            elif ev.match_level == MatchLevel.MEETS:
                q_text = (
                    f"Regarding your experience with {ev.competency_name} referenced in '{anchor}': "
                    f"How did you design for concurrency and data consistency across microservices?"
                )
                green_flags = [
                    "Explains idempotency, message ordering, or distributed transactions clearly.",
                    "Shows familiarity with caching strategies and database connection pooling.",
                ]
                red_flags = [
                    "Assumes network calls never fail.",
                    "Relies entirely on synchronous REST without considering retry storms.",
                ]
            else:
                q_text = (
                    f"The role requires strong capabilities in {ev.competency_name}. How have you approached "
                    f"similar technical challenges or ramped up quickly on complex infrastructure in past roles?"
                )
                green_flags = [
                    "Shows high learning agility and rapid mastery of new paradigms.",
                    "Draws strong transferable parallels from related frameworks.",
                ]
                red_flags = [
                    "Dismisses the importance of the competency.",
                    "Shows reluctance to work with unfamiliar technologies.",
                ]

            question = TailoredQuestion(
                question_id=f"q_{q_counter:03d}",
                target_competency=ev.competency_name,
                question_text=q_text,
                resume_anchor=anchor,
                intent=f"Validate candidate depth and production reliability in {ev.competency_name}.",
                expected_positive_signals=green_flags,
                red_flag_warnings=red_flags,
                adaptive_follow_ups=follow_ups,
            )
            questions.append(question)
            q_counter += 1

            # Log to provenance ledger
            provenance_ledger.record_insight(
                candidate_id=profile.candidate_id,
                insight_type="QUESTION_GENERATION",
                source_chunk_ids=[c.chunk_id for c in ev.citations],
                source_text_excerpts=[c.verbatim_quote for c in ev.citations],
                model_rationale=f"Generated tailored probe for competency '{ev.competency_name}' anchored to '{anchor}'.",
                confidence_score=0.95,
            )

        # 2. Add targeted probes for detected resume anomalies/gaps
        for anomaly in profile.detected_gaps[:2]:
            probe_dict = ProbeTreeBuilder.build_probe_for_gap(anomaly)
            gap_q = TailoredQuestion(
                question_id=f"q_{q_counter:03d}",
                target_competency=f"Resume Validation: {anomaly.type}",
                question_text=anomaly.validation_probe,
                resume_anchor=f"Anomaly [{anomaly.type}]",
                intent=f"Clarify and validate detected resume ambiguity: {anomaly.description}",
                expected_positive_signals=[
                    "Provides transparent, concise context without defensiveness.",
                    "Articulates concrete technical work and achievements.",
                ],
                red_flag_warnings=[
                    "Contradicts timeline or claims on resume.",
                    "Remains evasive or unclear on details.",
                ],
                adaptive_follow_ups=probe_dict,
            )
            questions.append(gap_q)
            q_counter += 1

        return questions
