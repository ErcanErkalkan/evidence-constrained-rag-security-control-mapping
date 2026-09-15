#!/usr/bin/env python3
"""Optional dense-embedding retrieval with explicitly pinned model.

No automatic fallback is allowed. Metrics are computed from the complete ranking;
--top-k only controls how many ranked documents are persisted for RAG.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from common import read_csv, split_ids, write_csv, json_dump, sha256_file

REPORT_KS=(1,5,10)


def metrics(gold, ranked):
    g=set(gold); out={}
    for k in REPORT_KS:
        out[f'recall@{k}']=len(g&set(ranked[:k]))/len(g) if g else 0.0
        out[f'hit@{k}']=1.0 if g&set(ranked[:k]) else 0.0
    out['mrr']=next((1/i for i,c in enumerate(ranked,1) if c in g),0.0)
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--benchmark',required=True); ap.add_argument('--corpus',required=True)
    ap.add_argument('--model',required=True,help='Pinned sentence-transformers model path or exact model identifier')
    ap.add_argument('--top-k',type=int,default=10); ap.add_argument('--outdir',default='retrieval_out')
    ap.add_argument('--split',choices=['dev','test','all'],default='all'); args=ap.parse_args()
    if args.top_k < 1: raise SystemExit('ERROR: --top-k must be >=1')
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise SystemExit('ERROR: install sentence-transformers; no fallback is permitted for dense baseline') from e
    b=read_csv(args.benchmark); c=read_csv(args.corpus)
    if args.split!='all': b=[r for r in b if r.get('split')==args.split]
    if not b: raise SystemExit('ERROR: no benchmark rows selected')
    if not c: raise SystemExit('ERROR: corpus empty')
    ids=[r['control_id'].strip().upper() for r in c]
    if len(set(ids))!=len(ids): raise SystemExit('ERROR: duplicate corpus control IDs')
    model=SentenceTransformer(args.model)
    D=model.encode([r['document_text'] for r in c],normalize_embeddings=True,show_progress_bar=False)
    Q=model.encode([r['ccm_control_text'] for r in b],normalize_embeddings=True,show_progress_bar=False)
    S=np.asarray(Q) @ np.asarray(D).T
    rows=[]; vals=[]
    for br,sim in zip(b,S):
        full_idx=sorted(range(len(c)),key=lambda i:(-float(sim[i]),c[i]['control_id']))
        full_ranked=[c[i]['control_id'].upper() for i in full_idx]
        idx=full_idx[:args.top_k]; persisted=[c[i]['control_id'].upper() for i in idx]
        gold=split_ids(br['gold_nist_control_ids']); m=metrics(gold,full_ranked); vals.append(m)
        rows.append({'query_id':br['query_id'],'split':br.get('split',''),'method':'dense','model':args.model,'gold_ids':'|'.join(gold),
                     'ranked_ids':'|'.join(persisted),'scores_json':json.dumps([round(float(sim[i]),8) for i in idx]),
                     **{k:f'{v:.10f}' for k,v in m.items()}})
    agg={k:sum(v[k] for v in vals)/len(vals) for k in vals[0]}; agg.update({'queries':len(vals),'method':'dense','model':args.model,
        'persisted_top_k':args.top_k,'metric_cutoffs':list(REPORT_KS),'split':args.split,'benchmark_sha256':sha256_file(args.benchmark),'corpus_sha256':sha256_file(args.corpus)})
    od=Path(args.outdir); od.mkdir(parents=True,exist_ok=True); write_csv(od/'dense_retrieval.csv',rows); json_dump(od/'dense_metrics.json',agg); print(json.dumps(agg,indent=2))
if __name__=='__main__': main()
