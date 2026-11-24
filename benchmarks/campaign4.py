"""Reproducible local Campaign 4 producers. No external services or dependencies.

Run from repository root: python3 -B benchmarks/campaign4.py PHASE
Existing legacy certificates are never modified. All searches remain bounded.
"""
import argparse
import hashlib
import json
import sys
import time
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from verifiers.common import write_json,canonical_json_bytes
from verifiers.standalone_verify import (verify_certificate,verify_sieve_null,replay,
    verify_finite,verify_prefix,digest_run)
from solvers.gk_bnb import solve


def save(name,value):
    (ROOT/'benchmarks'/name).write_text(json.dumps(value,indent=2)+'\n')


def quantized():
    from solvers.quantized_block import produce
    for depth in (6,10):
        write_json(f'certificates/c4_pure5_q_depth{depth}.json',produce(depth=depth))


def rigidity():
    from solvers.f5_decisive import solve_dual
    r=solve_dual(9,quantized=True)
    save('c4_dual_L9.json',r)
    if r['status']!='feasible exact dual':raise ValueError('unresolved dual')
    c=json.loads(Path('certificates/c3_rigidity_L8.json').read_text())
    c.update(schema='erd169.rigidity.v2',L='9',candidates=r['candidates'],dual_arcs=r['dual_arcs'],min_nonempty_loss={'num':'0','den':'1'})
    with digest_run('certificates'):verify_certificate(c,Path('certificates'))
    write_json('certificates/c4_rigidity_L9.json',c)


def prefixes():
    p=Path('benchmarks/oeis_tables.json'); tables=json.loads(p.read_text())
    for table in tables['tables']:
     k=int(table['k']); target=36 if k<5 else 48
     for n in range(int(table['endpoint'])+1,target+1):
      t=time.monotonic(); r=solve(k,n,max_seconds=30,warm_start=list(map(int,table['rows'][-1]['members'])))
      print(k,n,'complete',r['complete'],'nodes',r['nodes'],'seconds',r['seconds'],flush=True)
      if not r['complete']: break
      proof=r['proof']; replay(proof)
      witness=dict(schema='erd169.finite.v1',k=str(k),N=str(n),members=list(map(str,r['witness'])),score=proof['witness_score'])
      verify_finite(witness)
      stem=f'c4_g{k}_{n}'
      for kind,c in [('proof',proof),('witness',witness)]: write_json(f'certificates/{stem}_{kind}.json',c)
      prefix=dict(schema='erd169.prefix_opt.v1',k=str(k),N=str(n),witness_sha256=hashlib.sha256(canonical_json_bytes(witness)).hexdigest(),proof_sha256=hashlib.sha256(canonical_json_bytes(proof)).hexdigest(),proof_format='erd169.bnb.v1',tie_policy='first optimum in deterministic warm-start traversal')
      with digest_run('certificates'): verify_prefix(prefix,Path('certificates'))
      write_json(f'certificates/{stem}_prefix.json',prefix)
      table['rows'].append(dict(N=str(n),value=witness['score'],members=witness['members'],prefix=stem+'_prefix.json',proof_bytes=str(len(canonical_json_bytes(proof))),nodes=str(r['nodes']),replay_ns=str(int((time.monotonic()-t-r['seconds'])*10**9)),solve_ns=str(int(r['seconds']*10**9))))
      table['endpoint']=str(n)
      p.write_text(json.dumps(tables,indent=2)+'\n')
     table['target']=str(target)
     p.write_text(json.dumps(tables,indent=2)+'\n')


def sieves():
    for method,kl,kh,hi,label in [('cubic_crt_icbrt',3,3,5000000,'k3_5m'),('prime_power_exclusion',101,200,50000,'k101_200_50k')]:
     for s in (2,5):
      c=dict(schema='erd686.sieve_null.v1',s=str(s),k_lo=str(kl),k_hi=str(kh),n_lo='1',n_hi=str(hi),method=method,domain='n>=1')
      t=time.monotonic()
      try:
       answer=verify_sieve_null(c)
       write_json(f'certificates/c4_null_s{s}_{label}.json',c)
       print(method,s,answer,'seconds',time.monotonic()-t,flush=True)
      except Exception as e:
       print('UNRESOLVED',method,s,type(e).__name__,str(e),'seconds',time.monotonic()-t,flush=True)
       raise


