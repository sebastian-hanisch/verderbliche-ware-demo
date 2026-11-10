"""Einheiten des Kerns gegen Handrechnung (Handbeispiel, Brüche) und einfache Eigenschaften.

Handrechnung (Haltbarkeit 2, Lieferzeit 0, Nachfrage 0 / 1 / 2 mit 1/4, 1/2, 1/4, h = 1, p = 9, w = 5, Grenze 2):
  z = 1, a = 1, FIFO: d = 0: altes läuft ab, frisches wird übertragen: 5 + 1 = 6, z' = 1; d = 1: altes verkauft, frisches übertragen: 1, z' = 1;
                      d = 2: beide verkauft: 0, z' = 0. Erwartung 6/4 + 1/2 = 2, Übergänge 1 -> 1 (3/4), 0 (1/4).
  z = 1, a = 1, LIFO: d = 0: 6, z' = 1; d = 1: frisches verkauft, altes läuft ab: 5, z' = 0; d = 2: 0. Erwartung 6/4 + 5/2 = 4, Übergänge 1 -> 1 (1/4), 0 (3/4).
  Stationär, Base-Stock S = 2: FIFO g = 25/13, LIFO g = 59/23; Politik (2, 0, 0): g = 16/7."""

from fractions import Fraction as F
from math import comb

import numpy as np
import pytest

import vdw_algorithm as A
import vdw_hand as H
from conftest import hand_settings


def test_issue_fifo_and_lifo_take_different_classes():
    units = np.array([[1], [2]])            # ein altes (Klasse 1) und zwei frische (Klasse 2) Stück
    assert A.issue(units, 1, "FIFO").ravel().tolist() == [0, 2]
    assert A.issue(units, 1, "LIFO").ravel().tolist() == [1, 1]
    assert A.issue(units, 5, "FIFO").ravel().tolist() == [0, 0]       # Nachfrage über dem Bestand: alles verkauft
    assert A.issue(units, 0, "LIFO").ravel().tolist() == [1, 2]


def test_state_counts():
    assert A.n_states(1, 2) == 3 == len(A.compositions(1, 2))
    assert A.n_states(2, 12) == 91 == comb(14, 2)
    assert A.n_states(4, 12) == 1820
    assert A.box_states(4, 12) == 13**4 == 28561
    assert A.compositions(2, 2).tolist() == [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [2, 0]]


def test_poisson_pmf_sums_to_one_and_has_the_right_mean_shape():
    pmf = A.poisson_pmf(3.0, 16)
    assert pmf.sum() == pytest.approx(1.0, abs=1e-15)
    assert pmf[0] == pytest.approx(np.exp(-3.0)) and pmf[1] == pytest.approx(3 * np.exp(-3.0))


@pytest.mark.parametrize("rule, to_one, to_zero, cost", [("FIFO", 0.75, 0.25, 2.0), ("LIFO", 0.25, 0.75, 4.0)])
def test_one_period_from_state_one_with_order_one(rule, to_one, to_zero, cost):
    P = A.Perishable(hand_settings(rule))
    s = int(P.index(np.array([[1]]))[0])
    row = P.P[1][s].toarray().ravel()
    s_one, s_zero = int(P.index(np.array([[1]]))[0]), int(P.index(np.array([[0]]))[0])
    assert row[s_one] == pytest.approx(to_one) and row[s_zero] == pytest.approx(to_zero)
    assert P.cost[s, 1] == pytest.approx(cost)


def test_hand_step_function_matches_the_worked_cases():
    assert H.step(1, 1, 1, "FIFO")[:2] == (1, 1)         # (Folgezustand, Kosten)
    assert H.step(1, 1, 1, "LIFO")[:2] == (0, 5)
    assert H.step(2, 0, 0, "FIFO")[:2] == (0, 10)        # beide alten Stück laufen ab
    assert H.step(1, 0, 2, "LIFO")[:2] == (0, 9)         # ein Stück fehlt
    assert H.step(0, 2, 0, "LIFO")[:2] == (2, 2)


