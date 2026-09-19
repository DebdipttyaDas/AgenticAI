"""Natural language query engine over the processed candidate pool."""

import re
from typing import List, Optional
from hireflow.core.schemas import (
    CandidateScreeningReport,
    CandidateProfile,
    CandidateQueryRequest,
    CandidateQueryResponse,
    CandidateMatchSummary,
    ProvenanceCitation,
)
from hireflow.core.llm_client import llm_client
from hireflow.core.provenance import provenance_ledger


class NaturalLanguageQueryEngine:
    """Answers complex recruiter questions across candidates with verifiable evidence citations."""

    @classmethod
    def execute_query(
        cls,
        request: CandidateQueryRequest,
        reports: List[CandidateScreeningReport],
        profiles: List[CandidateProfile],
    ) -> CandidateQueryResponse:
        """Process natural language query and synthesize attributed response."""
        profile_map = {p.candidate_id: p for p in profiles}
        query_lower = request.query.lower()

        # 1. If LLM is live, utilize Claude for synthesis
        if llm_client.is_live:
            context_blocks = []
            for rep in reports:
                prof = profile_map.get(rep.candidate_id)
                prof_summary = f"Candidate: {rep.candidate_name} (ID: {rep.candidate_id}, Score: {rep.overall_match_score}%, Tier: {rep.assigned_tier.value}, Yrs Exp: {prof.total_years_experience if prof else 'N/A'})\n"
                prof_summary += f"Tags: {', '.join(rep.capability_tags)}\n"
                prof_summary += f"Strengths: {'; '.join(rep.strengths)}\n"
                prof_summary += f"Risks: {'; '.join(rep.risk_factors)}\n"
                context_blocks.append(prof_summary)

            prompt = (
                f"User Question: {request.query}\n\n"
                f"Candidate Pool Data:\n{'---'.join(context_blocks)}\n\n"
                f"Provide a clear, direct answer to the user's question citing specific candidate names, scores, and qualifications."
            )
            synthesized = llm_client.complete(prompt=prompt, system="You are an expert talent recruiter and intelligence assistant.")
            if synthesized:
                # Rank candidates by relevance
                matched_summaries = cls._rank_candidates_for_query(query_lower, reports, profile_map)
                return CandidateQueryResponse(
                    query=request.query,
                    synthesized_answer=synthesized,
                    matched_candidates=matched_summaries[: request.top_k],
                )

        # 2. Deterministic heuristic search & synthesis
        matched_summaries = cls._rank_candidates_for_query(query_lower, reports, profile_map)
        top_candidates = matched_summaries[: request.top_k]

        if not top_candidates:
            ans = f"No candidates in the pool directly matched the criteria specified in: \"{request.query}\"."
        else:
            cand_names = ", ".join([f"{c.candidate_name} ({c.match_score:.1f}%)" for c in top_candidates])
            ans = (
                f"Found {len(top_candidates)} matching candidate(s) for your query: {cand_names}. "
                f"Top recommendation is {top_candidates[0].candidate_name} based on strong alignment with requested criteria."
            )

        return CandidateQueryResponse(
            query=request.query,
            synthesized_answer=ans,
            matched_candidates=top_candidates,
        )

    @classmethod
    def _rank_candidates_for_query(
        cls,
        query: str,
        reports: List[CandidateScreeningReport],
        profile_map: dict,
    ) -> List[CandidateMatchSummary]:
        results = []
        stop_words = {"the", "and", "with", "for", "who", "find", "which", "show", "get", "list", "candidates", "candidate", "engineer", "engineers", "architect", "architects"}
        tokens = [t.lower() for t in re.findall(r"\b[A-Za-z0-9\+#\.]+\b", query) if (len(t) >= 2 or t.lower() in ["c", "r"]) and t.lower() not in stop_words]

        # Check for numeric years constraint (e.g. "4 years", ">5 years")
        years_match = re.search(r"(\d+)\+?\s*years", query)
        min_years = float(years_match.group(1)) if years_match else 0.0

        for rep in reports:
            prof = profile_map.get(rep.candidate_id)
            if not prof:
                continue

            if min_years > 0 and prof.total_years_experience < min_years:
                continue

            # Calculate match score based on token hits in profile chunks and skills
            hits = []
            combined_text = f"{prof.candidate_name} {prof.summary or ''} {' '.join([s.name for s in prof.skills])} {' '.join(rep.capability_tags)}".lower()

            for chunk in prof.chunks:
                chunk_lower = chunk.text.lower()
                for tok in tokens:
                    if tok in chunk_lower or tok in combined_text:
                        hits.append((tok, chunk))

            if hits or not tokens:
                unique_hits = {h[0] for h in hits}
                relevance_score = rep.overall_match_score + len(unique_hits) * 5.0

                citations: List[ProvenanceCitation] = []
                for _, chunk in hits[:2]:
                    citations.append(
                        provenance_ledger.build_citation(
                            chunk_id=chunk.chunk_id,
                            verbatim_quote=chunk.text[:100],
                            section=chunk.section,
                        )
                    )

                hit_terms = list(unique_hits)[:4] if unique_hits else ["overall profile"]
                explanation = (
                    f"Matches query criteria ({', '.join(hit_terms)}) with {prof.total_years_experience} "
                    f"years of experience and overall score of {rep.overall_match_score:.1f}%."
                )

                results.append(
                    CandidateMatchSummary(
                        candidate_id=rep.candidate_id,
                        candidate_name=rep.candidate_name,
                        match_score=rep.overall_match_score,
                        tier=rep.assigned_tier,
                        relevance_explanation=explanation,
                        supporting_citations=citations,
                    )
                )

        results.sort(key=lambda x: x.match_score, reverse=True)
        return results