def searches():
    from solvers.z125_solver import z25,z125,h0_orbit_probe,residual_probe
    from solvers.walker_search import search
    from solvers.puncture_search import search as punctures,window_probe
    r=z25()
    if r['status']=='complete':
        verify_certificate(r['certificate'])
        write_json('certificates/c4_z25_max.json',r.pop('certificate'))
    save('c4_z25.json',r)
    save('c4_z125.json',z125())
    fibres=h0_orbit_probe()
    save('c4_h0_orbits.json',fibres)
    save('c4_h0_residual.json',residual_probe(fibres))
    ub=int(json.loads(Path('certificates/c4_pure5_q_depth10.json').read_text())['ub_num'])
    save('c4_walker.json',search(ub))
    save('c4_puncture.json',punctures())
    save('c4_window_probe.json',window_probe())


def manifests():
    legacy=json.loads(Path('benchmarks/c4_legacy_bytes.json').read_text())
    for name,digest in legacy['raw_sha256'].items():
        if hashlib.sha256((Path('certificates')/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('legacy certificate bytes changed: '+name)
    path=Path('certificates/MANIFEST.json');m=json.loads(path.read_text())
    if m['certificates'][:471]!=legacy['entries']:raise ValueError('legacy manifest prefix changed')
    fast=[];deep=[]
    for path in sorted(Path('certificates').glob('c4_*.json')):
        c=json.loads(path.read_text())
        entry={'path':path.name,'sha256':hashlib.sha256(canonical_json_bytes(c)).hexdigest()}
        (deep if '_k101_200_' in path.name else fast).append(entry)
    wanted=legacy['entries']+fast
    # Existing default entries must remain in place; later additions append only.
    existing=m['certificates']
    if any(e not in wanted for e in existing):raise ValueError('refusing to discard manifest entries')
    m['certificates']=existing+[e for e in wanted if e not in existing]
    Path('certificates/MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n')
    Path('certificates/MANIFEST_DEEP.json').write_text(json.dumps({'schema':'erdos.manifest.v1','campaign':'ERD-071 deep replay','certificates':deep},indent=2)+'\n')


def measure():
    path=Path('benchmarks/c4_timings.json')
    results=json.loads(path.read_text()) if path.exists() else {}
    for name in ('MANIFEST.json','MANIFEST_DEEP.json'):
        t=time.monotonic()
        r=subprocess.run([sys.executable,'-B','verifiers/standalone_verify.py','certificates/'+name],capture_output=True,text=True)
        elapsed=time.monotonic()-t
        Path('benchmarks/c4_'+name+'.log').write_text(r.stdout+r.stderr)
        results[name]={'seconds':str(elapsed),'returncode':str(r.returncode),'summary':r.stdout.splitlines()[-1]}
        print(name,results[name],flush=True)
        if r.returncode:raise ValueError('manifest replay failed')
        if name=='MANIFEST.json' and elapsed>=10:raise ValueError('default replay exceeds 10 second gate')
    save('c4_timings.json',results)



def reconcile():
    q=json.loads(Path('certificates/c4_pure5_q_depth10.json').read_text())
    fast=json.loads(Path('certificates/MANIFEST.json').read_text())['certificates']
    deep=json.loads(Path('certificates/MANIFEST_DEEP.json').read_text())['certificates']
    prefixes={str(k):[] for k in range(3,7)}
    for entry in fast+deep:
        c=json.loads((Path('certificates')/entry['path']).read_text())
        if c['schema']=='erd169.prefix_opt.v1':prefixes[c['k']].append(c['N'])
    h0=json.loads(Path('benchmarks/c4_h0_orbits.json').read_text())
    residual=json.loads(Path('benchmarks/c4_h0_residual.json').read_text())
    window=json.loads(Path('benchmarks/c4_window_probe.json').read_text())
    walker=json.loads(Path('benchmarks/c4_walker.json').read_text())
    save('campaign4_results.json',{
        'scope':'ERD-071 local bounded Campaign 4; no external publication or infinite-problem resolution',
        'manifest_entries':{'default':str(len(fast)),'deep':str(len(deep))},
        'claims':[
            {'claim':'prefix optima','claim_level':'optimal','rows':str(sum(len(v) for v in prefixes.values())),
             'endpoints':{k:str(max(map(int,v))) for k,v in prefixes.items()},'certificate_patterns':['c2_g*_prefix.json','c4_g*_prefix.json']},
            {'claim':'pure S5 enclosure','claim_level':'feasible','certificate':'c4_pure5_q_depth10.json',
             'lb_num':q['lb_num'],'ub_num':q['ub_num'],'Q':q['Q'],'width_num':str(int(q['ub_num'])-int(q['lb_num']))},
            {'claim':'unchanged-tail rigidity','claim_level':'optimal','levels':['6','7','8','9'],
             'maximum_delta':'0','uniqueness_at_L9':False,'certificates':['c3_rigidity_L6.json','c3_rigidity_L7.json','c3_rigidity_L8.json','c4_rigidity_L9.json']},
            {'claim':'candidate sequence','values':['0','0','0','0','0','2','28','260','1994'],
             'certified_levels':['6','7','8','9'],'computed_uncertified_levels':['1','2','3','4','5']},
            {'claim':'Z25 cyclic maximum','claim_level':'optimal','value':'16','certificate':'c4_z25_max.json'},
            {'claim':'Z125 cyclic bounds','claim_level':'feasible lower bound; certified upper bound; unresolved maximum',
             'lower':'64','upper':'80','certificates':['c2_block_search125.json','c4_z25_max.json'],
             'orbit_representatives':str(len(h0['h0_representative_masks'])),'unexplored_branches':str(len(residual['unexplored_branches']))},
            {'claim':'cubic square sweep','claim_level':'bounded box','N':['4','25'],'k':['3'],'n_lo':'1','n_hi':'5000000',
             'certificates':['c4_null_s2_k3_5m.json','c4_null_s5_k3_5m.json']},
            {'claim':'higher-k square sweep','claim_level':'bounded box','N':['4','25'],'k_lo':'5','k_hi':'200','n_lo':'1','n_hi':'50000',
             'certificates':['c2_null_s2_k5_100.json','c2_null_s5_k5_100.json','c4_null_s2_k101_200_50k.json','c4_null_s5_k101_200_50k.json']}
        ],
        'research':{'claim':'none','walker_candidates':str(len(walker['candidates'])),'walker_promoted':str(len(walker['promoted_certificates'])),
                    'window_candidates':window['candidate_count'],'window_processed':window['processed'],'window_greedy_deficits':str(len(window['deficits'])),
                    'z125':'unresolved; see c4_h0_orbits.json and c4_h0_residual.json',
                    'glued_tail':'gated; no candidate crossed UB_ref; implementation not activated'},
        'limitations':['No complete positive H0 proof available for end-to-end validation.',
                       'Greedy puncture and window probes do not exhaust coupled or self-similar gluing constructions.',
                       'No literature baseline or external problem status was checked.'],
        'release':'User trial and explicit approval required; Relay cannot deploy.'})

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    phases={'quantized':quantized,'rigidity':rigidity,'prefixes':prefixes,'sieves':sieves,'searches':searches,'manifests':manifests,'measure':measure,'reconcile':reconcile}
    parser.add_argument('phase',choices=phases)
    args=parser.parse_args()
    if Path.cwd().resolve()!=ROOT:raise ValueError('run from repository root')
    start=time.monotonic();phases[args.phase]()
    print(args.phase,'seconds',time.monotonic()-start)


if __name__=='__main__':main()
