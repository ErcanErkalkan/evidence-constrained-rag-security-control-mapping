#!/usr/bin/env python3
"""Generate publication figures only from a verified final TEST bundle."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import matplotlib.pyplot as plt
from common import sha256_file
from final_common import load_json


def verify(root:Path):
    man=load_json(root/'FINAL_RUN_MANIFEST.json'); integ=load_json(root/'FINAL_RESULT_INTEGRITY.json')
    if man.get('status')!='PASS_FINAL_TEST_COMPLETE' or integ.get('status')!='PASS_FINAL_RESULT_INTEGRITY': raise RuntimeError('Final result bundle is not integrity-verified')
    if integ.get('final_manifest_sha256')!=sha256_file(root/'FINAL_RUN_MANIFEST.json'): raise RuntimeError('Stale final integrity stamp')
    return man


def save(fig, base:Path):
    fig.tight_layout(); fig.savefig(base.with_suffix('.pdf'),bbox_inches='tight'); fig.savefig(base.with_suffix('.png'),dpi=300,bbox_inches='tight'); plt.close(fig)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--final-run-dir',required=True); ap.add_argument('--phase2-test-dir',required=True); ap.add_argument('--outdir',default='publication_figures'); args=ap.parse_args()
    root=Path(args.final_run_dir).resolve(); td=Path(args.phase2_test_dir).resolve(); out=Path(args.outdir).resolve(); out.mkdir(parents=True,exist_ok=True); man=verify(root)
    prep=load_json(td/'PHASE2_TEST_PREP_MANIFEST.json')
    if sha256_file(td/'PHASE2_TEST_PREP_MANIFEST.json')!=man['test_preparation']['manifest_sha256']: raise RuntimeError('TEST prep manifest changed')

    # Fig. 1: retrieval Recall@k.
    fig,ax=plt.subplots()
    ks=[1,5,10]
    for method in prep.get('methods',{}):
        mp=td/f'retrieval_test_{method}'/f'{method}_metrics.json'
        if sha256_file(mp)!=prep['methods'][method].get('metrics_sha256'): raise RuntimeError(f'Retrieval metrics changed after TEST preparation: {method}')
        m=load_json(mp)
        ax.plot(ks,[float(m[f'recall@{k}']) for k in ks],marker='o',label=method.upper())
    ax.set_xlabel('k'); ax.set_ylabel('Macro Recall@k'); ax.set_xticks(ks); ax.set_ylim(0,1.02); ax.legend(); ax.grid(True,alpha=0.25)
    save(fig,out/'fig_retrieval_recall')

    # Fig. 2: security-utility trade-off for compromised vs hardened RAG, aggregated by model.
    fig,ax=plt.subplots()
    for mr in man['models']:
        s=load_json(root/mr['artifacts']['summary']['path']); model=mr['requested_model']
        for cond,marker in [('C2_COMPROMISED_RAG','o'),('C3_HARDENED_RAG','s')]:
            x=s.get(cond,{})
            ax.scatter([float(x.get('attack_success',0))],[float(x.get('f1',0))],marker=marker,label=f'{model} {cond.replace("_RAG","")}')
    ax.set_xlabel('Attack Success Rate'); ax.set_ylabel('Mapping F1'); ax.set_xlim(-0.02,1.02); ax.set_ylim(-0.02,1.02); ax.legend(fontsize='small'); ax.grid(True,alpha=0.25)
    save(fig,out/'fig_security_utility')

    # Fig. 3: hardened ASR by attack family (one series per model).
    fig,ax=plt.subplots()
    all_attacks=sorted({a for mr in man['models'] for a in load_json(root/mr['artifacts']['summary']['path']).get('_by_attack_type',{}).get('C3_HARDENED_RAG',{})})
    width=0.8/max(1,len(man['models'])); xs=list(range(len(all_attacks)))
    for j,mr in enumerate(man['models']):
        by=load_json(root/mr['artifacts']['summary']['path']).get('_by_attack_type',{}).get('C3_HARDENED_RAG',{})
        vals=[float(by.get(a,{}).get('attack_success',0)) for a in all_attacks]
        positions=[x-0.4+width/2+j*width for x in xs]
        ax.bar(positions,vals,width=width,label=mr['requested_model'])
    ax.set_xticks(xs); ax.set_xticklabels(all_attacks,rotation=25,ha='right'); ax.set_ylabel('Hardened ASR'); ax.set_ylim(0,1.02); ax.legend(fontsize='small'); ax.grid(True,axis='y',alpha=0.25)
    save(fig,out/'fig_hardened_asr_by_attack')

    # Fig. 4: layer ablation security-utility trade-off using the same frozen generations.
    fig,ax=plt.subplots()
    for mr in man['models']:
        full=load_json(root/mr['artifacts']['summary']['path'])
        prov=load_json(root/mr['artifacts']['provenance_only_summary']['path'])
        guard=load_json(root/mr['artifacts']['output_guard_only_summary']['path'])
        variants=[
          ('B',full.get('C2_COMPROMISED_RAG',{}),'o'),
          ('G',guard.get('C2_COMPROMISED_RAG',{}),'s'),
          ('P',prov.get('C3_HARDENED_RAG',{}),'^'),
          ('F',full.get('C3_HARDENED_RAG',{}),'D'),
        ]
        for code,x,marker in variants:
            ax.scatter([float(x.get('attack_success',0))],[float(x.get('f1',0))],marker=marker,label=f"{mr['requested_model']} {code}")
    ax.set_xlabel('Attack Success Rate'); ax.set_ylabel('Mapping F1'); ax.set_xlim(-0.02,1.02); ax.set_ylim(-0.02,1.02); ax.legend(fontsize='small',ncol=2); ax.grid(True,alpha=0.25)
    ax.text(0.02,0.02,'B=compromised, G=guard-only, P=provenance-only, F=full',transform=ax.transAxes,fontsize='small')
    save(fig,out/'fig_layer_ablation')

    files={p.name:sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out/'PUBLICATION_FIGURES_MANIFEST.json').write_text(json.dumps({'status':'PASS_DERIVED_FROM_VERIFIED_FINAL_RESULTS','final_manifest_sha256':sha256_file(root/'FINAL_RUN_MANIFEST.json'),'files':files,'note':'Figures contain verified final TEST results only.'},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'PASS: publication figures written to {out}')

if __name__=='__main__':
    try: main()
    except Exception as e: print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(2)
