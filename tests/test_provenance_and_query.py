"""Unit tests for provenance ledger, citations, and natural language queries."""

import pytest
from hireflow.core.provenance import provenance_ledger
from hireflow.ingestion.parser import DocumentParser
from hireflow.ingestion.chunker import SemanticChunker
from hireflow.extraction.jd_extractor import JobDescriptionExtractor
from hireflow.extraction.profile_extractor import CandidateProfileExtractor
from hireflow.matching.competency_matcher import CompetencyMatcher
from hireflow.intelligence.question_generator import InterviewQuestionGenerator
from hireflow.intelligence.evaluation_reporter import EvaluationReporter
from hireflow.query.nl_query_engine import NaturalLanguageQueryEngine
from hireflow.core.schemas import CandidateQueryRequest


def test_provenance_ledger_and_citations():
    text_alex, _ = DocumentParser.parse_file("fixtures/resume_alex_chen.md")
    chunks = SemanticChunker.chunk_document(text_alex, "alex_prov")
    prof_alex = CandidateProfileExtractor.extract_profile(text_alex, chunks, "alex_prov")

    jd_text, _ = DocumentParser.parse_file("fixtures/jd_senior_distributed_systems.md")
    jd = JobDescriptionExtractor.extract_from_text(jd_text)

    evals = CompetencyMatcher.evaluate_competencies(prof_alex, jd)
    questions = InterviewQuestionGenerator.generate_interview_plan(prof_alex, jd, evals)
    report = EvaluationReporter.build_screening_report(prof_alex, jd, evals, questions)

    # Verify citations in report
    verification = provenance_ledger.verify_citations(report.audit_trail)
    assert verification["total_citations"] > 0
    assert verification["verification_rate"] >= 80.0

    # Verify audit markdown rendering
    audit_md = provenance_ledger.export_audit_markdown("alex_prov")
    assert "alex_prov" in audit_md
    assert "Audit Provenance Trail" in audit_md


def test_natural_language_queries():
    jd_text, _ = DocumentParser.parse_file("fixtures/jd_senior_distributed_systems.md")
    jd = JobDescriptionExtractor.extract_from_text(jd_text)

    profiles = []
    reports = []
    for fpath, cid in [("fixtures/resume_alex_chen.md", "alex"), ("fixtures/resume_taylor_smith.md", "taylor")]:
        t, _ = DocumentParser.parse_file(fpath)
        c = SemanticChunker.chunk_document(t, cid)
        p = CandidateProfileExtractor.extract_profile(t, c, cid)
        e = CompetencyMatcher.evaluate_competencies(p, jd)
        q = InterviewQuestionGenerator.generate_interview_plan(p, jd, e)
        r = EvaluationReporter.build_screening_report(p, jd, e, q)
        profiles.append(p)
        reports.append(r)

    req = CandidateQueryRequest(query="Find candidates with experience in Go and distributed systems")
    resp = NaturalLanguageQueryEngine.execute_query(req, reports, profiles)
    assert len(resp.matched_candidates) >= 1
    assert resp.matched_candidates[0].candidate_name == "Alex Chen"
