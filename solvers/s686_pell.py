"""Exact continued-fraction Pell units and classical k=2 witnesses."""
from math import isqrt


def pell_unit(N):
    a0 = isqrt(N)
    if a0*a0 == N or N < 2:
        raise ValueError('N must be a nonsquare >= 2')
    m, d, a = 0, 1, a0
    p0, p1, q0, q1 = 1, a, 0, 1
    while p1*p1-N*q1*q1 != 1:
        m = d*a-m
        d = (N-m*m)//d
        a = (a0+m)//d
        p0, p1 = p1, a*p1+p0
        q0, q1 = q1, a*q1+q0
    return p1, q1


def produce(lo=2, hi=1000):
    rows = []
    for N in range(lo, hi+1):
        if isqrt(N)**2 == N:
            continue
        u, v = pell_unit(N)
        U, V = 2*u*u-1, 2*u*v
        n, m = (U+V-3)//2, (U+N*V-3)//2
        if max(u,v,n,m).bit_length() > 256:
            raise ValueError('Pell coordinate exceeds 256 bits')
        rows.append(dict(zip(('N','u','v','n','m'),map(str,(N,u,v,n,m)))))
    return dict(schema='erd686.pell_batch.v1', k='2', N_min=str(lo),
                N_max=str(hi), domain='n>=1', rows=rows)
