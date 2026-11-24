import unittest
from math import comb
from verifiers import standalone_verify as st,v686

class SieveTests(unittest.TestCase):
    def test_roots(self):
        for k in (3,5,101,200):
            for n in (1,2,10,123):
                for offset in (-1,0,1):
                    value=n**k+offset
                    r=st.iroot(value,k)
                    self.assertLessEqual(r**k,value);self.assertGreater((r+1)**k,value)
    def test_cubic_oracle_and_positive(self):
        for s in (2,3,4,5,10):
            expected=[(3,n,m) for n,m in st.box_hits(s*s,3,2000)]
            self.assertEqual(list(st.cubic_sieve_hits(s,1,2000)),expected)
            self.assertEqual(list(v686.cubic_sieve_hits(s,1,2000)),expected)
        # N=9 has a hit at n=11; m is beyond this single-n box.
        c=dict(schema='erd686.sieve_null.v1',s='3',k_lo='3',k_hi='3',n_lo='11',n_hi='11',method='cubic_crt_icbrt',domain='n>=1')
        with self.assertRaisesRegex(st.BadCertificate,'emit erd686.rep.v1'):st.verify_certificate(c)
    def test_prime_power_oracle(self):
        for s in (2,5):
            actual=list(st.prime_power_sieve_hits(s,5,120,1,2000))
            expected=[(k,n,m) for k in range(5,121) for n,m in st.box_hits(s*s,k,2000)]
            self.assertEqual(actual,expected)
            self.assertEqual(list(v686.prime_power_sieve_hits(s,101,102,1,100)),[(k,n,m) for k,n,m in expected if k in (101,102) and n<=100])
    def test_contract_caps_and_no_skip(self):
        c=dict(schema='erd686.sieve_null.v1',s='2',k_lo='101',k_hi='102',n_lo='1',n_hi='100',method='prime_power_exclusion',domain='n>=1')
        self.assertEqual(st.verify_certificate(c),v686.verify_certificate(c))
        for key,value in [('interval_jumps',[]),('n_hi','100001'),('n_lo','0')]:
            bad=dict(c);bad[key]=value
            with self.assertRaises(st.BadCertificate):st.verify_certificate(bad)
