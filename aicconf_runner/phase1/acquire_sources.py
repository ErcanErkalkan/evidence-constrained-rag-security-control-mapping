#!/usr/bin/env python3
"""Acquire the two frozen Phase-1 sources and verify immutable Git blob identities.

The raw URLs are pinned to one immutable Git commit. Validation is fail-closed:
size, Git blob SHA-1, JSON structure, and record counts must all match before a
SOURCE_FREEZE.json is emitted. SHA-256 is computed over the exact downloaded bytes.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sys, time, urllib.request
from pathlib import Path

REPO='CloudSecurityAlliance-DataSets/dataset-public-laws-regulations-standards'
COMMIT='74ff4b828e60531d70a3d173784231f8a882a18c'
SOURCES={
 'ccm': {
   'filename':'CCMv4.0.13_Generated-at_2024-10-31_ccm_normalized.json',
   'path':'control/cloudsecurityalliance.org/ccm/4.0.13/CSV/CCMv4.0.13_Generated-at_2024-10-31_ccm_normalized.json',
   'blob_sha':'7f43db83cff3af5599e456cdf2a10b9ad532c991',
   'size':2114160,
   'records':197,
 },
 'nist': {
   'filename':'800-53-r5-controls.json',
   'path':'control/nist.gov/800-53/r5/800-53-r5-controls.json',
   'blob_sha':'9630eab606b8a3ecf425717278f327a80574fe7c',
   'size':1328285,
   'records':1189,
 },
}

def sha256_bytes(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()

def git_blob_sha(data: bytes)->str:
    h=hashlib.sha1()
    h.update(f'blob {len(data)}\0'.encode('ascii'))
    h.update(data)
    return h.hexdigest()

def download(url: str, dest: Path, retries: int=4)->None:
    last=None
    for attempt in range(1,retries+1):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'AICCONF2027-Phase1/1.2'})
            with urllib.request.urlopen(req,timeout=90) as r, dest.open('wb') as f:
                shutil.copyfileobj(r,f)
            return
        except Exception as e:
            last=e
            dest.unlink(missing_ok=True)
            if attempt<retries: time.sleep(2**(attempt-1))
    raise RuntimeError(f'download failed after {retries} attempts: {url}: {last}')

def validate_json(kind: str, data: bytes, expected_count: int)->dict:
    try: obj=json.loads(data.decode('utf-8'))
    except Exception as e: raise ValueError(f'{kind}: invalid UTF-8 JSON: {e}')
    if isinstance(obj,dict):
        candidates=[obj.get(k) for k in ('controls','records','items','data','mappings') if isinstance(obj.get(k),list)]
        if len(candidates)==1: obj=candidates[0]
    if not isinstance(obj,list): raise ValueError(f'{kind}: expected top-level record list')
    if len(obj)!=expected_count: raise ValueError(f'{kind}: expected {expected_count} records, found {len(obj)}')
    if kind=='ccm':
        ids=[str(x.get('Control ID','')).strip() for x in obj if isinstance(x,dict)]
        if len(set(ids))!=197 or 'AIS-01' not in ids or 'A&A-01' not in ids:
            raise ValueError('ccm: control ID validation failed')
        map_key='Scope Applicability (Mappings)_NIST 800-53 rev 5 Control Mapping'
        if not all(isinstance(x,dict) and map_key in x for x in obj):
            raise ValueError('ccm: required NIST mapping field missing from one or more records')
        return {'records':len(obj),'unique_control_ids':len(set(ids)),'mapping_field':map_key}
    ids=[str(x.get('control_id','')).strip() for x in obj if isinstance(x,dict)]
    if len(set(ids))!=1189 or 'AC-1' not in ids or 'AC-2(1)' not in ids:
        raise ValueError('nist: control ID validation failed')
    return {'records':len(obj),'unique_control_ids':len(set(ids))}

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--outdir',default='sources/original')
    ap.add_argument('--skip-download',action='store_true',help='validate already-present exact files')
    ap.add_argument('--force',action='store_true')
    args=ap.parse_args()
    out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)
    manifest={'status':'PASS','repository':REPO,'commit':COMMIT,'files':{}}
    for kind,s in SOURCES.items():
        dest=out/s['filename']
        url=f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{s['path']}"
        if not args.skip_download:
            if dest.exists() and not args.force:
                print(f'Using existing {dest}; pass --force to redownload',file=sys.stderr)
            else:
                print(f'Downloading {kind}: {url}',file=sys.stderr)
                download(url,dest)
        if not dest.exists(): raise FileNotFoundError(dest)
        data=dest.read_bytes()
        if len(data)!=s['size']:
            raise ValueError(f"{kind}: byte size mismatch: expected {s['size']}, got {len(data)}")
        actual_blob=git_blob_sha(data)
        if actual_blob!=s['blob_sha']:
            raise ValueError(f"{kind}: Git blob mismatch: expected {s['blob_sha']}, got {actual_blob}")
        semantic=validate_json(kind,data,s['records'])
        manifest['files'][kind]={
          'filename':s['filename'],'repository_path':s['path'],'raw_url':url,
          'size_bytes':len(data),'git_blob_sha1':actual_blob,
          'sha256':sha256_bytes(data),'semantic_validation':semantic,
        }
    frozen=out/'SOURCE_FREEZE.json'
    frozen.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2,ensure_ascii=False))
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(f'ERROR: {e}',file=sys.stderr); raise SystemExit(2)
