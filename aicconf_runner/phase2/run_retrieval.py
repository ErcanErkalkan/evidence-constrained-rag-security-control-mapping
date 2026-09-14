#!/usr/bin/env python3
"""Deterministic multi-label retrieval baselines: BM25 and TF-IDF.

Metrics are always computed from the FULL ranking, independent of the number of
ranked items persisted to CSV. This avoids silently underestimating Recall@5/10
when --top-k is smaller than the reporting cutoff.
"""
from __future__ import annotations
import argparse, json, math
from collections import Counter
from pathlib import Path
from common import read_csv, split_ids, tokenize, write_csv, json_dump, sha256_file

REPORT_KS=(1,5,10)


def bm25_rank(corpus, queries, k1=1.5,b=0.75):
    docs=[tokenize(r['document_text']) for r in corpus]
    N=len(docs); avgdl=sum(map(len,docs))/max(N,1)
    df=Counter()
    for d in docs:
        for t in set(d): df[t]+=1
    idf={t:math.log(1+(N-n+0.5)/(n+0.5)) for t,n in df.items()}
    tfs=[Counter(d) for d in docs]
    for q in queries:
        qt=tokenize(q)
        scores=[]
        for i,(tf,d) in enumerate(zip(tfs,docs)):
            score=0.0; dl=len(d)
            for t in qt:
                f=tf.get(t,0)
                if not f: continue
                den=f+k1*(1-b+b*dl/max(avgdl,1e-12))
                score += idf.get(t,0.0)*f*(k1+1)/den
            scores.append((score,i))
        scores.sort(key=lambda x:(-x[0], corpus[x[1]]['control_id']))
        yield scores


def tfidf_rank(corpus, queries):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError as e: raise SystemExit('scikit-learn required for TF-IDF baseline') from e
    vect=TfidfVectorizer(lowercase=True, ngram_range=(1,2), sublinear_tf=True, norm='l2')
    X=vect.fit_transform([r['document_text'] for r in corpus])
    Q=vect.transform(queries); sim=cosine_similarity(Q,X)
    for row in sim:
        idx=sorted(range(len(corpus)),key=lambda i:(-float(row[i]),corpus[i]['control_id']))
        yield [(float(row[i]),i) for i in idx]


def score(gold, ranked, ks=REPORT_KS):
    g=set(gold); result={}
    for k in ks:
        top=set(ranked[:k]); result[f'recall@{k}']=len(g&top)/len(g) if g else 0.0
        result[f'hit@{k}']=1.0 if g&top else 0.0
    rr=0.0
    for rank,cid in enumerate(ranked,1):
        if cid in g: rr=1.0/rank; break
    result['mrr']=rr
    return result


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--benchmark',required=True); ap.add_argument('--corpus',required=True)
    ap.add_argument('--method',choices=['bm25','tfidf'],required=True); ap.add_argument('--top-k',type=int,default=10,
        help='number of ranked documents persisted for later RAG context; retrieval metrics still use the full ranking')
    ap.add_argument('--outdir',default='retrieval_out'); ap.add_argument('--split',choices=['dev','test','all'],default='all')
    args=ap.parse_args()
    if args.top_k < 1: raise SystemExit('ERROR: --top-k must be >=1')
    b=read_csv(args.benchmark); c=read_csv(args.corpus)
    if args.split!='all': b=[r for r in b if r.get('split')==args.split]
    if not b: raise SystemExit('ERROR: no benchmark rows selected')
    if not c: raise SystemExit('ERROR: corpus empty')
    ids=[r['control_id'].strip().upper() for r in c]
    if len(set(ids))!=len(ids): raise SystemExit('ERROR: duplicate corpus control IDs')
    queries=[r['ccm_control_text'] for r in b]
    ranker=bm25_rank(c,queries) if args.method=='bm25' else tfidf_rank(c,queries)
    out=[]; per=[]
    for br,scores in zip(b,ranker):
        full_ranked=[c[i]['control_id'].upper() for _,i in scores]
        top=scores[:args.top_k]; persisted=[c[i]['control_id'].upper() for _,i in top]
        gold=split_ids(br['gold_nist_control_ids'])
        sm=score(gold,full_ranked)
        per.append(sm)
        out.append({
          'query_id':br['query_id'],'split':br.get('split',''),'method':args.method,
          'gold_ids':'|'.join(gold),'ranked_ids':'|'.join(persisted),
          'scores_json':json.dumps([round(s,8) for s,_ in top]),
          **{k:f'{v:.10f}' for k,v in sm.items()}
        })
    metrics={k:sum(x[k] for x in per)/len(per) for k in per[0]}
    metrics.update({'queries':len(per),'method':args.method,'persisted_top_k':args.top_k,'metric_cutoffs':list(REPORT_KS),'split':args.split,
                    'benchmark_sha256':sha256_file(args.benchmark),'corpus_sha256':sha256_file(args.corpus)})
    od=Path(args.outdir); od.mkdir(parents=True,exist_ok=True)
    write_csv(od/f'{args.method}_retrieval.csv',out)
    json_dump(od/f'{args.method}_metrics.json',metrics)
    print(json.dumps(metrics,indent=2))
if __name__=='__main__': main()
