# Reproducibility Protocol

This artifact is deliberately staged so that model/configuration decisions are made on DEV before the held-out TEST split is opened.

## Stage 1 — Source and benchmark freeze

Phase 1 must finish with `PASS_PHASE1_FROZEN`. The release freeze validates pinned upstream identities, byte/hash checks, parsed record counts, mapping expansion, exclusions, and the final benchmark hash.

Current frozen benchmark facts:

- 195 valid CCM benchmark rows.
- 2 official no-mapping exclusions.
- 34 DEV queries.
- 161 held-out TEST queries.

## Stage 2 — DEV preparation

Phase 2 deterministically rebuilds the NIST target corpus, adversarial fixtures, retrieval outputs, and prompt cases from the frozen Phase-1 handoff. Retrieval/model selection is DEV-only.

The current DEV retrieval comparison selected BM25 over TF-IDF. The selected model for full DEV is `qwen2.5:1.5b`, pinned by Ollama digest during execution.

## Experimental conditions

- `C0_UNGROUNDED`: model-only baseline.
- `C1_CLEAN_RAG`: clean retrieval evidence.
- `C2_COMPROMISED_RAG`: retrieval with adversarial content.
- `C3_HARDENED_RAG`: compromised retrieval plus evidence/output guardrails.

Adversarial families include authority spoofing, evidence conflict, fabricated controls, instruction override, and schema breaking.

## Fail-closed principles

Final-scoring scripts reject missing or extra predictions, duplicate case IDs, inference errors, model-digest mismatches, and incomplete case sets. Synthetic smoke-test values are never promoted to manuscript results.

## TEST lock

The 161-query TEST split must remain unused until:

1. DEV retrieval/model/configuration choices are complete.
2. The selected configuration and model digest are frozen.
3. Full DEV evaluation passes integrity checks.
4. The TEST workflow is created as a one-shot run with no tuning based on TEST outcomes.

## Provenance expectations

A release-quality result bundle should contain:

- benchmark/source freeze manifests and SHA-256 values,
- code/configuration identity,
- model name and immutable digest,
- deterministic decoding parameters,
- case and prediction hashes,
- per-case metrics,
- aggregate metrics and pre-registered paired tests,
- explicit confirmation that TEST was not accessed during DEV.
