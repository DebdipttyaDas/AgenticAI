"""Adaptive follow-up probe trees for validating ambiguous or critical claims."""

from typing import Dict, List
from hireflow.core.schemas import GapAnomaly, CompetencyEvaluation, MatchLevel


class ProbeTreeBuilder:
    """Constructs dynamic, multi-branch follow-up question trees for interviewers."""

    @staticmethod
    def build_probe_tree_for_competency(
        competency_name: str, match_level: MatchLevel, anchor: str
    ) -> Dict[str, str]:
        """Generate if-then branching follow-up questions."""
        if match_level == MatchLevel.EXCEEDS:
            return {
                "if_strong": (
                    f"What were the hardest architectural tradeoffs or failure modes you encountered "
                    f"when scaling {competency_name} at that scale, and what would you do differently?"
                ),
                "if_vague": (
                    f"Can you dive into the exact protocol or data consistency model you chose for {competency_name} "
                    f"rather than the high-level architecture?"
                ),
                "if_overclaimed": (
                    f"What was your personal code contribution vs the platform team's shared libraries "
                    f"in this {competency_name} project?"
                ),
            }
        elif match_level == MatchLevel.MEETS:
            return {
                "if_shallow": (
                    f"How did you handle monitoring, alerting, and degradation when {competency_name} components "
                    f"experienced node partitions or high latency spikes?"
                ),
                "if_strong": (
                    f"How did you mentor junior engineers or establish best practices across the org around {competency_name}?"
                ),
                "if_vague": (
                    f"Could you write out pseudo-code or step through the request lifecycle for that {competency_name} pipeline?"
                ),
            }
        else:
            return {
                "if_transferable": (
                    f"While you primarily used other technologies, how would the core concepts translate "
                    f"to {competency_name} in our environment?"
                ),
                "if_theoretical": (
                    f"Have you built a proof-of-concept or debugged {competency_name} issues outside production?"
                ),
            }

    @staticmethod
    def build_probe_for_gap(anomaly: GapAnomaly) -> Dict[str, str]:
        """Generate targeted probes specifically addressing flagged anomalies."""
        if anomaly.type == "CAREER_GAP":
            return {
                "direct_probe": anomaly.validation_probe,
                "if_upskilling": "What specific open-source projects or technical certifications did you focus on during that sabbatical?",
                "if_consulting": "Can you share the technical scope of the client projects you delivered during that window?",
            }
        elif anomaly.type == "MISSING_METRIC":
            return {
                "direct_probe": anomaly.validation_probe,
                "if_estimated": "How did you measure baseline vs post-deployment throughput or latency?",
                "if_qualitative": "What team or business velocity improvements resulted from this refactor?",
            }
        else:
            return {
                "direct_probe": anomaly.validation_probe,
                "if_basic": f"What is the most complex bug or performance bottleneck you resolved using {anomaly.description}?",
            }
