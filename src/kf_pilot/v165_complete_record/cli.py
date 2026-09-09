import argparse
import json
from pathlib import Path
from .repository import ROOT,produce,offline_guard,verify_files
from kf_pilot.v164_semantics.canonical import canonical_bytes,sha256,require


def encode(name,value):
    if name.endswith('.md'):return value.encode('utf-8')
    if name.endswith('.jsonl'):return b''.join(canonical_bytes(r)+b'\n' for r in value)
    return canonical_bytes(value)+b'\n'


def outputs():
    with offline_guard() as counters:
        result=produce()
    result['readiness_report.json']['transport_attempts']=counters
    result['code_manifest.json']={p.relative_to(ROOT).as_posix():sha256(p.read_bytes())
        for p in sorted((ROOT/'src/kf_pilot/v165_complete_record').glob('*.py'))}
    return result


def write(path):
    require(not path.exists(),'OUTPUT_ALREADY_EXISTS')
    result=outputs()
    path.mkdir(parents=True)
    hashes={}
    for name,value in result.items():
        raw=encode(name,value);(path/name).write_bytes(raw);hashes[name]=sha256(raw)
    (path/'artifact_hashes.json').write_bytes(encode('artifact_hashes.json',hashes))
    return result['readiness_report.json']


def gate(path,replay):
    verify_files(path);verify_files(replay)
    require({p.name for p in path.iterdir()}=={p.name for p in replay.iterdir()},'REPLAY_FILESET_MISMATCH')
    for p in path.iterdir():require(p.read_bytes()==(replay/p.name).read_bytes(),'REPLAY_BYTES_MISMATCH',p.name)
    recomputed=outputs()
    require({p.name for p in path.iterdir()}==set(recomputed)|{'artifact_hashes.json'},'OUTPUT_FILESET_MISMATCH')
    for name,value in recomputed.items():
        require((path/name).read_bytes()==encode(name,value),'INDEPENDENT_RECOMPUTATION_MISMATCH',name)
    return {'status':'V165_INDEPENDENT_GATE_PASS','files':len(recomputed)+1,'replay':'BYTE_EQUAL'}


def main():
    parser=argparse.ArgumentParser(description='V16.5 LOCAL NO_WRITE; repository APPLY is not enabled')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--output',type=Path,required=True)
    verify=sub.add_parser('verify');verify.add_argument('final',type=Path);verify.add_argument('replay',type=Path)
    args=parser.parse_args()
    print(json.dumps(write(args.output) if args.command=='run' else gate(args.final,args.replay),indent=2))
