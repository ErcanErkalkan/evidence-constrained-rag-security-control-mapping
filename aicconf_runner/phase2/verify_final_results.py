#!/usr/bin/env python3
"""Fail-closed integrity verifier for a completed final TEST result bundle."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from common import sha256_file, json_dump
from final_common import load_json, verify_phase1_against_lock, verify_test_prep, match_model_freezes, verify_environment_freeze
from environment_preflight import probe as environment_probe

HERE=Path(__file__).resolve().parent


def verify_bundle(final_run_dir, phase1_run, phase2_test_dir, test_lock, environment_freeze, model_freezes, check_live_environment=True):
    root=Path(final_run_dir); mp=root/'FINAL_RUN_MANIFEST.json'
    if not mp.exists(): raise RuntimeError('FINAL_RUN_MANIFEST.json missing')
    man=load_json(mp)
    if man.get('status')!='PASS_FINAL_TEST_COMPLETE' or str(man.get('manifest_version'))!='1.6': raise RuntimeError('Final run manifest is not a PASS v1.6 result')
    lockp=Path(test_lock); lock=load_json(lockp)
    if sha256_file(lockp)!=man.get('test_lock',{}).get('sha256'): raise RuntimeError('Final manifest/test-lock hash mismatch')
    p1=verify_phase1_against_lock(phase1_run,lock)
    for k in ('release_sha256','benchmark_sha256','nist_source_sha256'):
        if man.get('phase1',{}).get(k)!=p1[k]: raise RuntimeError(f'Final manifest Phase-1 mismatch: {k}')
    live=environment_probe() if check_live_environment else None
    verify_environment_freeze(environment_freeze,lock,live_probe=live)
    if man.get('environment_freeze_sha256')!=sha256_file(environment_freeze): raise RuntimeError('Final manifest environment-freeze mismatch')
    prep=verify_test_prep(phase2_test_dir,lockp,lock)
    pm=man.get('test_preparation',{})
    checks={'manifest_sha256':sha256_file(prep['manifest_path']),'cases_sha256':sha256_file(prep['cases']),'corpus_sha256':sha256_file(prep['corpus']),'attack_fixtures_sha256':sha256_file(prep['attacks'])}
    for k,v in checks.items():
        if pm.get(k)!=v: raise RuntimeError(f'Final manifest TEST-prep mismatch: {k}')
    matched=match_model_freezes(model_freezes,lock); allowed={(m['requested_model'],m['model_digest'],m['sha256']) for m,_,_ in matched}
    seen=set()
    for mr in man.get('models',[]):
        ident=(mr.get('requested_model'),mr.get('model_digest'),mr.get('model_freeze_sha256'))
        if ident not in allowed: raise RuntimeError(f'Unrecognized model identity in final manifest: {ident}')
        if ident in seen: raise RuntimeError(f'Duplicate model result: {ident}')
        seen.add(ident)
        for label,meta in (mr.get('artifacts') or {}).items():
            p=root/meta.get('path','')
            if not p.is_file(): raise RuntimeError(f'Missing final artifact {label}: {p}')
            if sha256_file(p)!=meta.get('sha256'): raise RuntimeError(f'Final artifact hash mismatch {label}: {p}')
        inf=load_json(root/mr['artifacts']['inference_manifest']['path'])
        if inf.get('status')!='PASS_COMPLETE' or not inf.get('model_freeze_verified'): raise RuntimeError('Inference manifest is not a strict PASS')
        if inf.get('cases_sha256')!=pm.get('cases_sha256'): raise RuntimeError('Inference cases hash differs from final TEST cases')
        for skey in ['summary','provenance_only_summary','output_guard_only_summary']:
            if skey not in mr['artifacts']: raise RuntimeError(f'Missing required evaluation summary artifact: {skey}')
            sm=load_json(root/mr['artifacts'][skey]['path']); prov=sm.get('_provenance',{})
            if prov.get('cases_sha256')!=pm.get('cases_sha256') or prov.get('corpus_sha256')!=pm.get('corpus_sha256'):
                raise RuntimeError(f'Generation summary provenance mismatch: {skey}')
            if prov.get('missing_predictions') or prov.get('extra_predictions') or prov.get('inference_errors'):
                raise RuntimeError(f'Generation summary reports incomplete/error predictions: {skey}')
        aman=load_json(root/mr['artifacts']['ablation_stats_manifest']['path'])
        inputs=aman.get('inputs',{})
        if inputs.get('full_sha256')!=mr['artifacts']['per_case']['sha256'] or inputs.get('provenance_only_sha256')!=mr['artifacts']['provenance_only_per_case']['sha256'] or inputs.get('output_guard_only_sha256')!=mr['artifacts']['output_guard_only_per_case']['sha256']:
            raise RuntimeError('Ablation statistics input hashes do not match final artifacts')
    if seen!=allowed: raise RuntimeError('Final manifest does not contain exactly all locked models')
    return {'status':'PASS_FINAL_RESULT_INTEGRITY','final_manifest_sha256':sha256_file(mp),'models_verified':len(seen),'cases_sha256':pm.get('cases_sha256'),'corpus_sha256':pm.get('corpus_sha256')}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--final-run-dir',required=True); ap.add_argument('--phase1-run',required=True); ap.add_argument('--phase2-test-dir',required=True); ap.add_argument('--test-lock',required=True); ap.add_argument('--environment-freeze',required=True); ap.add_argument('--model-freeze',action='append',required=True); ap.add_argument('--skip-live-environment-check',action='store_true'); args=ap.parse_args()
    obj=verify_bundle(args.final_run_dir,args.phase1_run,args.phase2_test_dir,args.test_lock,args.environment_freeze,args.model_freeze,not args.skip_live_environment_check)
    json_dump(Path(args.final_run_dir)/'FINAL_RESULT_INTEGRITY.json', obj)
    print(json.dumps(obj,indent=2,ensure_ascii=False))

if __name__=='__main__':
    try: main()
    except Exception as e: print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(2)
