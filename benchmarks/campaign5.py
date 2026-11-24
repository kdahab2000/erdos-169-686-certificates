"""Bounded, offline Campaign 5 producers. Run phases from the worktree root."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from verifiers.common import canonical_json_bytes, write_json
from verifiers import standalone_verify as st


def save(path, value):
    Path(path).write_text(json.dumps(value,indent=2)+'\n')


def pell():
    from solvers.s686_pell import produce
    from verifiers.v686 import verify_pell_batch
    c = produce()
    t = time.monotonic()
    assert st.verify_pell_batch(c) == verify_pell_batch(c)
    elapsed = time.monotonic()-t
    write_json('certificates/c5_686_pell_batch_2_1000.json',c)
    largest = max(c['rows'],key=lambda r:int(r['m']).bit_length())
    save('benchmarks/c5_pell.json',{'rows':len(c['rows']),'largest_m_N':largest['N'],
         'max_m_bits':int(largest['m']).bit_length(),'both_replays_seconds':str(elapsed)})


def squares():
    from solvers.s686_divisor import solve_square
    from verifiers.v686 import verify_null
    source = Path('benchmarks/square_results.json')
    scans = json.loads(source.read_text())['records']
    scan_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    reps = {}
    for p in Path('certificates').glob('c2_square_*.json'):
        c=json.loads(p.read_text()); st.verify_686_rep(c)
        reps.setdefault((int(c['N']),int(c['k'])),[]).append(p.name)
    def evidence(name,kind):
        c=json.loads((Path('certificates')/name).read_text())
        return {'kind':kind,'path':name,'sha256':hashlib.sha256(canonical_json_bytes(c)).hexdigest()}
    atlas=[]
    for s in range(2,101):
        decision=solve_square(s)
        coverage=[r for r in scans if int(r['s'])==s]
        for ks,limit in [({3},500000),(set(range(5,51)),50000)]:
            assert any(ks<=set(map(int,r['k_set'])) and int(r['n_max'])>=limit for r in coverage),s
        for r in coverage:
            if 'divisor' in r:assert r['divisor']==decision
            for w in r['witnesses']:
                # Existing scan witnesses must have a replayed representation.
                assert any(json.loads((Path('certificates')/name).read_text())['n']==w['n']
                           and json.loads((Path('certificates')/name).read_text())['m']==w['m']
                           for name in reps.get((s*s,int(w['k'])),[])),(s,w)
        positive=bool(decision['witnesses']['2'])
        assert not decision['witnesses']['4']
        if positive:
            k2=evidence(reps[(s*s,2)][0],'rep')
            name=f'c5_686_s{s}_k4_null.json'; ks=['4']
        else:
            name=f'initial_686_s{s}_k24_null.json' if s in (4,25) else f'c5_686_s{s}_k24_null.json'
            ks=['2','4']
        c=dict(schema='erd686.null.v1',s=str(s),k_set=ks,method='divisor_complete',box=None,domain='n>=1')
        assert st.verify_686_null(c)==verify_null(c)
        if name.startswith('c5_'):write_json('certificates/'+name,c)
        k4=evidence(name,'null')
        if not positive:k2=k4.copy()
        atlas.append({'s':s,'N':s*s,'family_4t2':{'t':(s-2)//4} if s>=10 and s%4==2 else None,
                      'k2':k2,'k4':k4,'higher_k_witnesses':[evidence(name,'rep') for (N,k),names in reps.items() if N==s*s and k>=3 for name in names],
                      'scan_coverage':{'path':str(source),'raw_sha256':scan_digest,'k3_n_max':500000,'k5_50_n_max':50000,'m':'unbounded','claim':'benchmark evidence only'},
                      'note':'k=3 remains open; supplied positive-rank >=2 context is not an integral-point exclusion.' if s in (2,5) else ''})
    counts={'k2_positive':sum(r['k2']['kind']=='rep' for r in atlas),'k4_positive':0,'neither':sum(r['k2']['kind']=='null' for r in atlas)}
    assert list(counts.values())==[24,0,75],counts
    save('benchmarks/c5_square_atlas.json',{'counts':counts,'rows':atlas})


def prefixes():
    from solvers.gk_bnb import solve
    p=Path('benchmarks/oeis_tables.json'); tables=json.loads(p.read_text())
    with Path('benchmarks/c5_prefix.log').open('a') as log:
        for table in tables['tables']:
            k=int(table['k'])
            if k<5:continue
            for n in range(int(table['endpoint'])+1,61):
                r=solve(k,n,max_seconds=20,warm_start=list(map(int,table['rows'][-1]['members'])))
                line=f"k={k} N={n} complete={r['complete']} nodes={r['nodes']} seconds={r['seconds']}"
                print(line,flush=True);log.write(line+'\n');log.flush()
                if not r['complete']:break
                t=time.monotonic(); proof=r['proof']; st.replay(proof)
                elapsed=time.monotonic()-t
                witness=dict(schema='erd169.finite.v1',k=str(k),N=str(n),members=list(map(str,r['witness'])),score=proof['witness_score'])
                st.verify_finite(witness)
                stem=f'c5_g{k}_{n}'
                for kind,c in [('proof',proof),('witness',witness)]:write_json(f'certificates/{stem}_{kind}.json',c)
                prefix=dict(schema='erd169.prefix_opt.v1',k=str(k),N=str(n),witness_sha256=hashlib.sha256(canonical_json_bytes(witness)).hexdigest(),proof_sha256=hashlib.sha256(canonical_json_bytes(proof)).hexdigest(),proof_format='erd169.bnb.v1',tie_policy='first optimum in deterministic warm-start traversal')
                with st.digest_run('certificates'):st.verify_prefix(prefix,Path('certificates'))
                write_json(f'certificates/{stem}_prefix.json',prefix)
                table['rows'].append(dict(N=str(n),value=witness['score'],members=witness['members'],prefix=stem+'_prefix.json',proof_bytes=str(len(canonical_json_bytes(proof))),nodes=str(r['nodes']),replay_ns=str(int(elapsed*10**9)),solve_ns=str(int(r['seconds']*10**9))))
                table['endpoint']=str(n);table['target']='56'
                save(p,tables)
                if elapsed>=1:break


def manifests():
    legacy=json.loads(Path('benchmarks/c5_legacy_bytes.json').read_text())
    for name,digest in legacy['raw_sha256'].items():
        assert hashlib.sha256((Path('certificates')/name).read_bytes()).hexdigest()==digest,name
    for name,old in legacy['manifests'].items():
        p=Path('certificates')/name;m=json.loads(p.read_text());assert m['certificates'][:len(old)]==old
        if name=='MANIFEST.json':
            existing={e['path'] for e in m['certificates']}
            for path in sorted(Path('certificates').glob('c5_*.json')):
                if path.name not in existing:
                    m['certificates'].append({'path':path.name,'sha256':hashlib.sha256(canonical_json_bytes(json.loads(path.read_text()))).hexdigest()})
            save(p,m)


def z125():
    from solvers.z125_solver import prove_orbits
    result=prove_orbits(max_seconds=30,orbit_seconds=20)
    print(result['status'],result['completed_orbits'],flush=True)


def reconcile():
    atlas=json.loads(Path('benchmarks/c5_square_atlas.json').read_text())
    tables=json.loads(Path('benchmarks/oeis_tables.json').read_text())['tables']
    p=Path('benchmarks/campaign5_results.json')
    result=json.loads(p.read_text())
    result.update(manifest_entries={n:len(json.loads((Path('certificates')/n).read_text())['certificates']) for n in ('MANIFEST.json','MANIFEST_DEEP.json')},
                  pell=json.loads(Path('benchmarks/c5_pell.json').read_text()),
                  square_counts=atlas['counts'],prefix_endpoints={t['k']:int(t['endpoint']) for t in tables},
                  prefix_rows=sum(len(t['rows']) for t in tables),
                  new_certificates=len(list(Path('certificates').glob('c5_*.json'))),
                  z125=json.loads(Path('benchmarks/c5_z125_measure.json').read_text()))
    timings=Path('benchmarks/c5_timings.json')
    if timings.exists():
        result['timings']=json.loads(timings.read_text())
        result['default_under_12_seconds']=int(float(result['timings']['MANIFEST.json']['seconds'])*1000)<12000
    save(p,result)


def main():
    phases={'pell':pell,'squares':squares,'prefixes':prefixes,'manifests':manifests,'z125':z125,'reconcile':reconcile}
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=phases)
    args=p.parse_args()
    if Path.cwd().resolve()!=ROOT:raise ValueError('run from repository root')
    phases[args.phase]()

if __name__=='__main__':main()
