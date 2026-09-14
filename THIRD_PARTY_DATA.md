# Third-Party Data and Standards

This repository contains software that acquires, validates, transforms, and evaluates material derived from external standards/control catalogs. The MIT license in this repository applies to the project-authored software and documentation only; it does **not** relicense third-party source material.

## Upstream sources

The reproducibility protocol uses pinned upstream versions of:

- Cloud Security Alliance Cloud Controls Matrix (CCM) v4.0.13 control/mapping material.
- NIST SP 800-53 Rev. 5 control catalog material.

The Phase-1 acquisition code records immutable upstream commit/blob identity, byte size, cryptographic hashes, schema checks, and record counts before a benchmark release can be frozen.

## Redistribution policy

Authoritative raw upstream files are intentionally not treated as project-owned data. Reproduction should use the acquisition scripts and pinned provenance records to obtain the source material from its authoritative upstream location, subject to the upstream provider's current license, terms, notices, and attribution requirements.

NIST and Cloud Security Alliance names, standards, documents, trademarks, and other third-party rights remain with their respective owners. Nothing in this repository grants additional rights to third-party content.

## Derived experimental artifacts

Project-authored benchmark manifests, split metadata, retrieval outputs, adversarial fixtures, prediction/evaluation code, and provenance records may be distributed where doing so does not reproduce restricted third-party source content. A public release should prefer hashes, identifiers, derived metrics, and acquisition instructions over republishing authoritative source files.
