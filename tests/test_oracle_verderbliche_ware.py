"""Orakel-Tests: der Kern (`vdw_algorithm`, Vektoroperationen auf Zustandsvektoren) gegen unabhängige Rechenwege.

  O1  Handbeispiel in exakten Brüchen (`vdw_hand`, ohne numpy) gegen den Kern                       -> tests/test_algorithm.py
  O2  Einheiten-Referenz: Listen einzelner Stücke mit Alter statt Vektoroperationen. Übergänge und Kosten des Kerns gegen die Referenz auf
      allen Zuständen x Bestellmengen x Nachfragen (Lieferzeit 0 und 1, beide Regeln, Haltbarkeit 2 und 3)
  O2b sparse Lösung des Kerns gegen dichte Lösung der Referenz (Wörterbuch-Aufzählung) für zufällige Politiken
  O3  Aufzählung aller Politiken winziger Instanzen gegen die DP (und alle Tabellen nach Gesamtbestand)
  O4  Simulation auf Einheitenebene gegen die exakte Auswertung (vier Zufalls-Seeds)
  O5  Howard-Politikiteration gegen relative Wertiteration
  O6  FIFO = LIFO bei höchstens einer belegten Klasse, sonst Abweichung auf mindestens einer Instanz (Zweig-Test); Newsvendor-Identität bei w = h
  O7  Referenz ohne Verfall (verlorene Nachfrage, Lieferzeit 1, eigene kleine DP)
  O8  Ablaufmenge unter Base-Stock: FIFO höchstens LIFO; Abbruchregel der Base-Stock-Suche gegen volle Suche
Die Referenzen rechnen auf einem anderen Weg als der Kern; die Handbeispiel-Werte stehen in test_algorithm.py."""

import itertools
from math import exp, factorial

import numpy as np
import pytest
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import vdw_algorithm as A
from conftest import hand_settings


# ------------------------------------------------------------------------------------------------------------------------------ Referenz
def ref_step(state, a, d, cfg):
    """Einheitenebene: `state` = Zählung je Klasse (älteste zuerst). Rückgabe (nächster Zustand, Kosten)."""
    units = []
    for i, c in enumerate(state):
        units += [i + 1] * c                                   # Restlebensdauer i + 1
    if cfg.lead == 0:
        units += [cfg.m] * a
    units.sort()                                               # älteste zuerst
    left = units[d:] if cfg.rule == "FIFO" else units[: max(len(units) - d, 0)]
    lost = max(d - len(units), 0)
    waste = sum(1 for u in left if u == 1)
    carry = [u - 1 for u in left if u > 1]
    nxt = [0] * len(state)
    for v in carry:
        nxt[v - 1] += 1
    if cfg.lead == 1:
        nxt[cfg.m - 1] += a
    return tuple(nxt), cfg.h * len(carry) + cfg.p * lost + cfg.w * waste


def ref_amax(state, cfg):
    tot = sum(state)
    return cfg.T - tot if cfg.lead == 0 else cfg.T - (tot - state[0])


def ref_evaluate(cfg, polfun, pd):
    """Kosten der Politik: Zustände von leer per Wörterbuch aufzählen, dichte Lösung des linearen Systems."""
    start = tuple([0] * cfg.k)
    idx, order, trans, i = {start: 0}, [start], {}, 0
    while i < len(order):
        s = order[i]
        a = min(polfun(s), ref_amax(s, cfg))
        row, ec = {}, 0.0
        for d, pr in enumerate(pd):
            nx, co = ref_step(s, a, d, cfg)
            if nx not in idx:
                idx[nx] = len(order)
                order.append(nx)
            row[idx[nx]] = row.get(idx[nx], 0.0) + pr
            ec += pr * co
        trans[i] = (row, ec)
        i += 1
    n = len(order)
    Pm, c = np.zeros((n, n)), np.zeros(n)
    for i, (row, ec) in trans.items():
        for j, pr in row.items():
            Pm[i, j] += pr
        c[i] = ec
    M = (np.eye(n) - Pm).T
    M[-1, :] = 1.0
    rhs = np.zeros(n)
    rhs[-1] = 1.0
    return float(np.linalg.solve(M, rhs) @ c)


