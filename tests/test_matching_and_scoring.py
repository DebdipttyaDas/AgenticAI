"""Unit tests for competency matching, scoring math, and tier grouping."""

import pytest
from hireflow.ingestion.parser import DocumentParser
from hireflow.ingestion.chunker import SemanticChunker
from hireflow.extraction.jd_extractor import JobDescriptionExtractor
from hireflow.extraction.profile_extractor import CandidateProfileExtractor
from hireflow.matching.competency_matcher import CompetencyMatcher
from hireflow.matching.scoring_engine import ScoringEngine
from hireflow.matching.candidate_grouper import CandidateGrouper
from hireflow.core.schemas import CandidateTier, MatchLevel


def test_tier_distribution_across_fixtures():
    jd_text, _ = DocumentParser.parse_file("fixtures/jd_senior_distributed_systems.md")
    jd = JobDescriptionExtractor.extract_from_text(jd_text)

    # Alex (Tier 1)
    text_alex, _ = DocumentParser.parse_file("fixtures/resume_alex_chen.md")
    prof_alex = CandidateProfileExtractor.extract_profile(text_alex, SemanticChunker.chunk_document(text_alex, "alex"), "alex")
    evals_alex = CompetencyMatcher.evaluate_competencies(prof_alex, jd)
    score_alex, _, _, _ = ScoringEngine.calculate_overall_score(evals_alex)
    tier_alex = CandidateGrouper.assign_tier(score_alex, evals_alex, prof_alex)
    assert tier_alex == CandidateTier.TIER_1_SHORTLIST
    assert score_alex >= 85.0

    # Maya (Tier 2)
    text_maya, _ = DocumentParser.parse_file("fixtures/resume_maya_patel.md")
    prof_maya = CandidateProfileExtractor.extract_profile(text_maya, SemanticChunker.chunk_document(text_maya, "maya"), "maya")
    evals_maya = CompetencyMatcher.evaluate_competencies(prof_maya, jd)
    score_maya, _, _, _ = ScoringEngine.calculate_overall_score(evals_maya)
    tier_maya = CandidateGrouper.assign_tier(score_maya, evals_maya, prof_maya)
    assert tier_maya in [CandidateTier.TIER_2_CONTENDER, CandidateTier.TIER_1_SHORTLIST]

    # Taylor (Tier 4)
    text_taylor, _ = DocumentParser.parse_file("fixtures/resume_taylor_smith.md")
    prof_taylor = CandidateProfileExtractor.extract_profile(text_taylor, SemanticChunker.chunk_document(text_taylor, "taylor"), "taylor")
    evals_taylor = CompetencyMatcher.evaluate_competencies(prof_taylor, jd)
    score_taylor, _, _, _ = ScoringEngine.calculate_overall_score(evals_taylor)
    tier_taylor = CandidateGrouper.assign_tier(score_taylor, evals_taylor, prof_taylor)
    assert tier_taylor == CandidateTier.TIER_4_UNMATCHED
    assert score_taylor < 50.0
