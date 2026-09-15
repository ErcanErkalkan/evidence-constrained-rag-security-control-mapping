#!/usr/bin/env python3
"""Execute the locked one-shot TEST pipeline and emit a provenance-complete manifest.

This runner intentionally refuses silent reruns. A registry is written into the prepared
TEST directory when a real final run begins. A subsequent run requires an explicit
--acknowledge-rerun reason and a fresh empty output directory.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from common import sha256_file, json_dump
from final_common import load_json, slug, verify_phase1_against_lock, verify_test_prep, match_model_freezes, verify_environment_freeze
from environment_preflight import probe as environment_probe

HERE=Path(__file__).resolve().parent


def run_py(script: str, *args: str) -> None:
    cmd=[sys.executable,str(HERE/script),*map(str,args)]
    print('+',' '.join(cmd),flush=True)
    subprocess.run(cmd,check=True,cwd=HERE)


def assert_code_lock(lock: dict) -> None:
    expected=lock.get('phase2_code',{})
    if not expected: raise RuntimeError('FINAL_CONFIG_LOCK has no phase2_code hashes')
    for name,h in expected.items():
        p=HERE/name
        if not p.exists(): raise RuntimeError(f'Locked code file missing: {name}')
        got=sha256_file(p)
        if got!=h: raise RuntimeError(f'Locked code hash mismatch: {name}: {got} != {h}')


def registry_event(path: Path, event: dict) -> None:
    if path.exists():
        obj=load_json(path); events=obj.get('events',[])
        if not isinstance(events,list): raise RuntimeError('Malformed final TEST execution registry')
    else:
        obj={'registry_version':'1.0','events':[]}; events=obj['events']
    events.append(event)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
    tmp.replace(path)


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase1-run',required=True)
    ap.add_argument('--phase2-test-dir',required=True)
    ap.add_argument('--test-lock',required=True)
    ap.add_argument('--environment-freeze',required=True)
    ap.add_argument('--model-freeze',action='append',required=True)
    ap.add_argument('--outdir',default='FINAL_TEST_RUN')
    ap.add_argument('--acknowledge-rerun',default='',help='Required if a prior final run was already registered for this TEST preparation; state the reason.')
    ap.add_argument('--verify-only',action='store_true',help='Verify all frozen prerequisites but do not register or execute TEST.')
    args=ap.parse_args()

    phase1_run=Path(args.phase1_run).resolve(); test_dir=Path(args.phase2_test_dir).resolve(); lock_path=Path(args.test_lock).resolve(); env_freeze=Path(args.environment_freeze).resolve(); model_freeze_args=[str(Path(x).resolve()) for x in args.model_freeze]; lock=load_json(lock_path)
    if lock.get('status')!='LOCKED_FOR_TEST' or str(lock.get('lock_version'))!='1.6':
        raise RuntimeError('FINAL_CONFIG_LOCK must be status=LOCKED_FOR_TEST and lock_version=1.6')
    assert_code_lock(lock)
    p1=verify_phase1_against_lock(phase1_run,lock)
    live_env=environment_probe()
    verify_environment_freeze(env_freeze,lock,live_probe=live_env)
    prep=verify_test_prep(test_dir,lock_path,lock)
    models=match_model_freezes(model_freeze_args,lock)

    verification={
      'status':'PASS_FINAL_PREREQUISITES_VERIFIED',
      'lock_sha256':sha256_file(lock_path),
      'phase1_release_sha256':p1['release_sha256'],
      'test_prep_manifest_sha256':sha256_file(prep['manifest_path']),
      'primary_method':prep['primary_method'],
      'cases_sha256':sha256_file(prep['cases']),
      'corpus_sha256':sha256_file(prep['corpus']),
      'environment_freeze_sha256':sha256_file(env_freeze),
      'models':[{'requested_model':m.get('requested_model'),'model_digest':m.get('model_digest'),'freeze_sha256':m.get('sha256')} for m,_,_ in models]
    }
    print(json.dumps(verification,indent=2,ensure_ascii=False))
    if args.verify_only: return 0

    td=test_dir; registry=td/'FINAL_TEST_EXECUTION_REGISTRY.json'
    if registry.exists() and not args.acknowledge_rerun.strip():
        raise RuntimeError(f'A final TEST execution is already registered at {registry}. Do not rerun after seeing TEST results. If a genuine technical rerun is unavoidable, use a NEW --outdir and provide --acknowledge-rerun with the reason.')
    out=Path(args.outdir).resolve()
    if out.exists() and any(out.iterdir()): raise RuntimeError(f'Final output directory must be empty/new: {out}')
    out.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    event={'started_utc':started,'lock_sha256':verification['lock_sha256'],'cases_sha256':verification['cases_sha256'],'outdir':str(out.resolve()),'rerun_acknowledgement':args.acknowledge_rerun.strip()}
    registry_event(registry,event)
    json_dump(out/'FINAL_RUN_STARTED.json',{'status':'FINAL_TEST_STARTED',**verification,**event,'scientific_guard':'TEST has begun. Do not change prompts, models, retrieval, guard, decoding, or analysis choices based on TEST outputs.'})

    dec=lock['decoding']; guard=lock['output_guard']; stats=lock['statistics']; model_results=[]
    for m,freeze_path,freeze_obj in models:
        model=m['requested_model']; digest=m.get('model_digest',''); label=slug(model)+'_'+slug(digest[:12])
        md=out/'models'/label; md.mkdir(parents=True,exist_ok=False)
        raw=md/'predictions_raw.jsonl'; guarded=md/'predictions_guarded.jsonl'; ev=md/'generation_eval'; st=md/'stats'
        base=freeze_obj.get('base_url','http://localhost:11434')
        run_py('run_ollama.py','--cases',prep['cases'],'--model',model,'--model-freeze',freeze_path,'--base-url',base,
               '--temperature',str(dec['temperature']),'--seed',str(dec['seed']),'--num-ctx',str(dec['num_ctx']),'--num-predict',str(dec['num_predict']),
               '--top-p',str(dec['top_p']),'--top-k-sampling',str(dec['top_k_sampling']),'--repeat-penalty',str(dec['repeat_penalty']),
               '--timeout',str(dec['timeout_s']),'--retries',str(dec['retries']),'--out',raw)
        infman=load_json(str(raw)+'.manifest.json')
        if infman.get('status')!='PASS_COMPLETE' or not infman.get('model_freeze_verified'):
            raise RuntimeError(f'Inference did not complete cleanly for {model}')
        # Ablation A: provenance filtering only = C3 raw output before post-generation guard.
        prov_ev=md/'ablation_provenance_only_eval'
        run_py('evaluate_generation.py','--cases',prep['cases'],'--predictions',raw,'--corpus',prep['corpus'],'--outdir',prov_ev)
        # Ablation B: output guard only = same contaminated C2 generation, guarded post hoc; no extra LLM call.
        c2guard=md/'predictions_c2_output_guard_only.jsonl'; c2guard_ev=md/'ablation_output_guard_only_eval'
        run_py('apply_output_guard.py','--cases',prep['cases'],'--predictions',raw,'--out',c2guard,'--condition','C2_COMPROMISED_RAG',
               '--max-rationale-chars',str(guard['max_rationale_chars']),'--max-ids',str(guard['max_ids']),'--max-citations',str(guard['max_citations']))
        run_py('evaluate_generation.py','--cases',prep['cases'],'--predictions',c2guard,'--corpus',prep['corpus'],'--outdir',c2guard_ev)
        # Full system = provenance-filtered C3 input + post-generation C3 guard.
        run_py('apply_output_guard.py','--cases',prep['cases'],'--predictions',raw,'--out',guarded,
               '--max-rationale-chars',str(guard['max_rationale_chars']),'--max-ids',str(guard['max_ids']),'--max-citations',str(guard['max_citations']))
        run_py('evaluate_generation.py','--cases',prep['cases'],'--predictions',guarded,'--corpus',prep['corpus'],'--outdir',ev)
        run_py('statistical_tests.py','--per-case',ev/'generation_per_case.csv','--bootstrap-iters',str(stats['bootstrap_iters']),'--seed',str(stats['seed']),'--outdir',st)
        abst=md/'ablation_stats'
        run_py('ablation_tests.py','--full-per-case',ev/'generation_per_case.csv','--provenance-only-per-case',prov_ev/'generation_per_case.csv','--output-guard-only-per-case',c2guard_ev/'generation_per_case.csv','--bootstrap-iters',str(stats['bootstrap_iters']),'--seed',str(stats['seed']),'--outdir',abst)
        files={
          'raw_predictions':raw,'inference_manifest':Path(str(raw)+'.manifest.json'),'guarded_predictions':guarded,
          'per_case':ev/'generation_per_case.csv','summary':ev/'generation_summary.json',
          'paired_tests':st/'paired_tests.csv','stats_manifest':st/'stats_manifest.json',
          'provenance_only_per_case':prov_ev/'generation_per_case.csv','provenance_only_summary':prov_ev/'generation_summary.json',
          'output_guard_only_predictions':c2guard,'output_guard_only_per_case':c2guard_ev/'generation_per_case.csv','output_guard_only_summary':c2guard_ev/'generation_summary.json',
          'ablation_paired_tests':abst/'ablation_paired_tests.csv','ablation_stats_manifest':abst/'ablation_stats_manifest.json'
        }
        model_results.append({'requested_model':model,'resolved_name':m.get('resolved_name'),'model_digest':digest,'model_freeze_sha256':m['sha256'],'directory':str(md.relative_to(out)),
                              'artifacts':{k:{'path':str(v.relative_to(out)),'sha256':sha256_file(v)} for k,v in files.items()}})

    finished=datetime.now(timezone.utc).isoformat()
    manifest={
      'status':'PASS_FINAL_TEST_COMPLETE','manifest_version':'1.6','started_utc':started,'finished_utc':finished,
      'rerun_acknowledgement':args.acknowledge_rerun.strip(),
      'test_lock':{'path':str(lock_path),'sha256':sha256_file(lock_path)},
      'phase1':{'release_sha256':p1['release_sha256'],'benchmark_sha256':p1['benchmark_sha256'],'nist_source_sha256':p1['nist_source_sha256']},
      'test_preparation':{'manifest_path':str(prep['manifest_path']),'manifest_sha256':sha256_file(prep['manifest_path']),'primary_method':prep['primary_method'],
                          'cases_sha256':sha256_file(prep['cases']),'corpus_sha256':sha256_file(prep['corpus']),'attack_fixtures_sha256':sha256_file(prep['attacks'])},
      'environment_freeze_sha256':sha256_file(env_freeze),
      'models':model_results,
      'scientific_guard':'This manifest is valid only if verify_final_results.py passes. TEST outputs must not be used to retune the locked system.'
    }
    json_dump(out/'FINAL_RUN_MANIFEST.json',manifest)
    # Verify immediately before producing any publication-oriented derived artifacts.
    verify_args=['--final-run-dir',str(out),'--phase1-run',str(phase1_run),'--phase2-test-dir',str(test_dir),
                 '--test-lock',str(lock_path),'--environment-freeze',str(env_freeze)]
    for _,p,_ in models:
        verify_args += ['--model-freeze',str(p)]
    run_py('verify_final_results.py',*verify_args)
    run_py('make_results_tables.py','--final-run-dir',out,'--phase2-test-dir',test_dir,'--outdir',out/'publication_tables')
    try:
        run_py('make_figures.py','--final-run-dir',out,'--phase2-test-dir',test_dir,'--outdir',out/'publication_figures')
    except subprocess.CalledProcessError:
        # Scientific outputs remain valid; publication figure generation is derivative.
        print('WARNING: figure generation failed; core final results remain preserved. Run make_figures.py after fixing the plotting environment.',file=sys.stderr)
    print(json.dumps(manifest,indent=2,ensure_ascii=False))
    return 0


if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(2)
