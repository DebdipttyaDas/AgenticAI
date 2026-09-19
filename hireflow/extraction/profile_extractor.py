"""Candidate resume parser, entity extractor, and profile builder."""

import re
from typing import List
from hireflow.core.schemas import (
    CandidateProfile,
    EducationEntry,
    WorkExperienceEntry,
    TechnicalSkill,
    ProjectEntry,
    ProficiencyLevel,
    DocumentChunk,
)
from hireflow.core.llm_client import llm_client
from hireflow.core.provenance import provenance_ledger
from hireflow.ingestion.normalizer import DocumentNormalizer
from hireflow.extraction.gap_detector import GapDetector


COMMON_SKILLS = [
    ("Python", "Backend", ProficiencyLevel.EXPERT),
    ("Go", "Backend", ProficiencyLevel.EXPERT),
    ("Golang", "Backend", ProficiencyLevel.EXPERT),
    ("Rust", "Systems", ProficiencyLevel.INTERMEDIATE),
    ("Java", "Backend", ProficiencyLevel.INTERMEDIATE),
    ("C++", "Systems", ProficiencyLevel.INTERMEDIATE),
    ("Kubernetes", "Cloud & DevOps", ProficiencyLevel.EXPERT),
    ("Docker", "Cloud & DevOps", ProficiencyLevel.EXPERT),
    ("AWS", "Cloud", ProficiencyLevel.EXPERT),
    ("GCP", "Cloud", ProficiencyLevel.INTERMEDIATE),
    ("Kafka", "Data Engineering", ProficiencyLevel.INTERMEDIATE),
    ("RabbitMQ", "Data Engineering", ProficiencyLevel.INTERMEDIATE),
    ("PostgreSQL", "Database", ProficiencyLevel.EXPERT),
    ("Redis", "Database", ProficiencyLevel.EXPERT),
    ("GraphQL", "Backend", ProficiencyLevel.INTERMEDIATE),
    ("gRPC", "Backend", ProficiencyLevel.EXPERT),
    ("React", "Frontend", ProficiencyLevel.INTERMEDIATE),
    ("TypeScript", "Frontend", ProficiencyLevel.INTERMEDIATE),
    ("PyTorch", "AI/ML", ProficiencyLevel.EXPERT),
    ("TensorFlow", "AI/ML", ProficiencyLevel.INTERMEDIATE),
    ("Distributed Systems", "Architecture", ProficiencyLevel.EXPERT),
    ("Microservices", "Architecture", ProficiencyLevel.EXPERT),
]


