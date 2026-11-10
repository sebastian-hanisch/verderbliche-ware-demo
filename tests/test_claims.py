"""Jede Zahl der README an den vorgerechneten Zellen (data/vdw_grid.json) und, wo es billig ist, an einer Neuberechnung.

Alle Zahlen gelten für: ein Artikel, Poisson-Nachfrage mit Mittel 3 (bei 16 gekappt), h = 1 je übertragenem Stück, p = 9 je fehlendem Stück,
keine Bestellkosten, verlorene Nachfrage, Bestandsgrenze T = 12 (Strafverhältnis-Raster: T = 14), feste Haltbarkeit m, exakte relative Wertiteration.
Die Zählungen (k von n Zellen) stehen mit ihrer Gesamtzahl in der README; Ausnahmen stehen im selben Satz.
Zuordnung README-Zeile -> Test: Tabelle „Zahl → Test“ in der README."""

import re
from pathlib import Path

import pytest

import vdw_algorithm as A
import vdw_constants as C
import vdw_evaluation as ev
import vdw_grid as G
import vdw_rules as R

README = Path(__file__).resolve().parent.parent / "README.md"
W = G.W_VALUES


def mc(lead, rule, w, m):
    return G.load()[(lead, rule, float(w), 9.0, m, 12)]


def gap(lead, rule, w, m):
    return mc(lead, rule, w, m)["gap_bs"]


def main_cells(lead=None, rule=None):
    return [c for k, c in G.load().items() if k[3] == 9.0 and k[5] == 12 and (lead is None or k[0] == lead) and (rule is None or k[1] == rule)]


# ------------------------------------------------------------------------------------------------------------------------------ K1, K2
def test_k1_lead0_fifo_base_stock_is_exact_in_26_of_30_cells_with_four_exceptions():
    cells = main_cells(0, "FIFO")
    assert len(cells) == 30
    exact = [c for c in cells if ev.is_exact(c)]
    assert len(exact) == 26
    exceptions = {(c["m"], c["w"]): round(c["gap_bs"], 2) for c in cells if not ev.is_exact(c)}
    assert exceptions == {(2, 0.0): 1.25, (2, 10.0): 0.36, (2, 30.0): 1.36, (3, 30.0): 1.01}
    assert all(c["qgap_max"] == 0.0 for c in exact)                      # Q-Abstand 0: dieselbe Bestellung auf allen erreichten Zuständen


def test_k2_lead0_lifo_gaps_by_w():
    cells = main_cells(0, "LIFO")
    assert len(cells) == 30
    assert sum(ev.is_exact(c) for c in cells if c["w"] == 1.0) == 6                                  # w = h: 6 von 6 exakt
    w3 = [round(gap(0, "LIFO", 3.0, m), 2) for m in range(2, 8)]
    assert w3 == [3.80, 1.50, 0.63, 0.26, 0.11, 0.05]                                                # fällt mit der Haltbarkeit
    w10 = [gap(0, "LIFO", 10.0, m) for m in range(2, 8)]
    w30 = [gap(0, "LIFO", 30.0, m) for m in range(2, 8)]
    assert (round(min(w10), 2), round(max(w10), 2)) == (6.15, 9.61)                                  # bei w = 10 und 30 nicht
    assert (round(min(w30), 2), round(max(w30), 2)) == (11.86, 26.69)
    assert w10 != sorted(w10, reverse=True) and w30 != sorted(w30, reverse=True)
    ge3 = [c["gap_bs"] for c in cells if c["w"] >= 3.0]
    assert len(ge3) == 18 and (round(min(ge3), 2), round(max(ge3), 2)) == (0.05, 26.69)


def test_k3_lead0_w_zero_lifo_gaps_are_small_but_not_zero():
    g = [round(gap(0, "LIFO", 0.0, m), 2) for m in range(2, 8)]
    assert g == [1.37, 0.30, 0.55, 0.95, 0.72, 0.37]


