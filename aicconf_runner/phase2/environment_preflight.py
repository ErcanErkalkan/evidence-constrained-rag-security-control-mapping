#!/usr/bin/env python3
"""Freeze the Python analysis environment used for retrieval/statistics/reporting.

This does not claim bitwise reproducibility across operating systems, but it prevents a
final TEST run from silently changing Python or the core numerical/statistical package
versions after DEV decisions have been frozen.
"""
from __future__ import annotations
import argparse, importlib, json, platform, sys
from importlib import metadata
from common import json_dump

REQUIRED = {
    'numpy': 'numpy',
    'scikit-learn': 'sklearn',
    'scipy': 'scipy',
    'matplotlib': 'matplotlib',
}


def probe() -> dict:
    packages = {}
    errors = []
    for dist, module in REQUIRED.items():
        try:
            mod = importlib.import_module(module)
            version = metadata.version(dist)
            packages[dist] = {'version': version, 'module_version': getattr(mod, '__version__', '')}
        except Exception as e:
            errors.append(f'{dist}: {type(e).__name__}: {e}')
    return {
        'status': 'PASS_ENVIRONMENT_FROZEN' if not errors else 'FAIL_ENVIRONMENT_MISSING_DEPENDENCIES',
        'python': {'version': platform.python_version(), 'implementation': platform.python_implementation(),
                   'executable_name': sys.executable.split('/')[-1]},
        'platform': {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine()},
        'packages': packages,
        'errors': errors,
        'note': 'Exact package versions are frozen for the final TEST run. Platform identity is recorded for provenance, not claimed as a portability guarantee.'
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='ENVIRONMENT_FREEZE.json')
    args = ap.parse_args()
    obj = probe()
    json_dump(args.out, obj)
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    if obj['status'] != 'PASS_ENVIRONMENT_FROZEN':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
