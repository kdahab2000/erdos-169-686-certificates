import itertools
import json
import unittest
from pathlib import Path
from verifiers.standalone_verify import carry_ap_free
from verifiers.v169 import carry_ap_free as lab

class CarryTests(unittest.TestCase):
    def test_trap(self):
        self.assertFalse(carry_ap_free(4,[0,1,2],4))
    def test_small_brute_oracle(self):
        # Finite witnesses establish rejection; independent reachable-state oracle
        # establishes acceptance, using explicit carry vectors and fixed-point sets.
        for base in range(2,11):
            for digits in ([0,1],list(range(min(base-1,4)))):
                if len(digits)<2 or len(digits)>=base: continue
                accepted=carry_ap_free(base,digits,5)
                self.assertEqual(accepted,lab(base,digits,5))
                members=[x for x in range(base**3) if all((x//base**i)%base in digits for i in range(3))]
                present=set(members)
                brute=not any(all(a+j*d in present for j in range(5)) for a in members for d in range(1,(base**3-1-a)//4+1))
                if accepted: self.assertTrue(brute)
                # Reverse implication only claimed within this finite oracle family.
                self.assertEqual(accepted,brute)
    def test_existing_cyclic_certificates(self):
        for path in Path('certificates').glob('*.json'):
            cert=json.loads(path.read_text())
            if cert.get('schema')=='erd169.block_digit.v1':
                self.assertTrue(carry_ap_free(int(cert['p'])**int(cert['block_len']),list(map(int,cert['D'])),int(cert['k'])),path.name)
