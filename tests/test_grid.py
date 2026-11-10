"""Vorgerechnete Datei `data/vdw_grid.json`: Aufbau, innere Widerspruchsfreiheit, und die kleinen Zellen werden neu gerechnet und verglichen
(sonst könnte die Datei zu einem älteren Stand des Kerns gehören)."""

import math

import pytest

import vdw_algorithm as A
import vdw_evaluation as ev
import vdw_grid as G

FIELDS_ALWAYS = {"lead", "rule", "w", "p", "m", "T", "depth", "states", "box", "reach_any", "reach_dp", "reach_bs", "g", "cert", "g_bs", "S_bs",
                 "gap_bs", "qgap_max", "edge_order_dp", "edge_stock_dp", "edge_order_bs", "edge_stock_bs", "amb_tot", "amb_tot_z1", "dp", "bs"}


def test_the_file_has_the_documented_cells_and_stays_small():
    cells = G.load()
    main = [c for k, c in cells.items() if k[3] == 9.0 and k[5] == 12]
    pgrid = [c for k, c in cells.items() if k[5] == 14]
    assert len(main) == 110 and len(pgrid) == 72 and len(cells) == 182
    assert G.DATA_FILE.stat().st_size < 1_000_000
    assert {(k[0], k[4]) for k in cells if k[3] == 9.0 and k[5] == 12} == {(0, m) for m in range(2, 8)} | {(1, m) for m in range(2, 7)}
    assert {(k[2], k[4]) for k in cells if k[5] == 14} == {(w, m) for w in (3.0, 10.0) for m in (2, 3, 4)}
    assert {k[3] for k in cells if k[5] == 14} == {4.0, 9.0, 19.0}


def test_every_cell_has_the_fields_of_its_depth():
    for key, c in G.load().items():
        assert FIELDS_ALWAYS <= set(c), key
        assert c["depth"] == G.depth_for(c["lead"], c["m"], c["w"], c["p"]) or c["T"] == 14
        if c["depth"] >= 1:
            assert {"gap_age", "age_S", "age_beta", "gap_without_oldest", "gap_tab_total"} <= set(c)
        else:
            assert "gap_age" not in c and "gap_tab_total" not in c
        assert ("gap_tab_total_z1" in c) == (c["depth"] >= 2)


def test_cells_are_internally_consistent():
    for key, c in G.load().items():
        k = c["m"] - 1 if c["lead"] == 0 else c["m"]
        assert c["states"] == math.comb(c["T"] + k, k) and c["box"] == (c["T"] + 1) ** k
        assert 1 <= c["reach_dp"] <= c["reach_any"] <= c["states"] and c["reach_bs"] <= c["states"]
        assert c["cert"] < 1e-9, key
        assert c["gap_bs"] > -1e-7, key                       # der beste Base-Stock ist nie billiger als die exakte Politik
        for part, g in (("dp", c["g"]), ("bs", c["g_bs"])):
            comp = c[part]
            assert comp["carry"] + c["p"] * comp["lost"] + c["w"] * comp["waste"] == pytest.approx(g, abs=1e-8), key
        if "gap_age" in c:
            assert c["gap_age"] <= c["gap_bs"] + 1e-7          # beta = 0 ist im Raster: die Altersregel ist nie schlechter als der Base-Stock
            assert c["gap_age"] > -1e-7 and c["gap_tab_total"] > -1e-6


def test_cost_terms_add_up_to_the_cost():
    for key, c in G.load().items():
        for part, g in (("dp", c["g"]), ("bs", c["g_bs"])):
            assert ev.cost_terms(c[part], c["p"], c["w"])["summe"] == pytest.approx(g, abs=1e-8), key


@pytest.mark.parametrize("lead,rule,w,p,m,T", [(0, "LIFO", 10.0, 9.0, 3, 12), (1, "FIFO", 3.0, 9.0, 2, 12), (1, "LIFO", 0.0, 9.0, 2, 12),
                                                (0, "FIFO", 30.0, 9.0, 3, 12), (0, "LIFO", 3.0, 4.0, 2, 14)])
def test_small_cells_recomputed_equal_the_stored_ones(lead, rule, w, p, m, T):
    stored = G.load()[(lead, rule, w, p, m, T)]
    fresh = G.compute_cell(lead, rule, w, p, m, T, stored["depth"])
    assert set(fresh) - {"seconds"} == set(stored) - {"seconds"}
    for key, value in stored.items():
        if key == "seconds":
            continue
        if isinstance(value, float):
            assert fresh[key] == pytest.approx(value, abs=1e-8, rel=1e-8), key
        elif isinstance(value, dict):
            assert fresh[key] == pytest.approx(value, abs=1e-8), key
        else:
            assert fresh[key] == value, key


def test_lookup_and_live_range():
    assert G.lookup(0, "FIFO", 3.0, 5)["states"] == 1820
    assert G.lookup(1, "FIFO", 3.0, 7) is None                      # Lieferzeit 1, Haltbarkeit 7: nicht gerechnet
    assert G.lookup(0, "LIFO", 0.0, 3, p=4.0) is None                 # Strafverhältnis 4 gibt es nur für w = 3 und 10 und Haltbarkeit 2 bis 4
    assert G.lookup(0, "LIFO", 10.0, 5, p=4.0) is None
    assert G.lookup(0, "LIFO", 10.0, 3, p=4.0)["T"] == 14             # und dann mit Bestandsgrenze 14
    assert G.is_live(0, 5) and not G.is_live(0, 6) and G.is_live(1, 4) and not G.is_live(1, 5)
    assert A.n_states(5 - 1, 12) == 1820 == A.n_states(4, 12)      # Lieferzeit 0, Haltbarkeit 5 und Lieferzeit 1, Haltbarkeit 4: je 1.820 Zustände