def simulate(cfg, polfun, pd, n, seed, burn=500, blocks=10):
    rng = np.random.default_rng(seed)
    dem = rng.choice(len(pd), size=n + burn, p=pd)
    state = tuple([0] * cfg.k)
    costs = np.empty(n)
    for t in range(n + burn):
        a = min(polfun(state), ref_amax(state, cfg))
        state, co = ref_step(state, a, int(dem[t]), cfg)
        if t >= burn:
            costs[t - burn] = co
    b = costs.reshape(blocks, -1).mean(axis=1)
    return float(b.mean()), float(b.std(ddof=1) / np.sqrt(blocks))


# ------------------------------------------------------------------------------------------------------------------------------ O2
@pytest.mark.parametrize("lead", [0, 1])
@pytest.mark.parametrize("rule", ["FIFO", "LIFO"])
@pytest.mark.parametrize("m", [2, 3])
def test_o2_core_transitions_and_costs_equal_the_unit_reference(lead, rule, m):
    cfg = A.Settings(m=m, lead=lead, rule=rule, w=3.0, T=4, dmax=6)
    P = A.Perishable(cfg)
    states = [tuple(int(x) for x in z) for z in P.Z]
    index = {s: i for i, s in enumerate(states)}
    worst_p = worst_c = 0.0
    for a in range(P.A):
        Pa = P.P[a].tocsr()
        for si, s in enumerate(states):
            ae = min(a, ref_amax(s, cfg))
            row, ec = np.zeros(P.S), 0.0
            for d, pr in zip(P.d, P.pd):
                nx, co = ref_step(s, ae, int(d), cfg)
                row[index[nx]] += pr
                ec += pr * co
            worst_p = max(worst_p, float(np.abs(Pa[si].toarray().ravel() - row).max()))
            worst_c = max(worst_c, abs(P.cost[si, a] - ec))
    assert worst_p < 1e-12 and worst_c < 1e-12


def test_o2b_sparse_solution_equals_dense_reference_for_random_policies():
    rng = np.random.default_rng(7)
    for lead, rule in itertools.product((0, 1), ("FIFO", "LIFO")):
        cfg = A.Settings(m=3, lead=lead, rule=rule, w=3.0, T=6, dmax=9)
        P = A.Perishable(cfg)
        table = {tuple(int(x) for x in z): i for i, z in enumerate(P.Z)}
        for _ in range(2):
            pol = np.clip(P.base_stock(4) + rng.integers(-1, 2, size=P.S), 0, np.maximum(P.amax, 0)).astype(int)
            g1 = P.evaluate(pol)[0]
            g2 = ref_evaluate(cfg, lambda s: int(pol[table[s]]), P.pd)
            assert abs(g1 - g2) < 1e-9


# ------------------------------------------------------------------------------------------------------------------------------ O3
@pytest.mark.parametrize("m,lead,T", [(2, 0, 3), (2, 1, 2), (3, 0, 3)])
@pytest.mark.parametrize("rule", ["FIFO", "LIFO"])
def test_o3_enumerating_all_policies_gives_the_dp_value(m, lead, T, rule):
    P = A.Perishable(hand_settings(rule, m=m, lead=lead, T=T))
    g = P.solve()[0]
    ranges = [range(int(a) + 1) for a in P.amax]
    assert np.prod([len(r) for r in ranges], dtype=float) <= 5000
    best = min(P.evaluate(np.array(c))[0] for c in itertools.product(*ranges))
    assert best == pytest.approx(g, abs=1e-8)
    # alle Tabellen nach Gesamtbestand sind höchstens so gut wie die DP
    tots = sorted({int(t) for t in P.tot})
    best_tab = min(P.evaluate(np.array([dict(zip(tots, tab))[int(t)] for t in P.tot]))[0] for tab in itertools.product(range(T + 1), repeat=len(tots)))
    assert best_tab >= g - 1e-9


