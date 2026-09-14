#!/usr/bin/env python3
"""Create the retrieval corpus from the frozen NIST SP 800-53 JSON/CSV source.

Fail-closed on duplicate/invalid IDs. Primary document text is name + control_text.
Discussion can be included only through an explicit flag so that it can be treated
as a documented retrieval ablation rather than silently changing the corpus.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from common import NIST_ID_RE, json_dump, sha256_file, write_csv, normalise_ws


def load(path: Path) -> list[dict]:
    if path.suffix.lower()=='.json':
        x=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(x,list) or (x and not isinstance(x[0],dict)):
            raise ValueError('NIST JSON must be a list of objects')
        return x
    if path.suffix.lower()=='.csv':
        with path.open('r',encoding='utf-8-sig',newline='') as f:
            return [dict(r) for r in csv.DictReader(f)]
    raise ValueError('Only JSON/CSV NIST catalogs are supported')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--nist-catalog',required=True)
    ap.add_argument('--outdir',default='phase2_corpus')
    ap.add_argument('--include-discussion',action='store_true')
    ap.add_argument('--nist-version',required=True)
    ap.add_argument('--expected-count',type=int,default=1189)
    args=ap.parse_args()
    src=Path(args.nist_catalog); rows=load(src)
    if args.expected_count and len(rows)!=args.expected_count:
        raise SystemExit(f'ERROR: expected {args.expected_count} NIST records, got {len(rows)}')
    out=[]; seen=set(); blank_text=[]
    for i,r in enumerate(rows,1):
        cid=str(r.get('control_id','')).strip().upper()
        if not NIST_ID_RE.fullmatch(cid):
            raise SystemExit(f'ERROR: invalid control_id row {i}: {cid!r}')
        if cid in seen: raise SystemExit(f'ERROR: duplicate control_id {cid}')
        seen.add(cid)
        name=normalise_ws(str(r.get('name','')))
        ctl=normalise_ws(str(r.get('control_text','')))
        disc=normalise_ws(str(r.get('discussion','')))
        parts=[p for p in [name,ctl,(disc if args.include_discussion else '')] if p]
        doc='\n'.join(parts)
        if not doc: blank_text.append(cid)
        out.append({
            'document_id':f'NIST:{cid}', 'control_id':cid,
            'family':str(r.get('family','')).strip().upper(),
            'name':name, 'control_text':ctl,
            'discussion':disc if args.include_discussion else '',
            'document_text':doc,
            'trusted':'true','source_kind':'nist_official_structured',
            'nist_version':args.nist_version,
        })
    od=Path(args.outdir); od.mkdir(parents=True,exist_ok=True)
    write_csv(od/'nist_corpus.csv',out)
    manifest={
      'status':'CORPUS_CANDIDATE_REQUIRES_BENCHMARK_FREEZE',
      'source_file':src.name,'source_sha256':sha256_file(src),'nist_version':args.nist_version,
      'records':len(out),'unique_control_ids':len(seen),'blank_document_text_ids':blank_text,
      'include_discussion':bool(args.include_discussion),
      'retrieval_document_definition':'name + control_text' + (' + discussion' if args.include_discussion else ''),
    }
    json_dump(od/'corpus_manifest.json',manifest)
    print(json.dumps(manifest,indent=2))
if __name__=='__main__': main()
