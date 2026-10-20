"""Resolvable range of the D15 go/no-go rule for the same-device pilot.

Wilson 95% interval on the effective number of impostor attempts:
attempts = N victims x 3 impostors x 3 ten-window segments, clustered per victim (m = 9),
n_eff = attempts / (1 + (m-1) rho). rho is ASSUMED (0.1, 0.3), not measured.
"""
from math import sqrt

def wilson(p, n, z=1.96):
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return 100 * (c - h), 100 * (c + h)

print("N attempts rho n_eff go_if_observed>= stop_if_observed<=")
for N in (10, 15, 20):
    att, m = N * 3 * 3, 9
    for rho in (0.1, 0.3):
        neff = att / (1 + (m - 1) * rho)
        go = min(p / 100 for p in range(40, 100) if wilson(p / 100, neff)[0] >= 70)
        st = max(p / 100 for p in range(10, 90) if wilson(p / 100, neff)[1] < 60)
        print(N, att, rho, round(neff, 1), go, st)
