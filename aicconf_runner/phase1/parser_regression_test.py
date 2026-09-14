#!/usr/bin/env python3
"""Regression tests for CSA NIST mapping-cell parsing.

Examples below are drawn from the verified CCM v4.0.13 normalized payload pattern.
They protect against the critical loss of enhancement ranges such as SA-8(29)-(33).
"""
from __future__ import annotations
import runpy
from pathlib import Path

MOD = runpy.run_path(str(Path(__file__).with_name('build_benchmark.py')), run_name='benchmark_builder_test')
parse = MOD['parse_nist_mapping_cell']

CASES = [
    ('SA-8(29)-(33)', ['SA-8(29)','SA-8(30)','SA-8(31)','SA-8(32)','SA-8(33)']),
    ('SA-8(1)-(7)\nSA-8(9)-(13)\nSA-17\nSA-17(1)-(9)',
     [*(f'SA-8({i})' for i in range(1,8)), *(f'SA-8({i})' for i in range(9,14)), 'SA-17', *(f'SA-17({i})' for i in range(1,10))]),
    ('SI-2\nSI-2(2)-(6)\nSA-11\nSA-11(2)\nSA-15\nSA-15(1)-(3)\nSA-15(5)-(8)\nSA-15(10)-(12)',
     ['SI-2', *(f'SI-2({i})' for i in range(2,7)), 'SA-11','SA-11(2)','SA-15', *(f'SA-15({i})' for i in range(1,4)), *(f'SA-15({i})' for i in range(5,9)), *(f'SA-15({i})' for i in range(10,13))]),
    ('CA-2\nCA-2(1)-(3)\nPL-10\nPL-11', ['CA-2','CA-2(1)','CA-2(2)','CA-2(3)','PL-10','PL-11']),
    ('No Mapping', []),
]

for raw, expected in CASES:
    ids, ranges, bad = parse(raw)
    assert not bad, (raw, bad)
    assert ids == expected, (raw, ids, expected)

# Fail-closed behavior: ambiguous or malformed syntax must be surfaced.
for raw in ['SA-8(33)-(29)', 'SA-8-(33)', 'not-a-control']:
    ids, ranges, bad = parse(raw)
    assert bad, (raw, ids, ranges)

print(f'PASS: {len(CASES)} valid cases + 3 fail-closed cases')