# ------------------------------------------------------------------------------------------------------------------------------ K4: Ablaufmenge
def test_k4_expected_waste_at_base_stock_5_fifo_against_lifo():
    waste = {}
    for m in (2, 3, 4, 5):
        for rule in ("FIFO", "LIFO"):
            P = A.Perishable(A.Settings(m=m, lead=0, rule=rule, w=1.0, T=12, dmax=16))
            waste[(m, rule)] = P.components(P.base_stock(5))["waste"]
    assert [round(waste[(m, "FIFO")], 4) for m in (2, 3, 4, 5)] == [0.3446, 0.0566, 0.0076, 0.0009]
    assert [round(waste[(m, "LIFO")], 3) for m in (2, 3, 4, 5)] == [0.832, 0.441, 0.267, 0.174]


# ------------------------------------------------------------------------------------------------------------------------------ K5: Altersregel
def test_k5_age_rule_closes_93_to_98_percent_at_w3_lead0_and_80_to_82_at_lead1():
    s0 = [ev.share_closed(mc(0, "LIFO", 3.0, m)) for m in (3, 4, 5)]
    assert [round(x) for x in s0] == [98, 95, 93]
    s1 = [ev.share_closed(mc(1, "LIFO", 3.0, m)) for m in (3, 4)]
    assert [round(x) for x in s1] == [82, 80]
    assert [round(mc(0, "LIFO", 3.0, m)["gap_age"], 2) for m in (3, 4, 5)] == [0.04, 0.03, 0.02]


def test_k5b_age_rule_closes_13_to_76_percent_at_w_10_and_30():
    cells = [mc(0, "LIFO", w, m) for w in (10.0, 30.0) for m in (3, 4, 5)] + [mc(1, "LIFO", w, m) for w in (10.0, 30.0) for m in (3, 4)]
    assert len(cells) == 10
    shares = [ev.share_closed(c) for c in cells]
    assert (round(min(shares)), round(max(shares))) == (13, 76)
    assert min(range(10), key=lambda i: shares[i]) == 9 and cells[9]["lead"] == 1 and cells[9]["w"] == 30.0 and cells[9]["m"] == 4
    assert [round(c["gap_age"], 2) for c in cells[:6]] == [2.25, 4.70, 3.70, 5.47, 6.32, 7.21]


def test_k5c_age_rule_closes_everything_only_at_shelf_life_2_lead0_never_for_m_3_to_5():
    for w in (3.0, 10.0, 30.0):
        assert mc(0, "LIFO", w, 2)["gap_age"] < 0.005                                               # Haltbarkeit 2: Lücke vollständig geschlossen
        assert ev.share_closed(mc(0, "LIFO", w, 2)) == pytest.approx(100.0)
    rest = [mc(0, "LIFO", w, m)["gap_age"] for w in (3.0, 10.0, 30.0) for m in (3, 4, 5)] + [mc(1, "LIFO", w, m)["gap_age"] for w in (3.0, 10.0, 30.0) for m in (3, 4)]
    assert len(rest) == 15 and (round(min(rest), 2), round(max(rest), 2)) == (0.02, 7.21)           # in 15 von 15 Zellen bleibt eine Rest-Lücke


def test_k5d_sign_of_beta_flips_between_lead_times():
    l0 = [mc(0, "LIFO", w, m)["age_beta"] for w in (3.0, 10.0, 30.0) for m in (2, 3, 4, 5)]
    l1 = [mc(1, "LIFO", w, m)["age_beta"] for w in (3.0, 10.0, 30.0) for m in (2, 3, 4)]
    assert len(l0) == 12 and all(b < 0 for b in l0)
    assert len(l1) == 9 and all(b > 0 for b in l1)
    assert [mc(0, "LIFO", 30.0, m)["age_beta"] for m in (3, 4, 5)] == [-2.0, -2.0, -2.0]               # Rand des Rasters bei w = 30
    assert min(l0) == -2.0


def test_k5e_base_stock_on_stock_without_oldest_class_hurts_with_fifo_at_lead1():
    cells = [c for c in main_cells(1, "FIFO") if "gap_age" in c]
    assert len(cells) == 15
    assert all(c["gap_without_oldest"] > c["gap_bs"] for c in cells)                                 # 15 von 15 schlechter als der Base-Stock


