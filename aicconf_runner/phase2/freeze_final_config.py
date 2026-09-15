#!/usr/bin/env python3
"""Freeze the exact configuration permitted for one-shot TEST preparation/run."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from common import sha256_file, json_dump

HERE=Path(__file__).resolve().parent
CODE_FILES=[
 'build_target_corpus.py','run_retrieval.py','run_dense_retrieval.py','make_attack_fixtures.py',
 'compose_prompt_cases.py','apply_output_guard.py','evaluate_generation.py','statistical_tests.py',
 'run_ollama.py','ollama_preflight.py','environment_preflight.py','prepare_phase2.py',
 'run_final_test.py','verify_final_results.py','make_results_tables.py','make_figures.py',
 'final_common.py','common.py','ablation_tests.py','freeze_final_config.py','requirements.txt'
]
ATTACKS=['authority_spoof','evidence_conflict','fabricated_control','override','schema_break']


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase1-run',required=True)
    ap.add_argument('--model-freeze',action='append',required=True)
    ap.add_argument('--environment-freeze',required=True)
    ap.add_argument('--retrieval-method',action='append',choices=['bm25','tfidf'],default=None)
    ap.add_argument('--primary-retrieval-method',choices=['bm25','tfidf'],default='bm25')
    ap.add_argument('--context-k',type=int,default=5); ap.add_argument('--attack-rank',type=int,default=1); ap.add_argument('--top-k',type=int,default=10)
    ap.add_argument('--temperature',type=float,default=0.0); ap.add_argument('--seed',type=int,default=2027); ap.add_argument('--num-ctx',type=int,default=8192); ap.add_argument('--num-predict',type=int,default=512)
    ap.add_argument('--top-p',type=float,default=1.0); ap.add_argument('--top-k-sampling',type=int,default=40); ap.add_argument('--repeat-penalty',type=float,default=1.1)
    ap.add_argument('--timeout',type=int,default=180); ap.add_argument('--retries',type=int,default=2)
    ap.add_argument('--guard-max-rationale-chars',type=int,default=1500); ap.add_argument('--guard-max-ids',type=int,default=20); ap.add_argument('--guard-max-citations',type=int,default=20)
    ap.add_argument('--bootstrap-iters',type=int,default=10000); ap.add_argument('--stats-seed',type=int,default=2027)
    ap.add_argument('--out',default='FINAL_CONFIG_LOCK.json'); args=ap.parse_args()
    if args.top_k < args.context_k: raise SystemExit('ERROR: top-k must be >= context-k')
    if not (1 <= args.attack_rank <= args.context_k): raise SystemExit('ERROR: attack-rank must be within context budget')
    if args.retries < 0 or args.timeout < 1: raise SystemExit('ERROR: invalid timeout/retries')
    methods=args.retrieval_method or ['bm25','tfidf']
    methods=list(dict.fromkeys(methods))
    if args.primary_retrieval_method not in methods: raise SystemExit('ERROR: primary retrieval method must be among retrieval methods')
    p1=Path(args.phase1_run).resolve(); release=p1/'benchmark_frozen'/'PHASE1_RELEASE_FREEZE.json'; bench=p1/'benchmark_frozen'/'benchmark.csv'; nist=p1/'sources'/'original'/'800-53-r5-controls.json'
    fr=json.loads(release.read_text(encoding='utf-8'))
    if fr.get('status')!='PASS_PHASE1_FROZEN': raise SystemExit('ERROR: Phase-1 not frozen')
    envp=Path(args.environment_freeze).resolve(); env=json.loads(envp.read_text(encoding='utf-8'))
    if env.get('status')!='PASS_ENVIRONMENT_FROZEN': raise SystemExit('ERROR: environment freeze not PASS')
    models=[]; seen=set()
    for raw in args.model_freeze:
        pp=Path(raw).resolve(); x=json.loads(pp.read_text(encoding='utf-8')); h=sha256_file(pp)
        if x.get('status')!='PASS_OLLAMA_MODEL_FROZEN': raise SystemExit(f'ERROR: model freeze not PASS: {pp}')
        if h in seen: raise SystemExit(f'ERROR: duplicate model freeze bytes: {pp}')
        seen.add(h)
        models.append({'path_at_lock_time':str(pp),'sha256':h,'requested_model':x.get('requested_model'),'resolved_name':x.get('resolved_name'),'model_digest':x.get('model_digest'),'ollama_version':x.get('ollama_version')})
    missing=[f for f in CODE_FILES if not (HERE/f).exists()]
    if missing: raise SystemExit(f'ERROR: lock code file(s) missing: {missing}')
    lock={
      'status':'LOCKED_FOR_TEST','lock_version':'1.6',
      'phase1':{'release_sha256':sha256_file(release),'benchmark_sha256':sha256_file(bench),'nist_source_sha256':sha256_file(nist)},
      'phase2_code':{f:sha256_file(HERE/f) for f in CODE_FILES},
      'environment':{'path_at_lock_time':str(envp),'sha256':sha256_file(envp),'python':env.get('python',{}),'packages':env.get('packages',{})},
      'retrieval':{'methods':methods,'primary_method':args.primary_retrieval_method,'top_k':args.top_k,'context_k':args.context_k},
      'attack':{'attack_rank':args.attack_rank,'templates':ATTACKS},
      'models':models,
      'decoding':{'temperature':args.temperature,'seed':args.seed,'num_ctx':args.num_ctx,'num_predict':args.num_predict,'top_p':args.top_p,'top_k_sampling':args.top_k_sampling,'repeat_penalty':args.repeat_penalty,'timeout_s':args.timeout,'retries':args.retries},
      'output_guard':{'max_rationale_chars':args.guard_max_rationale_chars,'max_ids':args.guard_max_ids,'max_citations':args.guard_max_citations,'guarded_conditions':['C3_HARDENED_RAG']},
      'statistics':{'bootstrap_iters':args.bootstrap_iters,'seed':args.stats_seed,'correction':'Holm within each pre-registered hypothesis family','independent_unit':'query_id'},
      'scientific_gate':'Any code/config/model/environment/source hash mismatch invalidates this lock. After TEST begins, do not retune from TEST outputs.'
    }
    json_dump(Path(args.out).resolve(),lock); print(json.dumps(lock,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
