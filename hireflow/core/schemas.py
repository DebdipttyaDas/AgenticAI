"""Pydantic v2 data models and strict schemas for the HireFlow system."""

from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class MatchLevel(str, Enum):
    EXCEEDS = "EXCEEDS"
    MEETS = "MEETS"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    NOT_FOUND = "NOT_FOUND"


class CandidateTier(str, Enum):
    TIER_1_SHORTLIST = "TIER_1_SHORTLIST"
    TIER_2_CONTENDER = "TIER_2_CONTENDER"
    TIER_3_SPECIALIST_GAPPED = "TIER_3_SPECIALIST_GAPPED"
    TIER_4_UNMATCHED = "TIER_4_UNMATCHED"


class ProficiencyLevel(str, Enum):
    NOVICE = "NOVICE"
    INTERMEDIATE = "INTERMEDIATE"
    EXPERT = "EXPERT"


class RequirementType(str, Enum):
    MUST_HAVE = "MUST_HAVE"
    NICE_TO_HAVE = "NICE_TO_HAVE"


class FinalRecommendation(str, Enum):
    STRONG_HIRE = "STRONG_HIRE"
    HIRE = "HIRE"
    INCLINED = "INCLINED"
    DO_NOT_HIRE = "DO_NOT_HIRE"


class AnomalySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# --- Chunk & Provenance Models ---

class DocumentChunk(BaseModel):
    chunk_id: str = Field(description="Unique identifier for chunk e.g. chk_cand1_001")
    doc_id: str = Field(description="Parent document identifier")
    text: str = Field(description="Raw text content of the chunk")
    section: str = Field(default="body", description="Identified resume section (e.g. experience, education)")
    start_char: int = Field(default=0, description="Start character offset in original document")
    end_char: int = Field(default=0, description="End character offset in original document")
    chunk_hash: str = Field(description="SHA256 hash of the chunk text")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProvenanceCitation(BaseModel):
    chunk_id: str = Field(description="Chunk ID where evidence was located")
    verbatim_quote: str = Field(description="Exact snippet quoted from source resume or notes")
    section: str = Field(default="general", description="Document section")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class ProvenanceRecord(BaseModel):
    record_id: str
    candidate_id: str
    insight_type: str  # e.g., SKILL_EXTRACTION, MATCH_SCORE, GAP_FLAG, QUESTION_GEN, RECOMMENDATION
    source_chunk_ids: List[str]
    source_text_excerpts: List[str]
    model_rationale: str
    confidence_score: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --- Resume / Candidate Profile Models ---

class EducationEntry(BaseModel):
    degree: str
    institution: str
    graduation_year: Optional[int] = None
    major: Optional[str] = None
    gpa: Optional[str] = None
    chunk_id: Optional[str] = None


class WorkExperienceEntry(BaseModel):
    company: str
    role: str
    start_date: str  # e.g. "2020-01" or "Jan 2020"
    end_date: str    # e.g. "Present" or "2023-05"
    duration_months: int = 0
    key_achievements: List[str] = Field(default_factory=list)
    technologies_used: List[str] = Field(default_factory=list)
    chunk_ids: List[str] = Field(default_factory=list)


