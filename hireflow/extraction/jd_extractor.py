"""Job description parser and competency requirement extractor."""

import re
from typing import List
from hireflow.core.schemas import JobDescription, JobRequirement, RequirementType
from hireflow.core.llm_client import llm_client


class JobDescriptionExtractor:
    """Extracts structured requirements and competency weights from job descriptions."""

    @classmethod
    def extract_from_text(cls, text: str, job_id: str = "job_001") -> JobDescription:
        """Extract structured JobDescription using LLM or structured heuristic fallback."""
        # 1. Try LLM extraction if available
        if llm_client.is_live:
            prompt = (
                f"Extract a structured JobDescription model from the following text:\n\n{text}"
            )
            result = llm_client.generate_structured(prompt, JobDescription, system="You are an expert technical recruiter.")
            if result:
                return result

        # 2. Deterministic heuristic extraction
        return cls._heuristic_extract(text, job_id)

    @classmethod
    def _heuristic_extract(cls, text: str, job_id: str) -> JobDescription:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = "Senior Software Engineer"
        for line in lines[:5]:
            if any(k in line.lower() for k in ["engineer", "developer", "architect", "lead", "manager"]):
                title = re.sub(r"^[#\*\s]+", "", line).strip()
                break

        overview_lines = []
        requirements: List[JobRequirement] = []
        is_in_must_have = False
        is_in_nice_have = False
        req_counter = 1

        for line in lines:
            lower = line.lower()
            if any(k in lower for k in ["nice to have", "preferred", "bonus", "plus", "desired"]):
                is_in_must_have = False
                is_in_nice_have = True
                continue
            elif any(k in lower for k in ["must have", "must-have", "core requirement", "minimum qualification", "what you'll need", "requirements"]):
                is_in_must_have = True
                is_in_nice_have = False
                continue
            elif any(k in lower for k in ["benefits", "about us", "compensation", "perks"]):
                is_in_must_have = False
                is_in_nice_have = False
                continue

            if (is_in_must_have or is_in_nice_have) and line.startswith(("-", "*", "•", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
                clean_req = re.sub(r"^[\-\*•\d\.\+\s]+", "", line).strip()
                if len(clean_req) > 10:
                    req_type = RequirementType.MUST_HAVE if is_in_must_have else RequirementType.NICE_TO_HAVE
                    weight = 4 if req_type == RequirementType.MUST_HAVE else 2

                    # Determine category and clean title
                    cat = "Technical"
                    clean_lower = clean_req.lower()
                    if "grpc" in clean_lower or "protocol" in clean_lower or "tracing" in clean_lower or "opentelemetry" in clean_lower:
                        cat = "Technical"
                        req_title = "High-Performance Protocols & Distributed Tracing"
                    elif "distributed" in clean_lower or "architecture" in clean_lower or "concurrency" in clean_lower:
                        cat = "Architecture"
                        req_title = "Distributed Systems & Backend Architecture"
                    elif "kubernetes" in clean_lower or "docker" in clean_lower or "cloud" in clean_lower or "aws" in clean_lower:
                        cat = "Cloud & Infrastructure"
                        req_title = "Cloud Infrastructure & Container Orchestration"
                    elif "microservice" in clean_lower or "database" in clean_lower or "postgresql" in clean_lower or "redis" in clean_lower or "resilient" in clean_lower:
                        cat = "Architecture"
                        req_title = "Resilient Microservices & Database Schema Design"
                    elif "mentor" in clean_lower or "lead" in clean_lower or "review" in clean_lower:
                        cat = "Leadership"
                        req_title = "Technical Leadership & System Design Reviews"
                    elif "kafka" in clean_lower or "streaming" in clean_lower or "event" in clean_lower:
                        cat = "Streaming & Data"
                        req_title = "Event-Driven & Streaming Architecture"
                    elif "open-source" in clean_lower or "tooling" in clean_lower:
                        cat = "Domain"
                        req_title = "Open-Source & Infrastructure Contributions"
                    else:
                        req_title = clean_req[:50] + ("..." if len(clean_req) > 50 else "")

                    stop_words = {"and", "with", "for", "the", "experience", "years", "using", "maintaining", "designing", "track", "record", "prior", "handling", "what", "need"}
                    all_tokens = [w for w in re.findall(r"\b[A-Za-z0-9\+#\.]+\b", clean_req) if len(w) > 1 and w.lower() not in stop_words]

                    # Prioritize key technical terms
                    tech_keywords = [w for w in all_tokens if any(k in w.lower() for k in ["distribut", "python", "go", "rust", "kuber", "docker", "aws", "gcp", "microservice", "postgres", "redis", "schema", "mentor", "lead", "kafka", "rabbit", "grpc", "trace", "open-source"])]
                    other_keywords = [w for w in all_tokens if w not in tech_keywords]
                    combined_kws = (tech_keywords + other_keywords)[:8]

                    requirements.append(
                        JobRequirement(
                            requirement_id=f"req_{req_counter:03d}",
                            title=req_title,
                            description=clean_req,
                            requirement_type=req_type,
                            weight=weight,
                            category=cat,
                            keywords=combined_kws,
                        )
                    )
                    req_counter += 1
            else:
                if not is_in_must_have and not is_in_nice_have:
                    overview_lines.append(line)

        # Fallback requirements if none parsed
        if not requirements:
            requirements = [
                JobRequirement(
                    requirement_id="req_001",
                    title="Distributed Systems & Backend Architecture",
                    description="5+ years of experience designing and operating distributed, high-concurrency backend services.",
                    requirement_type=RequirementType.MUST_HAVE,
                    weight=5,
                    category="Architecture",
                    keywords=["Distributed", "Backend", "Concurrency", "Architecture"],
                ),
                JobRequirement(
                    requirement_id="req_002",
                    title="Cloud & Container Orchestration",
                    description="Deep hands-on experience with Kubernetes, Docker, and AWS or GCP.",
                    requirement_type=RequirementType.MUST_HAVE,
                    weight=4,
                    category="Cloud & Infrastructure",
                    keywords=["Kubernetes", "Docker", "AWS", "Cloud"],
                ),
                JobRequirement(
                    requirement_id="req_003",
                    title="Data Streaming & Event-Driven Pipelines",
                    description="Experience building event-driven systems with Kafka, RabbitMQ, or similar stream processing platforms.",
                    requirement_type=RequirementType.NICE_TO_HAVE,
                    weight=3,
                    category="Technical",
                    keywords=["Kafka", "Streaming", "Event-Driven"],
                ),
            ]

        overview = "\n".join(overview_lines[:4]) if overview_lines else "Exciting software engineering role."
        return JobDescription(
            job_id=job_id,
            title=title,
            seniority_level="Senior" if "senior" in title.lower() or "lead" in title.lower() else "Mid-Level",
            domain="Distributed Systems & Cloud",
            overview=overview,
            requirements=requirements,
            minimum_years_experience=5.0 if "senior" in title.lower() else 3.0,
        )
