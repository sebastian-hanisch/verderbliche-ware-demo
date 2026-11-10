"""Handbeispiel in exakter Bruchrechnung (ohne numpy, ohne den Rechenkern `vdw_algorithm`).

Instanz: Haltbarkeit 2, Lieferzeit 0, Nachfrage 0 / 1 / 2 mit Wahrscheinlichkeit 1/4, 1/2, 1/4, h = 1, p = 9, w = 5, Bestand nach der
Bestellung höchstens 2. Zustand z = Zahl der Stück mit noch einer Periode Restlebensdauer („alt“) vor der Bestellung; die Bestellung a kommt
frisch an (zwei Perioden). Zulässig ist a <= 2 - z, also gibt es 3 * 2 * 1 = 6 Politiken (a(0), a(1), a(2)).
Die Instanz ist nur zum Rechnen von Hand da (Mittel 1 statt 3, Grenze 2), sie ist nicht das Vehikel der übrigen Demo.
"""

from __future__ import annotations

import itertools
from fractions import Fraction as F

PROBS = (F(1, 4), F(1, 2), F(1, 4))
H, P_LOST, W_EXPIRE, LIMIT = F(1), F(9), F(5), 2


def step(z: int, a: int, d: int, rule: str, h=H, p=P_LOST, w=W_EXPIRE):
    """Eine Periode: z alte Stück (Rest 1), a neue (Rest 2), Nachfrage d. Rückgabe: (nächster Zustand, Kosten, verkauft alt, verkauft neu)."""
    if rule == "FIFO":
        sold_old = min(z, d)
        sold_new = min(a, d - sold_old)
    else:                                   # LIFO: frische Ware zuerst
        sold_new = min(a, d)
        sold_old = min(z, d - sold_new)
    lost = d - sold_old - sold_new
    old_left, new_left = z - sold_old, a - sold_new
    cost = h * new_left + p * lost + w * old_left          # new_left wird übertragen, old_left läuft ab
    return new_left, cost, sold_old, sold_new


def stationary(P: list[list[F]], start: int = 0) -> list[F]:
    """Stationäre Verteilung der von `start` erreichbaren Zustände (Gauß-Verfahren in Brüchen)."""
    n = len(P)
    seen, todo = {start}, [start]
    while todo:
        s = todo.pop()
        for j in range(n):
            if P[s][j] > 0 and j not in seen:
                seen.add(j)
                todo.append(j)
    R = sorted(seen)
    k = len(R)
    A = [[(F(1) if i == j else F(0)) - P[R[j]][R[i]] for j in range(k)] for i in range(k)]
    A[-1] = [F(1)] * k
    b = [F(0)] * (k - 1) + [F(1)]
    for c in range(k):
        piv = next(r for r in range(c, k) if A[r][c] != 0)
        A[c], A[piv] = A[piv], A[c]
        b[c], b[piv] = b[piv], b[c]
        for r in range(k):
            if r != c and A[r][c] != 0:
                f = A[r][c] / A[c][c]
                A[r] = [x - f * y for x, y in zip(A[r], A[c])]
                b[r] -= f * b[c]
    pi = [F(0)] * n
    for i, s in enumerate(R):
        pi[s] = b[i] / A[i][i]
    return pi


def transitions(policy, rule: str, probs=PROBS, h=H, p=P_LOST, w=W_EXPIRE):
    """Übergangsmatrix P[z][z'] und erwartete Kosten je Zustand unter der Politik."""
    n = len(policy)
    P = [[F(0)] * n for _ in range(n)]
    c = [F(0)] * n
    for z in range(n):
        for d, pr in enumerate(probs):
            zn, co, _, _ = step(z, policy[z], d, rule, h, p, w)
            P[z][zn] += pr
            c[z] += pr * co
    return P, c


def evaluate(policy, rule: str, probs=PROBS, h=H, p=P_LOST, w=W_EXPIRE):
    """(Kosten je Periode, stationäre Verteilung, erwartete Kosten je Zustand) einer festen Politik, alles als Brüche."""
    P, c = transitions(policy, rule, probs, h, p, w)
    pi = stationary(P)
    return sum(pi[z] * c[z] for z in range(len(policy))), pi, c


def all_policies(rule: str, probs=PROBS, h=H, p=P_LOST, w=W_EXPIRE, limit: int = LIMIT):
    """Alle zulässigen Politiken (a(0), ..., a(limit)) mit Kosten, aufsteigend nach Kosten. Eintrag: (Kosten, Politik, Verteilung, Kosten je Zustand)."""
    out = []
    for pol in itertools.product(*[range(limit - z + 1) for z in range(limit + 1)]):
        g, pi, c = evaluate(list(pol), rule, probs, h, p, w)
        out.append((g, pol, pi, c))
    out.sort(key=lambda r: r[0])
    return out


def base_stock_policy(level: int, limit: int = LIMIT) -> tuple:
    return tuple(max(level - z, 0) for z in range(limit + 1))


def summary(rule: str, w=W_EXPIRE):
    """Optimum, bester Base-Stock und Lücke (Bruch) der Instanz unter der Ausgaberegel."""
    res = all_policies(rule, w=w)
    best = res[0]
    bs = min((r for r in res if r[1] in {base_stock_policy(s) for s in range(LIMIT + 1)}), key=lambda r: r[0])
    return {"opt_policy": best[1], "opt_cost": best[0], "bs_policy": bs[1], "bs_cost": bs[0], "gap": bs[0] / best[0] - 1, "table": res}


def dot_source(policy, rule: str, probs=PROBS) -> str:
    """Zustandsgraph (Graphviz) der Kette unter der Politik: Knoten = Zahl alter Stück, Kanten = Übergangswahrscheinlichkeit."""
    P, c = transitions(policy, rule, probs)
    lines = ["digraph G {", "  rankdir=LR;", '  node [shape=circle, fontsize=12];', '  edge [fontsize=11];']
    for z in range(len(policy)):
        lines.append(f'  z{z} [label="z = {z}\\nKosten {c[z]}"];')
    for z in range(len(policy)):
        for zn in range(len(policy)):
            if P[z][zn] > 0:
                lines.append(f'  z{z} -> z{zn} [label="{P[z][zn]}"];')
    lines.append("}")
    return "\n".join(lines)
