#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, re
from pathlib import Path
from typing import Any, Iterable

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?")
NIST_ID_RE = re.compile(r"^[A-Z]{2,3}-\d{1,2}(?:\(\d{1,2}\))?$")


def sha256_file(path: str | Path) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or '')]


def split_ids(value: str | None) -> list[str]:
    if not value:
        return []
    out=[]
    for token in re.split(r"[|,;\s]+", str(value).strip()):
        token=token.strip().upper()
        if token and token not in out:
            out.append(token)
    return out


def read_csv(path: str | Path) -> list[dict[str,str]]:
    with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
        return [dict(r) for r in csv.DictReader(f)]


def write_csv(path: str | Path, rows: list[dict[str,Any]], fieldnames: list[str] | None=None) -> None:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames=[]
        seen=set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k); fieldnames.append(k)
    with p.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k:r.get(k,'') for k in fieldnames})


def read_jsonl(path: str | Path) -> list[dict[str,Any]]:
    out=[]
    with Path(path).open('r', encoding='utf-8') as f:
        for lineno,line in enumerate(f,1):
            if line.strip():
                try: out.append(json.loads(line))
                except Exception as e: raise ValueError(f'{path}:{lineno}: invalid JSONL: {e}') from e
    return out


def write_jsonl(path: str | Path, rows: Iterable[dict[str,Any]]) -> None:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')


def json_dump(path: str | Path, obj: Any) -> None:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')


def normalise_ws(text: str) -> str:
    return ' '.join((text or '').split())