def test_hand_exact_fractions():
    assert H.evaluate([2, 1, 0], "FIFO")[0] == F(25, 13)
    assert H.evaluate([2, 1, 0], "LIFO")[0] == F(59, 23)
    assert H.evaluate([2, 0, 0], "FIFO")[0] == F(16, 7)
    assert H.evaluate([2, 0, 0], "LIFO")[0] == F(16, 7)
    assert H.evaluate([2, 1, 0], "FIFO")[1] == [F(4, 13), F(8, 13), F(1, 13)]
    assert H.evaluate([2, 1, 0], "LIFO")[1] == [F(12, 23), F(8, 23), F(3, 23)]
    s = H.summary("LIFO")
    assert s["opt_policy"] == (2, 0, 0) and s["opt_cost"] == F(16, 7) and s["bs_cost"] == F(59, 23)
    assert s["gap"] == F(59, 23) / F(16, 7) - 1 == F(413, 368) - 1
    f = H.summary("FIFO")
    assert f["opt_policy"] == (2, 1, 0) and f["gap"] == 0


@pytest.mark.parametrize("rule, pol, exact", [("FIFO", (2, 1, 0), 25 / 13), ("LIFO", (2, 1, 0), 59 / 23), ("LIFO", (2, 0, 0), 16 / 7)])
def test_core_evaluate_matches_hand_fractions(rule, pol, exact):
    P = A.Perishable(hand_settings(rule))
    g, pi = P.evaluate(np.array(pol))
    assert g == pytest.approx(exact, abs=1e-12)
    assert pi.sum() == pytest.approx(1.0)


def test_core_solve_finds_the_hand_optimum_with_a_certificate():
    for rule, exact, pol in (("FIFO", 25 / 13, (2, 1, 0)), ("LIFO", 16 / 7, (2, 0, 0))):
        P = A.Perishable(hand_settings(rule))
        g, best, _, _, cert = P.solve()
        assert g == pytest.approx(exact, abs=1e-9) and cert < 1e-9
        assert tuple(int(x) for x in P.eff(best)) == pol
        assert P.evaluate(best)[0] == pytest.approx(exact, abs=1e-12)


def test_best_base_stock_of_the_hand_example():
    assert A.Perishable(hand_settings("LIFO")).best_base_stock()[:2] == (pytest.approx(59 / 23), 2)
    assert A.Perishable(hand_settings("FIFO")).best_base_stock()[1] == 2


def test_cost_components_add_up_and_waste_matches_hand():
    P = A.Perishable(hand_settings("LIFO"))
    pol = np.array([2, 1, 0])
    g, pi = P.evaluate(pol)
    c = P.components(pol, pi)
    assert 1.0 * c["carry"] + 9.0 * c["lost"] + 5.0 * c["waste"] == pytest.approx(g)
    # Handrechnung: pi = (12, 8, 3)/23; Ablauf nur aus z = 1 (d = 1: 1 Stück, d = 0: 1 Stück) und z = 2 (d = 0: 2, d = 1: 1)
    waste_by_state = [0.0, 1 / 4 + 1 / 2, 2 * (1 / 4) + 1 * (1 / 2)]
    assert c["waste"] == pytest.approx(sum(pi_z * wz for pi_z, wz in zip([12 / 23, 8 / 23, 3 / 23], waste_by_state)))


def test_dp_is_never_worse_than_any_fixed_policy_and_costs_grow_in_w():
    prev = 0.0
    for w in (0.0, 1.0, 3.0, 10.0):
        P = A.Perishable(A.Settings(m=3, lead=0, rule="LIFO", w=w, T=8, dmax=12))
        g = P.solve()[0]
        assert g >= prev - 1e-9
        prev = g
        for level in range(0, 9):
            assert P.evaluate(P.base_stock(level))[0] >= g - 1e-8


def test_reachable_states_are_a_subset_and_start_empty():
    P = A.Perishable(A.Settings(m=3, lead=0, rule="FIFO", w=3.0, T=6, dmax=10))
    reach = P.reachable(P.base_stock(4))
    assert P.empty in reach and len(reach) <= P.S
    assert P.reach_any_order() <= P.S


def test_settings_are_keyword_only_and_validated():
    with pytest.raises(TypeError):
        A.Settings(2, 0)       # nie positional
    for bad in (dict(m=1), dict(lead=2), dict(rule="LILO"), dict(T=0)):
        with pytest.raises(ValueError):
            A.Settings(**bad)
    assert A.Settings(m=4, lead=0).k == 3 and A.Settings(m=4, lead=1).k == 4
