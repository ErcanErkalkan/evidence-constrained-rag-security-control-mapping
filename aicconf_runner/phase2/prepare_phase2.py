#!/usr/bin/env python3
"""Gate-aware Phase-2 preparation from a PASS Phase-1 release.

DEV is default. TEST requires FINAL_CONFIG_LOCK.json and verifies source, benchmark,
Phase-2 code, retrieval/context/attack parameters before any test artifact is made.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOCKED_CODE_FILES=['build_target_corpus.py','run_retrieval.py','run_dense_retrieval.py','make_attack_fixtures.py','compose_prompt_cases.py','apply_output_guard.py','evaluate_generation.py','statistical_tests.py','run_ollama.py','ollama_preflight.py','environment_preflight.py','prepare_phase2.py','run_final_test.py','verify_final_results.py','make_results_tables.py','make_figures.py','final_common.py','common.py','ablation_tests.py','freeze_final_config.py','requirements.txt']


def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()


def run(*args):
 cmd=[sys.executable,*map(str,args)]; print('+',' '.join(cmd)); subprocess.run(cmd,check=True,cwd=HERE)


def main()->int:
 ap=argparse.ArgumentParser()
 ap.add_argument('--phase1-run',required=True,help='Phase-1 run directory containing sources/original and benchmark_frozen')
 ap.add_argument('--outdir',default='phase2_prepared'); ap.add_argument('--split',choices=['dev','test'],default='dev')
 ap.add_argument('--test-lock',help='Required for --split test; exact config/hash lock')
 ap.add_argument('--context-k',type=int,default=5); ap.add_argument('--attack-rank',type=int,default=1); ap.add_argument('--top-k',type=int,default=10)
 args=ap.parse_args()
 if args.top_k < args.context_k: raise RuntimeError('--top-k must be >= --context-k')
 if not (1 <= args.attack_rank <= args.context_k): raise RuntimeError('--attack-rank must be within 1..context-k')
 p1=Path(args.phase1_run).resolve(); freeze=p1/'benchmark_frozen'/'PHASE1_RELEASE_FREEZE.json'; bench=p1/'benchmark_frozen'/'benchmark.csv'; nist=p1/'sources'/'original'/'800-53-r5-controls.json'
 if not freeze.exists(): raise FileNotFoundError(f'Phase-1 release freeze missing: {freeze}')
 fr=json.loads(freeze.read_text(encoding='utf-8'))
 if fr.get('status')!='PASS_PHASE1_FROZEN': raise RuntimeError(f"Phase-1 status is not PASS_PHASE1_FROZEN: {fr.get('status')}")
 if not bench.exists() or not nist.exists(): raise FileNotFoundError('Frozen benchmark or NIST source missing')
 expected_bench=fr.get('artifacts',{}).get('benchmark.csv'); expected_nist=fr.get('source_freeze',{}).get('files',{}).get('nist',{}).get('sha256')
 if not expected_bench or sha256(bench)!=expected_bench: raise RuntimeError('benchmark.csv hash mismatch against Phase-1 release')
 if not expected_nist or sha256(nist)!=expected_nist: raise RuntimeError('NIST source hash mismatch against Phase-1 source freeze')
 methods=['bm25','tfidf']; lock=None
 if args.split=='test':
  if not args.test_lock: raise RuntimeError('--split test requires --test-lock')
  lock_path=Path(args.test_lock).resolve(); lock=json.loads(lock_path.read_text(encoding='utf-8'))
  if lock.get('status')!='LOCKED_FOR_TEST': raise RuntimeError('test lock status must be LOCKED_FOR_TEST')
  if lock.get('phase1',{}).get('release_sha256')!=sha256(freeze): raise RuntimeError('test lock Phase-1 release hash mismatch')
  if lock.get('phase1',{}).get('benchmark_sha256')!=sha256(bench): raise RuntimeError('test lock benchmark hash mismatch')
  if lock.get('phase1',{}).get('nist_source_sha256')!=sha256(nist): raise RuntimeError('test lock NIST hash mismatch')
  r=lock.get('retrieval',{}); a=lock.get('attack',{})
  if int(r.get('top_k',-1))!=args.top_k or int(r.get('context_k',-1))!=args.context_k or int(a.get('attack_rank',-1))!=args.attack_rank:
   raise RuntimeError('test CLI parameters do not match FINAL_CONFIG_LOCK')
  methods=list(r.get('methods',[]))
  expected_attacks=['authority_spoof','evidence_conflict','fabricated_control','override','schema_break']
  if sorted(lock.get('attack',{}).get('templates',[]))!=expected_attacks: raise RuntimeError('test lock attack template set mismatch')
  if any(m not in {'bm25','tfidf'} for m in methods):
   raise RuntimeError('prepare_phase2 currently supports locked bm25/tfidf preparation; dense is run separately with its pinned model')
  for f in LOCKED_CODE_FILES:
   expected=lock.get('phase2_code',{}).get(f)
   if not expected or sha256(HERE/f)!=expected: raise RuntimeError(f'Phase-2 code hash mismatch for {f}')
 out=Path(args.outdir).resolve(); out.mkdir(parents=True,exist_ok=True); corpus=out/'corpus_primary'; attacks=out/'attack_fixtures.csv'
 run(HERE/'build_target_corpus.py','--nist-catalog',nist,'--nist-version','NIST SP 800-53 Rev.5 Update 1 (Dec 2024)','--outdir',corpus)
 cman=json.loads((corpus/'corpus_manifest.json').read_text())
 if cman.get('records')!=1189 or cman.get('source_sha256')!=expected_nist or cman.get('blank_document_text_ids'):
  raise RuntimeError('NIST retrieval corpus validation failed')
 run(HERE/'make_attack_fixtures.py','--benchmark',bench,'--out',attacks)
 prepared={}
 for method in methods:
  rdir=out/f'retrieval_{args.split}_{method}'
  run(HERE/'run_retrieval.py','--benchmark',bench,'--corpus',corpus/'nist_corpus.csv','--method',method,'--top-k',str(args.top_k),'--split',args.split,'--outdir',rdir)
  rfile=rdir/f'{method}_retrieval.csv'; cases=out/f'prompt_cases_{args.split}_{method}.jsonl'
  run(HERE/'compose_prompt_cases.py','--benchmark',bench,'--corpus',corpus/'nist_corpus.csv','--retrieval',rfile,'--attacks',attacks,'--context-k',str(args.context_k),'--attack-rank',str(args.attack_rank),'--split',args.split,'--out',cases)
  mfile=rdir/f'{method}_metrics.json'
  prepared[method]={'retrieval':str(rfile),'retrieval_sha256':sha256(rfile),'metrics':str(mfile),'metrics_sha256':sha256(mfile),'cases':str(cases),'cases_sha256':sha256(cases)}
 manifest={
  'status':'DEV_PREP_READY_NO_MODEL_RUN' if args.split=='dev' else 'TEST_PREPARED_UNDER_VERIFIED_LOCK',
  'split':args.split,'phase1_release_freeze_sha256':sha256(freeze),'benchmark_sha256':sha256(bench),'nist_source_sha256':sha256(nist),
  'corpus_sha256':sha256(corpus/'nist_corpus.csv'),'attack_fixtures_sha256':sha256(attacks),'context_k':args.context_k,'attack_rank':args.attack_rank,'top_k':args.top_k,
  'methods':prepared,'test_lock_sha256':sha256(lock_path) if args.test_lock else '',
  'scientific_guard':'DEV may be used for tuning. TEST is prepared only when source/code/config hashes match FINAL_CONFIG_LOCK; do not retune from TEST outputs.'
 }
 (out/f'PHASE2_{args.split.upper()}_PREP_MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps(manifest,indent=2,ensure_ascii=False)); return 0
if __name__=='__main__':
 try: raise SystemExit(main())
 except Exception as e: print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(2)
