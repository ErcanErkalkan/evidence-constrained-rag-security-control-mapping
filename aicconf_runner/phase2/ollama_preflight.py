#!/usr/bin/env python3
"""Freeze local Ollama runtime/model identity for reproducible experiments."""
from __future__ import annotations
import argparse, json, hashlib, platform, sys, urllib.request
from pathlib import Path
from common import json_dump


def http_json(url:str, payload:dict|None=None, timeout:int=30):
    data=None if payload is None else json.dumps(payload).encode('utf-8')
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'} if data else {})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def canonical_sha(obj)->str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()


def probe(base_url:str, model:str, timeout:int=30)->dict:
    base=base_url.rstrip('/')
    version=http_json(base+'/api/version',timeout=timeout)
    tags=http_json(base+'/api/tags',timeout=timeout)
    show=http_json(base+'/api/show',{'model':model},timeout=timeout)
    entries=tags.get('models',[]) if isinstance(tags,dict) else []
    candidates=[x for x in entries if x.get('name')==model or x.get('model')==model]
    if not candidates:
        # Accept exact prefix aliases only if uniquely resolved by Ollama's own list.
        candidates=[x for x in entries if str(x.get('name','')).split(':')[0]==model.split(':')[0]]
    if len(candidates)!=1:
        raise RuntimeError(f'Could not uniquely resolve model {model!r} in /api/tags; matches={len(candidates)}')
    tag=candidates[0]
    return {
      'status':'PASS_OLLAMA_MODEL_FROZEN','base_url':base_url,'requested_model':model,'resolved_name':tag.get('name') or tag.get('model'),
      'model_digest':tag.get('digest',''),'model_size_bytes':tag.get('size'),'modified_at':tag.get('modified_at',''),
      'details':tag.get('details',{}),'ollama_version':version.get('version','') if isinstance(version,dict) else '',
      'show_response_sha256':canonical_sha(show),'show_details':show.get('details',{}) if isinstance(show,dict) else {},
      'show_model_info_sha256':canonical_sha(show.get('model_info',{})) if isinstance(show,dict) else '',
      'show_parameters_sha256':hashlib.sha256(str(show.get('parameters','')).encode('utf-8')).hexdigest() if isinstance(show,dict) else '',
      'runtime':{'python':sys.version.split()[0],'platform':platform.platform(),'machine':platform.machine()},
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model',required=True); ap.add_argument('--base-url',default='http://localhost:11434'); ap.add_argument('--timeout',type=int,default=30); ap.add_argument('--out',default='OLLAMA_MODEL_FREEZE.json'); args=ap.parse_args()
    fr=probe(args.base_url,args.model,args.timeout); json_dump(args.out,fr); print(json.dumps(fr,indent=2,ensure_ascii=False))
if __name__=='__main__':
    try: main()
    except Exception as e: print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(2)