# ------------------------------------------------------------------------------------------------------------------------------ K6: Tabellen
def test_k6_table_by_total_alone():
    lifo0 = [c["gap_tab_total"] for c in main_cells(0, "LIFO") if "gap_tab_total" in c]
    lifo1 = [c["gap_tab_total"] for c in main_cells(1, "LIFO") if "gap_tab_total" in c]
    assert len(lifo0) == 20 and round(max(lifo0), 2) == 10.96
    assert len(lifo1) == 15 and round(max(lifo1), 2) == 5.88
    fifo1 = [c["gap_tab_total"] for c in main_cells(1, "FIFO") if "gap_tab_total" in c]
    assert len(fifo1) == 15 and round(max(fifo1), 2) == 0.42                                          # Lieferzeit 1, FIFO, Haltbarkeit 2 bis 4
    fifo0 = [c["gap_tab_total"] for c in main_cells(0, "FIFO") if "gap_tab_total" in c]
    assert len(fifo0) == 20 and max(fifo0) < 0.015
    assert round(mc(0, "LIFO", 10.0, 4)["gap_tab_total"], 2) == 2.60 and round(mc(0, "LIFO", 10.0, 4)["gap_age"], 2) == 4.70   # Tabelle besser als Altersregel
    assert round(mc(0, "LIFO", 10.0, 5)["gap_tab_total"], 2) == 3.28 and round(mc(0, "LIFO", 10.0, 5)["gap_age"], 2) == 3.70


def test_k6b_table_by_total_and_oldest_class():
    z3 = [mc(lead, "LIFO", 3.0, m)["gap_tab_total_z1"] for lead in (0, 1) for m in (2, 3, 4)]
    assert len(z3) == 6 and round(max(z3), 2) == 0.03 and max(z3) < 0.04                            # höchstens +0,04 % (gerundet +0,03 %)
    z10_0 = [mc(0, "LIFO", 10.0, m)["gap_tab_total_z1"] for m in (2, 3, 4)]
    z10_1 = [mc(1, "LIFO", 10.0, m)["gap_tab_total_z1"] for m in (2, 3, 4)]
    assert round(max(z10_0), 2) == 0.48 and round(max(z10_1), 2) == 1.65
    both = [c["gap_tab_total_z1"] for c in main_cells() if "gap_tab_total_z1" in c]
    assert len(both) == 24                                                                           # 2 Lieferzeiten x 2 Regeln x 2 w x 3 Haltbarkeiten


# ------------------------------------------------------------------------------------------------------------------------------ K7: Lieferzeit 1
def test_k7_lead1_fifo_gap_is_mostly_the_lead_time_effect():
    cells = main_cells(1, "FIFO")
    assert len(cells) == 25
    g = [c["gap_bs"] for c in cells]
    assert (round(min(g), 2), round(max(g), 2)) == (1.36, 9.18)
    assert [round(gap(1, "FIFO", w, 6), 2) for w in W] == [1.74, 1.75, 1.75, 1.78, 1.86]         # lange Haltbarkeit: gegen die Referenz ohne Verfall (Orakel O7)
    assert sum(ev.is_exact(c) for c in cells) == 0


def test_k7b_lifo_lead1_gaps_reach_58_percent_at_w0_and_short_shelf_life():
    cells = main_cells(1, "LIFO")
    assert len(cells) == 25 and round(max(c["gap_bs"] for c in cells), 2) == 57.98
    assert [round(gap(1, "LIFO", 3.0, m), 2) for m in range(2, 7)] == [24.16, 10.93, 8.05, 5.73, 4.53]


# ------------------------------------------------------------------------------------------------------------------------------ K8: Ausgaberegel
def test_k8_rule_matters_more_than_the_order_rule():
    ratios = [100 * (mc(lead, "LIFO", w, m)["g"] / mc(lead, "FIFO", w, m)["g"] - 1) for lead in (0, 1) for w in (3.0, 10.0, 30.0) for m in range(2, C.GRID_M_MAX[lead] + 1)]
    assert len(ratios) == 33 and (round(min(ratios), 2), round(max(ratios), 2)) == (5.05, 74.14)
    w1 = [abs(mc(0, "LIFO", 1.0, m)["g"] - mc(0, "FIFO", 1.0, m)["g"]) for m in range(2, 8)]
    assert max(w1) < 1e-8                                                                            # w = h, Lieferzeit 0: kostengleich in 6 von 6
    w1_l1 = [100 * (mc(1, "LIFO", 1.0, m)["g"] / mc(1, "FIFO", 1.0, m)["g"] - 1) for m in range(2, 7)]
    assert [round(x, 2) for x in w1_l1] == [0.64, -2.15, -2.41, -1.96, -1.48]                        # Lieferzeit 1: bei w = h nicht gleich


