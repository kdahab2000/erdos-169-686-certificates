"""Local exact Campaign 3 searches. Incomplete searches never assert rigidity."""
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from verifiers.v169 import padded_member, tail_compatible
from solvers.head_tail import head_edges, cyclic_edges


@lru_cache(None)
def _step(states, digit):
    return tuple(sorted({tuple(v//5 for v in values)
                         for carries in states for d in range(5)
                         for values in [tuple(c+digit+j*d for j,c in enumerate(carries,1))]
                         if all(v%5 < 4 for v in values)}))


@lru_cache(None)
def _tail_possible(states):
    pending = [(c,0) for c in states]
    seen = set(pending)
    for carries,mask in pending:
        if carries == (0,0,0,0) and mask == 15:
            return True
        for d in range(5):
            values = tuple(c+j*d for j,c in enumerate(carries,1))
            if any(v%5 == 4 for v in values):
                continue
            nxt = (tuple(v//5 for v in values), mask | sum(1<<j for j,v in enumerate(values) if v%5))
            if nxt not in seen:
                seen.add(nxt)
                pending.append(nxt)
    return False


def build_tail_automaton(L):
    """Enumerate A(L) using determinized low-digit carry transitions."""
    if not 1 <= L <= 9:
        raise ValueError('level cap')
    answer = []
    def visit(pos, states, x, place, outside):
        if pos == L:
            if outside and not _tail_possible(states):
                answer.append(x+1)
            return
        for digit in range(5):
            visit(pos+1, _step(states,digit), x+digit*place, place*5, outside or digit == 4)
    visit(0, ((0,0,0,0),), 0, 1, False)
    return sorted(answer)


def count_A(L):
    return len(build_tail_automaton(L))


def edges_for(a,L):
    """All single-addition APs with a removable head point, by carry DFS.

    A head blocker implies d < 5**L: if a is first, one other term
    lies in the head; otherwise start>0 gives the bound.
    """
    bound = 5**L
    edges = set()
    for i in range(5):
        coefficients = [j-i for j in range(5) if j != i]
        def visit(pos,carries,d,place):
            if pos == L:
                if d and all(padded_member(c,[0,1,2,3]) for c in carries):
                    start = a-i*d
                    terms = tuple(start+j*d for j in range(5))
                    if start>0 and any(x != a and x<bound+1 for x in terms):
                        edges.add(terms)
                return
            for digit in range(5):
                values = tuple(c+j*digit for c,j in zip(carries,coefficients))
                if all(v%5 < 4 for v in values):
                    visit(pos+1,tuple(v//5 for v in values),d+digit*place,place*5)
        visit(0,(a-1,)*4,0,1)
    return sorted(edges)


def solve_dual(L, quantized=False):
    """Exact feasible sparse dual search; failure is explicitly inconclusive."""
    candidates = build_tail_automaton(L)
    capacity = {}
    arcs = []
    deficits = {}
    Q = 10**60
    def initial_capacity(r):
        return Fraction(Q//r,Q) if quantized else Fraction(1,r)
    for a in candidates:
        remaining = Fraction((Q+a-1)//a,Q) if quantized else Fraction(1,a)
        edges = edges_for(a,L)
        edges.sort(key=lambda e:(len([x for x in e if x!=a and x<1+5**L]),max(e),e))
        for edge in edges:
            head = [r for r in edge if r!=a and r<1+5**L]
            weight = min([remaining]+[capacity.get(r,initial_capacity(r)) for r in head])
            if weight<=0:
                continue
            arcs.append({'a':str(a),'start':str(edge[0]),'diff':str(edge[1]-edge[0]),
                         'weight':{'num':str(weight.numerator),'den':str(weight.denominator)}})
            for r in head:
                capacity[r] = capacity.get(r,initial_capacity(r))-weight
            remaining -= weight
            if not remaining:
                break
        if remaining:
            deficits[str(a)] = str(remaining)
    return {'L':str(L),'candidates':list(map(str,candidates)),'dual_arcs':arcs,
            'status':'feasible exact dual' if not deficits else 'unresolved', 'deficits':deficits}


def minimum_hitting_cost(edges,max_nodes=200000):
    """Exact weighted B&B; dominance removes only more expensive substitutes."""
    edges=set(map(frozenset,edges))
    if frozenset() in edges:
        return {'complete':True,'feasible':False,'nodes':'0'}
    if not edges:
        return {'complete':True,'feasible':True,'cost':{'num':'0','den':'1'},'removed':[],'nodes':'1'}
    vertices=set().union(*edges)
    incidence={r:frozenset(i for i,e in enumerate(edges) if r in e) for r in vertices}
    kept={r for r in vertices if not any(q>r and incidence[r]<=incidence[q] for q in vertices)}
    edges={e&kept for e in edges}
    edges={e for e in edges if not any(f<e for f in edges)}
    forced=set().union(*(e for e in edges if len(e)==1))
    edges={e for e in edges if not e&forced}
    initial=sum((Fraction(1,r) for r in forced),Fraction())
    incumbent=forced|set().union(*edges)
    best=sum((Fraction(1,r) for r in incumbent),Fraction())
    nodes=0
    complete=True
    memo={}
    def visit(todo,chosen,cost):
        nonlocal nodes,complete,best,incumbent
        if nodes>=max_nodes:
            complete=False
            return
        nodes+=1
        if not todo:
            if cost<=best:
                best,incumbent=cost,chosen
            return
        if cost>=best or memo.get(todo,best+1)<=cost:
            return
        memo[todo]=cost
        occupied=set()
        bound=cost
        for e in sorted(todo,key=lambda e:(-Fraction(1,max(e)),len(e),tuple(sorted(e)))):
            if not occupied&e:
                bound+=Fraction(1,max(e))
                occupied.update(e)
        if bound>=best:
            return
        edge=min(todo,key=lambda e:(len(e),tuple(sorted(e))))
        for r in sorted(edge,reverse=True):
            visit(frozenset(e for e in todo if r not in e),chosen|{r},cost+Fraction(1,r))
    visit(frozenset(edges),forced,initial)
    return {'complete':complete,'feasible':True,'cost':{'num':str(best.numerator),'den':str(best.denominator)},
            'removed':list(map(str,sorted(incumbent))),'nodes':str(nodes)}


def singleton_cost(a,L=6,max_nodes=200000):
    result=minimum_hitting_cost([set(x for x in e if x!=a and x<1+5**L)
                                for e in edges_for(a,L)],max_nodes)
    return dict(result,a=str(a))


def bnb(L,max_nodes=200000):
    """Exhaust all four A(6) subsets, including coupled-addition edges."""
    candidates=build_tail_automaton(L)
    if len(candidates)>2:
        return {'status':'unresolved','reason':'bounded exhaustive subset cap (2 candidates)','L':str(L)}
    from itertools import combinations
    records=[]
    for mask in range(1<<len(candidates)):
        added={a for i,a in enumerate(candidates) if mask>>i&1}
        edges={e for a in added for e in edges_for(a,L)}
        for a,b in combinations(sorted(added),2):
            for i in range(4):
                for j in range(i+1,5):
                    if (b-a)%(j-i):
                        continue
                    d=(b-a)//(j-i); start=a-i*d
                    terms=tuple(start+t*d for t in range(5))
                    if start>0 and all(x in added or padded_member(x-1,[0,1,2,3]) for x in terms):
                        edges.add(terms)
        repair=minimum_hitting_cost([set(x for x in e if x not in added and x<1+5**L) for e in edges],max_nodes)
        row={'added':list(map(str,sorted(added))),'repair':repair}
        if repair['feasible']:
            cost=Fraction(int(repair['cost']['num']),int(repair['cost']['den']))
            delta=sum((Fraction(1,a) for a in added),Fraction())-cost
            row['delta']={'num':str(delta.numerator),'den':str(delta.denominator)}
        records.append(row)
    return {'L':str(L),'status':'complete' if all(r['repair']['complete'] for r in records) else 'unresolved','subsets':records}


def puncture_pool(L):
    return {'status':'unresolved','L':str(L),'reason':'complete pool and four-disjoint infinite-tail witnesses not constructed'}


def puncture_bound(L,tail_pool_cap=10):
    """Bounded singleton search, not a complete puncture pool or upper bound.

    For A(L), edges_for lists every obstructing AP, so a fully hit edge
    family is feasible even with punctures. A positive edit still requires
    a reviewed punctured schema before certificate status.
    """
    from itertools import combinations
    records=[]
    for a in build_tail_automaton(L):
        edges=[set(e)-{a} for e in edges_for(a,L)]
        tail=set(r for e in edges for r in e if r>=1+5**L)
        ranked=sorted(tail,key=lambda r:(-sum(r in e for e in edges),-r))[:tail_pool_cap]
        best=None
        trials=0
        for budget in (1,2,3):
            for punctures in combinations(ranked,budget):
                trials+=1
                selected=set(punctures)
                todo=[e for e in edges if not e&selected]
                while todo:
                    choices=set(r for e in todo for r in e if r<1+5**L)
                    if not choices:
                        break
                    r=max(choices,key=lambda r:(sum(r in e for e in todo)*r,r))
                    selected.add(r)
                    todo=[e for e in todo if r not in e]
                if todo:
                    continue
                for r in sorted(selected):
                    if r not in punctures and all(e&(selected-{r}) for e in edges):
                        selected.remove(r)
                delta=Fraction(1,a)-sum((Fraction(1,r) for r in selected),Fraction())
                if best is None or delta>best[0]:
                    best=(delta,set(punctures),selected-set(punctures))
        row={'a':str(a),'trials':str(trials),'tail_pool_size':str(len(tail)),'searched_tail_pool':list(map(str,ranked))}
        if best:
            delta,punctures,removed=best
            row.update(delta={'num':str(delta.numerator),'den':str(delta.denominator)},
                       punctures=list(map(str,sorted(punctures))),removed=list(map(str,sorted(removed))))
        records.append(row)
    return {'status':'unresolved','L':str(L),'records':records,
            'scope':'singleton A(L), ranked finite tail pool, greedy head repair; no global null claim'}


def z125_search(max_nodes=2000):
    """Node-bounded exact cardinality B&B; incomplete output gives only bounds."""
    edges=cyclic_edges(125)
    masks=[sum(1<<r for r in e) for e in edges]
    incidence=[[mask for mask in masks if mask>>r&1] for r in range(125)]
    digits=[r for r in range(125) if padded_member(r,[0,1,2,3])]
    best=sum(1<<r for r in digits)
    prior=ROOT/'benchmarks/cyclic125_search.json'
    if prior.exists():
        candidate=sum(1<<int(r) for r in json.loads(prior.read_text())['digits'])
        if candidate.bit_count()>best.bit_count() and not any(candidate&e==e for e in masks):
            best=candidate
    nodes=0
    complete=True
    frontier=[]
    def visit(selected,undecided):
        nonlocal best,nodes,complete
        if nodes>=max_nodes:
            complete=False
            frontier.append({"selected_mask":str(selected),"undecided_mask":str(undecided)})
            return
        nodes+=1
        if selected.bit_count()+undecided.bit_count()<=best.bit_count():
            return
        if not undecided:
            if selected.bit_count()>best.bit_count():
                best=selected
            return
        bit=undecided&-undecided
        rest=undecided^bit
        r=bit.bit_length()-1
        candidate=selected|bit
        if not any(candidate&e==e for e in incidence[r]):
            # Unit propagation: completing the other four forbids the last point.
            forced=0
            for e in incidence[r]:
                missing=e&~candidate
                if missing.bit_count()==1:
                    forced|=missing
            visit(candidate,rest&~forced)
        visit(selected,rest)
    # Translation invariance permits requiring zero for cardinality alone.
    visit(1,((1<<125)-1)^1)
    return {'unexplored_branches':frontier,'distinct_progressions':str(len(edges)),'status':'complete' if complete else 'unresolved',
            'nodes':str(nodes),'node_limit':str(max_nodes),'cardinality_lower_bound':str(best.bit_count()),
            'digits':list(map(str,[r for r in range(125) if best>>r&1])),
            'cardinality_upper_bound':str(best.bit_count()) if complete else '100',
            'upper_bound_reason':'25 disjoint cosets of order 5 each omit at least one residue',
            'scope':'finite cyclic cardinality only; no infinite reciprocal-sum claim'}


def campaign_report():
    """Reproduce the bounded supporting computations without touching certificates."""
    reflection={}
    statistics=[]
    for L in (6,7,8,9):
        values=build_tail_automaton(L)
        present=set(values)
        reflection[str(L)]=all(3*(5**L-1)//4+2-a in present for a in values)
        if L<=8:
            result=solve_dual(L)
            statistics.append({'L':str(L),'candidates':str(len(values)),
                               'arcs':str(len(result['dual_arcs'])),
                               'search_status':result['status']})
    return {'unpunctured_status':'see separately verified c3_rigidity_L6_L7_L8 certificates',
            'a6_subsets':bnb(6),
            'singleton_costs':[singleton_cost(a,6) for a in build_tail_automaton(6)],
            'dual_statistics':statistics,'puncture_pool':puncture_pool(6),
            'punctures':puncture_bound(6),'z125':z125_search(),'reflection':reflection}


if __name__ == '__main__':
    if sys.argv[1:]==['--report']:
        report=campaign_report()
        (ROOT/'benchmarks/campaign3_f5_decisive.json').write_text(json.dumps(report,indent=2)+'\n')
        (ROOT/'benchmarks/c3_A6_exact_subsets.json').write_text(json.dumps(report['a6_subsets'],indent=2)+'\n')
        print('Local report regenerated; puncture and Z125 verdicts remain explicit.')
    else:
        print(json.dumps(solve_dual(int(sys.argv[1]) if len(sys.argv)>1 else 6),indent=2))
