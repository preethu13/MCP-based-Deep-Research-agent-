"""Unit tests for metadata verification, publication status classification,
evidence tier classification, author formatting, and bibliography count parity.
"""

from __future__ import annotations

import pytest
from src.tools.search import (
    classify_publication_status,
    classify_evidence_tier,
    is_simulation_study,
)
from src.tools.citation import format_authors_apa, format_authors_mla, generate_citation
from src.agent.validator import validate_and_reconcile_research
from src.tools.formatter import format_output


def test_publication_status_classification():
    """Verify distinction between preprints, journals, conferences, and unknown."""
    # 1. arXiv preprint — MUST NOT be classified as peer-reviewed
    arxiv_paper = {
        "title": "Diagnosing and Mitigating Context Rot in Long-horizon Search",
        "url": "https://arxiv.org/abs/2606.29718",
        "venue": "arXiv",
        "type": "preprint",
        "doi": "https://doi.org/10.48550/arxiv.2606.29718",
    }
    status, is_peer = classify_publication_status(arxiv_paper)
    assert status == "Preprint (arXiv)"
    assert is_peer is False

    # 2. bioRxiv preprint
    biorxiv_paper = {
        "title": "BioRxiv study on genes",
        "url": "https://biorxiv.org/content/123",
        "venue": "bioRxiv",
        "type": "preprint",
    }
    status, is_peer = classify_publication_status(biorxiv_paper)
    assert status == "Preprint"
    assert is_peer is False

    # 3. Peer-reviewed conference paper
    conf_paper = {
        "title": "Attention Is All You Need",
        "url": "https://proceedings.neurips.cc/paper/7181",
        "venue": "Advances in Neural Information Processing Systems (NeurIPS)",
        "type": "proceedings-article",
    }
    status, is_peer = classify_publication_status(conf_paper)
    assert status == "Peer-reviewed conference paper"
    assert is_peer is True

    # 4. Peer-reviewed journal article
    journal_paper = {
        "title": "Deep Residual Learning for Image Recognition",
        "url": "https://ieeexplore.ieee.org/document/7780459",
        "venue": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "type": "journal-article",
    }
    status, is_peer = classify_publication_status(journal_paper)
    assert status == "Peer-reviewed journal article"
    assert is_peer is True

    # 5. Missing venue and unknown status
    unknown_paper = {
        "title": "Some Untyped Document",
        "url": "https://example.com/doc",
    }
    status, is_peer = classify_publication_status(unknown_paper)
    assert status == "Unknown publication status"
    assert is_peer is False


def test_evidence_tier_classification():
    """Verify classification into Direct evidence, Supporting evidence, or Related work."""
    query = "Context Rot in Large Language Models"

    # Direct evidence: empirical measurement of context length degradation
    direct_paper = {
        "title": "Diagnosing and Mitigating Context Rot in Long-horizon Search",
        "abstract": "We empirically measure how increasing context length degrades model performance (context rot) in long-horizon search tasks.",
    }
    assert classify_evidence_tier(direct_paper, query) == "Direct evidence"

    # Supporting evidence: related sub-task or monitoring component
    supporting_paper = {
        "title": "Classifier Context Rot: Monitor Performance Degrades with Context Length",
        "abstract": "Monitoring LLM safety using classifiers shows that detection capabilities degrade as transcript length grows.",
    }
    assert classify_evidence_tier(supporting_paper, query) in ("Direct evidence", "Supporting evidence")

    # Related work: proposed architectural protocol or theoretical framework
    related_paper = {
        "title": "Charter Coherence Protocol: Eliminating Context Rot in Long-Running Autonomous Multi-Agent Systems",
        "abstract": "We propose a novel protocol and architecture for multi-agent systems, evaluated in simulated environments.",
    }
    assert classify_evidence_tier(related_paper, query) == "Related work"


def test_simulation_detection():
    """Verify detection of simulation or synthetic benchmark studies."""
    sim_paper = {
        "title": "Charter Coherence Protocol",
        "abstract": "The proposed architecture achieved zero violations in controlled simulation across synthetic agents.",
    }
    assert is_simulation_study(sim_paper) is True

    real_paper = {
        "title": "Empirical Evaluation of Long Context",
        "abstract": "We evaluate production human transcripts from deployed real-world customer search workflows.",
    }
    assert is_simulation_study(real_paper) is False


