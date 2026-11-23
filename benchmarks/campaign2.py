#!/usr/bin/env python3
"""Reproducible bounded local campaign. No partial proof/null is published."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fractions import Fraction
from solvers.gk_bnb import solve
from solvers.head_tail import (coupled_search, cyclic_edges, cyclic_maximum_25,
                               scan_tail_candidates, cyclic_weighted_25,
                               cyclic_125_search, coupled_subset_trials)
from solvers.s686_search import search
from solvers.s686_divisor import solve_square
from verifiers.common import canonical_json_bytes, fraction_object
from verifiers.proof_replay import replay_proof
from verifiers.v169 import block_enclosure, verify_block_digit, verify_prefix, verify_head_tail
from verifiers.v686 import verify_null, verify_representation
from verifiers.standalone_verify import verify_certificate

CERTS = ROOT/'certificates'
MANIFEST = CERTS/'MANIFEST.json'


def save(name, obj):
    raw = canonical_json_bytes(obj)
    path = CERTS/name
    if path.exists() and path.read_bytes().strip() != raw:
        raise RuntimeError('refusing to overwrite existing artifact: '+name)
    path.write_bytes(raw+b'\n')
    manifest = json.loads(MANIFEST.read_text())
    entry = {'path':name,'sha256':hashlib.sha256(raw).hexdigest()}
    old = [x for x in manifest['certificates'] if x['path']==name]
    if old and old != [entry]:
        raise RuntimeError('manifest conflict')
    if not old:
        manifest['certificates'].append(entry)
        MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
    return entry


def tables():
    output = {'schema':'erdos.oeis_tables.v1', 'novelty':'SOURCE_REPORTED_REQUIRES_LIVE_CHECK','tables':[]}
    for k,target in [(3,30),(4,30),(5,40),(6,40)]:
        rows=[]
        warm=None
        for n in range(1,target+1):
            result = solve(k,n,max_nodes=100000,max_seconds=5,warm_start=warm)
            if not result['complete']:
                print('incomplete',k,n,flush=True)
                break
            proof = result['proof']
            start = time.monotonic_ns()
            assert replay_proof(proof)['valid']
            assert verify_certificate(proof)['valid']
            replay_ns = time.monotonic_ns()-start
            witness = dict(schema='erd169.finite.v1',k=str(k),N=str(n),members=proof['witness'],score=proof['witness_score'])
            pe=save(f'c2_g{k}_{n}_proof.json',proof)
            we=save(f'c2_g{k}_{n}_witness.json',witness)
            wrapper=dict(schema='erd169.prefix_opt.v1',k=str(k),N=str(n),witness_sha256=we['sha256'],proof_sha256=pe['sha256'],proof_format='erd169.bnb.v1',tie_policy='first strict improvement')
            assert verify_prefix(wrapper,CERTS)['valid']
            save(f'c2_g{k}_{n}_prefix.json',wrapper)
            rows.append({'N':str(n),'value':proof['witness_score'],'members':proof['witness'],
                         'prefix':f'c2_g{k}_{n}_prefix.json','proof_bytes':str(len(canonical_json_bytes(proof))),
                         'nodes':str(result['nodes']),'replay_ns':str(replay_ns),'solve_ns':str(int(result['seconds']*1000000000))})
            warm=result['witness']
            print('certified',k,n,result['nodes'],flush=True)
        output['tables'].append({'k':str(k),'endpoint':str(len(rows)),'target':str(target),'rows':rows})
        (ROOT/'benchmarks/oeis_tables.json').write_text(json.dumps(output,indent=2)+'\n')


def heads():
    records=[]
    for depth in range(1,7):
        try:
            lb,ub=block_enclosure(5,[0,1,2,3],1,depth)
            cert=dict(schema='erd169.block_digit.v1',k='5',p='5',block_len='1',D=['0','1','2','3'],s='1',depth=str(depth),lb=fraction_object(lb),ub=fraction_object(ub))
            assert verify_block_digit(cert)['valid'] and verify_certificate(cert)['valid']
            entry=save(f'c2_pure5_depth{depth}.json',cert)
            records.append(dict(depth=str(depth),lb=cert['lb'],ub=cert['ub'],width=fraction_object(ub-lb),reference=entry))
        except ValueError as exc:
            records.append({'depth':str(depth),'status':'RESOURCE_CAP','reason':str(exc)})
            break
    data={'pure':records,'cyclic25':cyclic_maximum_25(),'cyclic125_edge_count':str(len(cyclic_edges(125))),
          'head_trials':[coupled_search([5,24,25,3380],L) for L in (6,7)],
          'unmet':['precision < 1e-6','full A(6), A(7), A(8)','weighted cyclic optimization','positive certified delta']}
    scans=[]
    for L in (6,7,8):
        scan=scan_tail_candidates(L, max_seconds=60)
        (ROOT/f'benchmarks/head_candidates_L{L}.json').write_text(json.dumps(scan,indent=2)+'\n')
        scans.append(scan)
    data['candidate_scans']=scans
    data['weighted25']=cyclic_weighted_25()
    data['heuristic125']=cyclic_125_search()
    data['coupled_trials']=[coupled_subset_trials(list(map(int,scan['tail_compatible'][:8])),int(scan['L']))
                            for scan in scans[:2]]
    for name,value in [('cyclic25_weighted',data['weighted25']),('cyclic125_search',data['heuristic125']),('head_coupled_trials',data['coupled_trials'])]:
        (ROOT/f'benchmarks/{name}.json').write_text(json.dumps(value,indent=2)+'\n')
    for length,digits,label,depth in [(2,data['weighted25']['digits'],'weighted25',2),(3,data['heuristic125']['digits'],'search125',1)]:
        lb,ub=block_enclosure(5**length,list(map(int,digits)),1,depth)
        cert=dict(schema='erd169.block_digit.v1',k='5',p='5',block_len=str(length),D=digits,s='1',depth=str(depth),lb=fraction_object(lb),ub=fraction_object(ub))
        verify_block_digit(cert);verify_certificate(cert)
        save(f'c2_block_{label}.json',cert)
    reference=[r for r in records if 'lb' in r][-1]['reference']['sha256']
    for trial in data['coupled_trials']:
        if 'delta_num' not in trial:
            continue
        cert=dict(schema='erd169.head_tail.v1',k='5',p='5',D=['0','1','2','3'],s='1',L=trial['L'],added=trial['added'],removed=trial['removed'],delta={'num':trial['delta_num'],'den':trial['delta_den']},pure_ref_sha256=reference)
        verify_head_tail(cert,CERTS);verify_certificate(cert,CERTS)
        save(f"c2_head_tail_trial_L{trial['L']}.json",cert)
    data['unmet']=['precision < 1e-6 under unchanged 4096-bit cap','global weighted cyclic125 optimum','positive certified delta','exhaustive coupled optimization at L=7,8']
    (ROOT/'benchmarks/head_tail_results.json').write_text(json.dumps(data,indent=2)+'\n')
    print('head evidence complete',flush=True)


def squares(full=False):
    records=[]
    start=time.monotonic_ns()
    for s in range(2,101):
        decision=solve_square(s)
        for k in (2,4):
            for hit in decision['witnesses'][str(k)]:
                cert=dict(schema='erd686.rep.v1',N=str(s*s),k=str(k),**hit)
                verify_representation(cert)
                save(f"c2_square_s{s}_k{k}_n{hit['n']}.json",cert)
        for ks,limit in [([3],500000 if full else 1000),(list(range(5,101)),50000 if full else 1000)]:
            result=search(s*s,ks,limit)
            for cert in result['certificates']:
                verify_representation(cert); verify_certificate(cert)
                save(f"c2_square_s{s}_k{cert['k']}_n{cert['n']}.json",cert)
            records.append({'s':str(s),'N':str(s*s),'n_max':str(limit),'k_set':list(map(str,ks)),
                            'witnesses':result['certificates'],'divisor':decision})
        print('square',s,'hits',sum(len(r['witnesses']) for r in records[-2:]),flush=True)
    for s in (2,5):
        for ks,limit,label in [([3],500000,'k3'),(list(range(5,101)),50000,'k5_100')]:
            result=search(s*s,ks,limit)
            cert=result['certificate']
            if result['status']=='not_found_in_box':
                verify_null(cert);verify_certificate(cert)
                save(f'c2_null_s{s}_{label}.json',cert)
            else:
                for cert in result['certificates']:
                    verify_representation(cert);verify_certificate(cert)
                    save(f"c2_square_s{s}_k{cert['k']}_n{cert['n']}.json",cert)
            records.append({'s':str(s),'N':str(s*s),'n_max':str(limit),'k_set':list(map(str,ks)),
                            'status':result['status'],'witnesses':result['certificates']})
            print('deep square',s,label,result['status'],flush=True)
    (ROOT/'benchmarks/square_results.json').write_text(json.dumps({'records':records,'elapsed_ns':str(time.monotonic_ns()-start)},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('track',choices=['tables','heads','squares'])
    parser.add_argument('--full-squares',action='store_true')
    args=parser.parse_args()
    if args.track == 'squares':
        squares(args.full_squares)
    else:
        globals()[args.track]()
