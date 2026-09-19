"""Standardized report generation in structured JSON, Markdown, and interactive HTML formats."""

from typing import List
from hireflow.core.schemas import (
    CandidateProfile,
    JobDescription,
    CompetencyEvaluation,
    TailoredQuestion,
    CandidateScreeningReport,
    InterviewEvaluationReport,
    CandidateTier,
)
from hireflow.matching.scoring_engine import ScoringEngine
from hireflow.matching.candidate_grouper import CandidateGrouper


class EvaluationReporter:
    """Produces recruiter-facing scorecards and reports."""

    @classmethod
    def build_screening_report(
        cls,
        profile: CandidateProfile,
        jd: JobDescription,
        evaluations: List[CompetencyEvaluation],
        questions: List[TailoredQuestion],
    ) -> CandidateScreeningReport:
        """Synthesize evaluations into CandidateScreeningReport."""
        score, strengths, risks, validations = ScoringEngine.calculate_overall_score(evaluations)
        tier = CandidateGrouper.assign_tier(score, evaluations, profile)
        tags = CandidateGrouper.generate_capability_tags(profile)

        # Collect citations
        all_citations = []
        for ev in evaluations:
            all_citations.extend(ev.citations)

        exec_summary = (
            f"{profile.candidate_name} presents {profile.total_years_experience} years of software experience. "
            f"Achieved an overall competency match score of {score:.1f}% ({tier.value}). "
            f"Demonstrates key strengths in {', '.join(tags[:3])}. "
            f"Identified {len(risks)} risk/deficit areas and {len(profile.detected_gaps)} resume anomalies for interview probing."
        )

        return CandidateScreeningReport(
            candidate_id=profile.candidate_id,
            candidate_name=profile.candidate_name,
            overall_match_score=score,
            assigned_tier=tier,
            capability_tags=tags,
            executive_summary=exec_summary,
            competency_evaluations=evaluations,
            strengths=strengths,
            risk_factors=risks,
            missing_validations=validations,
            recommended_interview_questions=questions,
            audit_trail=all_citations,
        )

    @classmethod
    def render_markdown(cls, report: CandidateScreeningReport) -> str:
        """Render markdown scorecard."""
        tier_badges = {
            CandidateTier.TIER_1_SHORTLIST: "🟢 **TIER 1 (SHORTLIST)**",
            CandidateTier.TIER_2_CONTENDER: "🔵 **TIER 2 (CONTENDER)**",
            CandidateTier.TIER_3_SPECIALIST_GAPPED: "🟡 **TIER 3 (SPECIALIST / GAPPED)**",
            CandidateTier.TIER_4_UNMATCHED: "🔴 **TIER 4 (UNMATCHED)**",
        }
        badge = tier_badges.get(report.assigned_tier, report.assigned_tier.value)

        lines = [
            f"# HireFlow Screening Scorecard: {report.candidate_name}",
            f"**Candidate ID:** `{report.candidate_id}` | **Overall Score:** `{report.overall_match_score:.1f}%` | **Tier:** {badge}",
            f"**Capability Tags:** {', '.join([f'`{t}`' for t in report.capability_tags])}\n",
            "## Executive Summary",
            f"{report.executive_summary}\n",
            "## Competency Breakdown",
            "| Requirement | Type | Match Level | Score | Evidence Justification |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for ev in report.competency_evaluations:
            lines.append(
                f"| **{ev.competency_name}** | `{ev.requirement_type.value}` | `{ev.match_level.value}` | `{ev.score:.1f}/10` | {ev.evidence_justification} |"
            )

        if report.strengths:
            lines.append("\n## Key Strengths")
            for s in report.strengths:
                lines.append(f"- ✅ {s}")

        if report.risk_factors:
            lines.append("\n## Risk Factors & Potential Deficits")
            for r in report.risk_factors:
                lines.append(f"- ⚠️ {r}")

        if report.recommended_interview_questions:
            lines.append("\n## Tailored Interview Plan & Probe Trees")
            for q in report.recommended_interview_questions:
                lines.append(f"### Q{q.question_id[-3:]}: {q.target_competency}")
                lines.append(f"> **Question:** {q.question_text}")
                lines.append(f"- **Anchor:** *\"{q.resume_anchor}\"*")
                lines.append(f"- **Intent:** {q.intent}")
                if q.expected_positive_signals:
                    lines.append(f"- **Green Flags (Positive Signals):** {'; '.join(q.expected_positive_signals)}")
                if q.red_flag_warnings:
                    lines.append(f"- **Red Flags (Warning Signs):** {'; '.join(q.red_flag_warnings)}")
                if q.adaptive_follow_ups:
                    lines.append("- **Adaptive Probes:**")
                    for condition, probe in q.adaptive_follow_ups.items():
                        lines.append(f"  - *[{condition}]:* {probe}")
                lines.append("")

        return "\n".join(lines)

    @classmethod
    def render_html_scorecard(cls, report: CandidateScreeningReport) -> str:
        """Generate standalone HTML scorecard with CSS styling."""
        tier_colors = {
            CandidateTier.TIER_1_SHORTLIST: "#10b981",
            CandidateTier.TIER_2_CONTENDER: "#3b82f6",
            CandidateTier.TIER_3_SPECIALIST_GAPPED: "#f59e0b",
            CandidateTier.TIER_4_UNMATCHED: "#ef4444",
        }
        accent = tier_colors.get(report.assigned_tier, "#4f46e5")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HireFlow Scorecard - {report.candidate_name}</title>
    <style>
        :root {{
            --primary: {accent};
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .score-pill {{
            background: var(--primary);
            color: #fff;
            padding: 12px 24px;
            border-radius: 9999px;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
        }}
        .tier-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-main);
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            margin-top: 6px;
        }}
        .tag {{
            display: inline-block;
            background: #334155;
            color: #cbd5e1;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 6px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
        }}
        th, td {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        th {{
            color: var(--text-muted);
            font-weight: 600;
        }}
        .badge-match {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
        }}
        .match-EXCEEDS {{ background: rgba(16, 185, 129, 0.2); color: #10b981; }}
        .match-MEETS {{ background: rgba(59, 130, 246, 0.2); color: #3b82f6; }}
        .match-PARTIAL {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; }}
        .match-INSUFFICIENT, .match-NOT_FOUND {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}
        .question-box {{
            background: #0f172a;
            border-left: 4px solid var(--primary);
            padding: 14px;
            border-radius: 4px;
            margin-bottom: 16px;
        }}
        .probe-item {{
            margin-left: 16px;
            font-size: 13px;
            color: #cbd5e1;
            margin-top: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 style="margin: 0; font-size: 28px;">{report.candidate_name}</h1>
                <div style="color: var(--text-muted); margin-top: 4px;">ID: {report.candidate_id}</div>
                <div style="margin-top: 8px;">
                    {' '.join([f'<span class="tag">{t}</span>' for t in report.capability_tags])}
                </div>
            </div>
            <div>
                <div class="score-pill">{report.overall_match_score:.1f}%</div>
                <div class="tier-badge" style="border-left: 3px solid var(--primary);">{report.assigned_tier.value}</div>
            </div>
        </div>

        <div class="card">
            <h3 style="margin-top: 0;">Executive Summary</h3>
            <p style="color: #cbd5e1;">{report.executive_summary}</p>
        </div>

        <div class="card">
            <h3 style="margin-top: 0;">Competency Evaluation Matrix</h3>
            <table>
                <thead>
                    <tr>
                        <th>Requirement</th>
                        <th>Type</th>
                        <th>Match Level</th>
                        <th>Score</th>
                        <th>Evidence Justification</th>
                    </tr>
                </thead>
                <tbody>
"""
        for ev in report.competency_evaluations:
            html += f"""
                    <tr>
                        <td><strong>{ev.competency_name}</strong></td>
                        <td><span class="tag">{ev.requirement_type.value}</span></td>
                        <td><span class="badge-match match-{ev.match_level.value}">{ev.match_level.value}</span></td>
                        <td>{ev.score:.1f}/10</td>
                        <td>{ev.evidence_justification}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3 style="margin-top: 0;">Recommended Interview Plan & Adaptive Probes</h3>
"""
        for q in report.recommended_interview_questions:
            html += f"""
            <div class="question-box">
                <div style="font-weight: bold; color: #38bdf8;">{q.target_competency} (Anchor: {q.resume_anchor})</div>
                <div style="margin-top: 6px; font-size: 15px;">{q.question_text}</div>
                <div style="margin-top: 8px; font-size: 12px; color: var(--text-muted);"><strong>Intent:</strong> {q.intent}</div>
                <div style="margin-top: 8px;">
                    <strong>Adaptive Probe Tree:</strong>
"""
            for cond, probe in q.adaptive_follow_ups.items():
                html += f'<div class="probe-item"><strong>[{cond}]:</strong> {probe}</div>'
            html += """
                </div>
            </div>
            """

        html += """
        </div>
    </div>
</body>
</html>
"""
        return html
