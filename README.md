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
- `.github/workflows/` — reproducible CI/experiment workflows

## Reproducibility protocol

The experimental workflow is intentionally staged:

1. Freeze and validate source data and benchmark provenance.
2. Build the DEV split and retrieval outputs deterministically.
3. Select model/configuration using **DEV only**.
4. Freeze the selected configuration and model digest.
5. Run the held-out TEST split only after all DEV decisions are locked.

The TEST split is not used for model selection or prompt tuning.

## Current status

- Phase 1 benchmark freeze: completed and provenance-checked
- Phase 2 model pilot: completed
- Selected DEV model: `qwen2.5:1.5b`
- Full DEV evaluation: in progress
- Held-out TEST evaluation: locked pending DEV completion

## Model reproducibility

The selected Ollama model is pinned by digest during experiment execution. Decoding parameters, case-file hashes, prediction hashes, and evaluation provenance are recorded by the workflows so that reported results can be traced to exact experimental inputs.

## Citation

A formal citation entry will be added when the associated manuscript metadata is finalized.

## License

No license is granted yet. A project license will be added before archival release.
