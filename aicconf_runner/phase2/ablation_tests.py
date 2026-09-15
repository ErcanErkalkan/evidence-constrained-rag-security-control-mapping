#!/usr/bin/env python3
"""Pre-registered layer-ablation tests from the SAME frozen model generations.

No extra LLM calls are made. Variants are reconstructed from saved raw outputs:
B = compromised RAG (C2, no output guard)
G = compromised RAG + output guard only (C2, post-generation guard)
P = provenance filtering only (C3 raw response before output guard)
F = full hardened system (C3 after output guard)

Independent unit: query_id. Attack families remain separate strata.
"""
from __future__ import annotations
import argparse, math
from pathlib import Path
from collections import defaultdict
from common import read_csv, write_csv, json_dump, sha256_file
from statistical_tests import bootstrap_diff, wilcoxon_p, mcnemar_exact, holm_family

UTILITY=['f1','precision','recall']
GROUNDING=['invalid_control_id_rate','ungrounded_id_rate','unsupported_citation_rate','evidence_supported_id_rate']
SECURITY=['attack_success','attack_target_adoption','malicious_source_cited']
BINARY=set(SECURITY)
CONTRASTS=[('B_COMPROMISED','G_OUTPUT_GUARD_ONLY'),('B_COMPROMISED','P_PROVENANCE_ONLY'),('P_PROVENANCE_ONLY','F_FULL_HARDENED')]


def fnum(x):
    try: return float(x)
    except Exception: return math.nan


def index(path,condition):
    out=defaultdict(dict)
    for r in read_csv(path):
        if r.get('condition')!=condition: continue
        at=r.get('attack_type','') or 'benign'; q=r['query_id']
        if at=='benign': continue
        if q in out[at]: raise RuntimeError(f'duplicate ablation row: {condition} {at} {q}')
        out[at][q]=r
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--full-per-case',required=True)
    ap.add_argument('--provenance-only-per-case',required=True)
    ap.add_argument('--output-guard-only-per-case',required=True)
    ap.add_argument('--bootstrap-iters',type=int,default=10000); ap.add_argument('--seed',type=int,default=2027); ap.add_argument('--outdir',default='ablation_stats')
    args=ap.parse_args()
    variants={
      'B_COMPROMISED':index(args.full_per_case,'C2_COMPROMISED_RAG'),
      'G_OUTPUT_GUARD_ONLY':index(args.output_guard_only_per_case,'C2_COMPROMISED_RAG'),
      'P_PROVENANCE_ONLY':index(args.provenance_only_per_case,'C3_HARDENED_RAG'),
      'F_FULL_HARDENED':index(args.full_per_case,'C3_HARDENED_RAG'),
    }
    attack_types=sorted(set.intersection(*(set(v) for v in variants.values())))
    if not attack_types: raise SystemExit('ERROR: no common attack families across ablation variants')
    tests=[]
    for at in attack_types:
      for fam,metrics in [('ablation_utility',UTILITY),('ablation_grounding',GROUNDING),('ablation_security',SECURITY)]:
        for A,B in CONTRASTS:
          ga,gb=variants[A][at],variants[B][at]; common=sorted(set(ga)&set(gb))
          if not common: continue
          for metric in metrics:
            a=[fnum(ga[q].get(metric,'')) for q in common]; b=[fnum(gb[q].get(metric,'')) for q in common]
            valid=[(x,y) for x,y in zip(a,b) if not (math.isnan(x) or math.isnan(y))]
            if metric in BINARY:
              p,b01,b10,n=mcnemar_exact(a,b); diff=sum(x-y for x,y in valid)/len(valid) if valid else math.nan; lo=hi=''; test='exact_mcnemar'
            else:
              diff,lo,hi,n=bootstrap_diff(a,b,args.bootstrap_iters,args.seed); p=wilcoxon_p(a,b); b01=b10=''; test='paired_wilcoxon'
            tests.append({'hypothesis_family':fam,'attack_type':at,'variant_a':A,'variant_b':B,'metric':metric,'test':test,'n_queries':n,
                          'mean_a':sum(x for x,_ in valid)/len(valid) if valid else math.nan,'mean_b':sum(y for _,y in valid)/len(valid) if valid else math.nan,
                          'mean_diff_a_minus_b':diff,'ci95_low':lo,'ci95_high':hi,'discordant_a0_b1':b01,'discordant_a1_b0':b10,'p_raw':p})
    holm_family(tests)
    for r in tests:
      for k in ['mean_a','mean_b','mean_diff_a_minus_b','ci95_low','ci95_high','p_raw','p_holm']:
        if isinstance(r.get(k),float) and not math.isnan(r[k]): r[k]=f'{r[k]:.10g}'
    od=Path(args.outdir); od.mkdir(parents=True,exist_ok=True); write_csv(od/'ablation_paired_tests.csv',tests)
    json_dump(od/'ablation_stats_manifest.json',{'status':'VALID_ONLY_FOR_FINAL_FROZEN_BENCHMARK_RESULTS','inputs':{'full_sha256':sha256_file(args.full_per_case),'provenance_only_sha256':sha256_file(args.provenance_only_per_case),'output_guard_only_sha256':sha256_file(args.output_guard_only_per_case)},'bootstrap_iters':args.bootstrap_iters,'seed':args.seed,'attack_types':attack_types,'contrasts':CONTRASTS,'families':{'ablation_utility':UTILITY,'ablation_grounding':GROUNDING,'ablation_security':SECURITY},'multiple_testing':'Holm correction separately within each ablation hypothesis family','independent_unit':'query_id','note':'All variants reuse the same underlying frozen model generations; no extra model calls are made.'})
    print(f'PASS: ablation tests written to {od}')

if __name__=='__main__': main()
