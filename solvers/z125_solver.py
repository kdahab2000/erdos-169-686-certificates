"""Bounded cyclic search; incomplete trees are never certificates."""
import time
from verifiers.v169 import cyclic_progressions

def z25(max_seconds=15,max_nodes=1000000):
    edges=cyclic_progressions(25)
    masks=[(sum(1<<v for v in edge),pair) for edge,pair in edges.items()]
    full=(1<<25)-1
    nodes=[]; start=time.monotonic()
    def visit(selected,excluded):
        if len(nodes)>=max_nodes or time.monotonic()-start>max_seconds:
            raise TimeoutError('cyclic search budget')
        for mask,pair in masks:
            if selected&mask==mask:
                nodes.append({'op':'conflict','ap':list(map(str,pair))})
                return
        undecided=full^(selected|excluded)
        active=[((mask&undecided).bit_count(),mask&undecided,pair) for mask,pair in masks if not mask&excluded]
        active.sort()
        occupied=0; packing=[]
        for count,mask,pair in active:
            full_edge=sum(1<<((pair[0]+j*pair[1])%25) for j in range(5))
            if mask and not full_edge&occupied:
                occupied|=full_edge; packing.append(list(map(str,pair)))
        if selected.bit_count()+undecided.bit_count()-len(packing)<=16:
            nodes.append({'op':'prune','aps':packing}); return
        counts={j:sum(bool(mask>>j&1) for _,mask,_ in active) for j in range(25) if undecided>>j&1}
        j=max(counts,key=lambda j:(counts[j],-j))
        nodes.append({'op':'branch','j':str(j)})
        visit(selected|1<<j,excluded)
        visit(selected,excluded|1<<j)
    try: visit(0,0)
    except TimeoutError:
        return {'status':'unresolved','claim':'none','nodes':str(len(nodes)),'checkpoint':{'max_seconds':str(max_seconds),'max_nodes':str(max_nodes),'restart':'deterministic full tree; no incomplete proof emitted'}}
    return {'status':'complete','certificate':{'schema':'erd169.cyclic_max.v1','modulus':'25','p':'5','max_cardinality':'16','witness':[str(a+5*b) for b in range(4) for a in range(4)],'mode':'direct_bnb','proof':nodes}}


def z125(max_nodes=20000):
    # Existing deterministic search is bounded; cardinality only.
    from solvers.f5_decisive import z125_search
    from pathlib import Path
    from verifiers.standalone_verify import load_strict,verify_cyclic_max
    verify_cyclic_max(load_strict(Path('certificates/c4_z25_max.json')))
    result=z125_search(max_nodes=max_nodes)
    result['claim']='none'
    result['cardinality_upper_bound']='80'
    result['upper_bound_requires']='replayed c4_z25_max.json; five disjoint Z25 fibres'
    result['checkpoint']={'restart_nodes':str(max_nodes),'unexplored_branches':'see top-level unexplored_branches masks; translation fixes zero, no fibre orbit pruning yet'}
    return result


def h0_orbit_probe(max_seconds=12):
    """Enumerate dense Z25 fibres and affine orbits, with explicit frontier.

    At threshold 65 some fibre has at least 13 points. Translation places it
    in H0; its affine orbit may be normalized for cardinality search only.
    A bounded probe cannot produce a maximum theorem.
    """
    from math import gcd
    edges=cyclic_progressions(25)
    masks=[sum(1<<x for x in edge) for edge in edges]
    incidence=[[e for e in masks if e>>j&1] for j in range(25)]
    units=[a for a in range(25) if gcd(a,25)==1]
    orbit_seen=set(); representatives=[]; frontier=[]
    nodes=0; start=time.monotonic()
    def visit(selected,todo):
        nonlocal nodes
        if time.monotonic()-start>max_seconds:
            frontier.append({'selected_mask':str(selected),'undecided_mask':str(todo)})
            return
        nodes+=1
        if selected.bit_count()+todo.bit_count()<13:return
        if not todo:
            if selected in orbit_seen:return
            members=[j for j in range(25) if selected>>j&1]
            orbit={sum(1<<((a*j+c)%25) for j in members) for a in units for c in range(25)}
            orbit_seen.update(orbit)
            representative=min(orbit)
            representatives.append(str(representative))
            return
        bit=todo&-todo;j=bit.bit_length()-1;rest=todo^bit
        chosen=selected|bit
        if not any(e&chosen==e for e in incidence[j]):
            forced=0
            for e in incidence[j]:
                missing=e&~chosen
                if missing.bit_count()==1:forced|=missing
            visit(chosen,rest&~forced)
        visit(selected,rest)
    visit(0,(1<<25)-1)
    return {'claim':'none','status':'unresolved','threshold':'65','upper_bound':'80',
            'nodes':str(nodes),'enumeration_complete':not frontier,
            'h0_representative_masks':representatives,'fibre_frontier':frontier,
            'residual_frontier':[{'selected_mask':str(sum(1<<(5*j) for j in range(25) if int(rep)>>j&1)),
                                  'excluded_mask':str(sum(1<<(5*j) for j in range(25) if not int(rep)>>j&1))} for rep in representatives],
            'checkpoint':'Finish fibre frontier then residual H0 trees with exact exclusions; no maximum certificate emitted.'}


