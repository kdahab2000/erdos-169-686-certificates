# Carry automaton equivalence and the ninth term

Let x=a-1, 0<=x<5^L. Write x and a prospective positive difference d
least significant digit first. For j=1,2,3,4, the jth other term minus one
is x+j*d. Start the four carries at zero. Reading input digit u of x and
choice v of d sends carry c_j to floor((c_j+u+j*v)/5), provided the output
(c_j+u+j*v) mod 5 is in {0,1,2,3}. This is the ordinary multiplication/addition
identity, so induction on the digit position proves exact agreement with the
four integers x+j*d. The state set after each input prefix contains precisely
all carry tuples reachable by some low digits of d; taking its union loses no
constraint because all four carries remain in one tuple.

After L input digits, x has only zero digits. At these higher positions track
one bit per output, recording whether it has ever had a nonzero digit. An
accepting state is four zero carries and all four bits set. It is equivalent
to a finite difference whose four outputs belong to K_5 and are >=5^L. Such
a difference is automatically positive. Conversely every forbidden all-tail
AP supplies a path to an accepting state by reading sufficiently many digits
and then padding with zeros. All carries are bounded (0<=c_j<=j after low
transitions, and the same bound is invariant afterwards), so reachability is
an exact finite graph calculation. Repeated states need no second expansion;
we require a finite accepting path, not an infinite path.

A value is outside 1+K_5 precisely when an input digit equals 4. Enumerating
all L-digit inputs, retaining outside inputs with no accepting continuation,
therefore computes exactly A(L). The domain is a=1..5^L, including its last
value. This proves completeness without the slower per-element full scan.
The solver and each verifier implement the decision separately; stored lists
are not inputs to verification.

Local run: counts L=6,7,8 reproduce the full earlier scans (2,28,260).
At L=9 the count is 1994; all 1994 values separately pass tail_compatible,
and the set is closed under a -> 3*(5^9-1)/4+2-a. Count is even.
Enumeration and individual checks together took under one second on this run.
The manuscript gives the exact scope; no claim about f(5) follows from a count.

For edges_for, fix the position i of a and compute the other four integers
(a-1)+(j-i)*d by signed carries. Enumerating L digits of d and requiring
nonnegative final carries with allowed base-5 digits is exact. Negative
carries cannot be mistaken for finite nonnegative integers. If i>0,
start>0 implies d<5^L. If i=0 and another term is in the head, its distance
from a implies the same bound. Thus every single-addition head blocker is
enumerated, even if some of its terms lie beyond the head.

# Dual argument

For any chosen additions U and removals R making the full set AP-free, every
arc of every a in U must meet R in its head terms: all its other terms are
baseline points, and the tail is fixed. Sum each arc's nonnegative rational
weight over these mandatory hits. Candidate coverage yields sum_U 1/a;
head capacity bounds the same sum by sum_R 1/r. Hence Delta<=0 for every U,
including choices generating extra multi-addition APs. Empty U,R attain 0.
A zero stored margin proves the maximum, without claiming uniqueness.