def test_k8b_w_zero_lifo_is_cheaper_by_construction_of_the_cost_convention():
    l0 = [100 * (mc(0, "LIFO", 0.0, m)["g"] / mc(0, "FIFO", 0.0, m)["g"] - 1) for m in range(2, 8)]
    l1 = [100 * (mc(1, "LIFO", 0.0, m)["g"] / mc(1, "FIFO", 0.0, m)["g"] - 1) for m in range(2, 7)]
    assert (round(min(l0), 2), round(max(l0), 2)) == (-24.37, -2.91)
    assert (round(min(l1), 2), round(max(l1), 2)) == (-25.57, -7.76)


# ------------------------------------------------------------------------------------------------------------------------------ K9: Zustandsraum
def test_k9_state_counts():
    assert [mc(0, "LIFO", 3.0, m)["states"] for m in range(2, 8)] == [13, 91, 455, 1820, 6188, 18564]
    assert [mc(0, "LIFO", 3.0, m)["box"] for m in range(2, 8)] == [13, 169, 2197, 28561, 371293, 4826809]
    for rule in ("FIFO", "LIFO"):
        assert [mc(0, rule, 3.0, m)["reach_dp"] for m in range(2, 8)] == [6, 21, 56, 126, 252, 462]
    assert [mc(1, "FIFO", 3.0, m)["states"] for m in range(2, 7)] == [91, 455, 1820, 6188, 18564]
    assert [mc(1, "FIFO", 3.0, m)["reach_dp"] for m in range(2, 7)] == [20, 107, 463, 1535, 4058]
    assert [mc(1, "LIFO", 3.0, m)["reach_dp"] for m in range(2, 7)] == [9, 91, 245, 1006, 2407]
    assert all(mc(0, "LIFO", 3.0, m)["reach_any"] == mc(0, "LIFO", 3.0, m)["states"] for m in range(2, 8))   # bei beliebiger Bestellung alle


# ------------------------------------------------------------------------------------------------------------------------------ K10: Bestandsgrenze
def test_k10_boundary_mass_zero_for_the_exact_policy_and_one_exception_for_base_stock():
    cells = main_cells()
    assert len(cells) == 110
    assert all(max(c["edge_order_dp"], c["edge_stock_dp"]) < 1e-4 for c in cells)                     # exakte Politik: Randmasse unter 1e-4 in 110 von 110
    flagged = [c for c in cells if max(c["edge_order_bs"], c["edge_stock_bs"]) > 1e-4 or c["S_bs"] >= c["T"]]
    assert [(c["lead"], c["rule"], c["w"], c["m"]) for c in flagged] == [(1, "LIFO", 0.0, 2)]
    pg = [c for k, c in G.load().items() if k[5] == 14]
    assert len(pg) == 72 and not [c for c in pg if max(c["edge_order_dp"], c["edge_stock_dp"], c["edge_order_bs"], c["edge_stock_bs"]) > 1e-4 or c["S_bs"] >= 14]


def test_k10b_the_one_exception_is_identical_with_limit_16_and_20():
    out = []
    for T in (12, 16, 20):
        P = A.Perishable(A.Settings(m=2, lead=1, rule="LIFO", w=0.0, T=T, dmax=16))
        g = P.solve()[0]
        gb, level, _ = P.best_base_stock()
        out.append((round(100 * (gb / g - 1), 2), level))
    assert out == [(57.98, 12)] * 3


def test_k10c_poisson_tail_above_16_is_2e_8():
    pmf = A.poisson_pmf(3.0, 16)
    from math import exp, factorial
    tail = 1.0 - sum(exp(-3.0) * 3.0**k / factorial(k) for k in range(17))
    assert 2.0e-8 < tail < 2.4e-8 and pmf[-1] > exp(-3.0) * 3.0**16 / factorial(16)


