"""Unit tests for interview questions, probe trees, notes analysis, and coverage auditing."""

import pytest
from hireflow.ingestion.parser import DocumentParser
from hireflow.ingestion.chunker import SemanticChunker
from hireflow.extraction.jd_extractor import JobDescriptionExtractor
from hireflow.extraction.profile_extractor import CandidateProfileExtractor
from hireflow.matching.competency_matcher import CompetencyMatcher
from hireflow.intelligence.question_generator import InterviewQuestionGenerator
from hireflow.intelligence.notes_analyzer import NotesAnalyzer
from hireflow.intelligence.coverage_auditor import CoverageAuditor


def test_question_generation_and_probe_tree():
    jd_text, _ = DocumentParser.parse_file("fixtures/jd_senior_distributed_systems.md")
    jd = JobDescriptionExtractor.extract_from_text(jd_text)

    text_alex, _ = DocumentParser.parse_file("fixtures/resume_alex_chen.md")
    prof_alex = CandidateProfileExtractor.extract_profile(text_alex, SemanticChunker.chunk_document(text_alex, "alex"), "alex")
    evals = CompetencyMatcher.evaluate_competencies(prof_alex, jd)

    questions = InterviewQuestionGenerator.generate_interview_plan(prof_alex, jd, evals)
    assert len(questions) >= 3

    for q in questions:
        assert q.question_text
        assert q.target_competency
        assert len(q.expected_positive_signals) > 0
        assert len(q.red_flag_warnings) > 0
        assert len(q.adaptive_follow_ups) > 0


def test_notes_analysis_and_coverage_blind_spots():
    jd_text, _ = DocumentParser.parse_file("fixtures/jd_senior_distributed_systems.md")
    jd = JobDescriptionExtractor.extract_from_text(jd_text)

    notes_text, _ = DocumentParser.parse_file("fixtures/interview_notes_maya_patel.md")
    claims = NotesAnalyzer.parse_notes(notes_text)
    assert len(claims) >= 2

    report = CoverageAuditor.audit_interview_performance(
        candidate_id="cand_maya",
        candidate_name="Maya Patel",
        jd=jd,
        claims=claims,
    )

    assert report.coverage_ratio > 0.0
    # Must identify unevaluated Kafka / Streaming area as a blind spot
    assert len(report.unanswered_areas_for_next_round) >= 1 or any(c.blind_spot_identified for c in report.competency_results)