def test_o3_one_class_instance_the_total_table_is_enough():
    """Haltbarkeit 2, Lieferzeit 0: der Zustand ist der Gesamtbestand selbst, die Tabelle nach Gesamtbestand ist die ganze Politik."""
    P = A.Perishable(hand_settings("LIFO", T=3))
    tots = sorted({int(t) for t in P.tot})
    best = min(P.evaluate(np.array([dict(zip(tots, tab))[int(t)] for t in P.tot]))[0] for tab in itertools.product(range(4), repeat=len(tots)))
    assert best == pytest.approx(P.solve()[0], abs=1e-8)


# ------------------------------------------------------------------------------------------------------------------------------ O4
@pytest.mark.parametrize("lead,rule", [(0, "LIFO"), (1, "FIFO")])
def test_o4_simulation_agrees_with_the_exact_evaluation(lead, rule):
    cfg = A.Settings(m=3, lead=lead, rule=rule, w=10.0, T=10, dmax=14)
    P = A.Perishable(cfg)
    gbs, level, _ = P.best_base_stock()
    pol = P.base_stock(level)
    table = {tuple(int(x) for x in z): i for i, z in enumerate(P.Z)}
    z = []
    for seed in range(4):
        mean, se = simulate(cfg, lambda s: int(pol[table[s]]), P.pd, 20000, seed)
        z.append((mean - gbs) / se)
    assert all(abs(v) < 4.0 for v in z), z
    assert abs(float(np.mean(z))) < 2.5


# ------------------------------------------------------------------------------------------------------------------------------ O5
def policy_iteration(P, pol0, maxit=50):
    n = P.S
    pol = pol0.copy()
    for _ in range(maxit):
        Pp, cp = P.chain(pol)
        idx = [s for s in range(n) if s != P.empty]
        M = sp.hstack([sp.csr_matrix(np.ones((n, 1))), (sp.identity(n, format="csr") - Pp).tocsr()[:, idx]], format="csc")
        sol = spla.spsolve(M, cp)
        h = np.zeros(n)
        h[idx] = sol[1:]
        Q = P.qvalues(h)
        best = Q.argmin(axis=1)
        better = Q[np.arange(n), best] < Q[np.arange(n), pol] - 1e-9
        if not better.any():
            return float(sol[0]), pol
        pol = np.where(better, best, pol)
    raise AssertionError("keine Konvergenz")


@pytest.mark.parametrize("lead,rule,m,w", [(1, "LIFO", 3, 3.0), (0, "LIFO", 4, 10.0)])
def test_o5_howard_policy_iteration_equals_value_iteration(lead, rule, m, w):
    P = A.Perishable(A.Settings(m=m, lead=lead, rule=rule, w=w, T=8, dmax=12))
    g, *_ = P.solve()
    gp, _ = policy_iteration(P, P.base_stock(P.best_base_stock()[1]))
    assert gp == pytest.approx(g, abs=1e-7)


# ------------------------------------------------------------------------------------------------------------------------------ O6
@pytest.mark.parametrize("lead", [0, 1])
@pytest.mark.parametrize("m", [2, 3])
def test_o6_rules_branch_differ_somewhere_and_agree_with_at_most_one_class(lead, m):
    Pf = A.Perishable(A.Settings(m=m, lead=lead, rule="FIFO", T=5, dmax=8))
    Pl = A.Perishable(A.Settings(m=m, lead=lead, rule="LIFO", T=5, dmax=8))
    nonempty = (Pf.Z > 0).sum(axis=1)
    differ_rows = same_but_one = bad = 0
    for a in range(Pf.A):
        dP = np.asarray(abs(Pf.P[a] - Pl.P[a]).sum(axis=1)).ravel()
        dc = np.abs(Pf.cost[:, a] - Pl.cost[:, a])
        differ = (dP > 1e-12) | (dc > 1e-12)
        classes = nonempty + ((np.minimum(a, Pf.amax) > 0) if lead == 0 else 0)
        one = classes <= 1
        bad += int((differ & one).sum())
        differ_rows += int(differ.sum())
    assert differ_rows > 0, "toter Zweig: FIFO und LIFO unterscheiden sich nirgends"
    assert bad == 0


