# AICCONF 2027 final model-selection rationale

Date: 2026-09-15

The locked model for the one-shot held-out TEST is `qwen2.5:1.5b`, digest `sha256:65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b`.

This choice is not a claim that the 1.5B model is universally superior to larger Qwen2.5 variants. It is a reproducibility decision made at the DEV-to-TEST boundary. At lock time, the repository contains a provenance-verified full-DEV execution for the 1.5B model (408 generation cases) and a validated 3B pilot workflow definition, but no comparable provenance-verified completed 3B or 7B result bundle was available in the canonical evidence chain. Therefore, escalating to a larger model would introduce an unverified configuration change immediately before TEST.

The final TEST configuration consequently preserves the only model with a complete, auditable full-DEV evidence chain. No held-out TEST metric was used in this selection. Larger-model evaluation remains future work and must not be used to retune the locked TEST configuration after TEST execution begins.

Integrity rule: if a previously unaccounted 3B/7B DEV artifact is later discovered, it may be reported as historical DEV evidence but must not be used to alter the already-executed TEST configuration.