def residual_probe(fibres,max_seconds=12,checkpoint=None):
    """Threshold-65 H0 trees with fibre/coset caps and restartable masks."""
    from solvers.head_tail import cyclic_edges
    edges=[sum(1<<x for x in e) for e in cyclic_edges(125)]
    incidence=[[e for e in edges if e>>j&1] for j in range(125)]
    full=(1<<125)-1
    cosets=[sum(1<<(a+25*j) for j in range(5)) for a in range(25)]
    fibres125=[sum(1<<(a+5*j) for j in range(25)) for a in range(5)]
    if checkpoint is None:
        stack=[(int(r['selected_mask']),full^(int(r['selected_mask'])|int(r['excluded_mask']))) for r in fibres['residual_frontier']]
    else:
        stack=[(int(r['selected_mask']),int(r['undecided_mask'])) for r in checkpoint['unexplored_branches']]
    nodes=0;start=time.monotonic();found=None
    while stack and time.monotonic()-start<max_seconds:
        selected,todo=stack.pop();nodes+=1
        if selected.bit_count()>=65:
            found=[str(j) for j in range(125) if selected>>j&1];break
        if selected.bit_count()+todo.bit_count()<65:continue
        def bound(parts,cap):
            return selected.bit_count()+sum(min((todo&part).bit_count(),cap-(selected&part).bit_count()) for part in parts)
        if bound(cosets,4)<65 or bound(fibres125,16)<65:continue
        forced=0;conflict=False
        for part,cap in [(p,4) for p in cosets]+[(p,16) for p in fibres125]:
            count=(selected&part).bit_count()
            if count>cap:conflict=True;break
            if count==cap:forced|=todo&part
        if conflict:continue
        todo &= ~forced
        if not todo:continue
        bit=todo&-todo;j=bit.bit_length()-1;rest=todo^bit
        stack.append((selected,rest))
        chosen=selected|bit
        if any(e&chosen==e for e in incidence[j]):continue
        forced=0
        for e in incidence[j]:
            missing=e&~chosen
            if missing.bit_count()==1:forced|=missing
        stack.append((chosen,rest&~forced))
    return {'claim':'none','status':'unresolved' if stack or not fibres['enumeration_complete'] else 'computed, uncertified',
            'nodes':str(nodes),'seconds':str(time.monotonic()-start),'threshold':'65','upper_bound':'80','found_digits':found,
            'unexplored_branches':[{'selected_mask':str(s),'undecided_mask':str(u)} for s,u in stack],
            'checkpoint':'Resume these residual masks plus fibre_frontier; a closed search still requires a replayable h0_orbit_bnb proof.'}


