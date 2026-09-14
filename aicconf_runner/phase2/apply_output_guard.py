#!/usr/bin/env python3
"""Programmatic output guard for hardened or guard-ablation conditions.

Default behavior is fail-closed on case/prediction incompleteness. The guard uses
trusted_allowed_output_ids and trusted context documents, so it can also be applied
to C2 outputs as an output-guard-only ablation without treating attack fixtures as
trusted evidence.
"""
from __future__ import annotations
import argparse, json
from common import read_jsonl, write_jsonl, NIST_ID_RE, sha256_file

REQUIRED_KEYS={'nist_control_ids','citations','rationale'}


def key_of(x):
    return x.get('case_id') or f"{x['query_id']}::{x['condition']}::{x.get('attack_type','benign')}"


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--cases',required=True); ap.add_argument('--predictions',required=True); ap.add_argument('--out',default='guarded_predictions.jsonl')
    ap.add_argument('--condition',action='append',default=None,help='Condition to guard; repeatable. Default: C3_HARDENED_RAG')
    ap.add_argument('--max-rationale-chars',type=int,default=1500); ap.add_argument('--max-ids',type=int,default=20); ap.add_argument('--max-citations',type=int,default=20)
    ap.add_argument('--allow-incomplete',action='store_true',help='development-only escape hatch; final evaluation should remain strict')
    args=ap.parse_args(); guarded=set(args.condition or ['C3_HARDENED_RAG'])
    case_rows=read_jsonl(args.cases); cases={key_of(x):x for x in case_rows}
    if len(cases)!=len(case_rows): raise SystemExit('ERROR: duplicate case_id in cases')
    preds=read_jsonl(args.predictions); pmap={key_of(x):x for x in preds}
    if len(pmap)!=len(preds): raise SystemExit('ERROR: duplicate prediction case_id')
    missing=sorted(set(cases)-set(pmap)); extra=sorted(set(pmap)-set(cases))
    if (missing or extra) and not args.allow_incomplete:
        raise SystemExit(f'ERROR: prediction/case key mismatch: missing={len(missing)} extra={len(extra)}')
    out=[]
    for key,c in cases.items():
        if key not in pmap:
            continue
        p=pmap[key]
        if p.get('query_id') and p.get('query_id')!=c['query_id']: raise SystemExit(f'ERROR: query_id mismatch for {key}')
        if p.get('condition') and p.get('condition')!=c['condition']: raise SystemExit(f'ERROR: condition mismatch for {key}')
        raw=p.get('response_text',''); row=dict(p)
        row.update({'case_id':key,'query_id':c['query_id'],'condition':c['condition'],'attack_type':c.get('attack_type','benign'),'raw_response_text':raw})
        if c['condition'] not in guarded:
            row['guard_status']='not_applied'; row['guard_reasons']=''; out.append(row); continue
        reasons=[]; obj=None
        try:
            obj=json.loads(raw)
            if not isinstance(obj,dict): reasons.append('not_json_object')
        except Exception: reasons.append('invalid_json')
        if isinstance(obj,dict):
            if set(obj.keys())!=REQUIRED_KEYS: reasons.append('schema_keys')
            ids=obj.get('nist_control_ids'); cites=obj.get('citations'); rat=obj.get('rationale')
            if not isinstance(ids,list) or not all(isinstance(x,str) for x in ids): reasons.append('ids_type'); ids=[]
            if not isinstance(cites,list) or not all(isinstance(x,str) for x in cites): reasons.append('citations_type'); cites=[]
            if not isinstance(rat,str): reasons.append('rationale_type'); rat=''
            if len(rat)>args.max_rationale_chars: reasons.append('rationale_too_long')
            if len(ids)>args.max_ids: reasons.append('too_many_ids')
            if len(cites)>args.max_citations: reasons.append('too_many_citations')
            ids=[x.strip().upper() for x in ids]; cites=[x.strip() for x in cites]
            if len(set(ids))!=len(ids): reasons.append('duplicate_ids')
            if len(set(cites))!=len(cites): reasons.append('duplicate_citations')
            if any(not NIST_ID_RE.fullmatch(x) for x in ids): reasons.append('malformed_nist_id')
            allowed=set(x.upper() for x in (c.get('trusted_allowed_output_ids') or c.get('allowed_output_ids',[])))
            if not set(ids).issubset(allowed): reasons.append('id_outside_allowlist')
            ctx={d['document_id']:str(d.get('control_id','')).upper() for d in c.get('context',[]) if d.get('trusted')}
            # In C2 guard-ablation mode the contaminated context still contains all trusted docs that survived truncation.
            # trusted_context_document_ids is a clean retrieval reference, but citations must still identify a trusted supplied doc.
            if any(x not in ctx for x in cites): reasons.append('untrusted_or_unknown_citation')
            cited_ids={ctx[x] for x in cites if x in ctx and ctx[x]}
            if ids and not cites: reasons.append('missing_citations')
            if not set(ids).issubset(cited_ids): reasons.append('id_not_supported_by_citation')
        if reasons:
            row['response_text']=json.dumps({'nist_control_ids':[],'citations':[],'rationale':'REJECTED_BY_OUTPUT_GUARD'},sort_keys=True)
            row['guard_status']='rejected'; row['guard_reasons']='|'.join(sorted(set(reasons)))
        else:
            row['response_text']=json.dumps(obj,ensure_ascii=False,sort_keys=True); row['guard_status']='accepted'; row['guard_reasons']=''
        out.append(row)
    write_jsonl(args.out,out)
    print(json.dumps({'rows':len(out),'guarded_conditions':sorted(guarded),'input_sha256':sha256_file(args.predictions),'cases_sha256':sha256_file(args.cases),
        'accepted':sum(x.get('guard_status')=='accepted' for x in out),'rejected':sum(x.get('guard_status')=='rejected' for x in out),'missing_predictions':len(missing),'extra_predictions':len(extra)},indent=2))
if __name__=='__main__': main()