def test_author_formatting_prevents_malformed_entries():
    """Ensure author parsing never generates 'al., S. X. Y...'."""
    source_with_list = {
        "authors": ["Shijie Xia", "Yikun Wang", "Z Zhangqin Huang", "Pengfei Liu"],
        "title": "Diagnosing and Mitigating Context Rot in Long-horizon Search",
        "year": 2026,
        "url": "https://arxiv.org/abs/2606.29718",
        "publication_status": "Preprint (arXiv)",
    }
    apa_str = format_authors_apa(source_with_list)
    assert "Xia, S." in apa_str
    assert "Wang, Y." in apa_str
    assert "Huang, Z. Z." in apa_str
    assert "Liu, P." in apa_str
    assert not apa_str.startswith("al.")

    # Even with raw 'et al.' in author string
    source_with_et_al = {
        "author": "Shijie Xia, Yikun Wang, Z Zhangqin Huang et al.",
        "title": "Diagnosing and Mitigating Context Rot in Long-horizon Search",
        "year": 2026,
        "url": "https://arxiv.org/abs/2606.29718",
        "publication_status": "Preprint (arXiv)",
    }
    apa_str2 = format_authors_apa(source_with_et_al)
    assert not apa_str2.startswith("al.")
    assert "Xia, S." in apa_str2

    citation = generate_citation(source_with_list, style="apa")
    assert "arXiv." in citation
    assert not citation.startswith("al.")


def test_exact_parity_between_analyzed_papers_and_bibliography():
    """Ensure the number of analyzed papers exactly matches the reference list count."""
    findings = [
        {
            "sub_question": "What is the empirical effect of context rot?",
            "claim": "Extensive context degrades model capabilities in long-horizon tasks.",
            "papers": [
                {
                    "title": "Diagnosing and Mitigating Context Rot in Long-horizon Search",
                    "authors": ["Shijie Xia", "Yikun Wang"],
                    "year": 2026,
                    "url": "https://arxiv.org/abs/2606.29718",
                    "doi": "https://doi.org/10.48550/arxiv.2606.29718",
                    "publication_status": "Preprint (arXiv)",
                    "is_peer_reviewed": False,
                    "evidence_tier": "Direct evidence",
                    "abstract": "We diagnose context rot in long-horizon search.",
                }
            ],
            "confidence": 0.9,
        },
        {
            "sub_question": "What are classifier monitoring impacts?",
            "claim": "Monitor performance degrades with transcript length.",
            "papers": [
                {
                    "title": "Classifier Context Rot: Monitor Performance Degrades with Context Length",
                    "authors": ["Alice Smith", "Bob Jones"],
                    "year": 2026,
                    "url": "https://arxiv.org/abs/2605.12366",
                    "doi": "https://doi.org/10.48550/arxiv.2605.12366",
                    "publication_status": "Preprint (arXiv)",
                    "is_peer_reviewed": False,
                    "evidence_tier": "Supporting evidence",
                    "abstract": "Classifiers degrade on long transcripts.",
                }
            ],
            "confidence": 0.9,
        },
    ]

    val_findings, verified_papers, warnings = validate_and_reconcile_research(
        findings, "Context Rot in Large Language Models"
    )
    assert len(verified_papers) == 2

    # Render brief and verify counts
    rendered = format_output(findings, "brief", query="Context Rot in Large Language Models")

    # Count analyzed papers in literature section
    assert "The following 2 paper(s) and scientific studies were analyzed" in rendered
    assert "0 peer-reviewed, 2 preprints" in rendered

    # Count numbered references in References section
    ref_section = rendered.split("## References")[-1]
    ref_lines = [line for line in ref_section.strip().split("\n") if line.strip() and line.strip()[0].isdigit()]
    assert len(ref_lines) == 2
    assert len(verified_papers) == len(ref_lines)


def test_quality_validation_reconciles_simulation_claims():
    """Ensure claims overstating simulation findings are reconciled."""
    findings = [
        {
            "sub_question": "How to eliminate context rot?",
            "claim": "The Charter Coherence Protocol eliminates context rot in enterprise multi-agent production systems.",
            "papers": [
                {
                    "title": "Charter Coherence Protocol: Eliminating Context Rot in Long-Running Autonomous Systems",
                    "authors": ["Eve Agent"],
                    "year": 2026,
                    "url": "https://arxiv.org/abs/2601.99999",
                    "publication_status": "Preprint (arXiv)",
                    "is_peer_reviewed": False,
                    "is_simulation": True,
                    "evidence_tier": "Related work",
                    "abstract": "We evaluate context rot mitigation for the protocol in controlled multi-agent simulation.",
                }
            ],
            "confidence": 0.8,
        }
    ]
    val_findings, verified_papers, warnings = validate_and_reconcile_research(
        findings, "Context Rot in Large Language Models"
    )
    assert len(val_findings) == 1
    # Check that overclaiming was adjusted
    claim_text = val_findings[0]["claim"]
    assert "simulation" in claim_text.lower() or "mitigate" in claim_text.lower()
