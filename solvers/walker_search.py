"""Deterministic general-base digit search. No literature or novelty claims."""
from verifiers.v169 import carry_ap_free, quantized_enclosure
from solvers.quantized_block import Q,produce

def product_lift(base,digits):
    if base not in (5,25,125):
        return False
    values=[0]; power=1
    while power<base:
        values=[5*x+d for x in values for d in range(4)];power*=5
    return digits==sorted(values)


def search(ub_ref):
    rows=[]; promoted=[]
    for base in range(6,61):
        # Three deterministic greedy orders, each anchored at zero.
        orders=[list(range(1,base)),list(range(base-1,0,-1)),list(range(1,base,2))+list(range(2,base,2))]
        seen=set()
        for order in orders:
            digits=[0]
            for digit in order:
                trial=sorted(digits+[digit])
                if len(trial)<base and carry_ap_free(base,trial,5):
                    digits=trial
            if len(digits)<2 or tuple(digits) in seen or product_lift(base,digits):
                continue
            seen.add(tuple(digits))
            lb,ub=quantized_enclosure(base,digits,1,2,Q)
            row={'B':str(base),'D':list(map(str,digits)),'depth2_lb_num':str(lb),'depth2_ub_num':str(ub),'status':'pruned by UB_ref' if ub<ub_ref else 'needs deeper score'}
            if ub>=ub_ref:
                depth=2
                while depth<20 and len(digits)**(depth+1)<=1100000:
                    depth+=1
                lb,ub=quantized_enclosure(base,digits,1,depth,Q)
                row.update(depth=str(depth),lb_num=str(lb),ub_num=str(ub),status='improvement candidate' if lb>ub_ref else 'no certified improvement')
                if lb>ub_ref:
                    promoted.append(produce(base,digits,depth=depth,mode='carry_automaton',params={}))
            rows.append(row)
    rows.sort(key=lambda r:int(r['depth2_ub_num']),reverse=True)
    return {'claim':'none','scope':'three greedy digit orders per base, B=6..60; not exhaustive','bases':list(map(str,range(6,61))),'candidates':rows,'promoted_certificates':promoted}