# ------------------------------------------------------------------------------------------------------------------------------ K11: Strafverhältnis
def test_k11_penalty_ratio_grid():
    g = {}
    for p in C.P_CHOICES:
        for lead in (0, 1):
            for rule in ("FIFO", "LIFO"):
                cells = [c for k, c in G.load().items() if k[5] == 14 and k[3] == p and k[0] == lead and k[1] == rule]
                assert len(cells) == 6
                g[(p, lead, rule)] = (round(max(c["gap_bs"] for c in cells), 2), round(max(c["gap_tab_total"] for c in cells), 2))
    assert [g[(p, 0, "FIFO")][0] for p in (4.0, 9.0, 19.0)] == [0.79, 0.36, 0.26]
    assert [g[(p, 0, "LIFO")][0] for p in (4.0, 9.0, 19.0)] == [12.91, 9.61, 6.44]
    assert [g[(p, 1, "FIFO")][0] for p in (4.0, 9.0, 19.0)] == [7.75, 6.69, 7.93]
    assert [g[(p, 1, "FIFO")][1] for p in (4.0, 9.0, 19.0)] == [0.05, 0.42, 0.42]
    assert [g[(p, 1, "LIFO")][0] for p in (4.0, 9.0, 19.0)] == [15.13, 24.16, 37.66]
    # die 24 Zellen mit p = 9 und Grenze 14 reproduzieren die Werte mit Grenze 12
    for k, c in G.load().items():
        if k[3] == 9.0 and k[5] == 14:
            assert c["gap_bs"] == pytest.approx(G.load()[(k[0], k[1], k[2], 9.0, k[4], 12)]["gap_bs"], abs=1e-6)


# ------------------------------------------------------------------------------------------------------------------------------ K12: Beschreibung der DP
def test_k12_dp_target_levels():
    live = ev.solve_live(0, "LIFO", 10.0, 3)
    tab = R.target_table(live.P, live.pol, live.pi)
    assert tab[(0, 0)][0] == 5                                                                       # leeres Lager: Ziel 5
    assert [tab[(t, 0)][0] for t in (1, 2, 3, 4)] == [4, 4, 4, 4]                                     # ohne älteste Klasse: Ziel 4
    assert [tab[(t, z1)][0] for t in (1, 2, 3) for z1 in range(1, t + 1)] == [3] * 6                # mit älterer Ware und Bestand bis 3: Ziel 3
    assert [tab[(4, z1)][0] for z1 in (1, 2, 3, 4)] == [4, 4, 4, 4]                                   # Ausnahme Gesamtbestand 4
    live1 = ev.solve_live(1, "LIFO", 3.0, 3)
    tab1 = R.target_table(live1.P, live1.pol, live1.pi)
    assert [tab1[(8, z1)][0] for z1 in (0, 1, 2, 3)] == [8, 9, 10, 11]                                # Lieferzeit 1: Ziel wächst um etwa 1 je Einheit z1


# ------------------------------------------------------------------------------------------------------------------------------ K13: Rechnung
def test_k13_lazy_chain_is_needed_for_lead1_lifo_shelf_life_2():
    P = A.Perishable(A.Settings(m=2, lead=1, rule="LIFO", w=3.0, T=12, dmax=16))
    g, _, _, it, cert = P.solve()
    assert cert < 1e-10 and it < 100
    g1, _, _, it1, cert1 = P.solve(tau=1.0, maxit=2000)
    assert it1 == 1999 and cert1 > 0.1                                                               # ohne träge Kette keine Konvergenz nach 2.000 Iterationen
    assert round(100 * (P.best_base_stock()[0] / g - 1), 2) == 24.16


def test_k13b_certificates_are_below_1e_10_in_all_cells():
    assert all(c["cert"] < 1e-10 for c in G.load().values())


# ------------------------------------------------------------------------------------------------------------------------------ README
def _readme() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_assumptions_text_is_the_apps_text():
    assert C.ASSUMPTIONS_MARKDOWN.strip() in _readme()


def test_readme_test_table_names_existing_tests():
    """Jeder in der README genannte Test existiert (in irgendeiner Testdatei), und jeder Test dieser Datei steht in der README."""
    names = set(re.findall(r"`(test_[a-z0-9_]+)`", _readme()))
    folder = Path(__file__).resolve().parent
    everywhere = set()
    for f in folder.glob("test_*.py"):
        everywhere |= set(re.findall(r"^def (test_[a-z0-9_]+)", f.read_text(encoding="utf-8"), re.M))
    mine = set(re.findall(r"^def (test_[a-z0-9_]+)", Path(__file__).read_text(encoding="utf-8"), re.M))
    assert names and names <= everywhere, sorted(names - everywhere)
    assert mine <= names, sorted(mine - names)