@pytest.mark.parametrize("m", [2, 3, 4])
def test_o6c_with_w_equal_h_lead_zero_every_rule_costs_the_newsvendor_value(m):
    """Bei w = h und Lieferzeit 0 hängt die Periodenkosten nur vom Bestand y nach der Bestellung ab: Auffüllen auf das Newsvendor-Niveau S = 5
    (kritisches Verhältnis 0,9, Poisson 3) kostet E[h (S-d)+ + p (d-S)+] bei jeder Haltbarkeit und jeder Ausgaberegel."""
    from vdw_algorithm import poisson_pmf
    pd = poisson_pmf(3.0, 16)
    newsvendor = sum(pr * (max(5 - d, 0) + 9 * max(d - 5, 0)) for d, pr in enumerate(pd))
    for rule in ("FIFO", "LIFO"):
        g = A.Perishable(A.Settings(m=m, lead=0, rule=rule, w=1.0, T=12, dmax=16)).solve()[0]
        assert g == pytest.approx(newsvendor, abs=1e-7)


# ------------------------------------------------------------------------------------------------------------------------------ O7
def lost_sales_lead1_without_spoilage(mean=3.0, h=1.0, p=9.0, T=12, dmax=16):
    """Eigene kleine DP ohne Verfall: Zustand = Bestand x, Nachfrage, danach kommt die Bestellung (Lieferzeit 1, verlorene Nachfrage)."""
    pmf = [exp(-mean) * mean**k / factorial(k) for k in range(dmax + 1)]
    pmf[-1] += 1.0 - sum(pmf)
    S = T + 1
    x = np.arange(S)

    def matrices(lazy):
        Pl, cost = [], np.zeros((S, T + 1))
        for a in range(T + 1):
            M = np.zeros((S, S))
            for d, pr in enumerate(pmf):
                ae = np.minimum(a, T - x)
                M[x, np.maximum(x - d, 0) + ae] += pr
                cost[:, a] += pr * (h * np.maximum(x - d, 0) + p * np.maximum(d - x, 0))
            Pl.append(lazy * M + (1 - lazy) * np.eye(S))
        return Pl, lazy * cost

    Pl, cost = matrices(0.5)
    hv = np.zeros(S)
    for _ in range(5000):
        v = np.min([cost[:, a] + Pl[a] @ hv for a in range(T + 1)], axis=0)
        d = v - hv
        hv = v - v[0]
        if d.max() - d.min() < 1e-12:
            break
    g = 0.5 * (d.max() + d.min()) / 0.5
    P1, c1 = matrices(1.0)
    best = np.inf
    for level in range(T + 1):
        pol = np.clip(level - x, 0, T - x)
        Pp = np.array([P1[pol[s]][s] for s in range(S)])
        cp = np.array([c1[s, pol[s]] for s in range(S)])
        M = (np.eye(S) - Pp).T
        M[-1, :] = 1.0
        rhs = np.zeros(S)
        rhs[-1] = 1.0
        best = min(best, float(np.linalg.solve(M, rhs) @ cp))
    return g, best


def test_o7_reference_without_spoilage_lead_one_gap_is_about_1_75_percent():
    g, best = lost_sales_lead1_without_spoilage()
    assert 100 * (best / g - 1) == pytest.approx(1.75, abs=0.005)


# ------------------------------------------------------------------------------------------------------------------------------ O8
@pytest.mark.parametrize("m", [2, 3, 4])
def test_o8_expected_waste_under_base_stock_is_smaller_with_fifo(m):
    waste = {}
    for rule in ("FIFO", "LIFO"):
        P = A.Perishable(A.Settings(m=m, lead=0, rule=rule, w=1.0, T=12, dmax=16))
        waste[rule] = P.components(P.base_stock(5))["waste"]
    assert waste["FIFO"] < waste["LIFO"]


def test_o8_early_stopping_of_the_base_stock_search_equals_the_full_search():
    for lead, rule, m, w in ((0, "LIFO", 3, 10.0), (0, "FIFO", 3, 30.0), (1, "LIFO", 2, 3.0), (1, "FIFO", 3, 3.0)):
        P = A.Perishable(A.Settings(m=m, lead=lead, rule=rule, w=w, T=12, dmax=16))
        g_stop, level, _ = P.best_base_stock()
        g_all = min(P.evaluate(P.base_stock(s))[0] for s in range(13))
        assert g_stop == pytest.approx(g_all, abs=1e-12)