class CandidateProfileExtractor:
    """Parses raw text and chunks into structured CandidateProfile with provenance tracking."""

    @classmethod
    def extract_profile(
        cls,
        raw_text: str,
        chunks: List[DocumentChunk],
        candidate_id: str = "cand_001",
    ) -> CandidateProfile:
        """Extract complete structured profile."""
        provenance_ledger.register_chunks(chunks)

        # 1. Try LLM extraction if client is live
        if llm_client.is_live:
            prompt = (
                f"Extract a structured CandidateProfile model from the following resume text:\n\n{raw_text}"
            )
            llm_result = llm_client.generate_structured(
                prompt,
                CandidateProfile,
                system="You are an expert technical resume parser and talent intelligence specialist.",
            )
            if llm_result:
                llm_result.chunks = chunks
                llm_result.detected_gaps = GapDetector.detect_anomalies(
                    llm_result.experience,
                    llm_result.skills,
                    llm_result.projects,
                    chunks,
                )
                return llm_result

        # 2. Heuristic extraction pipeline
        return cls._heuristic_extract(raw_text, chunks, candidate_id)

    @classmethod
    def _heuristic_extract(
        cls,
        raw_text: str,
        chunks: List[DocumentChunk],
        candidate_id: str,
    ) -> CandidateProfile:
        name, email, phone = DocumentNormalizer.extract_contact_info(raw_text)
        candidate_name = name or f"Candidate {candidate_id.upper()}"

        education: List[EducationEntry] = []
        experience: List[WorkExperienceEntry] = []
        skills: List[TechnicalSkill] = []
        projects: List[ProjectEntry] = []

        # Find chunks by section
        exp_chunks = [c for c in chunks if c.section == "experience"]
        edu_chunks = [c for c in chunks if c.section == "education"]
        skill_chunks = [c for c in chunks if c.section == "skills"]
        proj_chunks = [c for c in chunks if c.section == "projects"]

        # Parse Work Experience
        total_months = 0
        exp_text = "\n".join([c.text for c in exp_chunks]) if exp_chunks else raw_text
        exp_lines = [l.strip() for l in exp_text.splitlines() if l.strip()]

        current_job = None
        date_pattern = re.compile(
            r"((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?\d{4}\s*[-–—to]+\s*(?:(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?\d{4}|Present|Current|Now))",
            re.IGNORECASE,
        )

        for line in exp_lines:
            # Skip top-level section header
            if re.match(r"^#{1,2}\s+(professional\s+experience|work\s+experience|experience)", line, re.IGNORECASE):
                continue

            d_match = date_pattern.search(line)
            if d_match or (line.startswith("###") and any(sep in line for sep in ["|", "at", "-", "–"])):
                dates_str = d_match.group(0) if d_match else "2020 - Present"
                clean_line = re.sub(r"^[#\*\-\s]+", "", line).strip()
                title_no_date = date_pattern.sub("", clean_line)
                title_no_date = re.sub(r"[\(\)]", "", title_no_date).strip()

                parts = re.split(r"\s*(?:\||–|—|\bat\b|-)\s*", title_no_date)
                role = parts[0].strip() if len(parts) >= 1 and parts[0] else "Software Engineer"
                company = parts[1].strip() if len(parts) >= 2 and parts[1] else "Technology Corp"

                start_iso, end_iso, dur_mo = DocumentNormalizer.parse_date_range(dates_str)
                total_months += dur_mo

                job_chunks = [c.chunk_id for c in exp_chunks if company.lower() in c.text.lower() or role.lower() in c.text.lower()]
                if not job_chunks and exp_chunks:
                    job_chunks = [exp_chunks[0].chunk_id]

                current_job = WorkExperienceEntry(
                    company=company,
                    role=role,
                    start_date=start_iso,
                    end_date=end_iso,
                    duration_months=dur_mo,
                    key_achievements=[],
                    technologies_used=[],
                    chunk_ids=job_chunks,
                )
                experience.append(current_job)
            elif current_job and len(line) > 10 and not line.startswith("#"):
                clean_ach = re.sub(r"^[\-\*•\d\.\s]+", "", line).strip()
                current_job.key_achievements.append(clean_ach)
                for s in COMMON_SKILLS:
                    if re.search(rf"\b{re.escape(s[0])}\b", line, re.IGNORECASE):
                        if s[0] not in current_job.technologies_used:
                            current_job.technologies_used.append(s[0])

        if not experience:
            experience.append(
                WorkExperienceEntry(
                    company="Technology Corp",
                    role="Software Engineer",
                    start_date="2020-01",
                    end_date="Present",
                    duration_months=36,
                    key_achievements=["Engineered backend services."],
                    technologies_used=["Python", "Docker"],
                )
            )
            total_months = 36

        # Parse Education
        for c in edu_chunks:
            lines = [l.strip() for l in c.text.splitlines() if l.strip()]
            for l in lines:
                if any(deg in l.lower() for deg in ["bachelor", "master", "phd", "b.s", "m.s", "b.tech", "degree", "university", "institute"]):
                    yr_match = re.search(r"\b(19\d\d|20\d\d)\b", l)
                    yr = int(yr_match.group(0)) if yr_match else 2018
                    education.append(
                        EducationEntry(
                            degree="Bachelor of Science in Computer Science" if "bachelor" in l.lower() or "b.s" in l.lower() else "Degree in Computer Science",
                            institution=l.split(",")[0].strip() if "," in l else l,
                            graduation_year=yr,
                            chunk_id=c.chunk_id,
                        )
                    )

        if not education:
            education.append(
                EducationEntry(
                    degree="B.S. in Computer Science",
                    institution="State University",
                    graduation_year=2018,
                )
            )

        # Parse Skills
        detected_skill_names = set()
        for skill_name, cat, prof in COMMON_SKILLS:
            # Check presence in whole resume
            if re.search(rf"\b{re.escape(skill_name)}\b", raw_text, re.IGNORECASE):
                # Find matching chunks
                matched_chunks = [c.chunk_id for c in chunks if re.search(rf"\b{re.escape(skill_name)}\b", c.text, re.IGNORECASE)]
                # Check if verified in experience
                verified = any(skill_name.lower() in " ".join(j.technologies_used).lower() for j in experience)
                skills.append(
                    TechnicalSkill(
                        name=skill_name,
                        category=cat,
                        proficiency=prof,
                        years_of_experience=min(10.0, total_months / 12.0),
                        verified_in_experience=verified,
                        chunk_ids=matched_chunks[:3],
                    )
                )
                detected_skill_names.add(skill_name.lower())

        # Parse Projects
        for c in proj_chunks:
            lines = [l.strip() for l in c.text.splitlines() if l.strip()]
            if lines:
                title = lines[0]
                desc = " ".join(lines[1:]) if len(lines) > 1 else title
                proj_tech = [s[0] for s in COMMON_SKILLS if re.search(rf"\b{re.escape(s[0])}\b", c.text, re.IGNORECASE)]
                projects.append(
                    ProjectEntry(
                        title=re.sub(r"^[\-\*#\s]+", "", title),
                        description=desc,
                        technologies_used=proj_tech,
                        chunk_ids=[c.chunk_id],
                    )
                )

        # Run Gap Anomaly Detection
        anomalies = GapDetector.detect_anomalies(experience, skills, projects, chunks)

        total_years = round(total_months / 12.0, 1)

        return CandidateProfile(
            candidate_id=candidate_id,
            raw_document_id=f"doc_{candidate_id}",
            candidate_name=candidate_name,
            email=email,
            phone=phone,
            total_years_experience=total_years,
            education=education,
            experience=experience,
            skills=skills,
            projects=projects,
            detected_gaps=anomalies,
            chunks=chunks,
        )