class TechnicalSkill(BaseModel):
    name: str
    category: str = "General"  # e.g. Backend, Frontend, Cloud, DB, ML
    proficiency: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE
    years_of_experience: Optional[float] = None
    verified_in_experience: bool = False
    chunk_ids: List[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    title: str
    description: str
    technologies_used: List[str] = Field(default_factory=list)
    impact_metric: Optional[str] = None
    chunk_ids: List[str] = Field(default_factory=list)


class GapAnomaly(BaseModel):
    anomaly_id: str
    type: str  # CAREER_GAP, MISSING_METRIC, VAGUE_SKILL, TIMELINE_OVERLAP, UNVERIFIED_CLAIM
    description: str
    severity: AnomalySeverity = AnomalySeverity.MEDIUM
    chunk_id: Optional[str] = None
    validation_probe: str = Field(description="Suggested targeted interview probe to clarify this anomaly")


class CandidateProfile(BaseModel):
    candidate_id: str
    raw_document_id: str
    candidate_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    total_years_experience: float = 0.0
    education: List[EducationEntry] = Field(default_factory=list)
    experience: List[WorkExperienceEntry] = Field(default_factory=list)
    skills: List[TechnicalSkill] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    detected_gaps: List[GapAnomaly] = Field(default_factory=list)
    chunks: List[DocumentChunk] = Field(default_factory=list)


# --- Job Description Models ---

class JobRequirement(BaseModel):
    requirement_id: str
    title: str
    description: str
    requirement_type: RequirementType = RequirementType.MUST_HAVE
    weight: int = Field(default=3, ge=1, le=5)
    category: str = "Technical"  # Technical, Architecture, SoftSkill, Leadership, Domain
    keywords: List[str] = Field(default_factory=list)


class JobDescription(BaseModel):
    job_id: str
    title: str
    department: Optional[str] = None
    seniority_level: str = "Senior"
    domain: str = "Software Engineering"
    overview: str
    requirements: List[JobRequirement] = Field(default_factory=list)
    minimum_years_experience: float = 0.0
    preferred_qualifications: List[str] = Field(default_factory=list)


# --- Matching & Scoring Models ---

class CompetencyEvaluation(BaseModel):
    competency_id: str
    competency_name: str
    requirement_type: RequirementType
    weight: int
    match_level: MatchLevel
    score: float = Field(ge=0.0, le=10.0, description="Normalized score 0.0 to 10.0")
    evidence_justification: str
    citations: List[ProvenanceCitation] = Field(default_factory=list)
    detected_gaps: List[str] = Field(default_factory=list)


class TailoredQuestion(BaseModel):
    question_id: str
    target_competency: str
    question_text: str
    resume_anchor: str
    intent: str
    expected_positive_signals: List[str] = Field(default_factory=list)
    red_flag_warnings: List[str] = Field(default_factory=list)
    adaptive_follow_ups: Dict[str, str] = Field(
        default_factory=dict,
        description="Keys: 'if_vague', 'if_overclaimed', 'if_shallow', 'if_strong'"
    )


class CandidateScreeningReport(BaseModel):
    candidate_id: str
    candidate_name: str
    overall_match_score: float = Field(ge=0.0, le=100.0)
    assigned_tier: CandidateTier
    capability_tags: List[str] = Field(default_factory=list)
    executive_summary: str
    competency_evaluations: List[CompetencyEvaluation] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    missing_validations: List[str] = Field(default_factory=list)
    recommended_interview_questions: List[TailoredQuestion] = Field(default_factory=list)
    audit_trail: List[ProvenanceCitation] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --- Interview Notes & Coverage Auditing ---

class InterviewNoteClaim(BaseModel):
    competency_id: Optional[str] = None
    topic: str
    candidate_response_summary: str
    interviewer_rating: str  # STRONG, ACCEPTABLE, WEAK, NOT_EVALUATED
    direct_quote: Optional[str] = None
    is_verified: bool = True


class CompetencyCoverageResult(BaseModel):
    competency_id: str
    competency_name: str
    requirement_type: RequirementType
    was_covered: bool
    rating: str  # STRONG, ACCEPTABLE, WEAK, NOT_COVERED
    score: float  # 0.0 to 10.0
    evidence_summary: str
    blind_spot_identified: bool = False
    recommended_next_round_probe: Optional[str] = None


class InterviewEvaluationReport(BaseModel):
    candidate_id: str
    candidate_name: str
    role_title: str
    coverage_ratio: float = Field(ge=0.0, le=100.0, description="Percentage of required competencies covered")
    final_score: float = Field(ge=0.0, le=100.0)
    recommendation: FinalRecommendation
    executive_verdict: str
    competency_results: List[CompetencyCoverageResult] = Field(default_factory=list)
    evaluated_strengths: List[str] = Field(default_factory=list)
    verified_risks: List[str] = Field(default_factory=list)
    unanswered_areas_for_next_round: List[str] = Field(default_factory=list)
    audit_trail: List[ProvenanceCitation] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --- Query & Leaderboard Models ---

class CandidateFilter(BaseModel):
    min_score: Optional[float] = None
    tiers: Optional[List[CandidateTier]] = None
    required_skills: Optional[List[str]] = None
    min_years_experience: Optional[float] = None
    capability_tags: Optional[List[str]] = None


class CandidateQueryRequest(BaseModel):
    query: str
    filters: Optional[CandidateFilter] = None
    top_k: int = 5


class CandidateMatchSummary(BaseModel):
    candidate_id: str
    candidate_name: str
    match_score: float
    tier: CandidateTier
    relevance_explanation: str
    supporting_citations: List[ProvenanceCitation] = Field(default_factory=list)


class CandidateQueryResponse(BaseModel):
    query: str
    synthesized_answer: str
    matched_candidates: List[CandidateMatchSummary] = Field(default_factory=list)


class LeaderboardEntry(BaseModel):
    rank: int
    candidate_id: str
    candidate_name: str
    overall_score: float
    tier: CandidateTier
    years_experience: float
    must_haves_met: int
    total_must_haves: int
    top_strengths: List[str]
    critical_risks: List[str]


class ScreeningLeaderboard(BaseModel):
    job_id: str
    job_title: str
    total_candidates: int
    tier_distribution: Dict[str, int]
    leaderboard: List[LeaderboardEntry]
    reports: List[CandidateScreeningReport]
