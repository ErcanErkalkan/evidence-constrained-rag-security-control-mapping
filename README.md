# Evidence-Constrained RAG for Security-Control Mapping

Reproducibility repository for the research project **Evidence-Constrained RAG for Security-Control Mapping under Prompt Injection**.

The project studies whether retrieval-augmented generation systems can preserve correct security-control mapping and evidence grounding when retrieved context contains malicious, conflicting, or fabricated instructions.

## Research focus

The benchmark compares four generation conditions:

- `C0_UNGROUNDED` — model-only baseline
- `C1_CLEAN_RAG` — retrieval with clean evidence
- `C2_COMPROMISED_RAG` — retrieval containing adversarial evidence/instructions
- `C3_HARDENED_RAG` — retrieval plus evidence and output guardrails

The benchmark is built from reproducibly frozen security-control sources and evaluates attacks including authority spoofing, evidence conflicts, fabricated controls, instruction override, and schema breaking.

## Repository structure

- `aicconf_runner/phase1/` — source acquisition, parsing, benchmark construction, validation, and freeze logic
- `aicconf_runner/phase2/` — retrieval, adversarial fixtures, prompt-case composition, model execution, output guardrails, evaluation, and statistical tests
- `.github/workflows/` — reproducible experiment and integrity-check workflows
- `REPRODUCIBILITY.md` — staged protocol, fail-closed rules, and held-out TEST lock
- `THIRD_PARTY_DATA.md` — upstream data/standards provenance and licensing boundary

## Reproducibility protocol

The experimental workflow is intentionally staged:

1. Freeze and validate source data and benchmark provenance.
2. Build the DEV split and retrieval outputs deterministically.
3. Select model/configuration using **DEV only**.
4. Freeze the selected configuration and model digest.
5. Run the held-out TEST split only after all DEV decisions are locked.

The TEST split is not used for model selection or prompt tuning.

## Frozen benchmark

- Valid benchmark rows: **195**
- Official no-mapping exclusions: **2**
- DEV queries: **34**
- Held-out TEST queries: **161**
- Frozen benchmark SHA-256: `426d890e16513c3da449dfe08e93f29f556011e6a24288460c07ccba8f090f4f`

## DEV retrieval

BM25 is currently the selected DEV retriever:

- MRR: `0.29035`
- Hit@5: `0.44118`
- Hit@10: `0.61765`

It outperformed the corresponding TF-IDF DEV baseline in the frozen preparation.

## Full-DEV baseline

A complete **408-case** Qwen2.5-1.5B DEV run has passed merge, guard, evaluation, and pre-registered statistical-integrity checks. The model was pinned by digest:

`65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b`

The hardened condition eliminated measured final-output attack success and invalid/ungrounded IDs in this DEV run, while preserving a non-zero utility trade-off. Because absolute mapping F1 remains low, larger Qwen candidates are being evaluated on the same frozen DEV model-selection subset before configuration lock.

**No held-out TEST query has been accessed.**

## Current status

- Phase 1 benchmark freeze: **complete**
- BM25 vs TF-IDF DEV retrieval selection: **complete**
- Initial 1B/1.5B model pilot: **complete**
- 408-case Qwen2.5-1.5B full DEV baseline: **complete and provenance-verified**
- Larger-model DEV escalation (`qwen2.5:3b`, `qwen2.5:7b`): **in progress**
- Final configuration lock: **pending DEV escalation**
- Held-out TEST evaluation: **LOCKED**

## Model reproducibility

Ollama model identity is frozen by digest before inference. Decoding parameters, case-file hashes, prediction hashes, benchmark/corpus hashes, and evaluation provenance are recorded so reported results can be traced to exact experimental inputs.

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). Manuscript-specific publication identifiers will be added after publication metadata is finalized.

## License

Project-authored code and documentation are released under the [MIT License](LICENSE). Third-party standards and source material are **not** relicensed by this repository; see [`THIRD_PARTY_DATA.md`](THIRD_PARTY_DATA.md).
