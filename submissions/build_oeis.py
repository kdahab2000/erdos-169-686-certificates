"""Deterministic offline drafts. No submission, network or novelty claim."""
from pathlib import Path
import json
import inspect
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from solvers.f5_decisive import _step, _tail_possible, build_tail_automaton

SECTIONS=('NAME','DATA','OFFSET','COMMENTS','EXAMPLE','PROG','CROSSREFS','KEYWORD','AUTHOR')


def rational_program(k,part):
    return f'''from fractions import Fraction

def terms(n=12, k={k}):
    result = []
    for N in range(1, n+1):
        best = Fraction(0)
        suffix = [Fraction(0)]*(N+2)
        for v in range(N, 0, -1):
            suffix[v] = suffix[v+1]+Fraction(1,v)
        def search(v, chosen, score):
            nonlocal best
            if score+suffix[v] <= best:
                return
            if v > N:
                best = max(best, score)
                return
            if not any(all(v-j*d in chosen for j in range(1,k))
                       for d in range(1,(v-1)//(k-1)+1)):
                search(v+1, chosen | {{v}}, score+Fraction(1,v))
            search(v+1, chosen, score)
        search(1, set(), Fraction(0))
        result.append(best.{"numerator" if part=="num" else "denominator"})
    return result

print(", ".join(map(str,terms())))
# ~~~~'''


def tail_program():
    code='from functools import lru_cache\n\n'
    for f in (_step,_tail_possible,build_tail_automaton):
        code+=inspect.getsource(f)+'\n'
    return code+'print(", ".join(str(len(build_tail_automaton(L))) for L in range(1,7)))\n# ~~~~'


def render(fields):
    return '\n\n'.join(key+'\n'+fields[key] for key in SECTIONS)+'\n'


def certified_tables():
    """Build contiguous rows exclusively from manifest-backed replayed prefixes."""
    from verifiers.standalone_verify import load_strict,verify_prefix,digest_run,resolve_digest
    entries=[]
    for name in ('MANIFEST.json','MANIFEST_DEEP.json'):
        path=ROOT/'certificates'/name
        if path.exists(): entries.extend(load_strict(path)['certificates'])
    rows={k:{} for k in range(3,7)}
    with digest_run(ROOT/'certificates'):
        for entry in entries:
            certificate_path=(ROOT/'certificates'/entry['path']).resolve()
            certificate_path.relative_to((ROOT/'certificates').resolve())
            cert=load_strict(certificate_path)
            if cert.get('schema')!='erd169.prefix_opt.v1':continue
            # Bind the operational manifest entry as well as its reference digests.
            from verifiers.standalone_verify import verify_entry
            if not verify_entry(entry,ROOT/'certificates')['valid']:
                raise ValueError('invalid OEIS prefix certificate')
            witness=resolve_digest(cert['witness_sha256'],ROOT/'certificates')
            k=int(cert['k']); n=int(cert['N'])
            row={'N':str(n),'value':witness['score'],'members':witness['members']}
            if n in rows[k] and rows[k][n]!=row:raise ValueError('conflicting certified row')
            rows[k][n]=row
    tables=[]
    for k,data in rows.items():
        if sorted(data)!=list(range(1,max(data)+1)):raise ValueError('noncontiguous certified table')
        tables.append({'k':str(k),'rows':[data[n] for n in sorted(data)]})
    return tables


def build():
    out=ROOT/'submissions/oeis'
    out.mkdir(parents=True,exist_ok=True)
    tables=certified_tables()
    author='_Khaled Aboeldahab_, Nov 24 2026'
    counts=[]
    for L in range(1,10):
        p=ROOT/f'benchmarks/head_candidates_L{L}.json'
        if not p.exists():
            break
        scan=json.loads(p.read_text())
        if not scan['complete']:
            break
        counts.append(str(len(scan['tail_compatible'])))
    fields=dict(NAME='Number of positive integers a <= 5^L outside 1 + K_5 that create no 5-term arithmetic progression with a as first term and four terms in the tail {1+x: x >= 5^L, all base-5 digits of x in {0,1,2,3}}.',
                DATA=', '.join(counts),OFFSET='1,6',
                COMMENTS='K_5 consists of nonnegative integers whose base-5 digits are in {0,1,2,3}. Exact carry-automaton enumeration, with individual tail checks at L=9. Tail compatibility does not mean that a can be added without head removals. Novelty: SOURCE_REPORTED_REQUIRES_LIVE_CHECK.',
                EXAMPLE='For L=6 the two values are 3380 and 8340.',PROG=tail_program(),
                CROSSREFS='Related finite reciprocal maxima: A?????? (g_3 numerators), A?????? (g_3 denominators).',KEYWORD='nonn,more',AUTHOR=author)
    (out/'batch1_seq1_tail_compat_base5.txt').write_text(render(fields))
    (out/'b_tail_compat_base5.txt').write_text(''.join(f'{i} {a}\n' for i,a in enumerate(counts,1)))
    for table in tables:
        k=int(table['k']); rows=table['rows']
        values={part:[r['value'][part] for r in rows] for part in ('num','den')}
        endpoint=0
        for n in range(1,len(rows)+1):
            if all(len(', '.join(v[:n]))<=260 for v in values.values()):
                endpoint=n
            else:
                break
        for part in ('num','den'):
            label='Numerators' if part=='num' else 'Denominators'
            partner='denominators' if part=='num' else 'numerators'
            prefix=f'batch1_seq{2 if part=="num" else 3}_g3_{"numerators" if part=="num" else "denominators"}' if k==3 else f'batch2_g{k}_{part}'
            bname=f'b_g3_{"numerators" if part=="num" else "denominators"}.txt' if k==3 else f'b_g{k}_{part}.txt'
            sequence=values[part]
            first_large=next((i for i,a in enumerate(sequence,1) if int(a)>1),1)
            comments=f'g_{k}(n) is the maximum of sum(1/a for a in S) over all {k}-term arithmetic-progression-free subsets S of {{1,...,n}}. Fractions are reduced. The b-file contains all {len(rows)} certified terms, backed by finite optimization proof replays. Novelty: SOURCE_REPORTED_REQUIRES_LIVE_CHECK.'
            if k==3:
                comments+=' The greedy sequence differs from the optimum at n=9 (143/72 versus 39/20) and n=24 (6059/2640 versus 45831/20020).'
            fields=dict(NAME=f'{label} of g_{k}(n), the maximum reciprocal sum of a {k}-term arithmetic-progression-free subset of {{1,...,n}}.',DATA=', '.join(sequence[:endpoint]),OFFSET=f'1,{first_large}',COMMENTS=comments,EXAMPLE=f'For n=1, g_{k}(1)=1, so a(1)=1.',PROG=rational_program(k,part),CROSSREFS=f'A?????? ({partner} of g_{k}(n)).',KEYWORD='nonn,frac',AUTHOR=author)
            (out/(prefix+'.txt')).write_text(render(fields))
            (out/bname).write_text(''.join(f'{i} {a}\n' for i,a in enumerate(sequence,1)))


if __name__=='__main__':
    build()
