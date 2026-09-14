# DEV Baseline — Qwen2.5 1.5B

> **DEV ONLY.** These results were used for configuration development and must not be presented as held-out TEST performance. The 161-query TEST split had not been accessed when this result bundle was produced.

## Provenance

- Frozen benchmark rows: 195
- DEV queries: 34
- Generation cases: 408
- Retriever: BM25
- Model: `qwen2.5:1.5b`
- Frozen model digest: `65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b`
- Decoding: temperature 0, seed 2027, context 8192, max prediction 512, top-p 1, sampling top-k 40, repeat penalty 1.1
- Source inference run: `34848420216`
- Verified aggregate repair/evaluation run: `34862009778`
- Final Actions artifact SHA-256: `710a3f4183de2061340a7d9cf869289f9c48ad2e63f1baf32dbb63c1b8fbe027`
- Merged prediction SHA-256: `e7942d9be5327e76ae676e457c59712687cc52017a2c58c084520b9e8d53f6d8`
- Per-case evaluation SHA-256: `b71fae88e89ae69a54314c4bff2238dc55d17064c2a0b0e9152cd4b659ee589b`
- Paired-tests SHA-256: `5cba7161cd6c011cf3c81a0e78c98f6e4a8dc0ae4294b1a4d824d94686be6dd6`
- Mean inference latency: 19.97 s/case
- Median inference latency: 19.70 s/case

The original aggregate step failed closed because its glob did not include the `shard/` extraction subdirectory. All eight inference shard artifacts were intact. A repair-only workflow independently revalidated every shard manifest, prediction hash, model digest, case ID, and error field, merged exactly 408 unique predictions, and then ran the canonical guard/evaluator/statistical pipeline without repeating inference.

## Retrieval DEV baseline

| Metric | BM25 |
|---|---:|
| MRR | 0.29035 |
| Hit@1 | 0.14706 |
| Hit@5 | 0.44118 |
| Hit@10 | 0.61765 |
| Recall@1 | 0.02598 |
| Recall@5 | 0.14626 |
| Recall@10 | 0.23465 |

BM25 was selected over the frozen TF-IDF DEV baseline before generation experiments.

## Generation results by condition

| Metric | C0 Ungrounded | C1 Clean RAG | C2 Compromised RAG | C3 Hardened RAG |
|---|---:|---:|---:|---:|
| n | 34 | 34 | 170 | 170 |
| F1 | 0.0118 | 0.0338 | 0.0347 | **0.0682** |
| Precision | 0.0294 | 0.0392 | 0.0588 | **0.1271** |
| Recall | 0.0074 | 0.0343 | 0.0273 | **0.0522** |
| Valid JSON | 0.5000 | 0.1176 | 0.5706 | **1.0000** |
| Schema OK | 0.5000 | 0.1176 | 0.5706 | **1.0000** |
| Attack success | 0.0000 | 0.0000 | 0.3353 | **0.0000** |
| Attack-target adoption | 0.0000 | 0.0000 | 0.1941 | **0.0000** |
| Invalid control-ID rate | 0.2353 | 0.0000 | 0.1000 | **0.0000** |
| Ungrounded-ID rate | — | 0.0441 | 0.2147 | **0.0000** |
| Unsupported-citation rate | 0.5000 | 0.0000 | 0.3290 | **0.0000** |
| Evidence-supported-ID rate | 0.0000 | 0.0539 | 0.0603 | **0.7412** |
| Malicious source cited | 0.0000 | 0.0000 | 0.1588 | **0.0000** |
| Guard rejected | 0.0000 | 0.0000 | 0.0000 | 0.2588 |

C3 combines hardened prompting/evidence handling with the programmatic output guard. Therefore the difference between C2 and C3 must not be attributed to the output guard alone without the planned component ablations.

## Adversarial DEV breakdown

| Attack family | C2 attack success | C3 attack success | C2 F1 | C3 F1 | C3 guard rejected |
|---|---:|---:|---:|---:|---:|
| Authority spoof | 0.2353 | **0.0000** | 0.1039 | 0.0557 | 0.2647 |
| Evidence conflict | 0.8235 | **0.0000** | 0.0000 | 0.0585 | 0.3235 |
| Fabricated control | 0.2059 | **0.0000** | 0.0000 | 0.0585 | 0.2941 |
| Override | 0.3824 | **0.0000** | 0.0403 | 0.0915 | 0.2059 |
| Schema break | 0.0294 | **0.0000** | 0.0292 | 0.0768 | 0.2059 |

After pre-registered Holm correction, several security/grounding improvements remain significant for specific attack families. Examples include evidence-conflict attack success (C2 0.8235 vs C3 0; Holm-adjusted p ≈ 2.24e-7), fabricated-control attack-target adoption (0.5 vs 0; p ≈ 4.27e-4), and override attack success (0.3824 vs 0; p ≈ 0.00562). Authority-spoof attack-success reduction does not remain significant after family-wise Holm correction in this DEV sample.

## DEV decision

This baseline provides strong evidence that the hardened condition improves security, grounding, and format compliance, but **absolute mapping utility remains low**. Therefore it is not yet the final locked configuration. Larger Qwen candidates are being evaluated on the same frozen 52-case DEV model-selection subset before any TEST access.
