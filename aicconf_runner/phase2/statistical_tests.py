#!/usr/bin/env python3
"""Pre-registered query-level paired tests, stratified by attack family.

The independent unit is query_id. Attack families are separate strata and are never
pooled as independent query replicates. Inferential comparisons are restricted to
metrics for which the compared conditions make scientific sense.

Hypothesis families (Holm corrected within family):
- utility: precision, recall, f1 for C1↔C2, C2↔C3, C1↔C3
- grounding: invalid/ungrounded/evidence-support rates for the same comparisons
- format: valid_json, schema_ok, missing_citation_for_ids for the same comparisons
- security: attack_success, raw_attack_success, attack_target_adoption,
            malicious_source_cited for C2↔C3 only
Guard-rejected and other mechanically condition-specific metrics are descriptive only.
"""
from __future__ import annotations
import argparse, json, math, random
from scipy.stats import wilcoxon as scipy_wilcoxon, binomtest
from collections import defaultdict
from pathlib import Path
from common import read_csv, write_csv, json_dump, sha256_file

UTILITY=['f1','precision','recall']
GROUNDING=['invalid_control_id_rate','ungrounded_id_rate','unsupported_citation_rate','evidence_supported_id_rate']
FORMAT=['valid_json','schema_ok','missing_citation_for_ids']
SECURITY=['attack_success','raw_attack_success','attack_target_adoption','raw_attack_target_adoption','raw_invalid_control_id_rate','malicious_source_cited']
ALL_PAIRS=[('C1_CLEAN_RAG','C2_COMPROMISED_RAG'),('C2_COMPROMISED_RAG','C3_HARDENED_RAG'),('C1_CLEAN_RAG','C3_HARDENED_RAG')]
SECURITY_PAIRS=[('C2_COMPROMISED_RAG','C3_HARDENED_RAG')]
BINARY=set(FORMAT+SECURITY)


def fnum(x):
    try:return float(x)
    except Exception:return math.nan


def bootstrap_diff(a,b,iters=10000,seed=2027):
    pairs=[(x,y) for x,y in zip(a,b) if not (math.isnan(x) or math.isnan(y))]
    n=len(pairs)
    if n==0:return (math.nan,math.nan,math.nan,0)
    obs=sum(x-y for x,y in pairs)/n
    rng=random.Random(seed); diffs=[]
    for _ in range(iters):
        s=0.0
        for _j in range(n):
            x,y=pairs[rng.randrange(n)]; s += x-y
        diffs.append(s/n)
    diffs.sort(); return obs,diffs[int(.025*(iters-1))],diffs[int(.975*(iters-1))],n


def wilcoxon_p(a,b):
    pairs=[(x,y) for x,y in zip(a,b) if not (math.isnan(x) or math.isnan(y))]
    if not pairs:return math.nan
    aa=[x for x,_ in pairs]; bb=[y for _,y in pairs]; d=[x-y for x,y in pairs]
    if all(abs(x)<1e-15 for x in d): return 1.0
    return float(scipy_wilcoxon(aa,bb,zero_method='wilcox',alternative='two-sided',method='auto').pvalue)


def mcnemar_exact(a,b):
    pairs=[(x,y) for x,y in zip(a,b) if not (math.isnan(x) or math.isnan(y))]
    if not pairs:return math.nan,0,0,0
    aa=[int(round(x)) for x,_ in pairs]; bb=[int(round(y)) for _,y in pairs]
    b01=sum(int(x==0 and y==1) for x,y in zip(aa,bb)); b10=sum(int(x==1 and y==0) for x,y in zip(aa,bb)); n=b01+b10
    if n==0:return 1.0,b01,b10,len(pairs)
    p=float(binomtest(min(b01,b10),n=n,p=0.5,alternative='two-sided').pvalue)
    return p,b01,b10,len(pairs)


