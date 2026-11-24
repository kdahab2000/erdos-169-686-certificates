import copy
import json
import unittest
from fractions import Fraction
from pathlib import Path
from solvers.quantized_block import produce,Q
from verifiers import standalone_verify as st,v169 as lab

class QuantizedTests(unittest.TestCase):
    def test_oracle_and_parity(self):
        for depth in range(1,6):
            c=produce(depth=depth)
            values=[0]
            for _ in range(depth): values=[5*x+d for x in values for d in range(4)]
            head=sum((Fraction(1,1+x) for x in values),Fraction())
            lower=head+sum((Fraction(20,5*x+4) for x in values if x>=5**(depth-1)),Fraction())
            upper=head+sum((Fraction(4,x) for x in values if x>=5**(depth-1)),Fraction())
            self.assertLessEqual(Fraction(int(c['lb_num']),Q),lower)
            self.assertGreaterEqual(Fraction(int(c['ub_num']),Q),upper)
            self.assertEqual(st.verify_certificate(c),lab.verify_certificate(c))
            legacy=json.loads(Path(f'certificates/c2_pure5_depth{depth}.json').read_text())
            self.assertLessEqual(Fraction(int(c['lb_num']),Q),Fraction(**{'numerator':int(legacy['ub']['num']),'denominator':int(legacy['ub']['den'])}))
            self.assertGreaterEqual(Fraction(int(c['ub_num']),Q),Fraction(int(legacy['lb']['num']),int(legacy['lb']['den'])))
    def test_depth6_bridge(self):
        c=json.loads(Path('certificates/c4_pure5_q_depth6.json').read_text())
        old=json.loads(Path('certificates/c2_pure5_depth5.json').read_text())
        self.assertLessEqual(Fraction(int(c['lb_num']),Q),Fraction(int(old['ub']['num']),int(old['ub']['den'])))
        self.assertGreaterEqual(Fraction(int(c['ub_num']),Q),Fraction(int(old['lb']['num']),int(old['lb']['den'])))

    def test_tamper_caps_and_width(self):
        c=json.loads(Path('certificates/c4_pure5_q_depth10.json').read_text())
        self.assertLess(int(c['ub_num'])-int(c['lb_num']),2*10**53)
        for key in ('lb_num','ub_num'):
            for delta in (-1,1):
                bad=copy.deepcopy(c);bad[key]=str(int(bad[key])+delta)
                with self.assertRaises(st.BadCertificate): st.verify_certificate(bad)
                with self.assertRaises(ValueError): lab.verify_certificate(bad)
        for key,value in [('depth','20'),('Q','9'),('B','129')]:
            bad=copy.deepcopy(c);bad[key]=value
            with self.assertRaises(st.BadCertificate): st.verify_certificate(bad)
