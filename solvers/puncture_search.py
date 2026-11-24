"""Search estimates only. Infinite edited-set AP-freeness is never inferred."""
from fractions import Fraction
from solvers.f5_decisive import build_tail_automaton,edges_for,minimum_hitting_cost
from verifiers.common import fraction_object


def cylinder_loss_bounds(word,base=5,digits=(0,1,2,3),s=1):
    """MSD-prefix cylinder: root reciprocal <= loss <= B/((B-d)*root).

    At suffix length t, there are d**t words and every value >= root*B**t.
    This bounds all suffix lengths, including zero, without a finite-tail claim.
    """
    if not word or word[0]==0 or any(d not in digits for d in word):
        raise ValueError('invalid normalized cylinder')
    root=0
    for d in word: root=base*root+d
    return Fraction(1,s+root),Fraction(base,(base-len(digits))*root)


def search(level=6,cut=12):
    rows=[]
    for a in build_tail_automaton(level):
        edges=edges_for(a,level)
        # Any AP wholly below the cut survives every deep-cylinder puncture.
        protected=[e for e in edges if max(e)<1+5**cut]
        cost=minimum_hitting_cost([set(e)-{a} for e in protected],max_nodes=20000)
        rows.append({'added':str(a),'protected_APs':str(len(protected)),'head_removal_bound':cost})
    loss=cylinder_loss_bounds([1]+[0]*cut)
    return {'claim':'none','L':str(level),'L_cut':str(cut),'scope':'single additions from A(6), with exact finite hitting-cost bounds and deep MSD-cylinder mass bounds; no coupled gluing search',
            'rows':rows,'example_cylinder_loss':{'lb':fraction_object(loss[0]),'ub':fraction_object(loss[1])},
            'window_rigidity':'see c4_window_probe.json; the greedy tail-load probe is not a certificate',
            'glued_tail_gate':'not fired; no candidate estimated above UB_ref'}


def window_probe(level=6,max_seconds=12):
    """Bounded greedy dual probe with tail loads; incomplete => no theorem."""
    import time
    from verifiers.v169 import padded_member
    candidates=[a for a in range(1,2+5**level) if not padded_member(a-1,[0,1,2,3])]
    Q=10**60
    capacities={};deficits={};arcs=[];processed=0;start=time.monotonic()
    for a in candidates:
        if time.monotonic()-start>=max_seconds:break
        demand=(Q+a-1)//a
        for edge in edges_for(a,level):
            blockers=[r for r in edge if r!=a]
            weight=min([demand]+[capacities.get(r,Q//r) for r in blockers])
            if weight<=0:continue
            for r in blockers:capacities[r]=capacities.get(r,Q//r)-weight
            arcs.append({'a':str(a),'start':str(edge[0]),'diff':str(edge[1]-edge[0]),'weight':fraction_object(Fraction(weight,Q))})
            demand-=weight
            if not demand:break
        if demand:deficits[str(a)]=fraction_object(Fraction(demand,Q))
        processed+=1
    return {'claim':'none','status':'unresolved','L':str(level),'candidate_count':str(len(candidates)),
            'processed':str(processed),'deficits':deficits,'unprocessed':list(map(str,candidates[processed:])),
            'dual_arcs':arcs,'seconds':str(time.monotonic()-start),
            'scope':'greedy bounded dual probe, all baseline blockers including tail; greedy failure does not prove LP infeasibility'}