def holm_family(rows):
    byfam=defaultdict(list)
    for i,r in enumerate(rows):
        p=r['p_raw']
        if isinstance(p,float) and not math.isnan(p): byfam[r['hypothesis_family']].append((i,p))
    for fam,vals in byfam.items():
        vals.sort(key=lambda x:x[1]); m=len(vals); prev=0.0
        for rank,(idx,p) in enumerate(vals,1):
            adj=max(prev,min(1.0,(m-rank+1)*p)); rows[idx]['p_holm']=adj; prev=adj
    for r in rows:r.setdefault('p_holm',math.nan)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--per-case',required=True); ap.add_argument('--outdir',default='stats_out'); ap.add_argument('--bootstrap-iters',type=int,default=10000); ap.add_argument('--seed',type=int,default=2027); args=ap.parse_args()
    rows=read_csv(args.per_case)
    benign=defaultdict(dict); attacked=defaultdict(lambda:defaultdict(dict)); attack_types=set()
    for r in rows:
        cond=r['condition']; q=r['query_id']; at=r.get('attack_type','benign') or 'benign'
        if cond in {'C0_UNGROUNDED','C1_CLEAN_RAG'}:
            if q in benign[cond]: raise SystemExit(f'ERROR: duplicate benign query row: {cond} {q}')
            benign[cond][q]=r
        else:
            if at=='benign': raise SystemExit(f'ERROR: attacked condition missing attack_type: {cond} {q}')
            if q in attacked[cond][at]: raise SystemExit(f'ERROR: duplicate attacked row: {cond} {at} {q}')
            attacked[cond][at][q]=r; attack_types.add(at)
    tests=[]
    def group(cond,atype): return benign[cond] if cond in benign else attacked[cond][atype]
    plans=[('utility',UTILITY,ALL_PAIRS),('grounding',GROUNDING,ALL_PAIRS),('format',FORMAT,ALL_PAIRS),('security',SECURITY,SECURITY_PAIRS)]
    for atype in sorted(attack_types):
        for family,metrics,pairs in plans:
            for A,B in pairs:
                ga,gb=group(A,atype),group(B,atype); common=sorted(set(ga)&set(gb))
                if not common: continue
                for metric in metrics:
                    a=[fnum(ga[q].get(metric,'')) for q in common]; b=[fnum(gb[q].get(metric,'')) for q in common]
                    if metric in BINARY:
                        p,b01,b10,n_used=mcnemar_exact(a,b)
                        valid=[(x,y) for x,y in zip(a,b) if not (math.isnan(x) or math.isnan(y))]
                        diff=(sum(x-y for x,y in valid)/len(valid)) if valid else math.nan
                        tests.append({'hypothesis_family':family,'attack_type':atype,'condition_a':A,'condition_b':B,'metric':metric,'test':'exact_mcnemar','n_queries':n_used,
                            'mean_a':(sum(x for x,_ in valid)/len(valid)) if valid else math.nan,'mean_b':(sum(y for _,y in valid)/len(valid)) if valid else math.nan,
                            'mean_diff_a_minus_b':diff,'ci95_low':'','ci95_high':'','discordant_a0_b1':b01,'discordant_a1_b0':b10,'p_raw':p})
                    else:
                        diff,lo,hi,n_used=bootstrap_diff(a,b,args.bootstrap_iters,args.seed)
                        valid=[(x,y) for x,y in zip(a,b) if not (math.isnan(x) or math.isnan(y))]
                        tests.append({'hypothesis_family':family,'attack_type':atype,'condition_a':A,'condition_b':B,'metric':metric,'test':'paired_wilcoxon','n_queries':n_used,
                            'mean_a':(sum(x for x,_ in valid)/len(valid)) if valid else math.nan,'mean_b':(sum(y for _,y in valid)/len(valid)) if valid else math.nan,
                            'mean_diff_a_minus_b':diff,'ci95_low':lo,'ci95_high':hi,'discordant_a0_b1':'','discordant_a1_b0':'','p_raw':wilcoxon_p(a,b)})
    holm_family(tests)
    for r in tests:
        for k in ['mean_a','mean_b','mean_diff_a_minus_b','ci95_low','ci95_high','p_raw','p_holm']:
            if isinstance(r[k],float) and not math.isnan(r[k]): r[k]=f'{r[k]:.10g}'
    od=Path(args.outdir); od.mkdir(parents=True,exist_ok=True); write_csv(od/'paired_tests.csv',tests)
    manifest={'status':'VALID_ONLY_FOR_FINAL_FROZEN_BENCHMARK_RESULTS','input_sha256':sha256_file(args.per_case),'bootstrap_iters':args.bootstrap_iters,'seed':args.seed,
      'attack_types':sorted(attack_types),'hypothesis_families':{'utility':{'metrics':UTILITY,'pairs':ALL_PAIRS},'grounding':{'metrics':GROUNDING,'pairs':ALL_PAIRS},'format':{'metrics':FORMAT,'pairs':ALL_PAIRS},'security':{'metrics':SECURITY,'pairs':SECURITY_PAIRS}},
      'multiple_testing':'Holm correction separately within each pre-registered hypothesis family across attack types/comparisons/metrics',
      'independent_evaluation_unit':'query_id','pseudoreplication_guard':'attack families are analysed separately and are not pooled as independent query observations',
      'descriptive_only_metrics':['guard_rejected']
    }
    json_dump(od/'stats_manifest.json',manifest); print(json.dumps(manifest,indent=2))
if __name__=='__main__': main()
