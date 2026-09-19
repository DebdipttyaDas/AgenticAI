"""Structured filtering builder for querying candidate pools."""

from typing import List
from hireflow.core.schemas import (
    CandidateScreeningReport,
    CandidateProfile,
    CandidateFilter,
)


class CandidateFilterEngine:
    """Applies multi-attribute structured filters over candidate profiles and reports."""

    @staticmethod
    def apply_filters(
        reports: List[CandidateScreeningReport],
        profiles: List[CandidateProfile],
        filters: CandidateFilter,
    ) -> List[CandidateScreeningReport]:
        """Filter screening reports matching all specified criteria."""
        profile_map = {p.candidate_id: p for p in profiles}
        filtered: List[CandidateScreeningReport] = []

        for rep in reports:
            prof = profile_map.get(rep.candidate_id)

            # 1. Min Score Filter
            if filters.min_score is not None and rep.overall_match_score < filters.min_score:
                continue

            # 2. Tiers Filter
            if filters.tiers and rep.assigned_tier not in filters.tiers:
                continue

            # 3. Min Years Experience
            if filters.min_years_experience is not None:
                if not prof or prof.total_years_experience < filters.min_years_experience:
                    continue

            # 4. Required Skills
            if filters.required_skills and prof:
                prof_skill_names = {s.name.lower() for s in prof.skills}
                if not all(req_sk.lower() in prof_skill_names for req_sk in filters.required_skills):
                    continue

            # 5. Capability Tags
            if filters.capability_tags:
                if not any(tag in rep.capability_tags for tag in filters.capability_tags):
                    continue

            filtered.append(rep)

        return filtered
