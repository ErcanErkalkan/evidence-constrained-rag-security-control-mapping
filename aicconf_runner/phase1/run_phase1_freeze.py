#!/usr/bin/env python3
"""Acquire/validate frozen sources, build benchmark, and enforce Phase-1 release gates."""
from __future__ import annotations
import argparse, csv, hashlib, json, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
CCM='CCMv4.0.13_Generated-at_2024-10-31_ccm_normalized.json'
NIST='800-53-r5-controls.json'

def sha256(p:Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('--workdir',default=str(HERE/'run')); ap.add_argument('--skip-download',action='store_true'); args=ap.parse_args()
 work=Path(args.workdir); src=work/'sources'/'original'; out=work/'benchmark_frozen'; src.mkdir(parents=True,exist_ok=True)
 cmd=[sys.executable,str(HERE/'acquire_sources.py'),'--outdir',str(src)]
 if args.skip_download: cmd.append('--skip-download')
 subprocess.run(cmd,check=True)
 build=[sys.executable,str(HERE/'build_benchmark.py'),
  '--mapping',str(src/CCM),'--nist-catalog',str(src/NIST),
  '--ccm-id-field','Control ID','--text-field','CCM_Control Specification',
  '--nist-field','Scope Applicability (Mappings)_NIST 800-53 rev 5 Control Mapping',
  '--gap-field','Scope Applicability (Mappings)_Gap Level.7','--addendum-field','Scope Applicability (Mappings)_Addendum.7',
  '--title-field','Control Title','--domain-field','Control Domain',
  '--ccm-version','4.0.13','--mapping-version','CCM-4.0.13 normalized 2024-10-31',
  '--mapping-source-blob-sha','7f43db83cff3af5599e456cdf2a10b9ad532c991',
  '--nist-version','NIST SP 800-53 Rev.5 Update 1 (Dec 2024)',
  '--nist-source-blob-sha','9630eab606b8a3ecf425717278f327a80574fe7c',
  '--min-rows','1','--max-invalid-rate','0','--outdir',str(out)]
 subprocess.run(build,check=True)
 report=json.loads((out/'validation_report.json').read_text())
 manifest=json.loads((out/'source_manifest.json').read_text())
 source_freeze=json.loads((src/'SOURCE_FREEZE.json').read_text())
 # Full source must be accounted for: validated rows + exclusions == 197.
 if report.get('records_in_source')!=197: raise RuntimeError(f"Expected 197 source controls, got {report.get('records_in_source')}")
 if report.get('invalid_mappings_excluded')!=0: raise RuntimeError('Invalid/unparsed mappings are nonzero')
 if report.get('benchmark_rows',0)+report.get('exclusions',0)!=197: raise RuntimeError('Source accounting does not sum to 197')
 # Final freeze bundles source-byte identity and output identity.
 release={
  'status':'PASS_PHASE1_FROZEN', 'source_freeze':source_freeze,
  'validation_report':report,'source_manifest':manifest,
  'artifacts':{p.name:sha256(p) for p in [out/'benchmark.csv',out/'exclusions.csv',out/'source_manifest.json',out/'validation_report.json',out/'BENCHMARK_FREEZE.json']},
 }
 (out/'PHASE1_RELEASE_FREEZE.json').write_text(json.dumps(release,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps({'status':release['status'],'benchmark_rows':report['benchmark_rows'],'exclusions':report['exclusions'],'release_freeze':str(out/'PHASE1_RELEASE_FREEZE.json')},indent=2))
 return 0
if __name__=='__main__':
 try: raise SystemExit(main())
 except Exception as e: print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(2)
