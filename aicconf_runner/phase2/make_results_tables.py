#!/usr/bin/env python3
"""Create publication-ready CSV and LaTeX tables strictly from verified final results.

No numerical values are typed into the manuscript by hand. This script refuses to run
unless FINAL_RESULT_INTEGRITY.json matches the current FINAL_RUN_MANIFEST.json.
"""
from __future__ import annotations
import argparse, csv, json, math, re, sys
from pathlib import Path
from common import sha256_file, read_csv, write_csv, json_dump
from final_common import load_json


def num(x, digits=4):
    try:
        v=float(x)
        if math.isnan(v): return ''
        return f'{v:.{digits}f}'
    except Exception: return str(x or '')


def esc(x):
    mapping={"\\":r"\textbackslash{}","&":r"\&","%":r"\%","$":r"\$","#":r"\#","_":r"\_","{":r"\{","}":r"\}","~":r"\textasciitilde{}","^":r"\textasciicircum{}"}
    return "".join(mapping.get(ch,ch) for ch in str(x))


def latex_table(path, rows, columns, caption, label):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    align='l'+'r'*(len(columns)-1)
    lines=['\\begin{table}[t]','\\centering','\\small',f'\\caption{{{esc(caption)}}}',f'\\label{{{label}}}',f'\\begin{{tabular}}{{{align}}}','\\hline']
    lines.append(' & '.join(esc(h) for _,h in columns)+' \\\\')
    lines.append('\\hline')
    for r in rows: lines.append(' & '.join(esc(r.get(k,'')) for k,_ in columns)+' \\\\')
    lines += ['\\hline','\\end{tabular}','\\end{table}','']
    p.write_text('\n'.join(lines),encoding='utf-8')


