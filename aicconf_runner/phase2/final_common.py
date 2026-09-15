#!/usr/bin/env python3
"""Shared verification helpers for the one-shot final TEST and derived reports."""
from __future__ import annotations
import json, re
from pathlib import Path
from common import sha256_file


def load_json(path: str | Path) -> dict:
    p = Path(path)
    obj = json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise RuntimeError(f'Expected JSON object: {p}')
    return obj


def slug(text: str) -> str:
    x = re.sub(r'[^A-Za-z0-9._-]+', '_', text).strip('._-')
    return x or 'model'


def verify_phase1_against_lock(phase1_run: str | Path, lock: dict) -> dict:
    p1 = Path(phase1_run)
    release = p1/'benchmark_frozen'/'PHASE1_RELEASE_FREEZE.json'
    bench = p1/'benchmark_frozen'/'benchmark.csv'
    nist = p1/'sources'/'original'/'800-53-r5-controls.json'
    for p in (release, bench, nist):
        if not p.exists(): raise RuntimeError(f'Missing Phase-1 artifact: {p}')
    rel_obj = load_json(release)
    if rel_obj.get('status') != 'PASS_PHASE1_FROZEN':
        raise RuntimeError('Phase-1 release is not PASS_PHASE1_FROZEN')
    expected = lock.get('phase1', {})
    got = {
        'release_sha256': sha256_file(release),
        'benchmark_sha256': sha256_file(bench),
        'nist_source_sha256': sha256_file(nist),
    }
    if got != {k: expected.get(k) for k in got}:
        raise RuntimeError(f'Phase-1 hash mismatch against FINAL_CONFIG_LOCK: got={got} expected={expected}')
    return {'release': release, 'benchmark': bench, 'nist': nist, **got}


def verify_environment_freeze(path: str | Path, lock: dict, live_probe: dict | None = None) -> dict:
    p = Path(path); obj = load_json(p)
    if obj.get('status') != 'PASS_ENVIRONMENT_FROZEN': raise RuntimeError('Environment freeze is not PASS')
    expected = lock.get('environment', {})
    if sha256_file(p) != expected.get('sha256'):
        raise RuntimeError('Environment freeze file hash mismatch against FINAL_CONFIG_LOCK')
    if live_probe is not None:
        for key in ('python','packages'):
            if live_probe.get(key) != obj.get(key):
                raise RuntimeError(f'Live environment differs from frozen {key}')
        if live_probe.get('status') != 'PASS_ENVIRONMENT_FROZEN': raise RuntimeError('Live environment preflight failed')
    return obj


def match_model_freezes(paths: list[str], lock: dict) -> list[tuple[dict, Path, dict]]:
    supplied = {}
    for raw in paths:
        p = Path(raw); obj = load_json(p); h = sha256_file(p)
        if h in supplied: raise RuntimeError(f'Duplicate model-freeze bytes supplied: {p}')
        supplied[h] = (p, obj)
    out=[]
    locked = lock.get('models', [])
    if not locked: raise RuntimeError('No models present in FINAL_CONFIG_LOCK')
    for m in locked:
        h=m.get('sha256'); pair=supplied.get(h)
        if not pair: raise RuntimeError(f'Missing model freeze with locked sha256={h}')
        p,obj=pair
        if obj.get('status')!='PASS_OLLAMA_MODEL_FROZEN': raise RuntimeError(f'Model freeze not PASS: {p}')
        checks={'requested_model':m.get('requested_model'),'resolved_name':m.get('resolved_name'),'model_digest':m.get('model_digest'),'ollama_version':m.get('ollama_version')}
        for k,v in checks.items():
            if obj.get(k)!=v: raise RuntimeError(f'Model freeze field mismatch {k}: {p}')
        out.append((m,p,obj))
    if len(supplied)!=len(locked):
        extras=set(supplied)-{m.get('sha256') for m in locked}
        if extras: raise RuntimeError(f'Unregistered extra model freeze(s) supplied: {sorted(extras)}')
    return out


def verify_test_prep(test_dir: str | Path, lock_path: str | Path, lock: dict) -> dict:
    td=Path(test_dir); lp=Path(lock_path)
    manifest_path=td/'PHASE2_TEST_PREP_MANIFEST.json'
    if not manifest_path.exists(): raise RuntimeError(f'Missing TEST prep manifest: {manifest_path}')
    man=load_json(manifest_path)
    if man.get('status')!='TEST_PREPARED_UNDER_VERIFIED_LOCK': raise RuntimeError('TEST prep manifest status is not PASS')
    if man.get('test_lock_sha256')!=sha256_file(lp): raise RuntimeError('TEST prep was created under a different FINAL_CONFIG_LOCK')
    r=lock.get('retrieval',{}); primary=r.get('primary_method')
    locked_methods=list(r.get('methods',[])); prepared_methods=man.get('methods') or {}
    if sorted(prepared_methods)!=sorted(locked_methods): raise RuntimeError('Prepared retrieval-method set differs from FINAL_CONFIG_LOCK')
    if primary not in prepared_methods: raise RuntimeError('Primary retrieval method missing from TEST prep manifest')
    if int(man.get('top_k',-1))!=int(r.get('top_k',-2)) or int(man.get('context_k',-1))!=int(r.get('context_k',-2)):
        raise RuntimeError('TEST prep retrieval/context parameters differ from lock')
    if int(man.get('attack_rank',-1))!=int(lock.get('attack',{}).get('attack_rank',-2)):
        raise RuntimeError('TEST prep attack rank differs from lock')
    corpus=td/'corpus_primary'/'nist_corpus.csv'; attacks=td/'attack_fixtures.csv'
    for p in (corpus,attacks):
        if not p.exists(): raise RuntimeError(f'Missing TEST artifact: {p}')
    checks=[(corpus,man.get('corpus_sha256'),'corpus'),(attacks,man.get('attack_fixtures_sha256'),'attacks')]
    method_paths={}
    for method,mm in prepared_methods.items():
        rdir=td/f'retrieval_test_{method}'; retrieval=rdir/f'{method}_retrieval.csv'; metrics=rdir/f'{method}_metrics.json'; cases_m=td/f'prompt_cases_test_{method}.jsonl'
        for p in (retrieval,metrics,cases_m):
            if not p.exists(): raise RuntimeError(f'Missing TEST method artifact: {p}')
        checks += [(retrieval,mm.get('retrieval_sha256'),f'{method} retrieval'),(metrics,mm.get('metrics_sha256'),f'{method} metrics'),(cases_m,mm.get('cases_sha256'),f'{method} cases')]
        method_paths[method]={'retrieval':retrieval,'metrics':metrics,'cases':cases_m}
    for p,h,label in checks:
        if not h or sha256_file(p)!=h: raise RuntimeError(f'TEST {label} hash mismatch against prep manifest')
    cases=method_paths[primary]['cases']
    return {'manifest_path':manifest_path,'manifest':man,'primary_method':primary,'cases':cases,'corpus':corpus,'attacks':attacks,'method_paths':method_paths}
