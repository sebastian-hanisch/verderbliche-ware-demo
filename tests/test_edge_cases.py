"""Randfälle, an denen Kernroutinen erfahrungsgemäß brechen (DEMO-PLAYBOOK §12): kleinste Haltbarkeit, kleinste Grenze, nie Nachfrage,
Gleichstände, inklusive Grenzen und die Kostenkonvention bei w = 0."""

import numpy as np
import pytest

import vdw_algorithm as A
import vdw_rules as R


def test_smallest_shelf_life_has_one_age_class_at_lead_zero_and_two_at_lead_one():
    P0 = A.Perishable(A.Settings(m=2, lead=0, T=3, dmax=6))
    P1 = A.Perishable(A.Settings(m=2, lead=1, T=3, dmax=6))
    assert P0.k == 1 and P0.S == 4
    assert P1.k == 2 and P1.S == A.n_states(2, 3) == 10
    for P in (P0, P1):
        g = P.solve()[0]
        assert np.isfinite(g) and g > 0


def test_smallest_limit_t_equal_one():
    P = A.Perishable(A.Settings(m=3, lead=0, rule="LIFO", T=1, dmax=4))
    assert P.S == A.n_states(2, 1) == 3
    g, pol, _, _, cert = P.solve()
    assert cert < 1e-9 and P.amax.min() == 0 and P.amax.max() == 1
    assert P.evaluate(pol)[0] == pytest.approx(g, abs=1e-9)


def test_no_demand_at_all_costs_nothing_and_never_orders():
    for lead in (0, 1):
        for rule in ("FIFO", "LIFO"):
            P = A.Perishable(A.Settings(m=3, lead=lead, rule=rule, T=4, demand=(1.0,)))
            g, pol, _, _, _ = P.solve()
            assert g == pytest.approx(0.0, abs=1e-9)
            assert P.evaluate(P.base_stock(0))[0] == pytest.approx(0.0, abs=1e-12)


def test_cost_convention_at_w_zero_lifo_is_cheaper_than_fifo():
    """Kostenkonvention: h nur auf übertragene Stücke. Bei w = 0 kostet ablaufende Ware nichts, LIFO lässt mehr ablaufen und ist billiger."""
    for lead in (0, 1):
        g = {r: A.Perishable(A.Settings(m=3, lead=lead, rule=r, w=0.0, T=10, dmax=14)).solve()[0] for r in ("FIFO", "LIFO")}
        assert g["LIFO"] < g["FIFO"] - 1e-6


def test_fifo_and_lifo_cost_the_same_with_at_most_one_occupied_class():
    """Eine einzige belegte Klasse: die Ausgaberegel kann nichts unterscheiden (Zeilen des leeren Zustands bei Lieferzeit 1, Haltbarkeit 3)."""
    Pf = A.Perishable(A.Settings(m=3, lead=1, rule="FIFO", T=5, dmax=8))
    Pl = A.Perishable(A.Settings(m=3, lead=1, rule="LIFO", T=5, dmax=8))
    s = Pf.empty
    for a in range(Pf.A):
        assert Pf.cost[s, a] == pytest.approx(Pl.cost[s, a])
        assert abs(Pf.P[a][s] - Pl.P[a][s]).sum() < 1e-12


def test_orders_above_the_limit_are_capped_not_rejected():
    P = A.Perishable(A.Settings(m=2, lead=0, T=3, dmax=6))
    s_full = int(P.index(np.array([[3]]))[0])
    assert P.amax[s_full] == 0
    assert np.allclose(P.cost[s_full, 0], P.cost[s_full, 3]) and abs(P.P[0][s_full] - P.P[3][s_full]).sum() < 1e-12


def test_age_rule_with_beta_zero_is_the_base_stock_and_bounds_are_inclusive():
    P = A.Perishable(A.Settings(m=3, lead=0, rule="LIFO", w=10.0, T=8, dmax=12))
    for level in (0, 4, 8):                                    # S = 0 und S = T gehören dazu
        assert np.array_equal(R.age_policy(P, level, 0.0), P.base_stock(level))
    assert R.age_policy(P, 8, -2.0).min() >= 0              # nie negative Bestellung
    assert R.BETAS[0] == -2.0 and R.BETAS[-1] == 1.0 and len(R.BETAS) == 13


def test_age_rule_rounds_halves_up():
    P = A.Perishable(A.Settings(m=3, lead=0, rule="LIFO", T=6, dmax=8))
    tgt = R.age_target(P, 4, -0.5)
    s = int(P.index(np.array([[1, 0]]))[0])                    # z1 = 1: 4 - 0,5 = 3,5 -> 4
    assert tgt[s] == 4
    s2 = int(P.index(np.array([[3, 0]]))[0])                   # z1 = 3: 4 - 1,5 = 2,5 -> 3
    assert tgt[s2] == 3


def test_target_table_marks_ambiguous_keys():
    P = A.Perishable(A.Settings(m=4, lead=0, rule="LIFO", w=10.0, T=6, dmax=10))
    g, pol, _, _, _ = P.solve()
    _, pi = P.evaluate(pol)
    table = R.target_table(P, pol, pi, min_mass=1e-6)
    assert table and all(isinstance(v[1], bool) for v in table.values())
    ae = P.eff(pol)
    for (tot, z1), (target, unique) in table.items():
        states = np.flatnonzero((P.tot == tot) & (P.z1 == z1) & (pi > 1e-6))
        targets = {int(P.tot[s] + ae[s]) for s in states}
        assert (len(targets) == 1) == unique and target in targets