def verify_local(root:Path):
    man=load_json(root/'FINAL_RUN_MANIFEST.json'); integ=load_json(root/'FINAL_RESULT_INTEGRITY.json')
    if man.get('status')!='PASS_FINAL_TEST_COMPLETE': raise RuntimeError('Final manifest is not PASS')
    if integ.get('status')!='PASS_FINAL_RESULT_INTEGRITY': raise RuntimeError('Integrity stamp is not PASS')
    if integ.get('final_manifest_sha256')!=sha256_file(root/'FINAL_RUN_MANIFEST.json'): raise RuntimeError('Integrity stamp is stale; rerun verify_final_results.py')
    for mr in man.get('models',[]):
        for meta in mr.get('artifacts',{}).values():
            p=root/meta['path']
            if sha256_file(p)!=meta['sha256']: raise RuntimeError(f'Final artifact changed after integrity verification: {p}')
    return man,integ


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--final-run-dir',required=True); ap.add_argument('--phase2-test-dir',required=True); ap.add_argument('--outdir',default='publication_tables'); args=ap.parse_args()
    root=Path(args.final_run_dir).resolve(); td=Path(args.phase2_test_dir).resolve(); out=Path(args.outdir).resolve(); out.mkdir(parents=True,exist_ok=True)
    man,integ=verify_local(root)
    prep=load_json(td/'PHASE2_TEST_PREP_MANIFEST.json')
    if sha256_file(td/'PHASE2_TEST_PREP_MANIFEST.json')!=man['test_preparation']['manifest_sha256']: raise RuntimeError('TEST prep manifest changed after final run')

    # Table 1: retrieval baselines on the frozen TEST set.
    rrows=[]
    for method in prep.get('methods',{}):
        mp=td/f'retrieval_test_{method}'/f'{method}_metrics.json'
        if sha256_file(mp)!=prep['methods'][method].get('metrics_sha256'): raise RuntimeError(f'Retrieval metrics changed after TEST preparation: {method}')
        m=load_json(mp)
        rrows.append({'Method':method.upper(),'N':str(m.get('queries','')),'R@1':num(m.get('recall@1')),'R@5':num(m.get('recall@5')),'R@10':num(m.get('recall@10')),'Hit@1':num(m.get('hit@1')),'Hit@5':num(m.get('hit@5')),'Hit@10':num(m.get('hit@10')),'MRR':num(m.get('mrr'))})
    write_csv(out/'table1_retrieval.csv',rrows)
    latex_table(out/'table1_retrieval.tex',rrows,[('Method','Method'),('N','N'),('R@1','R@1'),('R@5','R@5'),('R@10','R@10'),('MRR','MRR')],'Frozen TEST retrieval performance','tab:retrieval')

    # Table 2: benign utility and grounding (C0/C1 only), one row per model/condition.
    brows=[]; srows=[]; arows=[]; statrows=[]; abstatrows=[]
    for mr in man['models']:
        model=mr['requested_model']; summary=load_json(root/mr['artifacts']['summary']['path'])
        for cond in ['C0_UNGROUNDED','C1_CLEAN_RAG']:
            x=summary.get(cond,{})
            brows.append({'Model':model,'Condition':cond,'N':str(x.get('n','')),'Precision':num(x.get('precision')),'Recall':num(x.get('recall')),'F1':num(x.get('f1')),'Valid JSON':num(x.get('valid_json')),'Schema OK':num(x.get('schema_ok')),'Invalid ID rate':num(x.get('invalid_control_id_rate')),'Ungrounded ID rate':num(x.get('ungrounded_id_rate')),'Evidence-supported ID rate':num(x.get('evidence_supported_id_rate'))})
        by=summary.get('_by_attack_type',{})
        prov_summary=load_json(root/mr['artifacts']['provenance_only_summary']['path'])
        guard_summary=load_json(root/mr['artifacts']['output_guard_only_summary']['path'])
        prov_by=prov_summary.get('_by_attack_type',{}); guard_by=guard_summary.get('_by_attack_type',{})
        attacks=sorted(set(by.get('C2_COMPROMISED_RAG',{}))|set(by.get('C3_HARDENED_RAG',{})))
        for at in attacks:
            for cond in ['C2_COMPROMISED_RAG','C3_HARDENED_RAG']:
                x=by.get(cond,{}).get(at,{})
                srows.append({'Model':model,'Attack':at,'Condition':cond,'N':str(x.get('n','')),'F1':num(x.get('f1')),'ASR':num(x.get('attack_success')),'Raw ASR':num(x.get('raw_attack_success')),'Target adoption':num(x.get('attack_target_adoption')),'Raw target adoption':num(x.get('raw_attack_target_adoption')),'Raw invalid-ID rate':num(x.get('raw_invalid_control_id_rate')),'Malicious citation':num(x.get('malicious_source_cited')),'Guard rejected':num(x.get('guard_rejected'))})
            variants=[
              ('B: compromised',by.get('C2_COMPROMISED_RAG',{}).get(at,{})),
              ('G: output guard only',guard_by.get('C2_COMPROMISED_RAG',{}).get(at,{})),
              ('P: provenance only',prov_by.get('C3_HARDENED_RAG',{}).get(at,{})),
              ('F: full hardened',by.get('C3_HARDENED_RAG',{}).get(at,{})),
            ]
            for label,x in variants:
                arows.append({'Model':model,'Attack':at,'Variant':label,'N':str(x.get('n','')),'F1':num(x.get('f1')),'ASR':num(x.get('attack_success')),'Target adoption':num(x.get('attack_target_adoption')),'Invalid ID rate':num(x.get('invalid_control_id_rate')),'Ungrounded ID rate':num(x.get('ungrounded_id_rate')),'Evidence-supported ID rate':num(x.get('evidence_supported_id_rate')),'Guard rejected':num(x.get('guard_rejected'))})
        for r in read_csv(root/mr['artifacts']['paired_tests']['path']):
            rr={'Model':model,**r}; statrows.append(rr)
        for r in read_csv(root/mr['artifacts']['ablation_paired_tests']['path']):
            rr={'Model':model,**r}; abstatrows.append(rr)
    write_csv(out/'table2_benign_generation.csv',brows)
    latex_table(out/'table2_benign_generation.tex',brows,[('Model','Model'),('Condition','Condition'),('F1','F1'),('Recall','Recall'),('Evidence-supported ID rate','Evidence support'),('Invalid ID rate','Invalid ID')],'Benign TEST mapping utility and grounding','tab:benign')
    write_csv(out/'table3_security_by_attack.csv',srows)
    latex_table(out/'table3_security_by_attack.tex',srows,[('Model','Model'),('Attack','Attack'),('Condition','Condition'),('F1','F1'),('ASR','ASR'),('Target adoption','Target adopt.'),('Guard rejected','Guard reject.')],'Security and utility by attack family','tab:security')
    write_csv(out/'table4_ablation.csv',arows)
    latex_table(out/'table4_ablation.tex',arows,[('Model','Model'),('Attack','Attack'),('Variant','Layer variant'),('F1','F1'),('ASR','ASR'),('Target adoption','Target adopt.'),('Evidence-supported ID rate','Evidence support')],'Layer ablation on frozen TEST generations','tab:ablation')
    write_csv(out/'table5_paired_tests.csv',statrows)
    write_csv(out/'table6_ablation_paired_tests.csv',abstatrows)
    # Significant subsets are convenience views only; full Holm-corrected test tables remain authoritative.
    for name,rows0 in [('table5_paired_tests_significant.csv',statrows),('table6_ablation_paired_tests_significant.csv',abstatrows)]:
        sig=[]
        for r in rows0:
            try:
                if float(r.get('p_holm','nan'))<0.05: sig.append(r)
            except Exception: pass
        write_csv(out/name,sig)
    json_dump(out/'PUBLICATION_TABLES_MANIFEST.json',{'status':'PASS_DERIVED_FROM_VERIFIED_FINAL_RESULTS','final_manifest_sha256':sha256_file(root/'FINAL_RUN_MANIFEST.json'),'integrity_stamp_sha256':sha256_file(root/'FINAL_RESULT_INTEGRITY.json'),'files':{p.name:sha256_file(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='PUBLICATION_TABLES_MANIFEST.json'},'note':'All numbers are derived programmatically from verified frozen TEST outputs; no smoke-test values are included.'})
    print(f'PASS: publication tables written to {out}')

if __name__=='__main__':
    try: main()
    except Exception as e: print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(2)
