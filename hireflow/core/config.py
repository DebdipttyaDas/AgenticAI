"""Configuration parameters and settings for HireFlow."""

import os
from pathlib import Path
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # LLM Settings
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    primary_model: str = Field(default_factory=lambda: os.getenv("HIREFLOW_PRIMARY_MODEL", "claude-3-5-sonnet-20241022"))
    fast_model: str = Field(default_factory=lambda: os.getenv("HIREFLOW_FAST_MODEL", "claude-3-5-haiku-20241022"))
    temperature: float = 0.1
    max_tokens: int = 4096

    # Scoring Weights & Thresholds
    must_have_weight: float = 3.0
    nice_to_have_weight: float = 1.0
    tier_1_threshold: float = 85.0
    tier_2_threshold: float = 70.0
    tier_3_threshold: float = 50.0

    # Audit & Gap Detection Thresholds
    career_gap_month_threshold: int = 6
    min_interview_coverage_ratio: float = 75.0

    # Base Directories
    root_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    fixtures_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "fixtures" if (Path(__file__).resolve().parent.parent.parent / "fixtures").exists() else Path("fixtures"))
    output_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "output" if (Path(__file__).resolve().parent.parent.parent / "output").exists() else Path("output"))

    # Server Settings (for Render / local containers)
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))

    # Feature Flags
    anonymize_pii_default: bool = False
    enable_strict_provenance: bool = True


# Global settings singleton
settings = Settings()
