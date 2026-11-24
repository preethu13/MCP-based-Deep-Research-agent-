"""Unit tests for relevance filtering, acronym collisions, grounding, and citation mapping."""

from __future__ import annotations

import pytest
from src.tools.search import (
    RELEVANCE_THRESHOLD,
    clean_search_query,
    is_paper_relevant,
    refine_search_queries,
    score_paper_relevance,
)
from src.agent.nodes.synthesizer import synthesizer_node
from src.agent.state import AgentDeps
from unittest.mock import MagicMock
from tests.fakes import FakeLLM


def test_unrelated_paper_rejection():
    """Unrelated papers must score below threshold and be rejected."""
    query = "Context Rot in Large Language Models"
    unrelated_papers = [
        {
            "title": "On the creativity of large language models",
            "abstract": "Large language models are revolutionizing several areas of Artificial Intelligence...",
        },
        {
            "title": "Managing LLM Bias in Investing: From Detection to Mitigation",
            "abstract": "Financial advisors using large language models must manage bias in investing...",
        },
        {
            "title": "SafetyBench: Evaluating the Safety of Large Language Models",
            "abstract": "We evaluate safety concerns in large language models across multiple benchmarks...",
        },
    ]
    for p in unrelated_papers:
        assert not is_paper_relevant(p, query, threshold=RELEVANCE_THRESHOLD)
        assert score_paper_relevance(p, query) < RELEVANCE_THRESHOLD


def test_acronym_collision_handling():
    """Acronym collisions (RoT, RAG1/2, ADHD Attention) must be penalized and rejected."""
    # RoT collisions vs Context Rot
    q_rot = "Context Rot in Large Language Models"
    rot_collisions = [
        {
            "title": "RoT: Enhancing Large Language Models with Reflection on Search Trees",
            "abstract": "We propose Reflection on Search Trees (RoT) to enhance reasoning in language models...",
        },
        {
            "title": "Concept-ROT: Poisoning Concepts in Large Language Models with Model Editing",
            "abstract": "We propose a trojan poisoning attack on weights using model editing...",
        },
        {
            "title": "GENERATIVE-AI AS RESOURCE AGAINST THE 'BRAIN ROT'",
            "abstract": "Brain rot is a slang term describing low quality online media...",
        },
    ]
    for p in rot_collisions:
        assert not is_paper_relevant(p, q_rot, threshold=RELEVANCE_THRESHOLD)

    # RAG biological gene collision vs Retrieval-Augmented Generation
    q_rag = "Retrieval-Augmented Generation (RAG)"
    bio_rag = {
        "title": "Role of RAG1 and RAG2 genes in B-cell antigen receptor gene rearrangement",
        "abstract": "The recombination-activating genes RAG1 and RAG2 mediate V(D)J recombination in developing lymphocytes...",
    }
    assert not is_paper_relevant(bio_rag, q_rag, threshold=RELEVANCE_THRESHOLD)

    # ADHD attention vs Transformer Attention Mechanism
    q_att = "Transformer Attention Mechanism"
    adhd_paper = {
        "title": "Attention deficit hyperactivity disorder in primary school children: A behavioral study",
        "abstract": "ADHD causes severe attention deficits in pediatric patients requiring clinical diagnosis...",
    }
    assert not is_paper_relevant(adhd_paper, q_att, threshold=RELEVANCE_THRESHOLD)

    # Biological vector collision vs Vector Database Retrieval
    q_vdb = "Vector Database Retrieval"
    mosquito_paper = {
        "title": "Aedes aegypti mosquito vector control and transmission of dengue virus",
        "abstract": "Vector-borne viral infections spread by mosquito vectors can be controlled using insecticides...",
    }
    assert not is_paper_relevant(mosquito_paper, q_vdb, threshold=RELEVANCE_THRESHOLD)


def test_legitimate_paper_acceptance():
    """Genuinely relevant papers discussing the searched concept must pass."""
    query = "Context Rot in Large Language Models"
    legit_papers = [
        {
            "title": "Diagnosing and Mitigating Context Rot in Long-horizon Search",
            "abstract": "Extensive context has become the norm as Large Language Models are deployed in long-horizon search tasks. The concern that increasing context length degrades performance (context rot)...",
        },
        {
            "title": "Classifier Context Rot: Monitor Performance Degrades with Context Length",
            "abstract": "Monitoring coding agents for dangerous behavior using language models requires classifying transcripts that exceed context limits. We study classifier context rot...",
        },
    ]
    for p in legit_papers:
        assert is_paper_relevant(p, query, threshold=RELEVANCE_THRESHOLD)
        assert score_paper_relevance(p, query) >= RELEVANCE_THRESHOLD


def test_empty_search_results_handling():
    """When research contains no relevant sources, synthesizer produces explicit notice with no citations."""
    state = {
        "query": "Context Rot in Large Language Models",
        "session_id": "test_sess_001",
        "output_format": "brief",
        "citation_style": "apa",
        "trace": [],
        "research": [
            {
                "sub_question": "What is the definition and core mechanism of context rot?",
                "sources": [],
                "memory_hits": [],
            }
        ],
    }
    fake_tools = MagicMock()
    deps = AgentDeps(llm=FakeLLM(), tools=fake_tools, sqlite=MagicMock(), settings=None)

    out = synthesizer_node(state, deps)
    findings = out["findings"]
    assert len(findings) == 1
    assert "No verified relevant" in findings[0]["claim"]
    assert findings[0]["citations"] == []
    assert findings[0]["sources"] == []
    assert findings[0]["papers"] == []
    assert findings[0]["confidence"] == 0.0


def test_unsupported_claims_strip_citations():
    """If synthesized claim reports insufficient evidence, citations must be stripped."""
    state = {
        "query": "Context Rot in Large Language Models",
        "session_id": "test_sess_002",
        "output_format": "brief",
        "citation_style": "apa",
        "trace": [],
        "research": [
            {
                "sub_question": "What are the quantum computing mitigations for context rot?",
                "sources": [
                    {
                        "url": "https://example.com/quantum",
                        "title": "Diagnosing Context Rot in Long-horizon Search",
                        "text": "Discussion on context rot in classical language models...",
                    }
                ],
                "memory_hits": [],
            }
        ],
    }

    class InsufficientLLM(FakeLLM):
        def complete(self, *a, **k):
            return "Insufficient direct evidence in the retrieved sources to address this question."

        def complete_json(self, *a, **k):
            return ["Insufficient reliable evidence in retrieved sources to address this question."]

    deps = AgentDeps(llm=InsufficientLLM(), tools=MagicMock(), sqlite=MagicMock(), settings=None)
    out = synthesizer_node(state, deps)
    finding = out["findings"][0]
    assert "Insufficient" in finding["claim"]
    assert finding["citations"] == []
    assert finding["papers"] == []
    assert finding["confidence"] <= 0.2


def test_query_refinement_generation():
    """refine_search_queries produces focused alternatives when initial search fails."""
    queries = refine_search_queries("Context Rot in Large Language Models", "What causes context rot?")
    assert len(queries) >= 1
    assert any("context rot" in q.lower() for q in queries)
