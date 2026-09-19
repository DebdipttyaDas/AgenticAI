"""Anomaly and ambiguity detector for candidate resumes."""

import re
from typing import List
from hireflow.core.schemas import (
    GapAnomaly,
    AnomalySeverity,
    WorkExperienceEntry,
    TechnicalSkill,
    ProjectEntry,
    DocumentChunk,
)
from hireflow.core.config import settings


class GapDetector:
    """Identifies career gaps, missing metrics, vague claims, and timeline anomalies."""

    @classmethod
    def detect_anomalies(
        cls,
        experience: List[WorkExperienceEntry],
        skills: List[TechnicalSkill],
        projects: List[ProjectEntry],
        chunks: List[DocumentChunk],
    ) -> List[GapAnomaly]:
        """Run all anomaly detection heuristics."""
        anomalies: List[GapAnomaly] = []
        anomaly_counter = 1

        # 1. Detect Career Gaps (> settings.career_gap_month_threshold)
        if len(experience) > 1:
            for i in range(len(experience) - 1):
                current_job = experience[i]
                prev_job = experience[i + 1]

                # If end_date of prev_job and start_date of current_job have a gap
                try:
                    if prev_job.end_date != "Present" and current_job.start_date != "Present":
                        p_yr, p_mo = [int(x) for x in prev_job.end_date.split("-")]
                        c_yr, c_mo = [int(x) for x in current_job.start_date.split("-")]

                        gap_months = (c_yr - p_yr) * 12 + (c_mo - p_mo)
                        if gap_months > settings.career_gap_month_threshold:
                            anomalies.append(
                                GapAnomaly(
                                    anomaly_id=f"anom_{anomaly_counter:03d}",
                                    type="CAREER_GAP",
                                    description=(
                                        f"Detected a {gap_months}-month career gap between {prev_job.company} "
                                        f"({prev_job.end_date}) and {current_job.company} ({current_job.start_date})."
                                    ),
                                    severity=AnomalySeverity.MEDIUM,
                                    chunk_id=current_job.chunk_ids[0] if current_job.chunk_ids else None,
                                    validation_probe=(
                                        f"Can you walk us through your activities and professional development "
                                        f"during the period between leaving {prev_job.company} and joining {current_job.company}?"
                                    ),
                                )
                            )
                            anomaly_counter += 1
                except Exception:
                    pass

        # 2. Detect Missing Quantifiable Metrics on Major Claims
        metric_pattern = re.compile(r"(\d+%\b|\$\d+|\b\d+x\b|\b\d+\s*ms\b|\b\d+\s*k\b|\b\d+\s*m\b|\b\d+\s*users\b|\b\d+\s*req/s\b)", re.IGNORECASE)
        for job in experience:
            for achievement in job.key_achievements:
                # If achievement is lengthy but lacks numbers/metrics
                if len(achievement.split()) > 12 and not metric_pattern.search(achievement):
                    if any(v in achievement.lower() for v in ["optimized", "scaled", "improved", "reduced", "led", "redesigned", "accelerated"]):
                        anomalies.append(
                            GapAnomaly(
                                anomaly_id=f"anom_{anomaly_counter:03d}",
                                type="MISSING_METRIC",
                                description=(
                                    f"Claim at {job.company} ('{achievement[:55]}...') lacks quantitative verification or impact metrics."
                                ),
                                severity=AnomalySeverity.LOW,
                                chunk_id=job.chunk_ids[0] if job.chunk_ids else None,
                                validation_probe=(
                                    f"You mentioned you '{achievement[:60]}...'. What exact metrics, latency improvements, "
                                    f"or business KPIs demonstrated the success of that initiative?"
                                ),
                            )
                        )
                        anomaly_counter += 1
                        break  # 1 per job is sufficient

        # 3. Detect Vague / Unsubstantiated Technical Skills
        exp_text = " ".join([f"{j.company} {j.role} {' '.join(j.key_achievements)} {' '.join(j.technologies_used)}" for j in experience]).lower()
        proj_text = " ".join([f"{p.title} {p.description} {' '.join(p.technologies_used)}" for p in projects]).lower()
        combined_body = f"{exp_text} {proj_text}"

        for skill in skills:
            skill_name_lower = skill.name.lower()
            if skill_name_lower not in combined_body and len(skill.name) > 2:
                anomalies.append(
                    GapAnomaly(
                        anomaly_id=f"anom_{anomaly_counter:03d}",
                        type="VAGUE_SKILL",
                        description=(
                            f"Skill '{skill.name}' is listed in the profile but never demonstrated in any work experience or project description."
                        ),
                        severity=AnomalySeverity.MEDIUM,
                        chunk_id=skill.chunk_ids[0] if skill.chunk_ids else None,
                        validation_probe=(
                            f"You listed '{skill.name}' under your core skills. Could you describe a production system where you "
                            f"personally designed, deployed, or debugged with {skill.name}?"
                        ),
                    )
                )
                anomaly_counter += 1

        return anomalies
