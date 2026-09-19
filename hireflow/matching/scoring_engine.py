"""Multi-factor weighted scoring engine for candidate evaluations."""

from typing import List, Tuple
from hireflow.core.schemas import (
    CompetencyEvaluation,
    RequirementType,
    MatchLevel,
)
from hireflow.core.config import settings


class ScoringEngine:
    """Computes normalized 0-100 scores and aggregates strengths & risks."""

    @classmethod
    def calculate_overall_score(
        cls, evaluations: List[CompetencyEvaluation]
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """
        Calculate weighted score and return (overall_score, strengths, risks, missing_validations).
        """
        if not evaluations:
            return 0.0, [], ["No requirements evaluated."], []

        total_weighted_points = 0.0
        max_possible_points = 0.0

        strengths: List[str] = []
        risks: List[str] = []
        missing_validations: List[str] = []

        for ev in evaluations:
            # Base multiplier by requirement type
            type_multiplier = (
                settings.must_have_weight
                if ev.requirement_type == RequirementType.MUST_HAVE
                else settings.nice_to_have_weight
            )
            effective_weight = ev.weight * type_multiplier

            max_possible_points += 10.0 * effective_weight
            total_weighted_points += ev.score * effective_weight

            # Categorize insights
            if ev.match_level in [MatchLevel.EXCEEDS, MatchLevel.MEETS]:
                strengths.append(
                    f"Strong competency in {ev.competency_name} ({ev.match_level.value}): {ev.evidence_justification}"
                )
            elif ev.match_level in [MatchLevel.PARTIAL, MatchLevel.INSUFFICIENT]:
                if ev.requirement_type == RequirementType.MUST_HAVE:
                    risks.append(
                        f"Must-Have Deficit in {ev.competency_name}: {ev.evidence_justification}"
                    )
                missing_validations.append(
                    f"Validate depth in {ev.competency_name} (Current level: {ev.match_level.value})"
                )
            elif ev.match_level == MatchLevel.NOT_FOUND:
                if ev.requirement_type == RequirementType.MUST_HAVE:
                    risks.append(
                        f"Critical Missing Must-Have: {ev.competency_name} (No evidence found)"
                    )
                else:
                    missing_validations.append(
                        f"Explore potential transferable background for nice-to-have: {ev.competency_name}"
                    )

        raw_percentage = (
            (total_weighted_points / max_possible_points * 100.0)
            if max_possible_points > 0
            else 0.0
        )
        final_score = round(max(0.0, min(100.0, raw_percentage)), 1)

        return final_score, strengths, risks, missing_validations
