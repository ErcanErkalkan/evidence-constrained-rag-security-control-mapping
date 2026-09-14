#!/usr/bin/env python3
"""Reproducible local Ollama adapter for prepared prompt cases.

DEV runs may use --resume. Progress is appended after every completed case so a
PowerShell/Windows interruption does not discard hours of local inference. Resume
is deliberately strict: the existing rows must be an exact prefix of the current
case file and must match the frozen model/runtime identity and decoding settings.
Final TEST orchestration still starts in a fresh output directory and does not use
resume by default.
"""
from __future__ import annotations
import argparse, json, time, urllib.request, sys, os
from pathlib import Path
from common import read_jsonl, sha256_file, json_dump
from ollama_preflight import probe


def call(base, model, system, user, options, timeout):
    payload=json.dumps({'model':model,'stream':False,'messages':[{'role':'system','content':system},{'role':'user','content':user}], 'options':options}).encode()
    req=urllib.request.Request(base.rstrip('/')+'/api/chat',data=payload,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        obj=json.loads(r.read().decode('utf-8'))
    return obj.get('message',{}).get('content',''),obj


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def verify_resume(existing, cases, model, runtime, case_hash, options):
    if len(existing) > len(cases):
        raise SystemExit('ERROR: resume output has more rows than the current case file')
    for i,row in enumerate(existing):
        c=cases[i]
        if row.get('case_id') != c.get('case_id'):
            raise SystemExit(f'ERROR: resume output is not an exact prefix at row {i+1}')
        if row.get('cases_sha256') != case_hash:
            raise SystemExit(f'ERROR: resume cases hash mismatch at row {i+1}')
        if row.get('model') != model:
            raise SystemExit(f'ERROR: resume model mismatch at row {i+1}')
        if row.get('model_digest') != runtime.get('model_digest',''):
            raise SystemExit(f'ERROR: resume model digest mismatch at row {i+1}')
        if row.get('ollama_version') != runtime.get('ollama_version',''):
            raise SystemExit(f'ERROR: resume Ollama version mismatch at row {i+1}')
        if row.get('decoding_options') != options:
            raise SystemExit(f'ERROR: resume decoding options mismatch at row {i+1}')
    return len(existing)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cases',required=True)
    ap.add_argument('--model',required=True)
    ap.add_argument('--out',default='model_predictions.jsonl')
    ap.add_argument('--base-url',default='http://localhost:11434')
    ap.add_argument('--model-freeze',help='OLLAMA_MODEL_FREEZE.json to verify exact model/runtime identity')
    ap.add_argument('--temperature',type=float,default=0.0)
    ap.add_argument('--seed',type=int,default=2027)
    ap.add_argument('--num-ctx',type=int,default=8192)
    ap.add_argument('--num-predict',type=int,default=512)
    ap.add_argument('--top-p',type=float,default=1.0)
    ap.add_argument('--top-k-sampling',type=int,default=40)
    ap.add_argument('--repeat-penalty',type=float,default=1.1)
    ap.add_argument('--timeout',type=int,default=180)
    ap.add_argument('--retries',type=int,default=2)
    ap.add_argument('--limit',type=int,default=0)
    ap.add_argument('--resume',action='store_true',help='DEV only: continue an exact-prefix partial output safely')
    args=ap.parse_args()

    cases=read_jsonl(args.cases)
    cases=cases[:args.limit] if args.limit else cases
    if not cases:
        raise SystemExit('ERROR: zero cases')
    case_ids=[c.get('case_id') for c in cases]
    if None in case_ids or len(case_ids)!=len(set(case_ids)):
        raise SystemExit('ERROR: cases require unique case_id')

    runtime=probe(args.base_url,args.model,min(args.timeout,30))
    freeze_verified=False; freeze_sha=''
    if args.model_freeze:
        fpath=Path(args.model_freeze)
        frozen=json.loads(fpath.read_text(encoding='utf-8'))
        freeze_sha=sha256_file(fpath)
        checks=[
            ('status',frozen.get('status'),'PASS_OLLAMA_MODEL_FROZEN'),
            ('requested_model',frozen.get('requested_model'),args.model),
            ('resolved_name',frozen.get('resolved_name'),runtime.get('resolved_name')),
            ('model_digest',frozen.get('model_digest'),runtime.get('model_digest')),
            ('ollama_version',frozen.get('ollama_version'),runtime.get('ollama_version')),
            ('show_response_sha256',frozen.get('show_response_sha256'),runtime.get('show_response_sha256')),
            ('show_model_info_sha256',frozen.get('show_model_info_sha256'),runtime.get('show_model_info_sha256')),
            ('show_parameters_sha256',frozen.get('show_parameters_sha256'),runtime.get('show_parameters_sha256')),
        ]
        bad=[x for x in checks if x[1]!=x[2]]
        if bad:
            raise SystemExit('ERROR: model-freeze mismatch: '+repr(bad))
        freeze_verified=True

    options={
        'temperature':args.temperature,'seed':args.seed,'num_ctx':args.num_ctx,
        'num_predict':args.num_predict,'top_p':args.top_p,
        'top_k':args.top_k_sampling,'repeat_penalty':args.repeat_penalty
    }
    out=Path(args.out)
    case_hash=sha256_file(args.cases)
    start_index=0
    failures=[]

    if out.exists():
        if not args.resume:
            raise SystemExit(f'ERROR: output already exists: {out}. Use --resume for a DEV continuation or choose a new --out.')
        existing=read_jsonl(out)
        start_index=verify_resume(existing,cases,args.model,runtime,case_hash,options)
        failures=[r['case_id'] for r in existing if r.get('error')]
        print(f'RESUME: {start_index}/{len(cases)} cases already persisted and verified.')
    elif args.resume:
        print('RESUME: output does not exist yet; starting a new DEV run.')

    progress=Path(str(out)+'.progress.json')
    for i in range(start_index,len(cases)):
        c=cases[i]
        t=time.perf_counter(); text=''; err=''; attempts=0
        for attempt in range(args.retries+1):
            attempts=attempt+1
            try:
                text,_=call(args.base_url,args.model,c['system_prompt'],c['user_prompt'],options,args.timeout)
                err=''; break
            except Exception as e:
                err=f'{type(e).__name__}: {e}'
                if attempt < args.retries:
                    time.sleep(min(2**attempt,8))
        if err:
            failures.append(c['case_id'])
        row={
            'case_id':c['case_id'],'query_id':c['query_id'],'condition':c['condition'],
            'attack_type':c.get('attack_type','benign'),'model':args.model,
            'model_digest':runtime.get('model_digest',''),'ollama_version':runtime.get('ollama_version',''),
            'response_text':text,'error':err,'attempts':attempts,
            'latency_s':round(time.perf_counter()-t,6),'cases_sha256':case_hash,
            'decoding_options':options,
        }
        append_jsonl(out,row)
        json_dump(progress,{
            'status':'RUNNING' if i+1 < len(cases) else 'INFERENCE_LOOP_COMPLETE',
            'completed':i+1,'total':len(cases),'last_case_id':c['case_id'],
            'cases_sha256':case_hash,'model':args.model,
            'model_digest':runtime.get('model_digest',''),'ollama_version':runtime.get('ollama_version',''),
            'decoding_options':options,'failures_so_far':failures,
        })
        print(f'[{i+1}/{len(cases)}] {c["case_id"]} {"OK" if not err else "ERROR"}', flush=True)

    rows=read_jsonl(out)
    if len(rows)!=len(cases):
        raise SystemExit(f'ERROR: persisted row count mismatch after run: {len(rows)} != {len(cases)}')
    manifest={
        'status':'PASS_COMPLETE' if not failures else 'FAIL_INFERENCE_ERRORS',
        'cases_sha256':case_hash,'predictions_sha256':sha256_file(out),
        'case_count':len(cases),'failures':failures,
        'model':args.model,'model_digest':runtime.get('model_digest',''),
        'ollama_version':runtime.get('ollama_version',''),'runtime_probe':runtime,
        'model_freeze_sha256':freeze_sha,'model_freeze_verified':freeze_verified,
        'decoding_options':options,'timeout_s':args.timeout,'retries':args.retries,
        'resume_capable':True,
        'scientific_note':'No API-level JSON format/schema coercion is used; schema robustness remains part of the measured behavior.'
    }
    json_dump(str(out)+'.manifest.json',manifest)
    json_dump(progress,{'status':manifest['status'],'completed':len(cases),'total':len(cases),'manifest':str(out)+'.manifest.json'})
    print(json.dumps(manifest,indent=2,ensure_ascii=False))
    if failures:
        raise SystemExit(2)

if __name__=='__main__':
    main()
