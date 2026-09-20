"""FastAPI REST API routes and React Dashboard serving for HireFlow."""

import os
import json
from pathlib import Path
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from hireflow.core.schemas import (
    ScreeningLeaderboard,
    CandidateScreeningReport,
    InterviewEvaluationReport,
    CandidateQueryRequest,
    CandidateQueryResponse,
    JobDescription,
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

app = FastAPI(
    title="HireFlow API & Dashboard",
    description="AI Candidate Screening & Interview Intelligence Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores for runtime
STORE_REPORTS: dict[str, CandidateScreeningReport] = {}
STORE_PROFILES: dict[str, Any] = {}
STORE_JDS: dict[str, JobDescription] = {}


def _resolve_dashboard_path() -> Optional[Path]:
    """Find dashboard.html across local development, Vercel serverless, and Render containers."""
    candidates = [
        Path(__file__).resolve().parent.parent / "static" / "dashboard.html",
        Path(__file__).resolve().parent.parent.parent / "hireflow" / "static" / "dashboard.html",
        Path("hireflow/static/dashboard.html"),
        Path("static/dashboard.html"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _resolve_fixture_path(rel_path: str) -> Path:
    """Resolve fixture file path across differing CWD execution contexts."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / rel_path,
        Path(rel_path),
        settings.fixtures_dir / Path(rel_path).name,
    ]
    for p in candidates:
        if p.exists():
            return p
    return Path(rel_path)


class RawInterviewEvalRequest(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    notes_text: str


@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for Render, Vercel, and uptime monitors."""
    return {
        "status": "healthy",
        "service": "hireflow",
        "version": "1.0.0",
        "active_candidates": len(STORE_REPORTS),
    }


@app.get("/api/v1/pool")
async def get_candidate_pool():
    """Retrieve all current candidates and active job descriptions."""
    active_jd = next(iter(STORE_JDS.values()), None)
    reports = list(STORE_REPORTS.values())
    reports.sort(key=lambda r: r.overall_match_score, reverse=True)

    tier_dist = {}
    for r in reports:
        tier_dist[r.assigned_tier.value] = tier_dist.get(r.assigned_tier.value, 0) + 1

    return {
        "job": active_jd,
        "total_candidates": len(reports),
        "tier_distribution": tier_dist,
        "candidates": reports,
        "profiles": {cid: p.model_dump() for cid, p in STORE_PROFILES.items()},
    }


@app.post("/api/v1/demo/load")
async def load_demo_dataset():
    """One-click loader: ingests 4 test fixture resumes and JD into the runtime store."""
    try:
        jd_file = _resolve_fixture_path("fixtures/jd_senior_distributed_systems.md")
        jd_text, _ = DocumentParser.parse_file(jd_file)
        jd = JobDescriptionExtractor.extract_from_text(jd_text, job_id="job_senior_distributed")
        STORE_JDS[jd.job_id] = jd

        resume_files = [
            ("cand_001", _resolve_fixture_path("fixtures/resume_alex_chen.md")),
            ("cand_002", _resolve_fixture_path("fixtures/resume_maya_patel.md")),
            ("cand_003", _resolve_fixture_path("fixtures/resume_jordan_lee.md")),
            ("cand_004", _resolve_fixture_path("fixtures/resume_taylor_smith.md")),
        ]

        reports = []
        for cid, rpath in resume_files:
            raw_text, _ = DocumentParser.parse_file(rpath)
            chunks = SemanticChunker.chunk_document(raw_text, doc_id=cid)
            profile = CandidateProfileExtractor.extract_profile(raw_text, chunks, candidate_id=cid)
            STORE_PROFILES[cid] = profile

            evals = CompetencyMatcher.evaluate_competencies(profile, jd)
            questions = InterviewQuestionGenerator.generate_interview_plan(profile, jd, evals)
            report = EvaluationReporter.build_screening_report(profile, jd, evals, questions)

            STORE_REPORTS[cid] = report
            reports.append(report)

        reports.sort(key=lambda r: r.overall_match_score, reverse=True)
        return {
            "status": "success",
            "message": f"Successfully loaded demo job '{jd.title}' and {len(reports)} candidate profiles.",
            "candidates_loaded": len(reports),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load demo dataset: {str(e)}")


@app.post("/api/v1/screen", response_model=ScreeningLeaderboard)
async def screen_candidates(
    jd_file: UploadFile = File(...),
    resume_files: List[UploadFile] = File(...),
):
    """Ingest JD and resumes, execute screening, and return leaderboard with reports."""
    try:
        jd_content = (await jd_file.read()).decode("utf-8", errors="replace")
        jd = JobDescriptionExtractor.extract_from_text(jd_content, job_id=jd_file.filename or "job_uploaded")
        STORE_JDS[jd.job_id] = jd

        reports: List[CandidateScreeningReport] = []
        profiles = []

        for idx, resume in enumerate(resume_files):
            cand_id = f"cand_{idx + 1:03d}"
            raw_text = (await resume.read()).decode("utf-8", errors="replace")
            chunks = SemanticChunker.chunk_document(raw_text, doc_id=cand_id)
            profile = CandidateProfileExtractor.extract_profile(raw_text, chunks, candidate_id=cand_id)
            profiles.append(profile)
            STORE_PROFILES[cand_id] = profile

            evaluations = CompetencyMatcher.evaluate_competencies(profile, jd)
            questions = InterviewQuestionGenerator.generate_interview_plan(profile, jd, evaluations)
            report = EvaluationReporter.build_screening_report(profile, jd, evaluations, questions)

            reports.append(report)
            STORE_REPORTS[cand_id] = report

        # Build leaderboard
        reports.sort(key=lambda r: r.overall_match_score, reverse=True)
        tier_dist = {}
        for r in reports:
            tier_dist[r.assigned_tier.value] = tier_dist.get(r.assigned_tier.value, 0) + 1

        leaderboard_entries = []
        for rank, r in enumerate(reports, 1):
            prof = STORE_PROFILES[r.candidate_id]
            must_met = len([e for e in r.competency_evaluations if e.requirement_type.value == "MUST_HAVE" and e.score >= 7.0])
            total_must = len([e for e in r.competency_evaluations if e.requirement_type.value == "MUST_HAVE"])
            leaderboard_entries.append(
                {
                    "rank": rank,
                    "candidate_id": r.candidate_id,
                    "candidate_name": r.candidate_name,
                    "overall_score": r.overall_match_score,
                    "tier": r.assigned_tier,
                    "years_experience": prof.total_years_experience,
                    "must_haves_met": must_met,
                    "total_must_haves": total_must,
                    "top_strengths": r.strengths[:2],
                    "critical_risks": r.risk_factors[:2],
                }
            )

        return ScreeningLeaderboard(
            job_id=jd.job_id,
            job_title=jd.title,
            total_candidates=len(reports),
            tier_distribution=tier_dist,
            leaderboard=leaderboard_entries,
            reports=reports,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/evaluate-interview-raw", response_model=InterviewEvaluationReport)
async def evaluate_interview_raw(request: RawInterviewEvalRequest):
    """Audit raw text interview notes against job requirements."""
    if request.candidate_id not in STORE_REPORTS:
        raise HTTPException(status_code=404, detail="Candidate not found in store. Please screen candidate first.")

    active_jd = STORE_JDS.get(request.job_id) if request.job_id else next(iter(STORE_JDS.values()), None)
    if not active_jd:
        raise HTTPException(status_code=404, detail="No active Job Description found.")

    report = STORE_REPORTS[request.candidate_id]
    claims = NotesAnalyzer.parse_notes(request.notes_text)

    eval_report = CoverageAuditor.audit_interview_performance(
        candidate_id=request.candidate_id,
        candidate_name=report.candidate_name,
        jd=active_jd,
        claims=claims,
    )
    return eval_report


@app.post("/api/v1/evaluate-interview", response_model=InterviewEvaluationReport)
async def evaluate_interview(
    candidate_id: str = Form(...),
    job_id: str = Form(...),
    notes_file: UploadFile = File(...),
):
    """Audit post-interview notes file against job requirements."""
    if candidate_id not in STORE_REPORTS:
        raise HTTPException(status_code=404, detail="Candidate not found in store.")

    active_jd = STORE_JDS.get(job_id) or next(iter(STORE_JDS.values()), None)
    if not active_jd:
        raise HTTPException(status_code=404, detail="Job description not found.")

    report = STORE_REPORTS[candidate_id]
    notes_text = (await notes_file.read()).decode("utf-8", errors="replace")

    claims = NotesAnalyzer.parse_notes(notes_text)
    eval_report = CoverageAuditor.audit_interview_performance(
        candidate_id=candidate_id,
        candidate_name=report.candidate_name,
        jd=active_jd,
        claims=claims,
    )
    return eval_report


@app.post("/api/v1/query", response_model=CandidateQueryResponse)
async def query_candidate_pool(request: CandidateQueryRequest):
    """Natural language query over current candidate pool."""
    reports = list(STORE_REPORTS.values())
    profiles = list(STORE_PROFILES.values())
    if not reports:
        raise HTTPException(status_code=400, detail="Candidate pool is empty. Please load demo or upload resumes first.")

    return NaturalLanguageQueryEngine.execute_query(request, reports, profiles)


@app.get("/api/v1/candidates/{candidate_id}/provenance")
async def get_candidate_provenance(candidate_id: str):
    """Retrieve full immutable audit provenance ledger for candidate."""
    records = provenance_ledger.get_candidate_records(candidate_id)
    return {
        "candidate_id": candidate_id,
        "total_records": len(records),
        "records": records,
    }


@app.get("/api/v1/candidates/{candidate_id}/scorecard.html", response_class=HTMLResponse)
async def get_scorecard_html(candidate_id: str):
    """Render standalone HTML scorecard for candidate."""
    if candidate_id not in STORE_REPORTS:
        raise HTTPException(status_code=404, detail="Candidate scorecard not found.")
    report = STORE_REPORTS[candidate_id]
    return EvaluationReporter.render_html_scorecard(report)


# Serve Full-Stack React + Tailwind CSS Web Dashboard at root /
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the complete interactive React + Tailwind CSS single-page application."""
    dashboard_file = _resolve_dashboard_path()
    if dashboard_file and dashboard_file.exists():
        return dashboard_file.read_text(encoding="utf-8")
    return "<h1>HireFlow API Online. Dashboard file missing.</h1>"