def prove_orbits(max_seconds=40, orbit_seconds=3, max_nodes=1000000):
    """Measure v2 before full production; persist complete orbits only.

    Failed measurements never emit a certificate. The checkpoint is local
    producer state, excluded from manifests, and is not a mathematical proof.
    """
    import hashlib
    import json
    from pathlib import Path
    from verifiers.common import canonical_json_bytes
    from verifiers import standalone_verify as st
    start=time.monotonic()
    # Reuse the complete C4 representative list, checked against the census
    # when a completed certificate is replayed; no coverage claim on timeout.
    source=json.loads(Path('benchmarks/c4_h0_orbits.json').read_text())
    if not source['enumeration_complete']:raise ValueError('incomplete C4 census')
    reps=sorted(map(int,source['h0_representative_masks']),key=lambda m:(-m.bit_count(),m))
    masks=[(sum(1<<x for x in e),list(map(str,p))) for e,p in cyclic_progressions(125).items()]
    full=(1<<125)-1
    fibres=[sum(1<<(a+5*j) for j in range(25)) for a in range(5)]
    cosets=[sum(1<<(a+25*j) for j in range(5)) for a in range(25)]
    setup=time.monotonic()-start
    progress_path=Path('benchmarks/c5_z125_progress.json')
    progress={'schema':'local.c5.orbit_checkpoint.v1','claim':'none','orbits':[]}
    if progress_path.exists():progress=json.loads(progress_path.read_text())
    completed={int(o['mask']):o for o in progress['orbits']}
    measurements=[];total_nodes=0
    def run(mask):
        nodes=[];began=time.monotonic(); cap=mask.bit_count()
        def visit(sel,exc):
            if len(nodes)+total_nodes>=max_nodes or time.monotonic()-began>orbit_seconds or time.monotonic()-start>max_seconds:
                raise TimeoutError('v2 measurement budget')
            und=full^(sel|exc)
            for bound,parts,limit in [('dominance',fibres,cap),('coset',cosets,4),('fibre',fibres,16)]:
                counts=[(sel&p).bit_count() for p in parts]
                upper=0 if any(n>limit for n in counts) else sel.bit_count()+sum(min((und&p).bit_count(),limit-n) for p,n in zip(parts,counts))
                if upper<=64:
                    nodes.append({'op':'prune','bound':bound});return
            active=[]
            for edge,pair in masks:
                if edge&exc:continue
                todo=edge&und
                if not todo:
                    nodes.append({'op':'conflict','ap':pair});return
                if todo.bit_count()==1:
                    j=todo.bit_length()-1
                    nodes.append({'op':'force','j':str(j),'ap':pair})
                    visit(sel,exc|todo);return
                active.append((todo.bit_count(),todo,pair))
            occupied=0;packing=[]
            for _,todo,pair in sorted(active):
                if not todo&occupied:
                    occupied|=todo;packing.append(pair)
            if sel.bit_count()+und.bit_count()-len(packing)<=64:
                nodes.append({'op':'prune','bound':'packing','aps':packing});return
            if sel.bit_count()>=65:
                raise ValueError('larger witness: '+str([j for j in range(125) if sel>>j&1]))
            counts={j:0 for j in range(125) if und>>j&1}
            for count,todo,_ in active:
                if count==2:
                    # Two-open constraints crossing fibres take priority.
                    js=[j for j in counts if todo>>j&1]
                    cross=len({j%5 for j in js})>1
                    for j in js:counts[j]+=2 if cross else 1
            j=max(counts,key=lambda j:(counts[j],-(cap-(sel&fibres[j%5]).bit_count()),-j))
            nodes.append({'op':'branch','j':str(j)})
            visit(sel|1<<j,exc);visit(sel,exc|1<<j)
        sel=sum(1<<(5*j) for j in range(25) if mask>>j&1)
        try:
            visit(sel,fibres[0]^sel);status='complete'
        except TimeoutError:
            status='budget exceeded'
        return nodes,status,time.monotonic()-began
    # Required sample order: all 16/15-point fibres, then 20 per 14/13 group.
    sample=[m for m in reps if m.bit_count()>=15]
    for size in (14,13):sample += [m for m in reps if m.bit_count()==size][:20]
    status='measurement incomplete'
    for mask in sample:
        if mask in completed:continue
        nodes,outcome,elapsed=run(mask)
        measurements.append({'mask':str(mask),'fibre_size':mask.bit_count(),'nodes':len(nodes),'bytes':len(canonical_json_bytes(nodes)),'seconds':str(elapsed),'status':outcome})
        if outcome!='complete':break
        total_nodes+=len(nodes)
        completed[mask]={'mask':str(mask),'fibre':[str(j) for j in range(25) if mask>>j&1],'tree':nodes}
        progress['orbits']=list(completed.values());progress_path.write_text(json.dumps(progress)+'\n')
    else:
        status='sample complete; projection and cold replay gate required before full run'
    result={'claim':'none','status':status,'setup_seconds':str(setup),'measurements':measurements,
            'completed_orbits':len(completed),'required_orbits':len(reps),'bounds':{'lower':64,'upper':80},
            'cold_replay_seconds':None,'projection_nodes':None,
            'continuation':'Optimize pruning/branching and finish the prescribed measurement; no maximum certificate emitted.'}
    progress['orbits']=list(completed.values())
    progress_path.write_text(json.dumps(progress)+'\n')
    Path('benchmarks/c5_z125_measure.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
