"""Unit tests for document parsing, chunking, and normalization."""

import pytest
from pathlib import Path
from hireflow.ingestion.parser import DocumentParser
from hireflow.ingestion.chunker import SemanticChunker
from hireflow.ingestion.normalizer import DocumentNormalizer


def test_markdown_parsing():
    text, meta = DocumentParser.parse_file("fixtures/resume_alex_chen.md")
    assert "Alex Chen" in text
    assert meta["extension"] == ".md"
    assert meta["size_bytes"] > 100


def test_semantic_chunker():
    text, _ = DocumentParser.parse_file("fixtures/resume_alex_chen.md")
    chunks = SemanticChunker.chunk_document(text, doc_id="cand_test")
    assert len(chunks) >= 3
    for c in chunks:
        assert c.chunk_id.startswith("chk_cand_test_")
        assert c.start_char >= 0
        assert c.end_char > c.start_char
        assert len(c.chunk_hash) == 16
        assert c.section in ["summary", "experience", "education", "skills", "projects", "certifications"]


def test_date_range_parsing():
    start, end, dur = DocumentNormalizer.parse_date_range("Jan 2020 - Dec 2022")
    assert start == "2020-01"
    assert end == "2022-12"
    assert dur == 35 or dur == 36

    start_pres, end_pres, dur_pres = DocumentNormalizer.parse_date_range("2021 - Present")
    assert start_pres == "2021-01"
    assert end_pres == "Present"
    assert dur_pres >= 36


def test_contact_extraction_and_anonymization():
    sample = "John Doe\nEmail: john.doe@example.com\nPhone: (555) 123-4567\nSummary of experience"
    name, email, phone = DocumentNormalizer.extract_contact_info(sample)
    assert name == "John Doe"
    assert email == "john.doe@example.com"
    assert phone == "(555) 123-4567"

    anonymized = DocumentNormalizer.anonymize_profile(sample, candidate_id="cand_999")
    assert "john.doe@example.com" not in anonymized
    assert "[EMAIL_REDACTED]" in anonymized
    assert "[PHONE_REDACTED]" in anonymized
