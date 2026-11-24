"""Exact integer producer for outward-rounded Kempner enclosures."""
from verifiers.v169 import quantized_enclosure, verify_quantized_block

Q=10**60

def produce(base=5,digits=(0,1,2,3),s=1,depth=10,k=5,mode='prime_power_cyclic',params=None):
    if not (3<=k<=6 and 2<=base<=128 and 1<=s<=10000 and 1<=depth<=20
            and 2<=len(digits)<base and len(digits)**depth<=1100000
            and list(digits)==sorted(set(digits)) and digits[0]==0 and digits[-1]<base):
        raise ValueError('producer parameter cap')
    lb,ub=quantized_enclosure(base,digits,s,depth,Q)
    cert={'schema':'erd169.quantized_block.v1','k':str(k),'B':str(base),'D':list(map(str,digits)),
          's':str(s),'depth':str(depth),'Q':str(Q),'ap_mode':mode,
          'ap_params':params if params is not None else {'p':'5','block_len':'1'},
          'lb_num':str(lb),'ub_num':str(ub)}
    verify_quantized_block(cert)
    return cert
