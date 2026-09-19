"""Unit tests for profile extraction, JD parsing, and anomaly gap detection."""

import pytest
from hireflow.ingestion.parser import DocumentParser
from hireflow.ingestion.chunker import SemanticChunker
from hireflow.extraction.jd_extractor import JobDescriptionExtractor
from hireflow.extraction.profile_extractor import CandidateProfileExtractor
from hireflow.extraction.gap_detector import GapDetector
from hireflow.core.schemas import RequirementType


def test_jd_extraction():
    jd_text, _ = DocumentParser.parse_file("fixtures/jd_senior_distributed_systems.md")
    jd = JobDescriptionExtractor.extract_from_text(jd_text)

    assert len(jd.requirements) >= 3
    must_haves = [r for r in jd.requirements if r.requirement_type == RequirementType.MUST_HAVE]
    assert len(must_haves) >= 1
    assert any("distributed" in r.title.lower() or "architecture" in r.title.lower() for r in jd.requirements)


def test_profile_extraction_alex():
    text, _ = DocumentParser.parse_file("fixtures/resume_alex_chen.md")
    chunks = SemanticChunker.chunk_document(text, doc_id="cand_alex")
    profile = CandidateProfileExtractor.extract_profile(text, chunks, candidate_id="cand_alex")

    assert profile.candidate_name == "Alex Chen"
    assert profile.total_years_experience >= 7.0
    assert len(profile.experience) >= 2
    assert any(s.name.lower() in ["go", "golang"] for s in profile.skills)


def test_gap_detection_maya():
    text, _ = DocumentParser.parse_file("fixtures/resume_maya_patel.md")
    chunks = SemanticChunker.chunk_document(text, doc_id="cand_maya")
    profile = CandidateProfileExtractor.extract_profile(text, chunks, candidate_id="cand_maya")

    # Maya has a gap between Dec 2021 and Sep 2022 (9 months)
    gap_anomalies = [g for g in profile.detected_gaps if g.type == "CAREER_GAP"]
    assert len(gap_anomalies) >= 1
    assert "career gap" in gap_anomalies[0].description.lower()
    assert len(gap_anomalies[0].validation_probe) > 10
