"""Rich interactive Command Line Interface for HireFlow."""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from hireflow.core.schemas import (
    CandidateScreeningReport,
    CandidateProfile,
    JobDescription,
    CandidateQueryRequest,
    CandidateTier,
)
from hireflow.core.provenance import provenance_ledger
from hireflow.ingestion.parser import DocumentParser
from hireflow.ingestion.chunker import SemanticChunker
from hireflow.extraction.jd_extractor import JobDescriptionExtractor
from hireflow.extraction.profile_extractor import CandidateProfileExtractor
from hireflow.matching.competency_matcher import CompetencyMatcher
from hireflow.intelligence.question_generator import InterviewQuestionGenerator
from hireflow.intelligence.evaluation_reporter import EvaluationReporter
from hireflow.intelligence.notes_analyzer import NotesAnalyzer
from hireflow.intelligence.coverage_auditor import CoverageAuditor
from hireflow.query.nl_query_engine import NaturalLanguageQueryEngine
from hireflow.core.config import settings

console = Console()


def run_screen(jd_path: str, resume_paths: List[str], output_dir: str = "output"):
    """Screen resumes against job description and produce leaderboards and reports."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel(
            f"[bold cyan]HireFlow AI Candidate Screening Engine[/bold cyan]\n"
            f"[dim]JD: {jd_path} | Resumes: {len(resume_paths)} files[/dim]",
            border_style="cyan",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task1 = progress.add_task("[green]Parsing Job Description...", total=1)
        jd_text, _ = DocumentParser.parse_file(jd_path)
        jd = JobDescriptionExtractor.extract_from_text(jd_text, job_id=Path(jd_path).stem)
        progress.update(task1, completed=1)

        reports: List[CandidateScreeningReport] = []
        profiles: List[CandidateProfile] = []

        task2 = progress.add_task("[yellow]Screening candidates & evaluating competencies...", total=len(resume_paths))
        for idx, rpath in enumerate(resume_paths):
            cand_id = f"cand_{idx + 1:03d}"
            raw_text, _ = DocumentParser.parse_file(rpath)
            chunks = SemanticChunker.chunk_document(raw_text, doc_id=cand_id)
            profile = CandidateProfileExtractor.extract_profile(raw_text, chunks, candidate_id=cand_id)
            profiles.append(profile)

            evaluations = CompetencyMatcher.evaluate_competencies(profile, jd)
            questions = InterviewQuestionGenerator.generate_interview_plan(profile, jd, evaluations)
            report = EvaluationReporter.build_screening_report(profile, jd, evaluations, questions)
            reports.append(report)

            # Persist individual JSON and HTML reports
            cand_json = out / f"{cand_id}_report.json"
            cand_json.write_text(report.model_dump_json(indent=2), encoding="utf-8")

            cand_html = out / f"{cand_id}_scorecard.html"
            cand_html.write_text(EvaluationReporter.render_html_scorecard(report), encoding="utf-8")

            cand_prof = out / f"{cand_id}_profile.json"
            cand_prof.write_text(profile.model_dump_json(indent=2), encoding="utf-8")

            progress.advance(task2)

    # Save job description for reuse
    (out / "job_description.json").write_text(jd.model_dump_json(indent=2), encoding="utf-8")

    # Render Leaderboard Table
    reports.sort(key=lambda r: r.overall_match_score, reverse=True)

    table = Table(title=f"🏆 Candidate Screening Leaderboard: {jd.title}", header_style="bold magenta")
    table.add_column("Rank", justify="center", style="bold")
    table.add_column("Candidate Name", style="cyan")
    table.add_column("Match Score", justify="center", style="bold")
    table.add_column("Tier", justify="center")
    table.add_column("Capability Tags", style="dim")
    table.add_column("Top Strength", style="green")
    table.add_column("Primary Risk / Gap", style="red")

    tier_colors = {
        CandidateTier.TIER_1_SHORTLIST: "[bold green]TIER 1 (Shortlist)[/bold green]",
        CandidateTier.TIER_2_CONTENDER: "[bold blue]TIER 2 (Contender)[/bold blue]",
        CandidateTier.TIER_3_SPECIALIST_GAPPED: "[bold yellow]TIER 3 (Specialist)[/bold yellow]",
        CandidateTier.TIER_4_UNMATCHED: "[bold red]TIER 4 (Unmatched)[/bold red]",
    }

    for rank, rep in enumerate(reports, 1):
        tier_str = tier_colors.get(rep.assigned_tier, rep.assigned_tier.value)
        top_str = rep.strengths[0][:40] + "..." if rep.strengths else "N/A"
        top_risk = rep.risk_factors[0][:40] + "..." if rep.risk_factors else "None flagged"

        score_color = "green" if rep.overall_match_score >= 85 else "blue" if rep.overall_match_score >= 70 else "yellow" if rep.overall_match_score >= 50 else "red"

        table.add_row(
            str(rank),
            rep.candidate_name,
            f"[{score_color}]{rep.overall_match_score:.1f}%[/{score_color}]",
            tier_str,
            ", ".join(rep.capability_tags[:2]),
            top_str,
            top_risk,
        )

    console.print(table)
    console.print(f"\n[bold green]✔ Screening complete![/bold green] Generated structured reports and HTML scorecards in [cyan]{output_dir}/[/cyan]\n")


def run_interview_plan(report_path: str):
    """Display interview questions, rubrics, and probe trees."""
    path = Path(report_path)
    if not path.exists():
        console.print(f"[red]Error: File not found: {report_path}[/red]")
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    report = CandidateScreeningReport.model_validate(data)

    console.print(
        Panel(
            f"[bold cyan]Tailored Interview Guide: {report.candidate_name}[/bold cyan]\n"
            f"[dim]Score: {report.overall_match_score:.1f}% | Tier: {report.assigned_tier.value}[/dim]",
            border_style="cyan",
        )
    )

    for idx, q in enumerate(report.recommended_interview_questions, 1):
        tree_text = ""
        for cond, probe in q.adaptive_follow_ups.items():
            tree_text += f"\n  • [bold yellow]\\[{cond}]:[/bold yellow] {probe}"

        panel_content = (
            f"[bold]Target Competency:[/bold] [cyan]{q.target_competency}[/cyan]\n"
            f"[bold]Resume Anchor:[/bold] [dim]\"{q.resume_anchor}\"[/dim]\n\n"
            f"[bold green]Question:[/bold green] {q.question_text}\n\n"
            f"[bold]Intent:[/bold] {q.intent}\n\n"
            f"[bold]Green Flags:[/bold] {'; '.join(q.expected_positive_signals)}\n"
            f"[bold red]Red Flags:[/bold red] {'; '.join(q.red_flag_warnings)}\n\n"
            f"[bold]Adaptive Probe Tree:[/bold]{tree_text}"
        )
        console.print(Panel(panel_content, title=f"Question {idx}", border_style="blue"))


def run_evaluate_interview(jd_path: str, candidate_report_path: str, notes_path: str):
    """Audit post-interview notes against requirements and output final recommendation."""
    jd_text, _ = DocumentParser.parse_file(jd_path)
    jd = JobDescriptionExtractor.extract_from_text(jd_text)

    rep_data = json.loads(Path(candidate_report_path).read_text(encoding="utf-8"))
    report = CandidateScreeningReport.model_validate(rep_data)

    notes_text, _ = DocumentParser.parse_file(notes_path)
    claims = NotesAnalyzer.parse_notes(notes_text)

    eval_result = CoverageAuditor.audit_interview_performance(
        candidate_id=report.candidate_id,
        candidate_name=report.candidate_name,
        jd=jd,
        claims=claims,
    )

    rec_colors = {
        "STRONG_HIRE": "[bold green]STRONG HIRE[/bold green]",
        "HIRE": "[bold blue]HIRE[/bold blue]",
        "INCLINED": "[bold yellow]INCLINED (FOLLOW-UP REQUIRED)[/bold yellow]",
        "DO_NOT_HIRE": "[bold red]DO NOT HIRE[/bold red]",
    }

    console.print(
        Panel(
            f"[bold cyan]Post-Interview Evaluation Report[/bold cyan]\n"
            f"Candidate: [bold]{eval_result.candidate_name}[/bold] | Role: [dim]{eval_result.role_title}[/dim]\n"
            f"Evaluation Coverage Ratio: [bold]{eval_result.coverage_ratio:.1f}%[/bold] | Final Score: [bold]{eval_result.final_score:.1f}%[/bold]\n"
            f"Final Recommendation: {rec_colors.get(eval_result.recommendation.value, eval_result.recommendation.value)}\n\n"
            f"[italic]{eval_result.executive_verdict}[/italic]",
            border_style="magenta",
        )
    )

    # Table of competencies
    table = Table(title="Competency Coverage Audit", header_style="bold cyan")
    table.add_column("Competency", style="bold")
    table.add_column("Covered?", justify="center")
    table.add_column("Rating", justify="center")
    table.add_column("Score", justify="center")
    table.add_column("Evidence from Notes", style="dim")

    for c in eval_result.competency_results:
        cov_icon = "✅ Yes" if c.was_covered else "❌ No"
        r_color = "green" if c.rating == "STRONG" else "yellow" if c.rating == "ACCEPTABLE" else "red"
        table.add_row(
            c.competency_name,
            cov_icon,
            f"[{r_color}]{c.rating}[/{r_color}]",
            f"{c.score:.1f}/10",
            c.evidence_summary[:60] + "...",
        )

    console.print(table)

    if eval_result.unanswered_areas_for_next_round:
        console.print("\n[bold yellow]⚠️ Unanswered Areas & Blind Spots (Action items for Round 2):[/bold yellow]")
        for ua in eval_result.unanswered_areas_for_next_round:
            console.print(f"  • {ua}")


def run_query(pool_dir: str, query_prompt: str):
    """Execute natural language search over the candidate pool."""
    pool_path = Path(pool_dir)
    if not pool_path.exists():
        console.print(f"[red]Error: Pool directory not found: {pool_dir}[/red]")
        sys.exit(1)

    reports = []
    profiles = []

    for f in pool_path.glob("*_report.json"):
        rep = CandidateScreeningReport.model_validate(json.loads(f.read_text(encoding="utf-8")))
        reports.append(rep)

    for f in pool_path.glob("*_profile.json"):
        prof = CandidateProfile.model_validate(json.loads(f.read_text(encoding="utf-8")))
        profiles.append(prof)

    if not reports:
        console.print(f"[yellow]No processed candidate reports found in {pool_dir}. Run `screen` first.[/yellow]")
        sys.exit(1)

    console.print(f"[bold cyan]🔍 Querying pool with:[/bold cyan] \"{query_prompt}\"\n")
    req = CandidateQueryRequest(query=query_prompt)
    resp = NaturalLanguageQueryEngine.execute_query(req, reports, profiles)

    console.print(Panel(f"[bold]Synthesized Answer:[/bold]\n\n{resp.synthesized_answer}", border_style="green"))

    if resp.matched_candidates:
        table = Table(title="Top Matched Candidates", header_style="bold blue")
        table.add_column("Rank", justify="center")
        table.add_column("Candidate Name", style="bold cyan")
        table.add_column("Score", justify="center")
        table.add_column("Tier", justify="center")
        table.add_column("Relevance Justification")

        for r, m in enumerate(resp.matched_candidates, 1):
            table.add_row(str(r), m.candidate_name, f"{m.match_score:.1f}%", m.tier.value, m.relevance_explanation)

        console.print(table)


def main():
    parser = argparse.ArgumentParser(description="HireFlow: AI Candidate Screening and Interview Intelligence CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: screen
    screen_parser = subparsers.add_parser("screen", help="Screen resumes against JD")
    screen_parser.add_argument("--jd", required=True, help="Path to Job Description file (.md, .txt, .pdf, .docx)")
    screen_parser.add_argument("--resumes", nargs="+", required=True, help="Paths to Resume files or glob patterns")
    screen_parser.add_argument("--out", default="output", help="Output directory (default: output)")

    # Command: interview-plan
    plan_parser = subparsers.add_parser("interview-plan", help="View tailored interview plan and probe trees")
    plan_parser.add_argument("--candidate-report", required=True, help="Path to candidate report JSON")

    # Command: evaluate-interview
    eval_parser = subparsers.add_parser("evaluate-interview", help="Audit interview notes against requirements")
    eval_parser.add_argument("--jd", required=True, help="Path to Job Description file")
    eval_parser.add_argument("--candidate", required=True, help="Path to candidate report JSON")
    eval_parser.add_argument("--notes", required=True, help="Path to interviewer notes file")

    # Command: query
    query_parser = subparsers.add_parser("query", help="Query candidate pool in natural language")
    query_parser.add_argument("--pool", default="output", help="Path to pool output directory (default: output)")
    query_parser.add_argument("--prompt", required=True, help="Natural language query prompt")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Start FastAPI REST server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host address")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port number")

    args = parser.parse_args()

    if args.command == "screen":
        # Expand resume glob if directory is passed
        all_resumes = []
        for r_arg in args.resumes:
            p = Path(r_arg)
            if p.is_dir():
                for ext in ["*.pdf", "*.docx", "*.txt", "*.md"]:
                    all_resumes.extend([str(f) for f in p.glob(ext)])
            else:
                all_resumes.append(r_arg)
        run_screen(args.jd, all_resumes, args.out)

    elif args.command == "interview-plan":
        run_interview_plan(args.candidate_report)

    elif args.command == "evaluate-interview":
        run_evaluate_interview(args.jd, args.candidate, args.notes)

    elif args.command == "query":
        run_query(args.pool, args.prompt)

    elif args.command == "serve":
        import uvicorn
        uvicorn.run("hireflow.api.routes:app", host=args.host, port=args.port, reload=True)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
