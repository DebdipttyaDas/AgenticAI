"""Candidate grouping, tier allocation, and capability tagging engine."""

from typing import List
from hireflow.core.schemas import (
    CandidateTier,
    CompetencyEvaluation,
    RequirementType,
    MatchLevel,
    CandidateProfile,
)
from hireflow.core.config import settings


class CandidateGrouper:
    """Allocates candidates into actionable tiers and generates capability tags."""

    @classmethod
    def assign_tier(
        cls,
        overall_score: float,
        evaluations: List[CompetencyEvaluation],
        profile: CandidateProfile,
    ) -> CandidateTier:
        """Determine appropriate tier based on scores and must-have criteria."""
        missing_must_haves = [
            ev
            for ev in evaluations
            if ev.requirement_type == RequirementType.MUST_HAVE
            and ev.match_level in [MatchLevel.NOT_FOUND, MatchLevel.INSUFFICIENT]
        ]

        if overall_score >= settings.tier_1_threshold and len(missing_must_haves) == 0:
            return CandidateTier.TIER_1_SHORTLIST
        elif overall_score >= settings.tier_2_threshold and len(missing_must_haves) <= 1:
            return CandidateTier.TIER_2_CONTENDER
        elif overall_score >= settings.tier_3_threshold:
            return CandidateTier.TIER_3_SPECIALIST_GAPPED
        else:
            return CandidateTier.TIER_4_UNMATCHED

    @classmethod
    def generate_capability_tags(cls, profile: CandidateProfile) -> List[str]:
        """Infer high-level capability tags from profile skills and experience."""
        tags = []
        skill_names = {s.name.lower() for s in profile.skills}

        if any(k in skill_names for k in ["go", "golang", "rust", "c++", "distributed systems", "grpc"]):
            tags.append("High Concurrency / Systems")
        if any(k in skill_names for k in ["kubernetes", "docker", "aws", "gcp", "terraform"]):
            tags.append("Cloud Native / Infra")
        if any(k in skill_names for k in ["kafka", "rabbitmq", "spark", "flink"]):
            tags.append("Streaming Data Architecture")
        if any(k in skill_names for k in ["pytorch", "tensorflow", "ml", "ai"]):
            tags.append("AI / Machine Learning")
        if any(k in skill_names for k in ["react", "typescript", "vue", "frontend"]):
            tags.append("Full-Stack / Frontend")
        if profile.total_years_experience >= 7.0:
            tags.append("Senior Staff Caliber")

        return tags or ["General Software Engineer"]
